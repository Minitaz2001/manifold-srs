import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS } from '../src/db/database';
import { buildDailyQueue, interleaveItems, selectRatioProbe } from '../src/core/queue';
import { compileContentPacks } from '../src/content/loader';
import type { ContentPack, ModuleId } from '../src/types/content';
import type { ItemState } from '../src/types/memory';

describe('hygiene interleaving, daily caps, and ratio probe selection', () => {
  it('enforces interleaving: never 2 consecutive same dimension, never >3 consecutive same module', () => {
    const items: { id: number; dimension_id: string; module: ModuleId }[] = [
      { id: 1, dimension_id: 'pop', module: 'geography' },
      { id: 2, dimension_id: 'pop', module: 'geography' },
      { id: 3, dimension_id: 'pop', module: 'geography' },
      { id: 4, dimension_id: 'gdp', module: 'geography' },
      { id: 5, dimension_id: 'gdp', module: 'geography' },
      { id: 6, dimension_id: 'power', module: 'physics' },
      { id: 7, dimension_id: 'power', module: 'physics' },
      { id: 8, dimension_id: 'density', module: 'physics' },
      { id: 9, dimension_id: 'code_in', module: 'are_built' },
      { id: 10, dimension_id: 'loads', module: 'are_built' },
      { id: 11, dimension_id: 'plain_card', module: 'natural_world' },
      { id: 12, dimension_id: 'plain_card', module: 'natural_world' },
    ];

    const interleaved = interleaveItems(items, 12345);
    expect(interleaved).toHaveLength(items.length);

    for (let i = 1; i < interleaved.length; i++) {
      expect(interleaved[i].dimension_id).not.toBe(interleaved[i - 1].dimension_id);
    }

    let run = 1;
    for (let i = 1; i < interleaved.length; i++) {
      run = interleaved[i].module === interleaved[i - 1].module ? run + 1 : 1;
      expect(run).toBeLessThanOrEqual(3);
    }
  });

  it('selects ratio probes only from mature non-colliding pairs (>1.2x)', () => {
    const pack: ContentPack = {
      pack_id: 'test-physics',
      version: '0.1.0',
      release_date: '2026-11-19',
      module: 'physics',
      entities: [
        { id: 'a', name: 'A', kind: 'k', module: 'physics', tags: [] },
        { id: 'b', name: 'B', kind: 'k', module: 'physics', tags: [] },
        { id: 'c', name: 'C', kind: 'k', module: 'physics', tags: [] },
      ],
      dimensions: [{ id: 'power_w', name: 'Power', unit: 'W', scale: 'log', tolerance: 2 }],
      facts: [
        { entity_id: 'a', dimension_id: 'power_w', value: 100, low: 100, high: 100, as_of: '2026-01-01', source_url: 'https://example.org', source_note: 'test 100 W', volatile: false },
        { entity_id: 'b', dimension_id: 'power_w', value: 110, low: 110, high: 110, as_of: '2026-01-01', source_url: 'https://example.org', source_note: 'test 110 W (collides)', volatile: false },
        { entity_id: 'c', dimension_id: 'power_w', value: 10000, low: 10000, high: 10000, as_of: '2026-01-01', source_url: 'https://example.org', source_note: 'test 10k W', volatile: false },
      ],
      anchor_sets: [{ dimension_id: 'power_w', entity_ids: ['a', 'c'] }],
      figures: [],
      plain_cards: [],
    };
    const content = compileContentPacks([pack]);

    const makeMature = (eid: string): ItemState => ({
      item_key: `${eid}::power_w::place`,
      entity_id: eid,
      dimension_id: 'power_w',
      task_type: 'place',
      module: 'physics',
      due: '2026-12-01T00:00:00Z',
      stability: 30,
      difficulty: 4,
      elapsed_days: 10,
      scheduled_days: 30,
      learning_steps: 0,
      reps: 4,
      lapses: 0,
      state: 2, // State.Review
      last_review: '2026-11-01T00:00:00Z',
      suspended: false,
      suspend_reason: null,
      last_error: 0.05,
      last_signed_error: 0.05,
    });

    // Only colliding pair mature -> null
    const collidingStates = new Map<string, ItemState>([
      ['a::power_w::place', makeMature('a')],
      ['b::power_w::place', makeMature('b')],
    ]);
    expect(selectRatioProbe({ content, states: collidingStates, seed: 1 })).toBeNull();

    // Add non-colliding mature C -> valid probe returned
    collidingStates.set('c::power_w::place', makeMature('c'));
    const probe = selectRatioProbe({ content, states: collidingStates, seed: 1 });
    expect(probe).not.toBeNull();
    expect(probe!.factA.value / probe!.factB.value).toBeGreaterThan(1.2);
  });

  it('caps new items at 10/day and filters stale volatile facts', () => {
    const facts = Array.from({ length: 20 }, (_, i) => ({
      entity_id: `ent-${i}`,
      dimension_id: 'power_w',
      value: Math.pow(10, i * 0.3 + 1),
      low: Math.pow(10, i * 0.3 + 1),
      high: Math.pow(10, i * 0.3 + 1),
      as_of: i === 0 ? '2022-01-01' : '2026-06-01',
      source_url: 'https://example.org',
      source_note: 'test fact',
      volatile: i === 0,
    }));
    const pack: ContentPack = {
      pack_id: 'cap-test',
      version: '0.1.0',
      release_date: '2026-11-19',
      module: 'physics',
      entities: facts.map((f) => ({ id: f.entity_id, name: f.entity_id, kind: 'k', module: 'physics', tags: [] })),
      dimensions: [{ id: 'power_w', name: 'Power', unit: 'W', scale: 'log', tolerance: 2 }],
      facts,
      anchor_sets: [],
      figures: [],
      plain_cards: [],
    };
    const content = compileContentPacks([pack]);
    const daily = buildDailyQueue({
      content,
      states: new Map(),
      probes: [],
      todayLogs: [],
      settings: DEFAULT_SETTINGS,
      now: new Date('2026-11-19T12:00:00Z'),
    });

    expect(daily.new_today_capped).toBe(10);
    expect(daily.queue.length).toBe(10);
    expect(daily.stale_suspended_keys).toContain('ent-0::power_w::place');
  });

  it('does not allow an 11th new card when today-introduced cards are re-reviewed in learning steps', () => {
    const facts = Array.from({ length: 15 }, (_, i) => ({
      entity_id: `ent-${i}`,
      dimension_id: 'power_w',
      value: Math.pow(10, i * 0.3 + 1),
      low: Math.pow(10, i * 0.3 + 1),
      high: Math.pow(10, i * 0.3 + 1),
      as_of: '2026-06-01',
      source_url: 'https://example.org',
      source_note: 'test fact',
      volatile: false,
    }));
    const pack: ContentPack = {
      pack_id: 'learning-cap-test',
      version: '0.1.0',
      release_date: '2026-11-19',
      module: 'physics',
      entities: facts.map((f) => ({ id: f.entity_id, name: f.entity_id, kind: 'k', module: 'physics', tags: [] })),
      dimensions: [{ id: 'power_w', name: 'Power', unit: 'W', scale: 'log', tolerance: 2 }],
      facts,
      anchor_sets: [],
      figures: [],
      plain_cards: [],
    };
    const content = compileContentPacks([pack]);
    const states = new Map<string, ItemState>();
    const logs = [];
    // Simulate 10 new cards introduced today, each reviewed TWICE (reps = 2) and now scheduled tomorrow
    for (let i = 0; i < 10; i++) {
      const key = `ent-${i}::power_w::flash`;
      states.set(key, {
        item_key: key,
        entity_id: `ent-${i}`,
        dimension_id: 'power_w',
        task_type: 'flash',
        module: 'physics',
        due: '2026-11-20T12:00:00Z',
        stability: 2,
        difficulty: 5,
        elapsed_days: 0,
        scheduled_days: 1,
        learning_steps: 0,
        reps: 2,
        lapses: 0,
        state: 2,
        last_review: '2026-11-19T11:00:00Z',
        suspended: false,
        suspend_reason: null,
        last_error: 0.1,
        last_signed_error: 0.1,
      });
      logs.push(
        { item_key: key, ts: '2026-11-19T10:00:00Z', task_type: 'flash' as const, module: 'physics' as const, dimension_id: 'power_w', prompt_json: '{}', response: '10', error: 0.5, signed_error: 0.5, grade: 'Again' as const, latency_ms: 2000 },
        { item_key: key, ts: '2026-11-19T11:00:00Z', task_type: 'flash' as const, module: 'physics' as const, dimension_id: 'power_w', prompt_json: '{}', response: '10', error: 0.1, signed_error: 0.1, grade: 'Good' as const, latency_ms: 2000 }
      );
    }

    const daily = buildDailyQueue({
      content,
      states,
      probes: [],
      todayLogs: logs,
      allLogs: logs,
      settings: DEFAULT_SETTINGS,
      now: new Date('2026-11-19T12:00:00Z'),
    });

    expect(daily.new_today_capped).toBe(0);
    // No 11th new flashcard; only the supplemental drills those learned cards unlocked (capped at 5/day)
    expect(daily.queue.length).toBe(5);
    for (const q of daily.queue) {
      if (q.kind === 'canonical') expect(q.task_type).toBe('place');
    }
  });
});
