import { describe, expect, it } from 'vitest';
import {
  effectiveTolerance,
  evaluateRatioProbe,
  gradeOcclusion,
  gradePlacement,
  isLogCollision,
  selectRulerConfig,
} from '../src/core/grading';
import type { Dimension, Fact, FigureRegion } from '../src/types/content';

const LOG_DIM: Dimension = {
  id: 'population',
  name: 'Population',
  unit: 'people',
  scale: 'log',
  tolerance: 2,
};

const LINEAR_DIM: Dimension = {
  id: 'code_dimension_in',
  name: 'Code Clearance',
  unit: 'in',
  scale: 'linear',
  tolerance: 4,
  tolerance_mode: 'absolute',
};

const DATE_DIM: Dimension = {
  id: 'historical_year',
  name: 'Year',
  unit: 'CE',
  scale: 'date',
  tolerance: 0.02,
  tolerance_mode: 'date_pct',
};

describe('gradePlacement — table-driven band-edge tests', () => {
  const logFact = { value: 100, low: 100, high: 100 };
  const tLog = Math.log10(2); // ~0.30103; t/2 => sqrt(2) ~1.4142; 2t => 4.0

  const logCases: {
    name: string;
    answer: number | null;
    latencyMs: number;
    skipped?: boolean;
    expectedGrade: string;
  }[] = [
    { name: 'exact fast -> Easy', answer: 100, latencyMs: 2500, expectedGrade: 'Easy' },
    { name: 'at t/2 edge fast (141.42) -> Easy', answer: 100 * Math.sqrt(2), latencyMs: 3000, expectedGrade: 'Easy' },
    { name: 'at t/2 edge slow (3001ms) -> Good', answer: 100 * Math.sqrt(2), latencyMs: 3001, expectedGrade: 'Good' },
    { name: 'above t/2 inside t (180) fast -> Good', answer: 180, latencyMs: 1500, expectedGrade: 'Good' },
    { name: 'at t upper edge (200) -> Good', answer: 200, latencyMs: 4000, expectedGrade: 'Good' },
    { name: 'at t lower edge (50) -> Good', answer: 50, latencyMs: 4000, expectedGrade: 'Good' },
    { name: 'just above t (201) -> Hard', answer: 201, latencyMs: 4000, expectedGrade: 'Hard' },
    { name: 'at 2t upper edge (400) -> Hard', answer: 400, latencyMs: 4000, expectedGrade: 'Hard' },
    { name: 'at 2t lower edge (25) -> Hard', answer: 25, latencyMs: 4000, expectedGrade: 'Hard' },
    { name: 'just outside 2t (401) -> Again', answer: 401, latencyMs: 2000, expectedGrade: 'Again' },
    { name: 'just below 2t (24.9) -> Again', answer: 24.9, latencyMs: 2000, expectedGrade: 'Again' },
    { name: 'timeout at 10000ms exact answer -> Again', answer: 100, latencyMs: 10000, expectedGrade: 'Again' },
    { name: 'skipped -> Again', answer: 100, latencyMs: 1000, skipped: true, expectedGrade: 'Again' },
    { name: 'null answer -> Again', answer: null, latencyMs: 1000, expectedGrade: 'Again' },
  ];

  for (const tc of logCases) {
    it(`log scale: ${tc.name}`, () => {
      const res = gradePlacement({
        dimension: LOG_DIM,
        fact: logFact,
        answer: tc.answer,
        latencyMs: tc.latencyMs,
        skipped: tc.skipped,
      });
      expect(res.grade).toBe(tc.expectedGrade);
      expect(res.tolerance).toBeCloseTo(tLog, 6);
    });
  }

  it('treats any answer inside fact [low, high] as error = 0', () => {
    const rangedFact = { value: 100, low: 80, high: 150 };
    const res = gradePlacement({
      dimension: LOG_DIM,
      fact: rangedFact,
      answer: 145,
      latencyMs: 2000,
    });
    expect(res.error).toBe(0);
    expect(res.signed_error).toBe(0);
    expect(res.grade).toBe('Easy');
  });

  it('linear scale grades accurately at band edges (t = 4)', () => {
    const fact = { value: 36, low: 36, high: 36 };
    expect(gradePlacement({ dimension: LINEAR_DIM, fact, answer: 38, latencyMs: 2500 }).grade).toBe('Easy');
    expect(gradePlacement({ dimension: LINEAR_DIM, fact, answer: 40, latencyMs: 4000 }).grade).toBe('Good');
    expect(gradePlacement({ dimension: LINEAR_DIM, fact, answer: 44, latencyMs: 4000 }).grade).toBe('Hard');
    expect(gradePlacement({ dimension: LINEAR_DIM, fact, answer: 44.1, latencyMs: 2000 }).grade).toBe('Again');
  });

  it('date scale follows ±2% years-before-present with ±2 yr floor (Design Doc examples)', () => {
    // 1944 in 2026 -> 82 yrs -> 2% = 1.64 -> floor 2 yrs
    expect(effectiveTolerance(DATE_DIM, 1944, 2026)).toBe(2);
    // 1177 BCE (-1177) in 2026 -> 3203 yrs -> 2% = 64.06 yrs
    expect(effectiveTolerance(DATE_DIM, -1177, 2026)).toBeCloseTo(64.06, 2);

    const res1944 = gradePlacement({
      dimension: DATE_DIM,
      fact: { value: 1944, low: 1944, high: 1944 },
      answer: 1946,
      latencyMs: 4500,
      currentYear: 2026,
    });
    expect(res1944.grade).toBe('Good');

    const resBronze = gradePlacement({
      dimension: DATE_DIM,
      fact: { value: -1177, low: -1177, high: -1177 },
      answer: -1115,
      latencyMs: 4500,
      currentYear: 2026,
    });
    expect(resBronze.grade).toBe('Good');
  });
});

