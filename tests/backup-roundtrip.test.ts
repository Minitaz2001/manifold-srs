import 'fake-indexeddb/auto';
import { describe, expect, it } from 'vitest';
import { DEFAULT_SETTINGS, ManifoldDatabase } from '../src/db/database';
import { exportFullBackup, importFullBackup, shouldPromptBackup } from '../src/core/backup';
import { applyCanonicalReview, createInitialItemState } from '../src/core/scheduler';

describe('M1 IndexedDB export -> wipe -> import round-trip', () => {
  it('restores identical item_state, review_log, probe_queue, inbox, and settings after full wipe', async () => {
    const db = new ManifoldDatabase(`manifold_test_${Date.now()}`);
    const now = new Date('2026-11-19T14:00:00.000Z');

    const init = createInitialItemState({
      entity_id: 'vietnam',
      dimension_id: 'population',
      task_type: 'place',
      module: 'geography',
      now,
    });
    const reviewed = applyCanonicalReview({
      prev: init,
      grade: 'Good',
      error: 0.14,
      signedError: -0.14,
      now,
      desiredRetention: 0.85,
    });

    await db.item_state.put(reviewed);
    const logId = await db.review_log.add({
      item_key: reviewed.item_key,
      ts: now.toISOString(),
      task_type: 'place',
      module: 'geography',
      dimension_id: 'population',
      prompt_json: '{"anchors":["singapore","united-states"]}',
      response: '72000000',
      error: 0.14,
      signed_error: -0.14,
      grade: 'Good',
      latency_ms: 3400,
    });
    await db.probe_queue.put({
      item_key: reviewed.item_key,
      due_ts: '2026-11-20T14:00:00.000Z',
      reason: 'ratio_miss',
      source_review_id: logId,
    });
    await db.inbox.add({
      ts: now.toISOString(),
      text: 'Thought Indonesia was 180M; actually ~280M',
      related_item_key: reviewed.item_key,
      reason: 'surprise',
      exported: false,
    });
    await db.settings.put({
      ...DEFAULT_SETTINGS,
      reviews_since_backup: 1,
      persist_granted: true,
    });

    // 1. Export full state as JSON string (simulating iOS Share Sheet file)
    const exported = await exportFullBackup(db, now);
    const serialized = JSON.stringify(exported);

    // 2. Complete wipe
    await db.item_state.clear();
    await db.review_log.clear();
    await db.probe_queue.clear();
    await db.inbox.clear();
    await db.settings.clear();
    expect(await db.item_state.count()).toBe(0);
    expect(await db.review_log.count()).toBe(0);

    // 3. Import from serialized JSON
    await importFullBackup(db, JSON.parse(serialized));

    // 4. Verify bit-for-bit identical restoration
    const restoredItems = await db.item_state.toArray();
    const restoredLogs = await db.review_log.orderBy('id').toArray();
    const restoredProbes = await db.probe_queue.toArray();
    const restoredInbox = await db.inbox.orderBy('id').toArray();
    const restoredSettings = await db.settings.get('singleton');

    expect(restoredItems).toEqual(exported.item_state);
    expect(restoredLogs).toEqual(exported.review_log);
    expect(restoredProbes).toEqual(exported.probe_queue);
    expect(restoredInbox).toEqual(exported.inbox);
    expect(restoredSettings).toEqual(exported.settings);

    await db.delete();
  });

  it('triggers backup prompt weekly or every 500 reviews', () => {
    const now = new Date('2026-11-19T12:00:00Z');
    expect(shouldPromptBackup({ ...DEFAULT_SETTINGS, reviews_since_backup: 500, last_backup_ts: '2026-11-19T11:00:00Z' }, now)).toBe(true);
    expect(shouldPromptBackup({ ...DEFAULT_SETTINGS, reviews_since_backup: 5, last_backup_ts: '2026-11-10T12:00:00Z' }, now)).toBe(true);
    expect(shouldPromptBackup({ ...DEFAULT_SETTINGS, reviews_since_backup: 5, last_backup_ts: '2026-11-18T12:00:00Z' }, now)).toBe(false);
  });
});
