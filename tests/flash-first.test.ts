import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS } from '../src/db/database';
import { buildDailyQueue } from '../src/core/queue';
import { compileContentPacks } from '../src/content/loader';
import { createInitialItemState } from '../src/core/scheduler';
import type { ContentPack } from '../src/types/content';
import type { ItemState } from '../src/types/memory';

function pack(n: number): ContentPack {
  const facts = Array.from({ length: n }, (_, i) => ({
    entity_id: `ent-${i}`, dimension_id: 'power_w', value: Math.pow(10, i * 0.5 + 1),
    low: Math.pow(10, i * 0.5 + 1), high: Math.pow(10, i * 0.5 + 1), as_of: '2026-06-01',
    source_url: 'https://example.org', source_note: 'test', volatile: false,
  }));
  return {
    pack_id: 'flash-test', version: '0.1.0', release_date: '2026-11-19', module: 'physics',
    entities: facts.map((f) => ({ id: f.entity_id, name: f.entity_id, kind: 'k', module: 'physics', tags: [] })),
    dimensions: [{ id: 'power_w', name: 'Power', unit: 'W', scale: 'log', tolerance: 2 }],
    facts, anchor_sets: [], figures: [], plain_cards: [],
  };
}

describe('flashcards first, scale drills supplemental', () => {
  const now = new Date('2026-11-19T12:00:00Z');

  it('day 1 queue is only plain flashcards — no placement drills or ratio probes', () => {
    const content = compileContentPacks([pack(6)]);
    const daily = buildDailyQueue({ content, states: new Map(), probes: [], todayLogs: [], settings: DEFAULT_SETTINGS, now });
    expect(daily.queue.length).toBe(6);
    for (const q of daily.queue) {
      expect(q.kind).toBe('canonical');
      if (q.kind === 'canonical') expect(q.task_type).toBe('flash');
    }
  });

  it('unlocks the placement drill only after that fact\'s flashcard is learned', () => {
    const content = compileContentPacks([pack(2)]);
    const learned: ItemState = {
      ...createInitialItemState({ entity_id: 'ent-0', dimension_id: 'power_w', task_type: 'flash', module: 'physics', now }),
      reps: 3, state: 2, stability: 5, due: '2026-12-01T00:00:00Z', last_review: new Date(now.getTime() - 2 * 86400000).toISOString(),
    };
    const states = new Map([[learned.item_key, learned]]);
    const daily = buildDailyQueue({ content, states, probes: [], todayLogs: [], settings: DEFAULT_SETTINGS, now });
    const keys = daily.queue.map((q) => q.item_key);
    expect(keys).toContain('ent-0::power_w::place');
    expect(keys).not.toContain('ent-1::power_w::place');
    expect(keys).toContain('ent-1::power_w::flash');
  });

  it('keeps a flashcard learned today from unlocking its drill until the next study day', () => {
    const content = compileContentPacks([pack(1)]);
    const learnedToday: ItemState = {
      ...createInitialItemState({ entity_id: 'ent-0', dimension_id: 'power_w', task_type: 'flash', module: 'physics', now }),
      reps: 2, state: 2, stability: 2, due: '2026-12-01T00:00:00Z', last_review: now.toISOString(),
    };
    const states = new Map([[learnedToday.item_key, learnedToday]]);
    const daily = buildDailyQueue({ content, states, probes: [], todayLogs: [], settings: DEFAULT_SETTINGS, now });
    expect(daily.queue.map((q) => q.item_key)).not.toContain('ent-0::power_w::place');
  });
});
