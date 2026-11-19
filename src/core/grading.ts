import type { CanonicalTaskType, Dimension, Fact, FigureRegion } from '../types/content';
import type { GradeName } from '../types/memory';

export const EASY_LATENCY_MS = 3000;
/** No time pressure: latency is recorded for telemetry only and never affects grades. */
export const TIMEOUT_LATENCY_MS = Number.POSITIVE_INFINITY;
export const ANTI_COLLISION_LOG_FACTOR = 1.2;
export const MIN_LOG_ANCHOR_GAP_DECADES = 0.5;
export const DATE_TOLERANCE_FLOOR_YEARS = 2;

export interface PlacementGradeResult {
  error: number;
  signed_error: number;
  tolerance: number;
  grade: GradeName;
  band_low: number;
  band_high: number;
}

export function canonicalTaskTypeForDimension(scale: Dimension['scale']): CanonicalTaskType {
  switch (scale) {
    case 'log':
    case 'linear':
      return 'place';
    case 'date':
      return 'place_timeline';
    case 'geo':
      return 'occlude';
    case 'categorical':
      return 'recall';
  }
}

/**
 * Computes effective tolerance `t` in the dimension's error metric space:
 * - log: `log10(tolerance_factor)`, default factor 2 -> ~0.30103
 * - date: `max(2, abs(currentYear - truthYear) * tolerance)` (default 0.02 -> ±2% YBP, floor ±2 yr)
 * - linear: absolute tolerance in dimension units (or relative factor if tolerance_mode === 'factor')
 */
export function effectiveTolerance(
  dimension: Dimension,
  truth: number,
  currentYear = 2026
): number {
  if (dimension.scale === 'log') {
    const factor = dimension.tolerance > 1 ? dimension.tolerance : 2;
    return Math.log10(factor);
  }
  if (dimension.scale === 'date') {
    const pct = dimension.tolerance > 0 && dimension.tolerance < 1 ? dimension.tolerance : 0.02;
    const yearsBeforePresent = Math.abs(currentYear - truth);
    return Math.max(DATE_TOLERANCE_FLOOR_YEARS, yearsBeforePresent * pct);
  }
  if (dimension.tolerance_mode === 'factor' && dimension.tolerance > 1) {
    return Math.abs(truth) * (dimension.tolerance - 1);
  }
  return dimension.tolerance;
}

export function toleranceBand(
  dimension: Dimension,
  fact: Pick<Fact, 'value' | 'low' | 'high'>,
  currentYear = 2026
): { band_low: number; band_high: number; t: number } {
  const t = effectiveTolerance(dimension, fact.value, currentYear);
  if (dimension.scale === 'log') {
    const factor = Math.pow(10, t);
    return {
      band_low: Math.min(fact.low, fact.value / factor),
      band_high: Math.max(fact.high, fact.value * factor),
      t,
    };
  }
  return {
    band_low: Math.min(fact.low, fact.value - t),
    band_high: Math.max(fact.high, fact.value + t),
    t,
  };
}

/**
 * Pure placement grading function (Design Doc v0.1 §4):
 * - If answer inside [fact.low, fact.high], error = 0.
 * - Else e = |log10(answer / truth)| for log, |answer - truth| for linear/date.
 * - e <= t/2 -> Easy (latency never affects the grade)
 * - e <= t -> Good
 * - e <= 2*t -> Hard
 * - e > 2*t, or skip -> Again
 */
