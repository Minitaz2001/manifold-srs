import { createEmptyCard, fsrs, Rating, State, type Card, type Grade } from 'ts-fsrs';
import type { CanonicalTaskType, CompiledContent, ModuleId } from '../types/content';
import { makeItemKey, type GradeName, type ItemState, type ReviewLogEntry, type UserSettings } from '../types/memory';

/** Anki defaults: leech at 8 lapses, then again every 4 further lapses. */
export const LEECH_LAPSE_THRESHOLD = 8;
export const LEECH_REPEAT_EVERY = 4;
export const DEFAULT_ROLLOVER_HOUR = 4;

export function isLeechLapse(prevLapses: number, nextLapses: number): boolean {
  if (nextLapses <= prevLapses || nextLapses < LEECH_LAPSE_THRESHOLD) return false;
  return (nextLapses - LEECH_LAPSE_THRESHOLD) % LEECH_REPEAT_EVERY === 0;
}

/**
 * ts-fsrs counts elapsed days on UTC calendar dates. Shifting every timestamp we hand it by
 * (local offset - rollover hour) makes its "UTC day" equal the user's local study day, so a
 * learning session that crosses 00:00 UTC (4 pm PST) is no longer treated as a multi-day gap.
 */
export function studyDayShiftMs(tzOffsetMin: number, rolloverHour: number = DEFAULT_ROLLOVER_HOUR): number {
  return -tzOffsetMin * 60_000 - rolloverHour * 3_600_000;
}
export const VOLATILE_STALE_MONTHS = 24;
export const MATURE_STABILITY_DAYS = 21;

export function gradeNameToRating(grade: GradeName): Grade {
  switch (grade) {
    case 'Again':
      return Rating.Again;
    case 'Hard':
      return Rating.Hard;
    case 'Good':
      return Rating.Good;
    case 'Easy':
      return Rating.Easy;
  }
}

export function getEffectiveRetention(settings: UserSettings, module: ModuleId): number {
  return settings.module_retention_overrides[module] ?? settings.desired_retention;
}

export function createScheduler(desiredRetention: number) {
  return fsrs({
    request_retention: desiredRetention,
    enable_fuzz: true,
    enable_short_term: true,
  });
}

export function createInitialItemState(params: {
  entity_id: string;
  dimension_id: string;
  task_type: CanonicalTaskType;
  module: ModuleId;
  now: Date;
}): ItemState {
  const empty = createEmptyCard(params.now);
  return {
    item_key: makeItemKey(params.entity_id, params.dimension_id, params.task_type),
    entity_id: params.entity_id,
    dimension_id: params.dimension_id,
    task_type: params.task_type,
    module: params.module,
    due: empty.due.toISOString(),
    stability: empty.stability,
    difficulty: empty.difficulty,
    elapsed_days: empty.elapsed_days,
    scheduled_days: empty.scheduled_days,
    learning_steps: empty.learning_steps,
    reps: empty.reps,
    lapses: empty.lapses,
    state: empty.state,
    last_review: empty.last_review ? empty.last_review.toISOString() : null,
    suspended: false,
    suspend_reason: null,
    last_error: null,
    last_signed_error: null,
  };
}

function itemStateToCard(state: ItemState): Card {
  return {
    due: new Date(state.due),
    stability: state.stability,
    difficulty: state.difficulty,
    elapsed_days: state.elapsed_days,
    scheduled_days: state.scheduled_days,
    learning_steps: state.learning_steps,
    reps: state.reps,
    lapses: state.lapses,
    state: state.state as State,
    last_review: state.last_review ? new Date(state.last_review) : undefined,
  };
}

/**
 * Pure FSRS step + Leech auto-suspend hygiene rule (Design Doc §4 & §7 #2).
 * Given a previous ItemState and a canonical review entry, returns the next ItemState.
 */
