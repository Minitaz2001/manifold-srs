import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS } from '../src/db/database';
import { buildDailyQueue, startOfLocalDay } from '../src/core/queue';
import { compileContentPacks } from '../src/content/loader';
import { applyCanonicalReview, createInitialItemState, isLeechLapse } from '../src/core/scheduler';
import type { ContentPack } from '../src/types/content';
import type { ItemState, ReviewLogEntry } from '../src/types/memory';

function pack(n: number, drill = true): ContentPack {
  const facts = Array.from({ length: n }, (_, i) => ({
    entity_id: `ent-${i}`, dimension_id: 'power_w', value: Math.pow(10, i * 0.5 + 1),
    low: Math.pow(10, i * 0.5 + 1), high: Math.pow(10, i * 0.5 + 1), as_of: '2026-06-01',
    source_url: 'https://example.org', source_note: 'test', volatile: false,
  }));
  return {
    pack_id: 'day-test', version: '0.1.0', release_date: '2026-11-19', module: 'physics',
    entities: facts.map((f) => ({ id: f.entity_id, name: f.entity_id, kind: 'k', module: 'physics', tags: [] })),
    dimensions: [{ id: 'power_w', name: 'Power', unit: 'W', scale: 'log', tolerance: 2, ...(drill ? {} : { drill: false }) }],
    facts, anchor_sets: [], figures: [], plain_cards: [],
  };
}

const local = (h: number, m = 0, dayOffset = 0) => new Date(2026, 10, 19 + dayOffset, h, m, 0, 0);

function stateAt(key: string, patch: Partial<ItemState>): ItemState {
  const [entity_id, dimension_id, task_type] = key.split('::');
  return {
    ...createInitialItemState({ entity_id, dimension_id, task_type: task_type as 'flash', module: 'physics', now: local(9) }),
    ...patch,
  };
}

function log(key: string, ts: Date, grade: ReviewLogEntry['grade'] = 'Good'): ReviewLogEntry {
  return {
    item_key: key, ts: ts.toISOString(), task_type: 'flash', module: 'physics', dimension_id: 'power_w',
    prompt_json: '{}', response: '', error: 0, signed_error: 0, grade, latency_ms: 1000,
  };
}

describe('study-day model', () => {
  it('rolls the day over at 4 am local, not midnight', () => {
    expect(startOfLocalDay(local(2, 30, 1))).toBe(local(4, 0, 0).getTime());
    expect(startOfLocalDay(local(4, 30, 1))).toBe(local(4, 0, 1).getTime());
  });

  it('gives the same FSRS result for a learning session whether or not it crosses 00:00 UTC', () => {
    // Same wall-clock gap (1 h, Good then Good) in a UTC-8 evening: 15:30→16:30 crosses 00:00 UTC.
    const run = (startIso: string) => {
      let st = createInitialItemState({ entity_id: 'e', dimension_id: 'd', task_type: 'flash', module: 'physics', now: new Date(startIso) });
      st = applyCanonicalReview({ prev: st, grade: 'Good', error: 0, signedError: 0, now: new Date(startIso), desiredRetention: 0.85, tzOffsetMin: 480 });
      const t2 = new Date(new Date(startIso).getTime() + 3600_000);
      st = applyCanonicalReview({ prev: st, grade: 'Good', error: 0, signedError: 0, now: t2, desiredRetention: 0.85, tzOffsetMin: 480 });
      return st.stability;
    };
    const crossing = run('2026-11-19T23:30:00Z'); // 15:30 → 16:30 PST
    const notCrossing = run('2026-11-19T19:30:00Z'); // 11:30 → 12:30 PST
    expect(crossing).toBeCloseTo(notCrossing, 6);
  });

  it('makes review cards due for the whole study day, not from the minute they were scheduled', () => {
    const content = compileContentPacks([pack(1)]);
    const key = 'ent-0::power_w::flash';
    const states = new Map([[key, stateAt(key, { reps: 3, state: 2, stability: 1, due: local(22).toISOString(), last_review: local(22, 0, -1).toISOString() })]]);
    const daily = buildDailyQueue({ content, states, probes: [], todayLogs: [], allLogs: [], settings: DEFAULT_SETTINGS, now: local(8) });
    expect(daily.queue.map((q) => q.item_key)).toContain(key);
  });
});