describe('gradeOcclusion — exact, adjacent, non-adjacent, timeout', () => {
  const target: FigureRegion = {
    region_id: 'region-vnm',
    label: 'Vietnam',
    adjacent_ids: ['region-chn', 'region-lao', 'region-khm'],
  };

  it('grades exact match as Good, adjacent as Hard, distant or timeout as Again', () => {
    expect(gradeOcclusion({ targetRegion: target, selectedRegionId: 'region-vnm', latencyMs: 1800 }).grade).toBe('Good');
    expect(gradeOcclusion({ targetRegion: target, selectedRegionId: 'region-lao', latencyMs: 2200 }).grade).toBe('Hard');
    expect(gradeOcclusion({ targetRegion: target, selectedRegionId: 'region-jpn', latencyMs: 1800 }).grade).toBe('Again');
    expect(gradeOcclusion({ targetRegion: target, selectedRegionId: 'region-vnm', latencyMs: 10000 }).grade).toBe('Again');
  });
});

describe('anti-collision & ruler anchor bracketing', () => {
  it('detects 1.2x log collisions symmetrically', () => {
    expect(isLogCollision(100, 119)).toBe(true);
    expect(isLogCollision(100, 120)).toBe(true);
    expect(isLogCollision(100, 121)).toBe(false);
    expect(isLogCollision(121, 100)).toBe(false);
  });

  it('brackets target value without selecting self or colliding anchors', () => {
    const targetFact: Fact = {
      entity_id: 'vietnam',
      dimension_id: 'population',
      value: 100_000_000,
      low: 98_000_000,
      high: 102_000_000,
      as_of: '2026-01-01',
      source_url: 'https://example.org',
      source_note: 'test fixture',
      volatile: true,
    };
    const candidates = [
      { entity_id: 'iceland', name: 'Iceland', value: 390_000 },
      { entity_id: 'singapore', name: 'Singapore', value: 6_000_000 },
      { entity_id: 'egypt', name: 'Egypt', value: 110_000_000 }, // within 1.2x -> must exclude!
      { entity_id: 'vietnam', name: 'Vietnam', value: 100_000_000 }, // self -> must exclude!
      { entity_id: 'united-states', name: 'United States', value: 340_000_000 },
      { entity_id: 'india', name: 'India', value: 1_450_000_000 },
    ];
    const cfg = selectRulerConfig({
      dimension: LOG_DIM,
      targetFact,
      candidateAnchors: candidates,
      allDimensionFacts: [targetFact],
    });
    expect(cfg.anchors.some((a) => a.entity_id === 'vietnam')).toBe(false);
    expect(cfg.anchors.some((a) => a.entity_id === 'egypt')).toBe(false);
    expect(cfg.anchors.some((a) => a.value < targetFact.value)).toBe(true);
    expect(cfg.anchors.some((a) => a.value > targetFact.value)).toBe(true);
    expect(cfg.min).toBeLessThan(targetFact.value);
    expect(cfg.max).toBeGreaterThan(targetFact.value);
  });

  it('evaluates ratio probes within tolerance factor', () => {
    // Jet fuel (43) / Li-ion (0.9) ≈ 47.8x
    expect(evaluateRatioProbe({ truthA: 43, truthB: 0.9, guessedRatio: 50, toleranceFactor: 2 }).hit).toBe(true);
    expect(evaluateRatioProbe({ truthA: 43, truthB: 0.9, guessedRatio: 10, toleranceFactor: 2 }).hit).toBe(false);
  });
});
