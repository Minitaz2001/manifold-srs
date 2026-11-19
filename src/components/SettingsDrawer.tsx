import React, { useMemo, useRef, useState } from 'react';
import { MODULE_LABELS, type CompiledContent, type ModuleId } from '../types/content';
import type { InboxEntry, ItemState, ReviewLogEntry, UserSettings } from '../types/memory';
import { computeLatencyStats, computeModuleCalibration } from '../core/telemetry';
import { readFileAsText, shareOrDownloadJson } from '../platform';

interface SettingsDrawerProps {
  open: boolean;
  onClose: () => void;
  settings: UserSettings;
  content: CompiledContent;
  states: Map<string, ItemState>;
  logs: ReviewLogEntry[];
  inbox: InboxEntry[];
  staleKeys: string[];
  onExportBackup: () => Promise<void>;
  onImportBackupText: (jsonText: string) => Promise<void>;
  onUnsuspendItem: (itemKey: string) => Promise<void>;
  onRequestRewrite: (itemKey: string, label: string) => Promise<void>;
  onUpdateRetention: (module: ModuleId | 'global', retention: number | null) => Promise<void>;
  onUpdateCaps: (caps: { new_per_day?: number; reviews_per_day?: number }) => Promise<void>;
  onMarkInboxExported: () => Promise<void>;
}

function CalibrationSparkline({ points }: { points: { bucketLabel: string; medianAbsError: number }[] }) {
  if (points.length === 0) {
    return <div className="spark-empty">no placement reviews yet</div>;
  }
  const W = 260;
  const H = 64;
  const pad = 8;
  const maxVal = Math.max(0.5, ...points.map((p) => p.medianAbsError));
  const stepX = points.length > 1 ? (W - pad * 2) / (points.length - 1) : 0;

  const coords = points.map((p, i) => {
    const x = points.length === 1 ? W / 2 : pad + i * stepX;
    const y = H - pad - (Math.min(maxVal, p.medianAbsError) / maxVal) * (H - pad * 2);
    return { x, y };
  });

  const pathD = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="spark-svg" aria-label="Median error over time">
      <line x1={pad} y1={H - pad} x2={W - pad} y2={H - pad} stroke="var(--border)" strokeWidth="1" />
      <path d={pathD} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
      {coords.map((c, idx) => (
        <circle key={idx} cx={c.x} cy={c.y} r="3" fill="var(--accent)" />
      ))}
    </svg>
  );
}

