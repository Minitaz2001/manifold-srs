import { useCallback, useEffect, useMemo, useState } from 'react';
import { getBundledContent } from './content/loader';
import { db, getOrInitSettings } from './db/database';
import {
  applyCanonicalReview,
  createInitialItemState,
  getEffectiveRetention,
  isMatureItem,
} from './core/scheduler';
import {
  buildDailyQueue,
  startOfLocalDay,
  type CanonicalQueueItem,
  type RatioProbeQueueItem,
  type SessionQueueItem,
} from './core/queue';
import { exportFullBackup, importFullBackup, shouldPromptBackup } from './core/backup';
import type { RulerAnchor } from './core/grading';
import type { ModuleId } from './types/content';
import type {
  InboxEntry,
  ItemState,
  ProbeQueueEntry,
  ReviewLogEntry,
  UserSettings,
} from './types/memory';
import { requestPersistentStorage, shareOrDownloadJson } from './platform';
import { RulerWidget, type RulerCompletePayload } from './widgets/RulerWidget';
import { OccludeWidget, type OccludeCompletePayload } from './widgets/OccludeWidget';
import { PlainCardWidget, type PlainCardCompletePayload } from './widgets/PlainCardWidget';
import { FlashWidget, type FlashCompletePayload } from './widgets/FlashWidget';
import { RatioProbeWidget, type RatioProbeCompletePayload } from './widgets/RatioProbeWidget';
import { SettingsDrawer } from './components/SettingsDrawer';
import { InboxModal } from './components/InboxModal';

