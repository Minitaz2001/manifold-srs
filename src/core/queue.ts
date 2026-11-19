import type {
  CanonicalTaskType,
  CompiledContent,
  Dimension,
  Entity,
  Fact,
  Figure,
  FigureRegion,
  ModuleId,
  PlainCard,
} from '../types/content';
import {
  makeItemKey,
  type ItemState,
  type ProbeQueueEntry,
  type ReviewLogEntry,
  type UserSettings,
} from '../types/memory';
import { canonicalTaskTypeForDimension, isLogCollision } from './grading';
import { isMatureItem, isVolatileStale } from './scheduler';

export interface CanonicalQueueItem {
  kind: 'canonical';
  item_key: string;
  entity_id: string;
  dimension_id: string;
  task_type: CanonicalTaskType;
  module: ModuleId;
  is_new: boolean;
  is_probe_followup: boolean;
  entity?: Entity;
  dimension?: Dimension;
  fact?: Fact;
  figure?: Figure;
  region?: FigureRegion;
  plain_card?: PlainCard;
  state?: ItemState;
}

export interface RatioProbeQueueItem {
  kind: 'ratio_probe';
  item_key: string;
  dimension_id: string;
  module: ModuleId;
  dimension: Dimension;
  entityA: Entity;
  factA: Fact;
  itemKeyA: string;
  entityB: Entity;
  factB: Fact;
  itemKeyB: string;
}

export type SessionQueueItem = CanonicalQueueItem | RatioProbeQueueItem;

export interface DailyQueueResult {
  queue: SessionQueueItem[];
  due_today_capped: number;
  new_today_capped: number;
  done_today: number;
  stale_suspended_keys: string[];
}

/** Max supplemental scale drills unlocked per day (they never count against the new-card cap). */
export const DRILL_UNLOCKS_PER_DAY = 5;

/** A flashcard counts as learned once it has graduated out of FSRS learning steps into Review. */
export function isFlashLearned(st: ItemState | undefined): boolean {
  return !!st && !st.suspended && st.reps >= 2 && st.state === 2;
}

function isDrillTask(t: CanonicalTaskType): boolean {
  return t === 'place' || t === 'place_timeline';
}

