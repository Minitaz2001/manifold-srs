import { useEffect, useRef, useState } from 'react';
import type { Dimension, Entity, Fact } from '../types/content';
import type { GradeName } from '../types/memory';
import { formatQuantity, formatSci } from '../core/grading';
import { nowMs, triggerHaptic } from '../platform';

export interface FlashCompletePayload {
  grade: GradeName;
  latency_ms: number;
  prompt_json: string;
}

interface FlashWidgetProps {
  entity: Entity;
  dimension: Dimension;
  fact: Fact;
  /** First exposure: teach the number (answer shown immediately), no recall test. */
  isNew: boolean;
  onComplete: (payload: FlashCompletePayload) => void;
}

/**
 * Plain number flashcard (`flash`) — the primary way a fact is learned.
 * New: shows the answer straight away ("learn this"), one tap to continue.
 * Review: question → tap to reveal → Again / Hard / Good / Easy. No timer.
 */
export function FlashWidget({ entity, dimension, fact, isNew, onComplete }: FlashWidgetProps) {
  const startTimeRef = useRef<number>(nowMs());
  const [flipped, setFlipped] = useState(isNew);

  useEffect(() => {
    startTimeRef.current = nowMs();
    setFlipped(isNew);
  }, [entity.id, dimension.id, isNew]);

  const answer = formatQuantity(fact.value, dimension);
  const showRange = fact.low !== fact.high && dimension.scale !== 'date';
  const range = showRange
    ? `${formatQuantity(fact.low, dimension)} – ${formatQuantity(fact.high, dimension)}`
    : null;

  const finish = (grade: GradeName) => {
    triggerHaptic(grade === 'Again' ? 'error' : 'success');
    onComplete({
      grade,
      latency_ms: Math.round(nowMs() - startTimeRef.current),
      prompt_json: JSON.stringify({ entity_id: entity.id, dimension_id: dimension.id, mode: isNew ? 'learn' : 'recall' }),
    });
  };

  return (
    <div className="widget-shell">
      <div className="prompt-zone plain-prompt-zone">
        <div className="prompt-eyebrow">
          {isNew && <span className="new-pill">new</span>}
          <span>{dimension.name}</span>
          {dimension.unit && dimension.scale !== 'date' && (
            <>
              <span className="dot-sep">·</span>
              <span>{dimension.unit}</span>
            </>
          )}
        </div>
        <h1 className="prompt-title plain-front">{entity.name}</h1>

        {flipped && (
          <div className="plain-back-box" role="region" aria-label="Answer">
            <p className="flash-answer">{answer}</p>
            {dimension.scale !== 'date' && <p className="sci-readout mono">{formatSci(fact.value)}</p>}
            {range && <p className="source-note">range {range}</p>}
            {fact.source_note && <p className="source-note">{fact.source_note}</p>}
          </div>
        )}
      </div>

      <div className="thumb-zone">
        {isNew ? (
          <button type="button" className="btn-primary btn-flip-large" onClick={() => finish('Good')}>
            Got it
          </button>
        ) : !flipped ? (
          <button
            type="button"
            className="btn-primary btn-flip-large"
            onClick={() => {
              triggerHaptic('light');
              setFlipped(true);
            }}
          >
            Tap to reveal
          </button>
        ) : (
          <GradeRow onGrade={finish} />
        )}
      </div>
    </div>
  );
}

export function GradeRow({ onGrade }: { onGrade: (g: GradeName) => void }) {
  return (
    <div className="action-row four-up">
      <button type="button" className="btn-again" onClick={() => onGrade('Again')}>Again</button>
      <button type="button" className="btn-hard" onClick={() => onGrade('Hard')}>Hard</button>
      <button type="button" className="btn-good" onClick={() => onGrade('Good')}>Good</button>
      <button type="button" className="btn-easy" onClick={() => onGrade('Easy')}>Easy</button>
    </div>
  );
}
