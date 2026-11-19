import type { CanonicalTaskType, ModuleId, ReviewTaskType } from './content';

export type GradeName = 'Again' | 'Hard' | 'Good' | 'Easy';

export type SuspendReason = 'leech' | 'stale' | 'manual' | null;

/** Serializable mirror of ts-fsrs Card fields + Manifold SRS metadata */
export interface ItemState {
  /** Composite stable key: `${entity_id}::${dimension_id}::${task_type}` */
  item_key: string;
  entity_id: string;
  dimension_id: string;
  task_type: CanonicalTaskType;
  module: ModuleId;
  /** ts-fsrs Card fields (dates stored as ISO strings for clean JSON export/replay) */
  due: string;
  stability: number;
  difficulty: number;
  elapsed_days: number;
  scheduled_days: number;
  learning_steps: number;
  reps: number;
  lapses: number;
  state: number;
  last_review: string | null;
  /** Manifold hygiene fields */
  suspended: boolean;
  suspend_reason: SuspendReason;
  last_error: number | null;
  last_signed_error: number | null;
}

export interface ReviewLogEntry {
  id?: number;
  item_key: string;
  ts: string;
  task_type: ReviewTaskType;
  module: ModuleId;
  dimension_id: string;
  /** Frozen prompt snapshot so calibration analysis never depends on regenerating */
  prompt_json: string;
  response: string;
  error: number;
  signed_error: number;
  grade: GradeName;
  latency_ms: number;
  is_probe?: boolean;
}

export interface ProbeQueueEntry {
  item_key: string;
  due_ts: string;
  reason: 'ratio_miss';
  source_review_id: number;
}

export interface InboxEntry {
  id?: number;
  ts: string;
  text: string;
  related_item_key: string | null;
  reason: 'surprise' | 'rewrite';
  exported: boolean;
}

export interface UserSettings {
  id: 'singleton';
  desired_retention: number;
  module_retention_overrides: Partial<Record<ModuleId, number>>;
  new_per_day: number;
  reviews_per_day: number;
  last_backup_ts: string | null;
  reviews_since_backup: number;
  persist_granted: boolean | null;
  persist_warned: boolean;
}

export interface BackupPayload {
  schema_version: 1;
  exported_at: string;
  item_state: ItemState[];
  review_log: ReviewLogEntry[];
  probe_queue: ProbeQueueEntry[];
  inbox: InboxEntry[];
  settings: UserSettings;
}

export function makeItemKey(
  entityId: string,
  dimensionId: string,
  taskType: CanonicalTaskType
): string {
  return `${entityId}::${dimensionId}::${taskType}`;
}
