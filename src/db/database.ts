import Dexie, { type Table } from 'dexie';
import type {
  InboxEntry,
  ItemState,
  ProbeQueueEntry,
  ReviewLogEntry,
  UserSettings,
} from '../types/memory';

export const DEFAULT_SETTINGS: UserSettings = {
  id: 'singleton',
  desired_retention: 0.85,
  module_retention_overrides: {},
  new_per_day: 10,
  reviews_per_day: 120,
  last_backup_ts: null,
  reviews_since_backup: 0,
  persist_granted: null,
  persist_warned: false,
};

export class ManifoldDatabase extends Dexie {
  item_state!: Table<ItemState, string>;
  review_log!: Table<ReviewLogEntry, number>;
  probe_queue!: Table<ProbeQueueEntry, string>;
  inbox!: Table<InboxEntry, number>;
  settings!: Table<UserSettings, string>;

  constructor(name = 'manifold_srs_v1') {
    super(name);
    this.version(1).stores({
      item_state: 'item_key, entity_id, dimension_id, module, due, suspended',
      review_log: '++id, item_key, ts, task_type, module, dimension_id',
      probe_queue: 'item_key, due_ts, source_review_id',
      inbox: '++id, ts, reason, exported',
      settings: 'id',
    });
  }
}

export const db = new ManifoldDatabase();

export async function getOrInitSettings(database: ManifoldDatabase = db): Promise<UserSettings> {
  const existing = await database.settings.get('singleton');
  if (existing) return existing;
  await database.settings.put({ ...DEFAULT_SETTINGS });
  return { ...DEFAULT_SETTINGS };
}
