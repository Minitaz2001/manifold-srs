import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS } from '../src/db/database';
import {
  applyCanonicalReview,
  createInitialItemState,
  isVolatileStale,
  LEECH_LAPSE_THRESHOLD,
  replayReviewLog,
} from '../src/core/scheduler';
import type { GradeName, ItemState, ReviewLogEntry } from '../src/types/memory';

describe('scheduler, leech auto-suspend, volatile staleness, and exact log replay', () => {
  it('reproduces item_state identically by replaying review_log (M2 acceptance test)', () => {
    const liveStates = new Map<string, ItemState>();
    const logs: ReviewLogEntry[] = [];
    const startMs = new Date('2026-11-01T12:00:00.000Z').getTime();

    const sequence: {
      entity: string;
      dim: string;
      task: 'place' | 'occlude' | 'recall';
      module: 'geography' | 'physics' | 'natural_world' | 'are_built';
      grade: GradeName;
      dayOffset: number;
      err: number;
      signed: number;
    }[] = [
      { entity: 'vietnam', dim: 'population', task: 'place', module: 'geography', grade: 'Good', dayOffset: 0, err: 0.12, signed: -0.12 },
      { entity: 'li-ion-battery', dim: 'energy_density_mj_kg', task: 'place', module: 'physics', grade: 'Easy', dayOffset: 0, err: 0.05, signed: 0.05 },
      { entity: 'nw-red-maple', dim: 'plain_card', task: 'recall', module: 'natural_world', grade: 'Good', dayOffset: 0, err: 0, signed: 0 },
      { entity: 'vietnam', dim: 'population', task: 'place', module: 'geography', grade: 'Hard', dayOffset: 2, err: 0.42, signed: 0.42 },
      { entity: 'vietnam', dim: 'population', task: 'place', module: 'geography', grade: 'Again', dayOffset: 4, err: 0.85, signed: -0.85 },
      { entity: 'vietnam', dim: 'population', task: 'place', module: 'geography', grade: 'Good', dayOffset: 5, err: 0.1, signed: 0.1 },
      { entity: 'li-ion-battery', dim: 'energy_density_mj_kg', task: 'place', module: 'physics', grade: 'Good', dayOffset: 10, err: 0.08, signed: -0.08 },
      { entity: 'east-se-asia-map__region-vnm', dim: 'geo_east_se_asia', task: 'occlude', module: 'geography', grade: 'Hard', dayOffset: 11, err: 0.5, signed: 0.5 },
      { entity: 'ada-turning-circle', dim: 'code_dimension_in', task: 'place', module: 'are_built', grade: 'Good', dayOffset: 12, err: 1.5, signed: 1.5 },
    ];

    let logId = 1;
    for (const step of sequence) {
      const now = new Date(startMs + step.dayOffset * 86400000);
      const itemKey = `${step.entity}::${step.dim}::${step.task}`;
      const prev =
        liveStates.get(itemKey) ??
        createInitialItemState({
          entity_id: step.entity,
          dimension_id: step.dim,
          task_type: step.task,
          module: step.module,
          now,
        });

      const next = applyCanonicalReview({
        prev,
        grade: step.grade,
        error: step.err,
        signedError: step.signed,
        now,
        desiredRetention: DEFAULT_SETTINGS.desired_retention,
      });
      liveStates.set(itemKey, next);

      logs.push({
        id: logId++,
        item_key: itemKey,
        ts: now.toISOString(),
        task_type: step.task,
        module: step.module,
        dimension_id: step.dim,
        prompt_json: '{}',
        response: '100',
        error: step.err,
        signed_error: step.signed,
        grade: step.grade,
        latency_ms: 2800,
      });
    }

    // Also mix in an unscored ratio probe that MUST NOT affect FSRS state
    logs.push({
      id: logId++,
      item_key: 'probe::diesel-jet-fuel::li-ion-battery::energy_density_mj_kg',
      ts: new Date(startMs + 13 * 86400000).toISOString(),
      task_type: 'ratio_probe',
      module: 'physics',
      dimension_id: 'energy_density_mj_kg',
      prompt_json: '{}',
      response: '10',
      error: 0.68,
      signed_error: -0.68,
      grade: 'Again',
      latency_ms: 3100,
      is_probe: true,
    });

    const replayed = replayReviewLog({ logs, settings: DEFAULT_SETTINGS });
    expect(replayed.size).toBe(liveStates.size);
    for (const [key, expected] of liveStates.entries()) {
      expect(replayed.get(key)).toEqual(expected);
    }
  });

  it('auto-suspends a leech on its 5th lapse and not before', () => {
    let ts = new Date('2026-01-01T10:00:00Z').getTime();
    let state = createInitialItemState({
      entity_id: 'hard-item',
      dimension_id: 'population',
      task_type: 'place',
      module: 'geography',
      now: new Date(ts),
    });

    // Graduate to Review state first
    state = applyCanonicalReview({ prev: state, grade: 'Easy', error: 0, signedError: 0, now: new Date(ts), desiredRetention: 0.85 });

    // Trigger 5 distinct lapses from Review state
    for (let i = 1; i <= LEECH_LAPSE_THRESHOLD; i++) {
      ts += 5 * 86400000;
      state = applyCanonicalReview({ prev: state, grade: 'Again', error: 1, signedError: 1, now: new Date(ts), desiredRetention: 0.85 });
      if (i < LEECH_LAPSE_THRESHOLD) {
        expect(state.suspended).toBe(false);
        // Re-graduate back to Review so next Again counts as a new lapse
        ts += 86400000;
        state = applyCanonicalReview({ prev: state, grade: 'Easy', error: 0, signedError: 0, now: new Date(ts), desiredRetention: 0.85 });
      }
    }

    expect(state.lapses).toBe(LEECH_LAPSE_THRESHOLD);
    expect(state.suspended).toBe(true);
    expect(state.suspend_reason).toBe('leech');
  });

  it('flags volatile facts older than 24 months as stale', () => {
    const now = new Date('2026-11-19T00:00:00Z');
    expect(isVolatileStale('2024-09-01', true, now)).toBe(true);
    expect(isVolatileStale('2025-06-01', true, now)).toBe(false);
    expect(isVolatileStale('2020-01-01', false, now)).toBe(false);
  });
});
