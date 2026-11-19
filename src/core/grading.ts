import type { CanonicalTaskType, Dimension, Fact, FigureRegion } from '../types/content';
import type { GradeName } from '../types/memory';

export const EASY_LATENCY_MS = 3000;
export const TIMEOUT_LATENCY_MS = 10000;
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
 * - e <= t/2 and latency <= 3000ms -> Easy
 * - e <= t -> Good
 * - e <= 2*t -> Hard
 * - e > 2*t, timeout (>= 10000ms), or skip -> Again
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
  if (error <= t / 2 + eps && latencyMs <= EASY_LATENCY_MS) {
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

/**
 * Selects 2-3 bracketing anchors for a target fact on a ruler/timeline:
 * - Never includes the target entity itself
 * - Never includes an anchor within 1.2x on log scales
 * - Prefers one below and one above at least 0.5 decades (log) or 1 tick (linear/date) from truth
 * - Adds a 3rd informative anchor if available cleanly inside the span
 */
export function selectRulerConfig(params: {
  dimension: Dimension;
  targetFact: Fact;
  candidateAnchors: RulerAnchor[];
  allDimensionFacts: Fact[];
  currentYear?: number;
}): RulerConfig {
  const { dimension, targetFact, candidateAnchors, allDimensionFacts, currentYear = 2026 } = params;
  const truth = targetFact.value;

  const eligible = candidateAnchors
    .filter((a) => a.entity_id !== targetFact.entity_id)
    .filter((a) => (dimension.scale === 'log' ? !isLogCollision(a.value, truth) : a.value !== truth))
    .sort((a, b) => a.value - b.value);

  if (dimension.scale === 'log') {
    const belowCandidates = eligible.filter((a) => Math.log10(truth / a.value) >= MIN_LOG_ANCHOR_GAP_DECADES);
    const aboveCandidates = eligible.filter((a) => Math.log10(a.value / truth) >= MIN_LOG_ANCHOR_GAP_DECADES);

    // Fallback to any non-colliding lower/upper anchor if target is near the extreme end
    const belowPool = belowCandidates.length > 0 ? belowCandidates : eligible.filter((a) => a.value < truth);
    const abovePool = aboveCandidates.length > 0 ? aboveCandidates : eligible.filter((a) => a.value > truth);

    const chosen: RulerAnchor[] = [];
    if (belowPool.length > 0) chosen.push(belowPool[belowPool.length - 1]);
    if (abovePool.length > 0) chosen.push(abovePool[0]);

    // Optional 3rd anchor spaced well outside chosen two for broader visual scale
    for (const cand of eligible) {
      if (chosen.length >= 3) break;
      if (chosen.some((c) => c.entity_id === cand.entity_id)) continue;
      if (chosen.every((c) => Math.abs(Math.log10(c.value / cand.value)) >= 0.6)) {
        if (Math.abs(Math.log10(truth / cand.value)) >= MIN_LOG_ANCHOR_GAP_DECADES) {
          chosen.push(cand);
        }
      }
    }
    chosen.sort((a, b) => a.value - b.value);

    const allVals = [...chosen.map((c) => c.value), truth, targetFact.low, targetFact.high].filter((v) => v > 0);
    const minExp = Math.floor(Math.log10(Math.min(...allVals))) - 0.5;
    const maxExp = Math.ceil(Math.log10(Math.max(...allVals))) + 0.5;
    const ticks: number[] = [];
    for (let e = Math.ceil(minExp); e <= Math.floor(maxExp); e++) {
      ticks.push(Math.pow(10, e));
    }
    return {
      min: Math.pow(10, minExp),
      max: Math.pow(10, maxExp),
      anchors: chosen,
      ticks,
    };
  }

  // Linear or Date ruler
  const allVals = allDimensionFacts.map((f) => f.value);
  const rawMin = dimension.min_domain ?? Math.min(...allVals);
  const rawMax = dimension.max_domain ?? Math.max(...allVals);
  const span = Math.max(1, rawMax - rawMin);
  const tickStep = chooseLinearTickStep(span, dimension.scale === 'date');

  const minGap = dimension.scale === 'date' ? Math.max(tickStep * 0.5, effectiveTolerance(dimension, truth, currentYear) * 2) : tickStep;
  const belowCandidates = eligible.filter((a) => truth - a.value >= minGap);
  const aboveCandidates = eligible.filter((a) => a.value - truth >= minGap);
  const belowPool = belowCandidates.length > 0 ? belowCandidates : eligible.filter((a) => a.value < truth);
  const abovePool = aboveCandidates.length > 0 ? aboveCandidates : eligible.filter((a) => a.value > truth);

  const chosen: RulerAnchor[] = [];
  if (belowPool.length > 0) chosen.push(belowPool[belowPool.length - 1]);
  if (abovePool.length > 0) chosen.push(abovePool[0]);
  if (chosen.length < 3) {
    for (const cand of eligible) {
      if (chosen.length >= 3) break;
      if (chosen.some((c) => c.entity_id === cand.entity_id)) continue;
      if (Math.abs(cand.value - truth) >= minGap && chosen.every((c) => Math.abs(c.value - cand.value) >= tickStep * 0.8)) {
        chosen.push(cand);
      }
    }
  }
  chosen.sort((a, b) => a.value - b.value);

  const domainVals = [...chosen.map((c) => c.value), truth, rawMin, rawMax];
  const minVal = Math.floor(Math.min(...domainVals) / tickStep) * tickStep;
  const maxVal = Math.ceil(Math.max(...domainVals) / tickStep) * tickStep;
  const ticks: number[] = [];
  for (let v = minVal; v <= maxVal + tickStep * 0.001; v += tickStep) {
    ticks.push(Number(v.toFixed(6)));
  }

  return {
    min: minVal,
    max: maxVal,
    anchors: chosen,
    ticks,
  };
}

function chooseLinearTickStep(span: number, isDate: boolean): number {
  if (isDate) {
    if (span >= 1500) return 500;
    if (span >= 600) return 200;
    if (span >= 250) return 100;
    if (span >= 80) return 50;
    return 10;
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
