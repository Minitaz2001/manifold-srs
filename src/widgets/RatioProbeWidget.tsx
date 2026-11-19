import { useEffect, useMemo, useRef, useState } from 'react';
import type { RatioProbeQueueItem } from '../core/queue';
import { evaluateRatioProbe, formatQuantity } from '../core/grading';
import { nowMs, triggerHaptic } from '../platform';

export interface RatioProbeCompletePayload {
  hit: boolean;
  guessed_ratio: number;
  true_ratio: number;
  log_error: number;
  signed_error: number;
  latency_ms: number;
  prompt_json: string;
}

interface RatioProbeWidgetProps {
  probe: RatioProbeQueueItem;
  onComplete: (payload: RatioProbeCompletePayload) => void;
}

const REVEAL_MS = 1400;

/**
 * Unscored ratio probe detector (Design Doc §4):
 * Shown at most once per session between two mature non-colliding items.
 * Never alters FSRS directly — on miss, queues both items for canonical follow-up in 1–2 days.
 */
export function RatioProbeWidget({ probe, onComplete }: RatioProbeWidgetProps) {
  const startTimeRef = useRef<number>(nowMs());
  const timerRef = useRef<number | null>(null);
  const [result, setResult] = useState<RatioProbeCompletePayload | null>(null);

  const trueRatio = probe.factA.value / probe.factB.value;

  // Build 6 clean logarithmic ratio pills bracketing the true ratio without giving it away
  const ratioOptions = useMemo(() => {
    const ladder = [1.5, 2, 3, 5, 10, 20, 50, 100, 300, 1000, 3000, 10000, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10];
    let nearestIdx = 0;
    let bestDist = Infinity;
    for (let i = 0; i < ladder.length; i++) {
      const d = Math.abs(Math.log10(ladder[i] / trueRatio));
      if (d < bestDist) {
        bestDist = d;
        nearestIdx = i;
      }
    }
    const start = Math.max(0, Math.min(ladder.length - 6, nearestIdx - 2));
    return ladder.slice(start, start + 6);
  }, [trueRatio]);

  useEffect(() => {
    startTimeRef.current = nowMs();
    setResult(null);
    return () => {
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [probe.item_key]);

  const formatRatio = (r: number) => {
    if (r >= 1e9) return `${(r / 1e9).toPrecision(2).replace(/\.0+$/, '')}B×`;
    if (r >= 1e6) return `${(r / 1e6).toPrecision(2).replace(/\.0+$/, '')}M×`;
    if (r >= 1e4) return `${(r / 1e3).toPrecision(2).replace(/\.0+$/, '')}k×`;
    return `${Number(r.toPrecision(2))}×`;
  };

  const advanceNow = (p: RatioProbeCompletePayload) => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    onComplete(p);
  };

  const handlePick = (guess: number) => {
    if (result) return;
    const latencyMs = Math.round(nowMs() - startTimeRef.current);
    const ev = evaluateRatioProbe({
      truthA: probe.factA.value,
      truthB: probe.factB.value,
      guessedRatio: guess,
      toleranceFactor: probe.dimension.scale === 'log' ? probe.dimension.tolerance : 2,
    });
    triggerHaptic(ev.hit ? 'success' : 'error');

    const payload: RatioProbeCompletePayload = {
      hit: ev.hit,
      guessed_ratio: guess,
      true_ratio: ev.trueRatio,
      log_error: ev.logError,
      signed_error: ev.signedError,
      latency_ms: latencyMs,
      prompt_json: JSON.stringify({
        entityA: probe.entityA.id,
        entityB: probe.entityB.id,
        dimension_id: probe.dimension_id,
      }),
    };
    setResult(payload);
    timerRef.current = window.setTimeout(() => advanceNow(payload), REVEAL_MS);
  };

  return (
    <div
      className="widget-shell"
      onClick={() => {
        if (result) advanceNow(result);
      }}
    >
      <div className="prompt-zone">
        <div className="prompt-eyebrow">
          <span className="probe-pill">unscored ratio probe</span>
          <span className="dot-sep">·</span>
          <span>{probe.dimension.name}</span>
        </div>
        <h1 className="prompt-title ratio-title">
          <span>{probe.entityA.name}</span>
          <span className="ratio-divider">÷</span>
          <span>{probe.entityB.name}</span>
        </h1>

        {result ? (
          <div className="reveal-panel" role="status">
            <div className="reveal-row">
              <span className={`grade-badge ${result.hit ? 'grade-good' : 'grade-hard'}`}>
                {result.hit ? 'Calibrated' : 'Queued Check'}
              </span>
              <span className="truth-readout mono">≈ {formatRatio(result.true_ratio)}</span>
            </div>
            <p className="source-note">
              {formatQuantity(probe.factA.value, probe.dimension)} vs.{' '}
              {formatQuantity(probe.factB.value, probe.dimension)}.{' '}
              {result.hit
                ? 'Logged; FSRS untouched.'
                : 'FSRS untouched; both queued for canonical placement in 1–2 days.'}
            </p>
          </div>
        ) : (
          <div className="live-estimate">Roughly how many times larger?</div>
        )}
      </div>

      <div className="thumb-zone">
        <div className="choice-grid ratio-grid">
          {ratioOptions.map((opt) => (
            <button
              key={opt}
              type="button"
              disabled={!!result}
              className="choice-pill mono"
              onClick={(e) => {
                e.stopPropagation();
                handlePick(opt);
              }}
            >
              {formatRatio(opt)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