export function gradePlacement(params: {
  dimension: Dimension;
  fact: Pick<Fact, 'value' | 'low' | 'high'>;
  answer: number | null;
  latencyMs: number;
  skipped?: boolean;
  currentYear?: number;
}): PlacementGradeResult {
  const { dimension, fact, answer, latencyMs, skipped = false, currentYear = 2026 } = params;
  const { band_low, band_high, t } = toleranceBand(dimension, fact, currentYear);

  const isTimeout = latencyMs >= TIMEOUT_LATENCY_MS;
  if (skipped || isTimeout || answer === null || !Number.isFinite(answer)) {
    return {
      error: Infinity,
      signed_error: 0,
      tolerance: t,
      grade: 'Again',
      band_low,
      band_high,
    };
  }

  if (dimension.scale === 'log' && answer <= 0) {
    return {
      error: Infinity,
      signed_error: -Infinity,
      tolerance: t,
      grade: 'Again',
      band_low,
      band_high,
    };
  }

  let signedError = 0;
  let error = 0;
  if (answer >= fact.low && answer <= fact.high) {
    signedError = 0;
    error = 0;
  } else if (dimension.scale === 'log') {
    signedError = Math.log10(answer / fact.value);
    error = Math.abs(signedError);
  } else {
    signedError = answer - fact.value;
    error = Math.abs(signedError);
  }

  const eps = 1e-12;
  let grade: GradeName;
  if (error <= t / 2 + eps) {
    grade = 'Easy';
  } else if (error <= t + eps) {
    grade = 'Good';
  } else if (error <= 2 * t + eps) {
    grade = 'Hard';
  } else {
    grade = 'Again';
  }

  return {
    error,
    signed_error: signedError,
    tolerance: t,
    grade,
    band_low,
    band_high,
  };
}

/**
 * Pure occlusion grading function (Design Doc v0.1 §4):
 * Exact target region -> Good; adjacent region -> Hard; anything else / timeout / skip -> Again.
 */
export function gradeOcclusion(params: {
  targetRegion: FigureRegion;
  selectedRegionId: string | null;
  latencyMs: number;
  skipped?: boolean;
}): { grade: GradeName; error: number } {
  const { targetRegion, selectedRegionId, latencyMs, skipped = false } = params;
  if (skipped || latencyMs >= TIMEOUT_LATENCY_MS || !selectedRegionId) {
    return { grade: 'Again', error: 1 };
  }
  if (selectedRegionId === targetRegion.region_id) {
    return { grade: 'Good', error: 0 };
  }
  if ((targetRegion.adjacent_ids ?? []).includes(selectedRegionId)) {
    return { grade: 'Hard', error: 0.5 };
  }
  return { grade: 'Again', error: 1 };
}

/**
 * Pure ratio probe evaluator (unscored detector):
 * Checks if user's estimated ratio A/B is within dimension tolerance factor (default 2x).
 */
export function evaluateRatioProbe(params: {
  truthA: number;
  truthB: number;
  guessedRatio: number;
  toleranceFactor?: number;
}): { hit: boolean; trueRatio: number; logError: number; signedError: number } {
  const { truthA, truthB, guessedRatio, toleranceFactor = 2 } = params;
  const trueRatio = truthA / truthB;
  const signedError = Math.log10(guessedRatio / trueRatio);
  const logError = Math.abs(signedError);
  const hit = logError <= Math.log10(toleranceFactor) + 1e-12;
  return { hit, trueRatio, logError, signedError };
}

/**
 * Anti-collision rule (#5): two entities within 1.2x on the same log dimension
 * cannot serve as anchors for each other or pair in a ratio probe.
 */
export function isLogCollision(valueA: number, valueB: number): boolean {
  if (valueA <= 0 || valueB <= 0) return true;
  const ratio = Math.max(valueA / valueB, valueB / valueA);
  return ratio <= ANTI_COLLISION_LOG_FACTOR;
}

export interface RulerAnchor {
  entity_id: string;
  name: string;
  value: number;
}

export interface RulerConfig {
  min: number;
  max: number;
  anchors: RulerAnchor[];
  ticks: number[];
}

/** Log rulers show a fixed window this many decades wide (Good band ~15% of the ruler). */
export const LOG_WINDOW_DECADES = 4;
/** Linear/date rulers show a window this many tolerances wide (Good band ~14% of the ruler). */
export const LINEAR_WINDOW_TOLERANCES = 14;

