import type { ManifoldDatabase } from '../db/database';
import { DEFAULT_SETTINGS, getOrInitSettings } from '../db/database';
import type { BackupPayload, UserSettings } from '../types/memory';

export const BACKUP_INTERVAL_DAYS = 7;
export const BACKUP_REVIEW_THRESHOLD = 500;

export function shouldPromptBackup(settings: UserSettings, now: Date): boolean {
  if (settings.reviews_since_backup >= BACKUP_REVIEW_THRESHOLD) {
    return true;
  }
  if (settings.reviews_since_backup === 0) {
    return false;
  }
  if (!settings.last_backup_ts) {
    return settings.reviews_since_backup >= 20;
  }
  const elapsedMs = now.getTime() - new Date(settings.last_backup_ts).getTime();
  return elapsedMs >= BACKUP_INTERVAL_DAYS * 86400000;
}

export async function exportFullBackup(database: ManifoldDatabase, now = new Date()): Promise<BackupPayload> {
  const [item_state, review_log, probe_queue, inbox, settings] = await Promise.all([
    database.item_state.toArray(),
    database.review_log.orderBy('id').toArray(),
    database.probe_queue.toArray(),
    database.inbox.orderBy('id').toArray(),
    getOrInitSettings(database),
  ]);

  return {
    schema_version: 1,
    exported_at: now.toISOString(),
    item_state,
    review_log,
    probe_queue,
    inbox,
    settings,
  };
}

export function validateBackupPayload(raw: unknown): BackupPayload {
  if (!raw || typeof raw !== 'object') {
    throw new Error('Backup JSON must be an object');
  }
  const obj = raw as Partial<BackupPayload>;
  if (obj.schema_version !== 1) {
    throw new Error(`Unsupported backup schema_version: ${String(obj.schema_version)}`);
  }
  if (!Array.isArray(obj.item_state) || !Array.isArray(obj.review_log)) {
    throw new Error('Backup missing required item_state or review_log arrays');
  }
  return {
    schema_version: 1,
    exported_at: typeof obj.exported_at === 'string' ? obj.exported_at : new Date().toISOString(),
    item_state: obj.item_state,
    review_log: obj.review_log,
    probe_queue: Array.isArray(obj.probe_queue) ? obj.probe_queue : [],
    inbox: Array.isArray(obj.inbox) ? obj.inbox : [],
    settings: obj.settings ? { ...DEFAULT_SETTINGS, ...obj.settings, id: 'singleton' } : { ...DEFAULT_SETTINGS },
  };
}

/**
 * Exact transactional wipe + restore (M1 acceptance test:
 * "passes an export -> wipe -> import round-trip with identical item_state").
 */
export async function importFullBackup(
  database: ManifoldDatabase,
  rawPayload: unknown
): Promise<BackupPayload> {
  const payload = validateBackupPayload(rawPayload);

  await database.transaction(
    'rw',
    [database.item_state, database.review_log, database.probe_queue, database.inbox, database.settings],
    async () => {
      await database.item_state.clear();
      await database.review_log.clear();
      await database.probe_queue.clear();
      await database.inbox.clear();
      await database.settings.clear();

      if (payload.item_state.length > 0) {
        await database.item_state.bulkPut(payload.item_state);
      }
      if (payload.review_log.length > 0) {
        await database.review_log.bulkPut(payload.review_log);
      }
      if (payload.probe_queue.length > 0) {
        await database.probe_queue.bulkPut(payload.probe_queue);
      }
      if (payload.inbox.length > 0) {
        await database.inbox.bulkPut(payload.inbox);
      }
      await database.settings.put(payload.settings);
    }
  );

  return payload;
}