describe('keep going: learn-ahead and caps', () => {
  it('shows a learning card early when nothing else is left, and reports pending ones', () => {
    const content = compileContentPacks([pack(1)]);
    const key = 'ent-0::power_w::flash';
    const now = local(12);
    const st = stateAt(key, { reps: 1, state: 1, due: new Date(now.getTime() + 8 * 60_000).toISOString(), last_review: now.toISOString() });
    const states = new Map([[key, st]]);
    const logs = [log(key, now)];
    const settings = { ...DEFAULT_SETTINGS, new_per_day: 1 };

    const ahead = buildDailyQueue({ content, states, probes: [], todayLogs: logs, allLogs: logs, settings, now });
    expect(ahead.queue.map((q) => q.item_key)).toEqual([key]);

    const noAhead = buildDailyQueue({ content, states, probes: [], todayLogs: logs, allLogs: logs, settings, now, learnAheadMs: 0 });
    expect(noAhead.queue).toHaveLength(0);
    expect(noAhead.learning_pending).toBe(1);
    expect(noAhead.next_learning_due).toBe(now.getTime() + 8 * 60_000);
  });

  it('never lets learning-step repeats eat the review cap', () => {
    const content = compileContentPacks([pack(4)]);
    const now = local(15);
    const states = new Map<string, ItemState>();
    const logs: ReviewLogEntry[] = [];
    // ent-0: a learned card that lapsed today and was repeated 5x in relearning (one card, one cap slot)
    const k0 = 'ent-0::power_w::flash';
    logs.push(log(k0, local(9, 0, -10)));
    for (let i = 0; i < 5; i++) logs.push(log(k0, local(10, i), 'Again'));
    states.set(k0, stateAt(k0, { reps: 8, state: 3, lapses: 1, due: local(18).toISOString(), last_review: local(10, 4).toISOString() }));
    // ent-1, ent-2: review cards due today
    for (const i of [1, 2]) {
      const k = `ent-${i}::power_w::flash`;
      logs.push(log(k, local(9, 0, -5)));
      states.set(k, stateAt(k, { reps: 3, state: 2, stability: 3, due: local(9).toISOString(), last_review: local(9, 0, -5).toISOString() }));
    }
    const settings = { ...DEFAULT_SETTINGS, reviews_per_day: 3, new_per_day: 0 };
    const todayLogs = logs.filter((l) => new Date(l.ts).getTime() >= startOfLocalDay(now));
    const daily = buildDailyQueue({ content, states, probes: [], todayLogs, allLogs: logs, settings, now, learnAheadMs: 0 });
    // 1 slot used by ent-0, 2 left → both due reviews fit
    expect(daily.due_today_capped).toBe(2);
  });

  it('honours a +5 new bump for today only', () => {
    const content = compileContentPacks([pack(12)]);
    const now = local(12);
    const settings = { ...DEFAULT_SETTINGS, new_per_day: 3, extra_new: { day: startOfLocalDay(now), count: 5 } };
    const today = buildDailyQueue({ content, states: new Map(), probes: [], todayLogs: [], allLogs: [], settings, now });
    expect(today.new_today_capped).toBe(8);
    const tomorrow = buildDailyQueue({ content, states: new Map(), probes: [], todayLogs: [], allLogs: [], settings, now: local(12, 0, 1) });
    expect(tomorrow.new_today_capped).toBe(3);
  });
});

describe('siblings, exact dimensions, leeches', () => {
  it('buries a fact\'s drill on a day its flashcard was reviewed', () => {
    const content = compileContentPacks([pack(1)]);
    const now = local(12);
    const flash = 'ent-0::power_w::flash';
    const drill = 'ent-0::power_w::place';
    const states = new Map([
      [flash, stateAt(flash, { reps: 4, state: 2, stability: 10, due: local(12, 0, 9).toISOString(), last_review: local(10).toISOString() })],
      [drill, stateAt(drill, { task_type: 'place', reps: 3, state: 2, stability: 5, due: local(8).toISOString(), last_review: local(9, 0, -5).toISOString() })],
    ]);
    const logs = [log(flash, local(10))];
    const daily = buildDailyQueue({ content, states, probes: [], todayLogs: logs, allLogs: logs, settings: DEFAULT_SETTINGS, now });
    expect(daily.queue.map((q) => q.item_key)).not.toContain(drill);
  });

  it('never creates drills for exact-value dimensions', () => {
    const content = compileContentPacks([pack(1, false)]);
    const flash = 'ent-0::power_w::flash';
    const states = new Map([[flash, stateAt(flash, { reps: 4, state: 2, stability: 10, due: local(12, 0, 9).toISOString(), last_review: local(10, 0, -3).toISOString() })]]);
    const daily = buildDailyQueue({ content, states, probes: [], todayLogs: [], allLogs: [], settings: DEFAULT_SETTINGS, now: local(12) });
    expect(daily.queue.some((q) => q.item_key.endsWith('::place'))).toBe(false);
  });

  it('flags leeches at 8 lapses and every 4 after, never on a non-lapse', () => {
    expect(isLeechLapse(7, 8)).toBe(true);
    expect(isLeechLapse(8, 8)).toBe(false);
    expect(isLeechLapse(8, 9)).toBe(false);
    expect(isLeechLapse(11, 12)).toBe(true);
  });
});