export function SettingsDrawer({
  open,
  onClose,
  settings,
  content,
  states,
  logs,
  inbox,
  staleKeys,
  onExportBackup,
  onImportBackupText,
  onUnsuspendItem,
  onRequestRewrite,
  onUpdateRetention,
  onUpdateCaps,
  onMarkInboxExported,
}: SettingsDrawerProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const latency = useMemo(() => computeLatencyStats(logs), [logs]);
  const modules: ModuleId[] = ['geography', 'physics', 'natural_world', 'are_built'];
  const calibrations = useMemo(
    () => modules.map((m) => computeModuleCalibration(logs, m)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [logs]
  );

  const leeches = useMemo(
    () => Array.from(states.values()).filter((s) => s.suspended && (s.suspend_reason === 'leech' || s.suspend_reason === 'manual')),
    [states]
  );

  if (!open) return null;

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await readFileAsText(file);
      await onImportBackupText(text);
      setStatusMsg('Backup restored.');
    } catch (err) {
      setStatusMsg(`Import failed: ${(err as Error).message}`);
    } finally {
      e.target.value = '';
    }
  };

  const handleExportInbox = async () => {
    const json = JSON.stringify(inbox, null, 2);
    try {
      await shareOrDownloadJson(`manifold-inbox-${new Date().toISOString().slice(0, 10)}.json`, json);
      await onMarkInboxExported();
      setStatusMsg(`Exported ${inbox.length} pull-lane notes.`);
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setStatusMsg(`Inbox export failed: ${(err as Error).message}`);
      }
    }
  };

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer-sheet" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Settings and Telemetry">
        <div className="drawer-header">
          <h2>Diagnostics & Settings</h2>
          <button type="button" className="icon-btn" onClick={onClose}>
            Done
          </button>
        </div>

        {statusMsg && <div className="status-toast">{statusMsg}</div>}

        {/* Storage & Backup */}
        <section className="settings-section">
          <h3>Storage & Backup</h3>
          <div className="kv-row">
            <span>Persistent storage</span>
            <span className={`mono ${settings.persist_granted ? 'ok-text' : 'warn-text'}`}>
              {settings.persist_granted === null
                ? 'checking'
                : settings.persist_granted
                  ? 'granted'
                  : 'not granted'}
            </span>
          </div>
          <div className="kv-row">
            <span>Total logged reviews</span>
            <span className="mono">{logs.length}</span>
          </div>
          <div className="kv-row">
            <span>Since last backup</span>
            <span className="mono">{settings.reviews_since_backup} reviews</span>
          </div>
          <div className="kv-row">
            <span>Last backup</span>
            <span className="mono">
              {settings.last_backup_ts ? settings.last_backup_ts.slice(0, 10) : 'never'}
            </span>
          </div>
          <div className="btn-row">
            <button
              type="button"
              className="btn-primary small"
              onClick={async () => {
                try {
                  await onExportBackup();
                  setStatusMsg('Backup exported.');
                } catch (err) {
                  if ((err as Error).name !== 'AbortError') {
                    setStatusMsg(`Export failed: ${(err as Error).message}`);
                  }
                }
              }}
            >
              Export JSON
            </button>
            <button
              type="button"
              className="btn-secondary small"
              onClick={() => fileInputRef.current?.click()}
            >
              Import JSON
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/json,.json"
              style={{ display: 'none' }}
              onChange={handleImportFile}
            />
          </div>
        </section>

        {/* Latency */}
        <section className="settings-section">
          <h3>Review Latency (7d Median)</h3>
          <div className="kv-row">
            <span>Session median</span>
            <span className="mono">
              {latency.overallMedianMs !== null ? `${(latency.overallMedianMs / 1000).toFixed(2)}s` : '—'}
            </span>
          </div>
          {latency.byWidget.map((w) => (
            <div key={w.task_type} className="kv-row">
              <span className="mono">{w.task_type}</span>
              <span className={`mono ${w.flaggedForRedesign ? 'warn-text' : ''}`}>
                {w.medianMs !== null ? `${(w.medianMs / 1000).toFixed(2)}s` : '—'}
                {w.flaggedForRedesign ? ' · >6s flag' : ''}
              </span>
            </div>
          ))}
        </section>

        {/* Calibration Telemetry */}
        <section className="settings-section">
          <h3>Calibration by Module</h3>
          {calibrations.map((cal) => (
            <div key={cal.module} className="cal-card">
              <div className="cal-header">
                <span>{MODULE_LABELS[cal.module]}</span>
                <span className="mono">
                  {cal.medianAbsError !== null
                    ? `err ${cal.medianAbsError.toFixed(2)} · bias ${cal.medianBias! >= 0 ? '+' : ''}${cal.medianBias!.toFixed(2)}`
                    : '—'}
                </span>
              </div>
              <CalibrationSparkline points={cal.series} />
            </div>
          ))}
        </section>

        {/* FSRS Settings */}
        <section className="settings-section">
          <h3>FSRS Scheduling</h3>
          <div className="kv-row">
            <span>New cards / day</span>
            <div className="stepper">
              <button type="button" className="seg-btn" aria-label="Fewer new cards"
                onClick={() => onUpdateCaps({ new_per_day: Math.max(0, settings.new_per_day - 5) })}>−</button>
              <span className="mono stepper-val">{settings.new_per_day}</span>
              <button type="button" className="seg-btn" aria-label="More new cards"
                onClick={() => onUpdateCaps({ new_per_day: Math.min(100, settings.new_per_day + 5) })}>+</button>
            </div>
          </div>
          <div className="kv-row">
            <span>Reviews / day</span>
            <div className="stepper">
              <button type="button" className="seg-btn" aria-label="Fewer reviews"
                onClick={() => onUpdateCaps({ reviews_per_day: Math.max(10, settings.reviews_per_day - 20) })}>−</button>
              <span className="mono stepper-val">{settings.reviews_per_day}</span>
              <button type="button" className="seg-btn" aria-label="More reviews"
                onClick={() => onUpdateCaps({ reviews_per_day: Math.min(500, settings.reviews_per_day + 20) })}>+</button>
            </div>
          </div>
          <div className="kv-row">
            <span>Desired retention (global)</span>
            <div className="seg-row">
              {[0.85, 0.9].map((r) => (
                <button
                  key={r}
                  type="button"
                  className={`seg-btn ${settings.desired_retention === r ? 'active' : ''}`}
                  onClick={() => onUpdateRetention('global', r)}
                >
                  {Math.round(r * 100)}%
                </button>
              ))}
            </div>
          </div>
          <div className="kv-row">
            <span>ARE module override</span>
            <div className="seg-row">
              <button
                type="button"
                className={`seg-btn ${!settings.module_retention_overrides.are_built ? 'active' : ''}`}
                onClick={() => onUpdateRetention('are_built', null)}
              >
                default
              </button>
              <button
                type="button"
                className={`seg-btn ${settings.module_retention_overrides.are_built === 0.9 ? 'active' : ''}`}
                onClick={() => onUpdateRetention('are_built', 0.9)}
              >
                90%
              </button>
            </div>
          </div>
        </section>

        {/* Leeches & Stale */}
        <section className="settings-section">
          <h3>Hygiene ({leeches.length} suspended · {staleKeys.length} stale)</h3>
          {leeches.length === 0 ? (
            <p className="muted-note">Nothing suspended (leeches auto-suspend at 8 lapses; Suspend on a card puts it here too).</p>
          ) : (
            <div className="leech-list">
              {leeches.map((l) => {
                const entity = content.entities.get(l.entity_id);
                const label = entity?.name ?? l.entity_id;
                return (
                  <div key={l.item_key} className="leech-row">
                    <div>
                      <div className="leech-name">{label}</div>
                      <div className="leech-meta mono">
                        {l.dimension_id} · {l.suspend_reason === 'manual' ? 'suspended by you' : `${l.lapses} lapses`}
                      </div>
                    </div>
                    <div className="btn-row compact">
                      <button
                        type="button"
                        className="btn-secondary tiny"
                        onClick={() => onRequestRewrite(l.item_key, label)}
                      >
                        Rewrite
                      </button>
                      <button
                        type="button"
                        className="btn-secondary tiny"
                        onClick={() => onUnsuspendItem(l.item_key)}
                      >
                        Restore
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Pull-lane Inbox Export */}
        <section className="settings-section">
          <h3>Pull-Lane Inbox ({inbox.length} notes)</h3>
          <button
            type="button"
            className="btn-secondary small"
            disabled={inbox.length === 0}
            onClick={handleExportInbox}
          >
            Export Inbox JSON
          </button>
        </section>
      </div>
    </div>
  );
}