/**
 * Builds a ZOOMED ruler around the target instead of spanning the whole dimension
 * (atom to universe made every tolerance band a few pixels wide):
 * - Window is LOG_WINDOW_DECADES (log) or LINEAR_WINDOW_TOLERANCES x t (linear/date) wide,
 *   always containing the fact's [low, high] band.
 * - Truth sits at a random 25-75% position so the window itself does not leak the answer.
 * - Up to 3 anchors from inside the window: never the target, never within 1.2x (log),
 *   never closer than 0.5 decades / 2t to truth, spaced apart from each other.
 */
export function selectRulerConfig(params: {
  dimension: Dimension;
  targetFact: Fact;
  candidateAnchors: RulerAnchor[];
  allDimensionFacts: Fact[];
  currentYear?: number;
  rand?: () => number;
}): RulerConfig {
  const { dimension, targetFact, candidateAnchors, allDimensionFacts, currentYear = 2026, rand = Math.random } = params;
  const truth = targetFact.value;
  const offset = 0.25 + 0.5 * rand();

  const eligible = candidateAnchors
    .filter((a) => a.entity_id !== targetFact.entity_id)
    .filter((a) => (dimension.scale === 'log' ? a.value > 0 && !isLogCollision(a.value, truth) : a.value !== truth));

  const pickAnchors = (
    inWindow: RulerAnchor[],
    dist: (a: number, b: number) => number,
    minFromTruth: number,
    minApart: number
  ): RulerAnchor[] => {
    const pool = inWindow.filter((a) => dist(a.value, truth) >= minFromTruth);
    const below = pool.filter((a) => a.value < truth).sort((x, y) => y.value - x.value);
    const above = pool.filter((a) => a.value > truth).sort((x, y) => x.value - y.value);
    const chosen: RulerAnchor[] = [];
    const tryAdd = (c: RulerAnchor | undefined) => {
      if (!c || chosen.length >= 3) return;
      if (chosen.some((x) => x.entity_id === c.entity_id)) return;
      if (chosen.every((x) => dist(x.value, c.value) >= minApart)) chosen.push(c);
    };
    tryAdd(below[0]);
    tryAdd(above[0]);
    for (const c of [...below.slice(1), ...above.slice(1)]) tryAdd(c);
    return chosen.sort((x, y) => x.value - y.value);
  };

  if (dimension.scale === 'log') {
    const lt = Math.log10(truth);
    const bandLo = Math.log10(Math.min(targetFact.low > 0 ? targetFact.low : truth, truth));
    const bandHi = Math.log10(Math.max(targetFact.high, truth));
    const width = Math.max(LOG_WINDOW_DECADES, bandHi - bandLo + 1);
    let minExp = lt - offset * width;
    if (minExp > bandLo - 0.2) minExp = bandLo - 0.2;
    if (minExp + width < bandHi + 0.2) minExp = bandHi + 0.2 - width;
    const maxExp = minExp + width;

    const logDist = (a: number, b: number) => Math.abs(Math.log10(a / b));
    const inWindow = eligible.filter((a) => {
      const la = Math.log10(a.value);
      return la >= minExp + 0.15 && la <= maxExp - 0.15;
    });
    const anchors = pickAnchors(inWindow, logDist, MIN_LOG_ANCHOR_GAP_DECADES, 0.4);

    const ticks: number[] = [];
    for (let e = Math.ceil(minExp); e <= Math.floor(maxExp); e++) ticks.push(Math.pow(10, e));
    return { min: Math.pow(10, minExp), max: Math.pow(10, maxExp), anchors, ticks };
  }

  // Linear or Date ruler
  const t = effectiveTolerance(dimension, truth, currentYear);
  const lo = Math.min(targetFact.low, truth);
  const hi = Math.max(targetFact.high, truth);
  const width = Math.max(LINEAR_WINDOW_TOLERANCES * t, hi - lo + 4 * t);
  let minRaw = truth - offset * width;
  if (minRaw > lo - t) minRaw = lo - t;
  if (minRaw + width < hi + t) minRaw = hi + t - width;

  const allNonNeg = allDimensionFacts.every((f) => f.value >= 0) && truth >= 0;
  const floor = dimension.min_domain ?? (dimension.scale !== 'date' && allNonNeg ? 0 : -Infinity);
  const ceiling = dimension.max_domain ?? (dimension.scale === 'date' ? currentYear : Infinity);
  if (minRaw < floor) minRaw = floor;
  if (minRaw + width > ceiling) minRaw = Math.max(floor, ceiling - width);
  const maxRaw = minRaw + width;

  const tickStep = chooseLinearTickStep(width, dimension.scale === 'date');
  const minVal = Math.max(floor, Math.floor(minRaw / tickStep) * tickStep);
  const maxVal = Math.ceil(maxRaw / tickStep) * tickStep;

  const linDist = (a: number, b: number) => Math.abs(a - b);
  const inWindow = eligible.filter((a) => a.value >= minVal && a.value <= maxVal);
  const anchors = pickAnchors(inWindow, linDist, 2 * t, Math.max(tickStep * 0.8, t));

  const ticks: number[] = [];
  for (let v = minVal; v <= maxVal + tickStep * 0.001; v += tickStep) ticks.push(Number(v.toFixed(6)));
  return { min: minVal, max: maxVal, anchors, ticks };
}