export function applyCanonicalReview(params: {
  prev: ItemState;
  grade: GradeName;
  error: number;
  signedError: number;
  now: Date;
  desiredRetention: number;
  /** Date#getTimezoneOffset() at review time; defaults to the device's offset for `now`. */
  tzOffsetMin?: number;
  rolloverHour?: number;
}): ItemState {
  const { prev, grade, error, signedError, now, desiredRetention } = params;
  const shift = studyDayShiftMs(params.tzOffsetMin ?? now.getTimezoneOffset(), params.rolloverHour);
  const sh = (d: Date) => new Date(d.getTime() + shift);
  const unsh = (d: Date) => new Date(d.getTime() - shift);

  const scheduler = createScheduler(desiredRetention);
  const raw = itemStateToCard(prev);
  const card: Card = {
    ...raw,
    due: sh(raw.due),
    last_review: raw.last_review ? sh(raw.last_review) : undefined,
  };
  const record = scheduler.repeat(card, sh(now));
  const shifted = record[gradeNameToRating(grade)].card;
  const nextCard: Card = {
    ...shifted,
    due: unsh(shifted.due),
    last_review: shifted.last_review ? unsh(shifted.last_review) : undefined,
  };

  const isLeech = isLeechLapse(prev.lapses, nextCard.lapses);

  return {
    ...prev,
    due: nextCard.due.toISOString(),
    stability: nextCard.stability,
    difficulty: nextCard.difficulty,
    elapsed_days: nextCard.elapsed_days,
    scheduled_days: nextCard.scheduled_days,
    learning_steps: nextCard.learning_steps,
    reps: nextCard.reps,
    lapses: nextCard.lapses,
    state: nextCard.state,
    last_review: nextCard.last_review ? nextCard.last_review.toISOString() : now.toISOString(),
    suspended: isLeech ? true : prev.suspended,
    suspend_reason: isLeech ? 'leech' : prev.suspend_reason,
    last_error: Number.isFinite(error) ? error : null,
    last_signed_error: Number.isFinite(signedError) ? signedError : null,
  };
}

/**
 * Checks whether a volatile fact/card is stale (> 24 months old relative to `now`).
 */
export function isVolatileStale(asOf: string | undefined, volatile: boolean | undefined, now: Date): boolean {
  if (!volatile || !asOf) return false;
  const parsed = new Date(asOf.length === 4 ? `${asOf}-01-01T00:00:00Z` : asOf);
  if (Number.isNaN(parsed.getTime())) return false;
  const monthsDiff =
    (now.getUTCFullYear() - parsed.getUTCFullYear()) * 12 +
    (now.getUTCMonth() - parsed.getUTCMonth()) +
    (now.getUTCDate() - parsed.getUTCDate()) / 30;
  return monthsDiff > VOLATILE_STALE_MONTHS;
}

export function isMatureItem(state: ItemState | undefined): boolean {
  if (!state || state.suspended) return false;
  return state.state === State.Review && state.stability >= MATURE_STABILITY_DAYS;
}

/**
 * Rebuilds the full `item_state` map purely by replaying the append-only `review_log`
 * (Design Doc §3 & M2 acceptance test: "replaying review_log reproduces item_state exactly").
 */
export function replayReviewLog(params: {
  logs: ReviewLogEntry[];
  settings: UserSettings;
  content?: CompiledContent;
}): Map<string, ItemState> {
  const { logs, settings } = params;
  const sorted = [...logs].sort((a, b) => {
    const dt = new Date(a.ts).getTime() - new Date(b.ts).getTime();
    if (dt !== 0) return dt;
    return (a.id ?? 0) - (b.id ?? 0);
  });

  const states = new Map<string, ItemState>();

  for (const log of sorted) {
    // Ratio probes are unscored detectors and never touch FSRS state
    if (log.is_probe || log.task_type === 'ratio_probe') {
      continue;
    }

    const parts = log.item_key.split('::');
    const entityId = parts[0];
    const dimensionId = parts[1] ?? log.dimension_id;
    const taskType = (parts[2] ?? log.task_type) as CanonicalTaskType;
    const reviewTime = new Date(log.ts);

    let prev = states.get(log.item_key);
    if (!prev) {
      prev = createInitialItemState({
        entity_id: entityId,
        dimension_id: dimensionId,
        task_type: taskType,
        module: log.module,
        now: reviewTime,
      });
    }

    const retention = getEffectiveRetention(settings, log.module);
    const next = applyCanonicalReview({
      prev,
      grade: log.grade,
      error: log.error,
      signedError: log.signed_error,
      now: reviewTime,
      desiredRetention: retention,
      tzOffsetMin: log.tz_offset_min,
      rolloverHour: settings.rollover_hour,
    });
    states.set(log.item_key, next);
  }

  return states;
}
