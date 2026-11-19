import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { Figure, FigureRegion } from '../types/content';
import type { GradeName } from '../types/memory';
import { BUNDLED_SVGS } from '../content/loader';
import { gradeOcclusion, TIMEOUT_LATENCY_MS } from '../core/grading';
import { nowMs, triggerHaptic } from '../platform';

export interface OccludeCompletePayload {
  selected_region_id: string | null;
  mode: 'name_region' | 'tap_region';
  grade: GradeName;
  error: number;
  latency_ms: number;
  prompt_json: string;
}

interface OccludeWidgetProps {
  figure: Figure;
  targetRegion: FigureRegion;
  repCount: number;
  onComplete: (payload: OccludeCompletePayload) => void;
}

const REVEAL_MS = 1200;

export function OccludeWidget({ figure, targetRegion, repCount, onComplete }: OccludeWidgetProps) {
  // Alternate between "name this region" (4 nearby labels) and "tap where X is"
  const mode: 'name_region' | 'tap_region' = repCount % 2 === 0 ? 'name_region' : 'tap_region';
  const rawSvg = BUNDLED_SVGS[figure.svg_path] ?? '';

  const svgContainerRef = useRef<HTMLDivElement | null>(null);
  const startTimeRef = useRef<number>(nowMs());
  const revealTimerRef = useRef<number | null>(null);
  const finishedRef = useRef(false);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [grade, setGrade] = useState<GradeName | null>(null);
  const [payload, setPayload] = useState<OccludeCompletePayload | null>(null);
  const [elapsedRatio, setElapsedRatio] = useState(0);

  // Pick 4 nearby/adjacent label choices for "name_region" mode
  const labelChoices = useMemo(() => {
    const byId = new Map(figure.regions.map((r) => [r.region_id, r]));
    const picked: FigureRegion[] = [targetRegion];
    const adj = (targetRegion.adjacent_ids ?? [])
      .map((id) => byId.get(id))
      .filter((r): r is FigureRegion => Boolean(r));
    for (const r of adj) {
      if (picked.length >= 4) break;
      if (!picked.some((p) => p.region_id === r.region_id)) picked.push(r);
    }
    for (const r of figure.regions) {
      if (picked.length >= 4) break;
      if (!picked.some((p) => p.region_id === r.region_id)) picked.push(r);
    }
    // Deterministic sort by label length + id hash so target isn't always first
    return picked.sort((a, b) => a.label.localeCompare(b.label));
  }, [figure, targetRegion]);

  useEffect(() => {
    startTimeRef.current = nowMs();
    finishedRef.current = false;
    setSelectedId(null);
    setGrade(null);
    setPayload(null);
    setElapsedRatio(0);
    return () => {
      if (revealTimerRef.current !== null) window.clearTimeout(revealTimerRef.current);
    };
  }, [figure.id, targetRegion.region_id, mode]);

  // 10s timeout
  useEffect(() => {
    if (grade) return;
    const id = window.setInterval(() => {
      const elapsed = nowMs() - startTimeRef.current;
      setElapsedRatio(Math.min(1, elapsed / TIMEOUT_LATENCY_MS));
      if (elapsed >= TIMEOUT_LATENCY_MS && !finishedRef.current) {
        window.clearInterval(id);
        submitChoice(null, true);
      }
    }, 60);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grade, figure.id, targetRegion.region_id]);

  // Style SVG regions dynamically based on mode & reveal state
  useEffect(() => {
    const container = svgContainerRef.current;
    if (!container) return;
    const regionEls = container.querySelectorAll<SVGElement>('[data-region], .figure-region');
    regionEls.forEach((el) => {
      const rid = el.getAttribute('id') ?? el.getAttribute('data-region') ?? '';
      el.classList.remove('region-target', 'region-selected', 'region-correct', 'region-adjacent', 'region-wrong');
      if (grade) {
        if (rid === targetRegion.region_id) {
          el.classList.add('region-correct');
        } else if (rid === selectedId) {
          el.classList.add(grade === 'Hard' ? 'region-adjacent' : 'region-wrong');
        }
      } else if (mode === 'name_region' && rid === targetRegion.region_id) {
        el.classList.add('region-target');
      } else if (mode === 'tap_region' && rid === selectedId) {
        el.classList.add('region-selected');
      }
    });
  }, [rawSvg, mode, targetRegion.region_id, selectedId, grade]);

  const advanceNow = (p: OccludeCompletePayload) => {
    if (revealTimerRef.current !== null) {
      window.clearTimeout(revealTimerRef.current);
      revealTimerRef.current = null;
    }
    onComplete(p);
  };

  const submitChoice = (choiceId: string | null, skipped = false) => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    const latencyMs = Math.round(nowMs() - startTimeRef.current);
    const res = gradeOcclusion({
      targetRegion,
      selectedRegionId: choiceId,
      latencyMs,
      skipped,
    });

    triggerHaptic(res.grade === 'Again' ? 'error' : 'success');
    const out: OccludeCompletePayload = {
      selected_region_id: choiceId,
      mode,
      grade: res.grade,
      error: res.error,
      latency_ms: latencyMs,
      prompt_json: JSON.stringify({
        figure_id: figure.id,
        target_region_id: targetRegion.region_id,
        mode,
      }),
    };

    setSelectedId(choiceId);
    setGrade(res.grade);
    setPayload(out);

    revealTimerRef.current = window.setTimeout(() => {
      advanceNow(out);
    }, REVEAL_MS);
  };

  const handleSvgTap = (e: React.MouseEvent<HTMLDivElement>) => {
    if (grade || mode !== 'tap_region') return;
    const target = e.target as Element | null;
    const regionEl = target?.closest?.('[id].figure-region, [data-region]');
    if (!regionEl) return;
    const rid = regionEl.getAttribute('id') ?? regionEl.getAttribute('data-region');
    if (rid) {
      e.stopPropagation();
      setSelectedId(rid);
      triggerHaptic('light');
    }
  };

  return (
    <div
      className="widget-shell"
      onClick={() => {
        if (grade && payload) advanceNow(payload);
      }}
    >
      <div className="timeout-bar-track" aria-hidden="true">
        <div className="timeout-bar-fill" style={{ width: `${(grade ? 0 : elapsedRatio) * 100}%` }} />
      </div>

      <div className="prompt-zone compact">
        <div className="prompt-eyebrow">
          <span>{figure.title}</span>
          <span className="dot-sep">·</span>
          <span>{mode === 'name_region' ? 'name highlighted region' : 'tap region on figure'}</span>
        </div>
        <h1 className="prompt-title">
          {mode === 'name_region' ? 'Which region is highlighted?' : targetRegion.label}
        </h1>
        {grade && (
          <div className="reveal-panel inline" role="status">
            <span className={`grade-badge grade-${grade.toLowerCase()}`}>{grade}</span>
            <span className="truth-readout">{targetRegion.label}</span>
          </div>
        )}
      </div>

      <div className="thumb-zone figure-thumb-zone">
        <div
          ref={svgContainerRef}
          className={`figure-canvas ${mode === 'tap_region' ? 'interactive' : ''}`}
          onClick={handleSvgTap}
          dangerouslySetInnerHTML={{ __html: rawSvg }}
        />

        {mode === 'name_region' ? (
          <div className="choice-grid">
            {labelChoices.map((choice) => {
              const isTrue = grade && choice.region_id === targetRegion.region_id;
              const isPicked = selectedId === choice.region_id;
              return (
                <button
                  key={choice.region_id}
                  type="button"
                  disabled={!!grade}
                  className={`choice-pill ${isTrue ? 'correct' : ''} ${
                    grade && isPicked && !isTrue ? 'wrong' : ''
                  }`}
                  onClick={(e) => {
                    e.stopPropagation();
                    submitChoice(choice.region_id, false);
                  }}
                >
                  {choice.label}
                </button>
              );
            })}
          </div>
        ) : (
          <div className="action-row">
            <button
              type="button"
              className="btn-secondary"
              disabled={!!grade}
              onClick={(e) => {
                e.stopPropagation();
                submitChoice(null, true);
              }}
            >
              Skip
            </button>
            <button
              type="button"
              className="btn-primary"
              disabled={!selectedId || !!grade}
              onClick={(e) => {
                e.stopPropagation();
                submitChoice(selectedId, false);
              }}
            >
              Confirm
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