function chooseLinearTickStep(span: number, isDate: boolean): number {
  if (isDate) {
    if (span >= 1500) return 500;
    if (span >= 600) return 200;
    if (span >= 250) return 100;
    if (span >= 80) return 20;
    if (span >= 30) return 10;
    return 5;
  }
  const rough = span / 5;
  const pow = Math.pow(10, Math.floor(Math.log10(rough)));
  const norm = rough / pow;
  if (norm <= 1.5) return 1 * pow;
  if (norm <= 3.5) return 2 * pow;
  if (norm <= 7.5) return 5 * pow;
  return 10 * pow;
}

export function valueToPosition(value: number, min: number, max: number, scale: Dimension['scale']): number {
  if (scale === 'log') {
    const logMin = Math.log10(min);
    const logMax = Math.log10(max);
    const clamped = Math.max(min, Math.min(max, value));
    return (Math.log10(clamped) - logMin) / (logMax - logMin);
  }
  const clamped = Math.max(min, Math.min(max, value));
  return (clamped - min) / (max - min);
}

export function positionToValue(pos01: number, min: number, max: number, scale: Dimension['scale']): number {
  const p = Math.max(0, Math.min(1, pos01));
  if (scale === 'log') {
    const logMin = Math.log10(min);
    const logMax = Math.log10(max);
    return Math.pow(10, logMin + p * (logMax - logMin));
  }
  return min + p * (max - min);
}

export function formatQuantity(value: number, dimension: Pick<Dimension, 'scale' | 'unit'>): string {
  if (dimension.scale === 'date') {
    const yr = Math.round(value);
    return yr < 0 ? `${Math.abs(yr)} BCE` : `${yr}`;
  }
  const abs = Math.abs(value);
  let numStr: string;
  if (abs === 0) {
    numStr = '0';
  } else if (abs >= 1e12) {
    numStr = `${(value / 1e12).toPrecision(3).replace(/\.0+$/, '')}T`;
  } else if (abs >= 1e9) {
    numStr = `${(value / 1e9).toPrecision(3).replace(/\.0+$/, '')}B`;
  } else if (abs >= 1e6) {
    numStr = `${(value / 1e6).toPrecision(3).replace(/\.0+$/, '')}M`;
  } else if (abs >= 1e4) {
    numStr = `${(value / 1e3).toPrecision(3).replace(/\.0+$/, '')}k`;
  } else if (abs >= 100) {
    numStr = `${Math.round(value)}`;
  } else if (abs >= 1) {
    numStr = `${Number(value.toPrecision(3))}`;
  } else if (abs >= 0.01) {
    numStr = `${Number(value.toPrecision(2))}`;
  } else {
    numStr = value.toExponential(1);
  }
  if (!dimension.unit || dimension.unit === 'people') return numStr;
  if (dimension.unit === 'USD') return `$${numStr}`;
  return `${numStr} ${dimension.unit}`;
}
