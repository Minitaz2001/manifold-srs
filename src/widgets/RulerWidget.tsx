import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { Dimension, Entity, Fact } from '../types/content';
import type { GradeName } from '../types/memory';
import {
  formatQuantity,
  gradePlacement,
  positionToValue,
  selectRulerConfig,
  TIMEOUT_LATENCY_MS,
  valueToPosition,
  type PlacementGradeResult,
  type RulerAnchor,
} from '../core/grading';
import { nowMs, triggerHaptic } from '../platform';

export interface RulerCompletePayload {
  answer: number | null;
  error: number;
  signed_error: number;
  grade: GradeName;
  latency_ms: number;
  prompt_json: string;
}

interface RulerWidgetProps {
  entity: Entity;
  dimension: Dimension;
  fact: Fact;
  candidateAnchors: RulerAnchor[];
  allDimensionFacts: Fact[];
  isProbeFollowup?: boolean;
  onComplete: (payload: RulerCompletePayload) => void;
}

const REVEAL_MS = 1200;

export function RulerWidget({
  entity,
  dimension,
  fact,
  candidateAnchors,
  allDimensionFacts,
  isProbeFollowup,
  onComplete,
}: RulerWidgetProps) {
  const currentYear = new Date().getFullYear();

  const ruler = useMemo(
    () =>
      selectRulerConfig({
        dimension,
        targetFact: fact,
        candidateAnchors,
        allDimensionFacts,
        currentYear,
      }),
    [dimension, fact, candidateAnchors, allDimensionFacts, currentYear]
  );

  const trackRef = useRef<HTMLDivElement | null>(null);
  const startTimeRef = useRef<number>(nowMs());
  const revealTimerRef = useRef<number | null>(null);
  const finishedRef = useRef(false);

  const [markerPos, setMarkerPos] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);
  const [revealed, setRevealed] = useState<PlacementGradeResult | null>(null);
  const [revealPayload, setRevealPayload] = useState<RulerCompletePayload | null>(null);
  const [elapsedRatio, setElapsedRatio] = useState(0);

  // Reset when item changes
  useEffect(() => {
    startTimeRef.current = nowMs();
    finishedRef.current = false;
    setMarkerPos(null);
    setDragging(false);
    setRevealed(null);
    setRevealPayload(null);
    setElapsedRatio(0);
    return () => {
      if (revealTimerRef.current !== null) {
        window.clearTimeout(revealTimerRef.current);
      }
    };
  }, [entity.id, dimension.id]);

  // 10s timeout timer + hairline progress
  useEffect(() => {
    if (revealed) return;
    const id = window.setInterval(() => {
      const elapsed = nowMs() - startTimeRef.current;
      setElapsedRatio(Math.min(1, elapsed / TIMEOUT_LATENCY_MS));
      if (elapsed >= TIMEOUT_LATENCY_MS && !finishedRef.current) {
        window.clearInterval(id);
        submitAnswer(null, true);
      }
    }, 60);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealed, entity.id, dimension.id]);

  const posFromClientX = (clientX: number): number => {
    const el = trackRef.current;
    if (!el) return 0.5;
    const rect = el.getBoundingClientRect();
    return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
  };

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (revealed) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    setDragging(true);
    setMarkerPos(posFromClientX(e.clientX));
    triggerHaptic('light');
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging || revealed) return;
    setMarkerPos(posFromClientX(e.clientX));
  };

  const handlePointerUp = () => {
    setDragging(false);
  };

  const advanceNow = (payload: RulerCompletePayload) => {
    if (revealTimerRef.current !== null) {
      window.clearTimeout(revealTimerRef.current);
      revealTimerRef.current = null;
    }
    onComplete(payload);
  };

  const submitAnswer = (posOverride: number | null, skipped = false) => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    const latencyMs = Math.round(nowMs() - startTimeRef.current);
    const chosenPos = posOverride ?? markerPos;
    const answerVal =
      !skipped && chosenPos !== null
        ? positionToValue(chosenPos, ruler.min, ruler.max, dimension.scale)
        : null;

    const result = gradePlacement({
      dimension,
      fact,
      answer: answerVal,
      latencyMs,
      skipped,
      currentYear,
    });

    triggerHaptic(result.grade === 'Again' ? 'error' : 'success');

    const payload: RulerCompletePayload = {
      answer: answerVal,
      error: result.error,
      signed_error: result.signed_error,
      grade: result.grade,
      latency_ms: latencyMs,
      prompt_json: JSON.stringify({
        entity_id: entity.id,
        dimension_id: dimension.id,
        min: ruler.min,
        max: ruler.max,
        anchors: ruler.anchors.map((a) => ({ id: a.entity_id, value: a.value })),
      }),
    };

    setRevealed(result);
    setRevealPayload(payload);

    revealTimerRef.current = window.setTimeout(() => {
      advanceNow(payload);
    }, REVEAL_MS);
  };

  const currentAnswerVal =
    markerPos !== null ? positionToValue(markerPos, ruler.min, ruler.max, dimension.scale) : null;

  const truthPos = valueToPosition(fact.value, ruler.min, ruler.max, dimension.scale);
  const bandLeft = revealed ? valueToPosition(revealed.band_low, ruler.min, ruler.max, dimension.scale) : 0;
  const bandRight = revealed ? valueToPosition(revealed.band_high, ruler.min, ruler.max, dimension.scale) : 0;

  return (
    <div
      className="widget-shell"
      onClick={() => {
        if (revealed && revealPayload) {
          advanceNow(revealPayload);
        }
      }}
    >
      <div className="timeout-bar-track" aria-hidden="true">
        <div
          className="timeout-bar-fill"
          style={{ width: `${(revealed ? 0 : elapsedRatio) * 100}%` }}
        />
      </div>

      {/* Top 40%: calm prompt & reveal readout */}
      <div className="prompt-zone">
        <div className="prompt-eyebrow">
          <span>{dimension.name}</span>
          {dimension.unit && <span className="dot-sep">·</span>}
          {dimension.unit && <span>{dimension.unit}</span>}
          {dimension.scale === 'log' && <span className="scale-pill">log</span>}
          {dimension.scale === 'date' && <span className="scale-pill">timeline</span>}
          {isProbeFollowup && <span className="probe-pill">follow-up</span>}
        </div>
        <h1 className="prompt-title">{entity.name}</h1>

        {revealed ? (
          <div className="reveal-panel" role="status">
            <div className="reveal-row">
              <span className={`grade-badge grade-${revealed.grade.toLowerCase()}`}>
                {revealed.grade}
              </span>
              <span className="truth-readout mono">
                {formatQuantity(fact.value, dimension)}
              </span>
              {fact.volatile && <span className="volatile-badge">as of {fact.as_of.slice(0, 4)}</span>}
            </div>
            <p className="source-note">{fact.source_note}</p>
            <div className="reveal-hint">tap anywhere to advance</div>
          </div>
        ) : (
          <div className="live-estimate mono">
            {currentAnswerVal !== null
              ? formatQuantity(currentAnswerVal, dimension)
              : 'tap the scale below'}
          </div>
        )}
      </div>

      {/* Bottom 60%: one-thumb interactive ruler + confirm */}
      <div className="thumb-zone">
        <div
          ref={trackRef}
          className="ruler-touch-area"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          role="slider"
          aria-label={`${entity.name} ${dimension.name}`}
          aria-valuemin={ruler.min}
          aria-valuemax={ruler.max}
          aria-valuenow={currentAnswerVal ?? undefined}
        >
          {/* Anchors row above track */}
          <div className="ruler-anchors">
            {ruler.anchors.map((anchor, idx) => {
              const leftPct = valueToPosition(anchor.value, ruler.min, ruler.max, dimension.scale) * 100;
              const edgeClass = leftPct < 16 ? 'edge-left' : leftPct > 84 ? 'edge-right' : '';
              return (
                <div
                  key={anchor.entity_id}
                  className={`ruler-anchor ${idx % 2 === 1 ? 'stagger' : ''} ${edgeClass}`}
                  style={{ left: `${leftPct}%` }}
                >
                  <div className="anchor-label">{anchor.name}</div>
                  <div className="anchor-val mono">{formatQuantity(anchor.value, dimension)}</div>
                  <div className="anchor-stem" />
                </div>
              );
            })}
          </div>

          {/* Main track */}
          <div className="ruler-track">
            {/* Revealed tolerance pass band */}
            {revealed && (
              <div
                className="tolerance-band"
                style={{
                  left: `${bandLeft * 100}%`,
                  width: `${Math.max(1.5, (bandRight - bandLeft) * 100)}%`,
                }}
              />
            )}

            {/* Scale ticks */}
            {ruler.ticks.map((tick) => {
              const p = valueToPosition(tick, ruler.min, ruler.max, dimension.scale);
              if (p < 0 || p > 1) return null;
              return (
                <div key={tick} className="ruler-tick" style={{ left: `${p * 100}%` }}>
                  <div className="tick-mark" />
                  <div className="tick-label mono">{formatQuantity(tick, { scale: dimension.scale, unit: '' })}</div>
                </div>
              );
            })}

            {/* Anchor dots on track */}
            {ruler.anchors.map((anchor) => {
              const leftPct = valueToPosition(anchor.value, ruler.min, ruler.max, dimension.scale) * 100;
              return <div key={anchor.entity_id} className="anchor-dot" style={{ left: `${leftPct}%` }} />;
            })}

            {/* True position pin on reveal */}
            {revealed && (
              <div className="truth-marker" style={{ left: `${truthPos * 100}%` }} />
            )}

            {/* User marker */}
            {markerPos !== null && (
              <div
                className={`user-marker ${dragging ? 'dragging' : ''}`}
                style={{ left: `${markerPos * 100}%` }}
              />
            )}
          </div>
        </div>

        <div className="action-row">
          <button
            type="button"
            className="btn-secondary"
            disabled={!!revealed}
            onClick={(e) => {
              e.stopPropagation();
              submitAnswer(null, true);
            }}
          >
            Skip
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={markerPos === null || !!revealed}
            onClick={(e) => {
              e.stopPropagation();
              submitAnswer(markerPos, false);
            }}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