export function App() {
  const content = useMemo(() => getBundledContent(), []);

  const [ready, setReady] = useState(false);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [states, setStates] = useState<Map<string, ItemState>>(new Map());
  const [logs, setLogs] = useState<ReviewLogEntry[]>([]);
  const [probes, setProbes] = useState<ProbeQueueEntry[]>([]);
  const [inbox, setInbox] = useState<InboxEntry[]>([]);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [inboxOpen, setInboxOpen] = useState(false);
  const [dismissPersistBanner, setDismissPersistBanner] = useState(false);
  const [dismissBackupBanner, setDismissBackupBanner] = useState(false);

  const loadAllFromDb = useCallback(async () => {
    const [stList, logList, probeList, inboxList, userSettings] = await Promise.all([
      db.item_state.toArray(),
      db.review_log.orderBy('id').toArray(),
      db.probe_queue.toArray(),
      db.inbox.orderBy('id').toArray(),
      getOrInitSettings(db),
    ]);

    setStates(new Map(stList.map((s) => [s.item_key, s])));
    setLogs(logList);
    setProbes(probeList);
    setInbox(inboxList);
    setSettings(userSettings);
    setReady(true);

    // On first launch, request persistent storage (Design Doc §2 Req 3)
    if (userSettings.persist_granted === null) {
      const granted = await requestPersistentStorage();
      const updated: UserSettings = { ...userSettings, persist_granted: granted };
      await db.settings.put(updated);
      setSettings(updated);
    }
  }, []);

  useEffect(() => {
    void loadAllFromDb();
  }, [loadAllFromDb]);

  const now = useMemo(() => new Date(), [logs.length, states.size]);

  const todayLogs = useMemo(() => {
    const dayStart = startOfLocalDay(now);
    return logs.filter((l) => new Date(l.ts).getTime() >= dayStart);
  }, [logs, now]);

  const daily = useMemo(() => {
    if (!settings) return null;
    return buildDailyQueue({
      content,
      states,
      probes,
      todayLogs,
      allLogs: logs,
      settings,
      now,
    });
  }, [content, states, probes, todayLogs, logs, settings, now]);

  const currentItem: SessionQueueItem | null = daily && daily.queue.length > 0 ? daily.queue[0] : null;

  // Resolve candidate anchors for a Ruler item: prefer mature anchors from anchor_set,
  // falling back to all anchors in anchor_set so Day 1 rulers always bracket truth cleanly.
  const getCandidateAnchors = useCallback(
    (item: CanonicalQueueItem): RulerAnchor[] => {
      const dimId = item.dimension_id;
      const anchorSet = content.anchorSets.get(dimId);
      const dimFacts = content.factsByDimension.get(dimId) ?? [];
      const factByEnt = new Map(dimFacts.map((f) => [f.entity_id, f]));

      const ids = anchorSet ? anchorSet.entity_ids : dimFacts.map((f) => f.entity_id);
      const matureAnchors: RulerAnchor[] = [];
      const allAnchors: RulerAnchor[] = [];

      for (const eid of ids) {
        const f = factByEnt.get(eid);
        const e = content.entities.get(eid);
        if (!f || !e) continue;
        const anchor: RulerAnchor = { entity_id: eid, name: e.name, value: f.value };
        allAnchors.push(anchor);
        const key = `${eid}::${dimId}::${item.task_type}`;
        if (isMatureItem(states.get(key))) {
          matureAnchors.push(anchor);
        }
      }

      return matureAnchors.length >= 2 ? matureAnchors : allAnchors;
    },
    [content, states]
  );

  const commitCanonicalReview = useCallback(
    async (
      item: CanonicalQueueItem,
      params: {
        response: string;
        error: number;
        signed_error: number;
        grade: 'Again' | 'Hard' | 'Good' | 'Easy';
        latency_ms: number;
        prompt_json: string;
      }
    ) => {
      if (!settings) return;
      const reviewNow = new Date();
      const prev =
        states.get(item.item_key) ??
        createInitialItemState({
          entity_id: item.entity_id,
          dimension_id: item.dimension_id,
          task_type: item.task_type,
          module: item.module,
          now: reviewNow,
        });

      const retention = getEffectiveRetention(settings, item.module);
      const nextState = applyCanonicalReview({
        prev,
        grade: params.grade,
        error: params.error,
        signedError: params.signed_error,
        now: reviewNow,
        desiredRetention: retention,
      });

      const logEntry: ReviewLogEntry = {
        item_key: item.item_key,
        ts: reviewNow.toISOString(),
        task_type: item.task_type,
        module: item.module,
        dimension_id: item.dimension_id,
        prompt_json: params.prompt_json,
        response: params.response,
        error: params.error,
        signed_error: params.signed_error,
        grade: params.grade,
        latency_ms: params.latency_ms,
      };

      const updatedSettings: UserSettings = {
        ...settings,
        reviews_since_backup: settings.reviews_since_backup + 1,
      };

      // Persist transactionally and update in-memory state immediately (<100ms confirm-to-next)
      let assignedId = Date.now();
      await db.transaction('rw', [db.item_state, db.review_log, db.probe_queue, db.settings], async () => {
        await db.item_state.put(nextState);
        assignedId = await db.review_log.add(logEntry);
        if (item.is_probe_followup) {
          await db.probe_queue.delete(item.item_key);
        }
        await db.settings.put(updatedSettings);
      });

      setStates((prevMap) => {
        const nextMap = new Map(prevMap);
        nextMap.set(nextState.item_key, nextState);
        return nextMap;
      });
      setLogs((prevLogs) => [...prevLogs, { ...logEntry, id: assignedId }]);
      if (item.is_probe_followup) {
        setProbes((prevProbes) => prevProbes.filter((p) => p.item_key !== item.item_key));
      }
      setSettings(updatedSettings);
    },
    [settings, states]
  );

  const handleRulerComplete = useCallback(
    (item: CanonicalQueueItem, p: RulerCompletePayload) => {
      void commitCanonicalReview(item, {
        response: p.answer === null ? 'skip' : String(p.answer),
        error: p.error,
        signed_error: p.signed_error,
        grade: p.grade,
        latency_ms: p.latency_ms,
        prompt_json: p.prompt_json,
      });
    },
    [commitCanonicalReview]
  );

  const handleOccludeComplete = useCallback(
    (item: CanonicalQueueItem, p: OccludeCompletePayload) => {
      void commitCanonicalReview(item, {
        response: p.selected_region_id ?? 'skip',
        error: p.error,
        signed_error: p.error,
        grade: p.grade,
        latency_ms: p.latency_ms,
        prompt_json: p.prompt_json,
      });
    },
    [commitCanonicalReview]
  );

  const handlePlainCardComplete = useCallback(
    (item: CanonicalQueueItem, p: PlainCardCompletePayload) => {
      void commitCanonicalReview(item, {
        response: p.grade,
        error: p.grade === 'Again' ? 1 : 0,
        signed_error: 0,
        grade: p.grade,
        latency_ms: p.latency_ms,
        prompt_json: p.prompt_json,
      });
    },
    [commitCanonicalReview]
  );

  const handleFlashComplete = useCallback(
    (item: CanonicalQueueItem, p: FlashCompletePayload) => {
      void commitCanonicalReview(item, {
        response: p.grade,
        error: p.grade === 'Again' ? 1 : 0,
        signed_error: 0,
        grade: p.grade,
        latency_ms: p.latency_ms,
        prompt_json: p.prompt_json,
      });
    },
    [commitCanonicalReview]
  );

  const handleRatioProbeComplete = useCallback(
    async (probe: RatioProbeQueueItem, p: RatioProbeCompletePayload) => {
      const reviewNow = new Date();
      const logEntry: ReviewLogEntry = {
        item_key: probe.item_key,
        ts: reviewNow.toISOString(),
        task_type: 'ratio_probe',
        module: probe.module,
        dimension_id: probe.dimension_id,
        prompt_json: p.prompt_json,
        response: String(p.guessed_ratio),
        error: p.log_error,
        signed_error: p.signed_error,
        grade: p.hit ? 'Good' : 'Again',
        latency_ms: p.latency_ms,
        is_probe: true,
      };

      const logId = await db.review_log.add(logEntry);
      const newProbes: ProbeQueueEntry[] = [];

      // Ratio probe miss NEVER grades FSRS; queues both items for 1–2 days out
      if (!p.hit) {
        const dueA = new Date(reviewNow.getTime() + 24 * 3600 * 1000).toISOString();
        const dueB = new Date(reviewNow.getTime() + 48 * 3600 * 1000).toISOString();
        newProbes.push(
          { item_key: probe.itemKeyA, due_ts: dueA, reason: 'ratio_miss', source_review_id: logId },
          { item_key: probe.itemKeyB, due_ts: dueB, reason: 'ratio_miss', source_review_id: logId }
        );
        await db.probe_queue.bulkPut(newProbes);
      }

      setLogs((prev) => [...prev, { ...logEntry, id: logId }]);
      if (newProbes.length > 0) {
        setProbes((prev) => {
          const map = new Map(prev.map((x) => [x.item_key, x]));
          for (const np of newProbes) map.set(np.item_key, np);
          return Array.from(map.values());
        });
      }
    },
    []
  );

  const handleExportBackup = useCallback(async () => {
    const payload = await exportFullBackup(db);
    const filename = `manifold-srs-backup-${payload.exported_at.slice(0, 10)}.json`;
    await shareOrDownloadJson(filename, JSON.stringify(payload, null, 2));
    if (settings) {
      const updated: UserSettings = {
        ...settings,
        last_backup_ts: payload.exported_at,
        reviews_since_backup: 0,
      };
      await db.settings.put(updated);
      setSettings(updated);
      setDismissBackupBanner(true);
    }
  }, [settings]);

  const handleImportBackupText = useCallback(
    async (jsonText: string) => {
      const parsed = JSON.parse(jsonText);
      await importFullBackup(db, parsed);
      await loadAllFromDb();
    },
    [loadAllFromDb]
  );

  const handleSaveInboxNote = useCallback(async (text: string) => {
    const entry: InboxEntry = {
      ts: new Date().toISOString(),
      text,
      related_item_key: currentItem?.item_key ?? null,
      reason: 'surprise',
      exported: false,
    };
    const id = await db.inbox.add(entry);
    setInbox((prev) => [...prev, { ...entry, id }]);
  }, [currentItem]);

  const handleRequestRewrite = useCallback(async (itemKey: string, label: string) => {
    const entry: InboxEntry = {
      ts: new Date().toISOString(),
      text: `Rewrite leech: ${label} (${itemKey})`,
      related_item_key: itemKey,
      reason: 'rewrite',
      exported: false,
    };
    const id = await db.inbox.add(entry);
    setInbox((prev) => [...prev, { ...entry, id }]);
  }, []);

  const handleUnsuspend = useCallback(async (itemKey: string) => {
    const st = states.get(itemKey);
    if (!st) return;
    const updated: ItemState = { ...st, suspended: false, suspend_reason: null };
    await db.item_state.put(updated);
    setStates((prev) => {
      const next = new Map(prev);
      next.set(itemKey, updated);
      return next;
    });
  }, [states]);

  const handleUpdateRetention = useCallback(
    async (module: ModuleId | 'global', retention: number | null) => {
      if (!settings) return;
      const next: UserSettings =
        module === 'global'
          ? { ...settings, desired_retention: retention ?? 0.85 }
          : {
              ...settings,
              module_retention_overrides: {
                ...settings.module_retention_overrides,
                [module]: retention ?? undefined,
              },
            };
      if (module !== 'global' && retention === null) {
        delete next.module_retention_overrides[module];
      }
      await db.settings.put(next);
      setSettings(next);
    },
    [settings]
  );

  const handleMarkInboxExported = useCallback(async () => {
    await db.inbox.toCollection().modify({ exported: true });
    setInbox((prev) => prev.map((x) => ({ ...x, exported: true })));
  }, []);

  if (!ready || !settings || !daily) {
    return (
      <main className="app-shell loading-shell">
        <span className="mono muted-note">loading manifold…</span>
      </main>
    );
  }

  const showPersistWarning =
    settings.persist_granted === false && !settings.persist_warned && !dismissPersistBanner;
  const showBackupPrompt = shouldPromptBackup(settings, now) && !dismissBackupBanner;

  const remainingCapped = daily.queue.length;

  return (
    <main className="app-shell">
      <header className="top-bar">
        <div className="top-bar-left">
          <span className="brand-mark">MANIFOLD</span>
          <span className="queue-counter mono" aria-label="Remaining today">
            {remainingCapped > 0 ? `${remainingCapped} left` : 'done'}
          </span>
        </div>
        <div className="top-bar-right">
          <button
            type="button"
            className="top-pill"
            onClick={() => setInboxOpen(true)}
          >
            + Surprised me
          </button>
          <button
            type="button"
            className="icon-btn"
            aria-label="Settings"
            onClick={() => setSettingsOpen(true)}
          >
            ⚙
          </button>
        </div>
      </header>

      {showPersistWarning && (
        <div className="notice-banner" role="alert">
          <span>Persistent storage wasn’t granted — back up periodically from Settings.</span>
          <button
            type="button"
            className="banner-btn"
            onClick={async () => {
              setDismissPersistBanner(true);
              const updated = { ...settings, persist_warned: true };
              await db.settings.put(updated);
              setSettings(updated);
            }}
          >
            OK
          </button>
        </div>
      )}

      {showBackupPrompt && (
        <div className="notice-banner">
          <span>Backup due ({settings.reviews_since_backup} reviews since last export).</span>
          <div className="btn-row compact">
            <button type="button" className="banner-btn primary" onClick={() => void handleExportBackup()}>
              Export
            </button>
            <button type="button" className="banner-btn" onClick={() => setDismissBackupBanner(true)}>
              Later
            </button>
          </div>
        </div>
      )}

      <section className="stage">
        {!currentItem ? (
          <div className="empty-state">
            <h1 className="done-title">Session complete</h1>
            <p className="muted-note">
              {daily.done_today} reviewed today. Queue caps ({settings.new_per_day} new / {settings.reviews_per_day} rev) reset tomorrow.
            </p>
            <div className="btn-row">
              <button type="button" className="btn-secondary small" onClick={() => setInboxOpen(true)}>
                + Surprised me
              </button>
              <button type="button" className="btn-secondary small" onClick={() => setSettingsOpen(true)}>
                Calibration & Backup
              </button>
            </div>
          </div>
        ) : currentItem.kind === 'ratio_probe' ? (
          <RatioProbeWidget
            key={currentItem.item_key}
            probe={currentItem}
            onComplete={(p) => void handleRatioProbeComplete(currentItem, p)}
          />
        ) : currentItem.task_type === 'flash' ? (
          <FlashWidget
            key={currentItem.item_key + (currentItem.is_new ? ':learn' : ':recall')}
            entity={currentItem.entity!}
            dimension={currentItem.dimension!}
            fact={currentItem.fact!}
            isNew={currentItem.is_new}
            onComplete={(p) => handleFlashComplete(currentItem, p)}
          />
        ) : currentItem.task_type === 'place' || currentItem.task_type === 'place_timeline' ? (
          <RulerWidget
            key={currentItem.item_key}
            entity={currentItem.entity!}
            dimension={currentItem.dimension!}
            fact={currentItem.fact!}
            candidateAnchors={getCandidateAnchors(currentItem)}
            allDimensionFacts={content.factsByDimension.get(currentItem.dimension_id) ?? []}
            isProbeFollowup={currentItem.is_probe_followup}
            onComplete={(p) => handleRulerComplete(currentItem, p)}
          />
        ) : currentItem.task_type === 'occlude' ? (
          <OccludeWidget
            key={currentItem.item_key}
            figure={currentItem.figure!}
            targetRegion={currentItem.region!}
            repCount={currentItem.state?.reps ?? 0}
            onComplete={(p) => handleOccludeComplete(currentItem, p)}
          />
        ) : (
          <PlainCardWidget
            key={currentItem.item_key}
            card={currentItem.plain_card!}
            onComplete={(p) => handlePlainCardComplete(currentItem, p)}
          />
        )}
      </section>

      <SettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        content={content}
        states={states}
        logs={logs}
        inbox={inbox}
        staleKeys={daily.stale_suspended_keys}
        onExportBackup={handleExportBackup}
        onImportBackupText={handleImportBackupText}
        onUnsuspendItem={handleUnsuspend}
        onRequestRewrite={handleRequestRewrite}
        onUpdateRetention={handleUpdateRetention}
        onMarkInboxExported={handleMarkInboxExported}
      />

      <InboxModal
        open={inboxOpen}
        onClose={() => setInboxOpen(false)}
        onSaveNote={handleSaveInboxNote}
      />
    </main>
  );
}