export function startOfLocalDay(now: Date): number {
  const d = new Date(now);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

/**
 * Enumerates every schedulable canonical item from compiled static content packs.
 * - Every Fact produces a `flash` item (learn the number as a normal flashcard) AND a supplemental
 *   scale drill (`place` / `place_timeline`) that only unlocks once the flashcard is learned.
 * - Every Figure region produces one `occlude` item keyed to `(figure.id:region.region_id, figure.dimension_id, occlude)`.
 * - Every PlainCard produces one `recall` item keyed to `(card.id, plain_card, recall)`.
 */
export function enumerateCanonicalItems(content: CompiledContent): CanonicalQueueItem[] {
  const items: CanonicalQueueItem[] = [];

  for (const fact of content.facts) {
    const entity = content.entities.get(fact.entity_id);
    const dimension = content.dimensions.get(fact.dimension_id);
    if (!entity || !dimension) continue;
    items.push({
      kind: 'canonical',
      item_key: makeItemKey(fact.entity_id, fact.dimension_id, 'flash'),
      entity_id: fact.entity_id,
      dimension_id: fact.dimension_id,
      task_type: 'flash',
      module: entity.module,
      is_new: true,
      is_probe_followup: false,
      entity,
      dimension,
      fact,
    });
    const taskType = canonicalTaskTypeForDimension(dimension.scale);
    items.push({
      kind: 'canonical',
      item_key: makeItemKey(fact.entity_id, fact.dimension_id, taskType),
      entity_id: fact.entity_id,
      dimension_id: fact.dimension_id,
      task_type: taskType,
      module: entity.module,
      is_new: true,
      is_probe_followup: false,
      entity,
      dimension,
      fact,
    });
  }

  for (const figure of content.figures.values()) {
    const dimension = content.dimensions.get(figure.dimension_id);
    if (!dimension) continue;
    for (const region of figure.regions) {
      const entityId = `${figure.id}__${region.region_id}`;
      items.push({
        kind: 'canonical',
        item_key: makeItemKey(entityId, figure.dimension_id, 'occlude'),
        entity_id: entityId,
        dimension_id: figure.dimension_id,
        task_type: 'occlude',
        module: figure.module,
        is_new: true,
        is_probe_followup: false,
        entity: region.entity_id ? content.entities.get(region.entity_id) : undefined,
        dimension,
        figure,
        region,
      });
    }
  }

  for (const card of content.plainCards.values()) {
    items.push({
      kind: 'canonical',
      item_key: makeItemKey(card.id, 'plain_card', 'recall'),
      entity_id: card.id,
      dimension_id: 'plain_card',
      task_type: 'recall',
      module: card.module,
      is_new: true,
      is_probe_followup: false,
      entity: card.entity_id ? content.entities.get(card.entity_id) : undefined,
      plain_card: card,
    });
  }

  return items;
}

/**
 * Deterministic seeded PRNG (Mulberry32) so interleaving is testable and repeatable per day.
 */
function mulberry32(seed: number): () => number {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Hygiene Rule #1 (Interleave):
 * Shuffles items subject to:
 * - Never 2 consecutive items from the same `dimension_id`
 * - Never > 3 consecutive items from the same `module`
 * Falls back gracefully only when remaining items make satisfying both impossible.
 */
export function interleaveItems<T extends { dimension_id: string; module: ModuleId }>(
  items: T[],
  seed = 42
): T[] {
  const rand = mulberry32(seed);
  const pool = [...items];
  // Fisher-Yates shuffle first
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }

  const result: T[] = [];
  while (pool.length > 0) {
    const lastDim = result.length > 0 ? result[result.length - 1].dimension_id : null;
    let consecutiveMod = 0;
    const lastMod = result.length > 0 ? result[result.length - 1].module : null;
    if (lastMod) {
      for (let k = result.length - 1; k >= 0 && result[k].module === lastMod; k--) {
        consecutiveMod++;
      }
    }

    // Tier 1: satisfies BOTH dimension and module constraints
    let pickIdx = pool.findIndex(
      (item) =>
        item.dimension_id !== lastDim &&
        !(consecutiveMod >= 3 && item.module === lastMod)
    );
    // Tier 2: satisfies dimension constraint only
    if (pickIdx === -1) {
      pickIdx = pool.findIndex((item) => item.dimension_id !== lastDim);
    }
    // Tier 3: satisfies module constraint only
    if (pickIdx === -1) {
      pickIdx = pool.findIndex((item) => !(consecutiveMod >= 3 && item.module === lastMod));
    }
    // Tier 4: unavoidable fallback
    if (pickIdx === -1) {
      pickIdx = 0;
    }

    result.push(pool.splice(pickIdx, 1)[0]);
  }

  return result;
}

/**
 * Selects at most ONE ratio probe per session from two mature items on the same
 * log/linear dimension that do not violate the 1.2x anti-collision rule (#5).
 */
export function selectRatioProbe(params: {
  content: CompiledContent;
  states: Map<string, ItemState>;
  seed: number;
}): RatioProbeQueueItem | null {
  const { content, states, seed } = params;
  const rand = mulberry32(seed + 997);

  const candidates: RatioProbeQueueItem[] = [];
  for (const [dimId, dimFacts] of content.factsByDimension.entries()) {
    const dimension = content.dimensions.get(dimId);
    if (!dimension || (dimension.scale !== 'log' && dimension.scale !== 'linear')) continue;

    const matureFacts = dimFacts.filter((f) => {
      const key = makeItemKey(f.entity_id, f.dimension_id, canonicalTaskTypeForDimension(dimension.scale));
      return isMatureItem(states.get(key)) && f.value > 0;
    });

    if (matureFacts.length < 2) continue;

    for (let i = 0; i < matureFacts.length; i++) {
      for (let j = i + 1; j < matureFacts.length; j++) {
        const a = matureFacts[i];
        const b = matureFacts[j];
        if (dimension.scale === 'log' && isLogCollision(a.value, b.value)) continue;
        // Put larger value on top so ratio >= 1.2x is clean and intuitive
        const [hi, lo] = a.value >= b.value ? [a, b] : [b, a];
        const entityA = content.entities.get(hi.entity_id);
        const entityB = content.entities.get(lo.entity_id);
        if (!entityA || !entityB) continue;

        const taskType = canonicalTaskTypeForDimension(dimension.scale);
        candidates.push({
          kind: 'ratio_probe',
          item_key: `probe::${hi.entity_id}::${lo.entity_id}::${dimId}`,
          dimension_id: dimId,
          module: entityA.module,
          dimension,
          entityA,
          factA: hi,
          itemKeyA: makeItemKey(hi.entity_id, dimId, taskType),
          entityB,
          factB: lo,
          itemKeyB: makeItemKey(lo.entity_id, dimId, taskType),
        });
      }
    }
  }

  if (candidates.length === 0) return null;
  const idx = Math.floor(rand() * candidates.length);
  return candidates[idx];
}

/**
 * Builds today's session queue enforcing:
 * - Caps: settings.new_per_day (10), settings.reviews_per_day (120)
 * - Never exposes backlog larger than today's remaining cap
 * - Volatile >24mo stale items automatically excluded & reported for suspension
 * - Probe queue due items prioritized into today's due reviews
 * - Interleaving rule (#1)
 * - At most 1 ratio probe per session if mature pairs exist and no probe ran today
 */
export function buildDailyQueue(params: {
  content: CompiledContent;
  states: Map<string, ItemState>;
  probes: ProbeQueueEntry[];
  todayLogs: ReviewLogEntry[];
  allLogs?: ReviewLogEntry[];
  settings: UserSettings;
  now: Date;
}): DailyQueueResult {
  const { content, states, probes, todayLogs, allLogs, settings, now } = params;
  const nowTs = now.getTime();
  const dayStart = startOfLocalDay(now);
  const daySeed = Math.floor(dayStart / 86400000);

  const canonicalLogsToday = todayLogs.filter((l) => !l.is_probe && l.task_type !== 'ratio_probe');
  const probeRanToday = todayLogs.some((l) => l.is_probe || l.task_type === 'ratio_probe');

  // Count how many new items were FIRST introduced today (robust even if re-reviewed in learning steps today)
  let newIntroducedToday = 0;
  let drillsIntroducedToday = 0;
  if (allLogs) {
    const firstSeenByKey = new Map<string, number>();
    for (const log of allLogs) {
      if (log.is_probe || log.task_type === 'ratio_probe') continue;
      const t = new Date(log.ts).getTime();
      const prev = firstSeenByKey.get(log.item_key);
      if (prev === undefined || t < prev) firstSeenByKey.set(log.item_key, t);
    }
    for (const [key, firstTs] of firstSeenByKey.entries()) {
      if (firstTs < dayStart) continue;
      if (/::place(_timeline)?$/.test(key)) drillsIntroducedToday++;
      else newIntroducedToday++;
    }
  } else {
    const reviewedTodayKeys = new Set(canonicalLogsToday.map((l) => l.item_key));
    for (const key of reviewedTodayKeys) {
      const st = states.get(key);
      if (st && st.reps <= 1) newIntroducedToday++;
    }
  }

  const reviewsRemaining = Math.max(0, settings.reviews_per_day - canonicalLogsToday.length);
  const newRemaining = Math.max(0, settings.new_per_day - newIntroducedToday);

  const probeDueSet = new Set(
    probes.filter((p) => new Date(p.due_ts).getTime() <= nowTs).map((p) => p.item_key)
  );

  const allItems = enumerateCanonicalItems(content);
  const staleSuspendedKeys: string[] = [];
  const dueItems: CanonicalQueueItem[] = [];
  const newItems: CanonicalQueueItem[] = [];
  const newDrills: CanonicalQueueItem[] = [];

  for (const item of allItems) {
    const st = states.get(item.item_key);
    if (st?.suspended) continue;

    // Hygiene Rule #4: volatile facts > 24 months old (by as_of or content release_date) auto-suspend
    const asOf = item.fact?.as_of ?? item.plain_card?.as_of;
    const isVol = item.fact?.volatile ?? item.plain_card?.volatile ?? false;
    if (isVolatileStale(asOf, isVol, now) || isVolatileStale(content.releaseDate, isVol, now)) {
      staleSuspendedKeys.push(item.item_key);
      continue;
    }

    if (!st || st.reps === 0) {
      if (isDrillTask(item.task_type)) {
        // Supplemental: only once the plain flashcard for this fact is learned
        const flashKey = makeItemKey(item.entity_id, item.dimension_id, 'flash');
        if (isFlashLearned(states.get(flashKey))) newDrills.push({ ...item, is_new: true, state: st });
        continue;
      }
      newItems.push({ ...item, is_new: true, state: st });
    } else {
      const dueMs = new Date(st.due).getTime();
      const isProbeFollowup = probeDueSet.has(item.item_key);
      if (dueMs <= nowTs || isProbeFollowup) {
        dueItems.push({
          ...item,
          is_new: false,
          is_probe_followup: isProbeFollowup,
          state: st,
        });
      }
    }
  }

  // Sort due items: probe followups first, then earliest due
  dueItems.sort((a, b) => {
    if (a.is_probe_followup !== b.is_probe_followup) {
      return a.is_probe_followup ? -1 : 1;
    }
    const da = a.state ? new Date(a.state.due).getTime() : 0;
    const db = b.state ? new Date(b.state.due).getTime() : 0;
    return da - db;
  });

  // Balance new items across modules/dimensions before capping so Day 1 shows all widgets
  const balancedNew = interleaveItems(newItems, daySeed);

  const cappedDue = dueItems.slice(0, reviewsRemaining);
  const slotsLeftForNew = Math.max(0, reviewsRemaining - cappedDue.length);
  const cappedNew = balancedNew.slice(0, Math.min(newRemaining, slotsLeftForNew));
  const drillsRemaining = Math.max(0, DRILL_UNLOCKS_PER_DAY - drillsIntroducedToday);
  const slotsLeftForDrills = Math.max(0, slotsLeftForNew - cappedNew.length);
  const cappedDrills = interleaveItems(newDrills, daySeed + 5).slice(0, Math.min(drillsRemaining, slotsLeftForDrills));

  const combined = interleaveItems([...cappedDue, ...cappedNew, ...cappedDrills], daySeed + 17);
  const queue: SessionQueueItem[] = [...combined];

  if (!probeRanToday && queue.length >= 2) {
    const probe = selectRatioProbe({ content, states, seed: daySeed });
    if (probe) {
      const insertAt = Math.min(3, queue.length);
      queue.splice(insertAt, 0, probe);
    }
  }

  return {
    queue,
    due_today_capped: cappedDue.length,
    new_today_capped: cappedNew.length,
    done_today: canonicalLogsToday.length,
    stale_suspended_keys: staleSuspendedKeys,
  };
}
