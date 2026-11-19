import { useEffect, useRef, useState } from 'react';
import type { PlainCard } from '../types/content';
import type { GradeName } from '../types/memory';
import { nowMs, triggerHaptic } from '../platform';

export interface PlainCardCompletePayload {
  grade: Extract<GradeName, 'Again' | 'Good'>;
  latency_ms: number;
  prompt_json: string;
}

interface PlainCardWidgetProps {
  card: PlainCard;
  onComplete: (payload: PlainCardCompletePayload) => void;
}

/**
 * Widget 3: Plain card (`recall`).
 * Front, tap to flip, then self-grade with Again or Good ONLY (Design Doc v0.1 §5).
 */
export function PlainCardWidget({ card, onComplete }: PlainCardWidgetProps) {
  const startTimeRef = useRef<number>(nowMs());
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    startTimeRef.current = nowMs();
    setFlipped(false);
  }, [card.id]);

  const handleGrade = (grade: 'Again' | 'Good') => {
    const latencyMs = Math.round(nowMs() - startTimeRef.current);
    triggerHaptic(grade === 'Again' ? 'error' : 'success');
    onComplete({
      grade,
      latency_ms: latencyMs,
      prompt_json: JSON.stringify({ card_id: card.id, front: card.front }),
    });
  };

  return (
    <div className="widget-shell">
      <div className="prompt-zone plain-prompt-zone">
        {card.media && (
          <div className="card-media-frame">
            <img src={`./${card.media}`} alt={card.front} className="card-media-img" />
          </div>
        )}
        <div className="prompt-eyebrow">
          <span>{card.module.replace('_', ' ')}</span>
          {card.tags && card.tags.length > 0 && (
            <>
              <span className="dot-sep">·</span>
              <span>{card.tags.slice(0, 3).join(' · ')}</span>
            </>
          )}
        </div>
        <h1 className="prompt-title plain-front">{card.front}</h1>

        {flipped && (
          <div className="plain-back-box" role="region" aria-label="Answer">
            <p className="plain-back-text">{card.back}</p>
            {card.attribution && <p className="attribution-line">{card.attribution}</p>}
            {card.source_note && <p className="source-note">{card.source_note}</p>}
          </div>
        )}
      </div>

      <div className="thumb-zone">
        {!flipped ? (
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
          <div className="action-row two-up">
            <button
              type="button"
              className="btn-again"
              onClick={() => handleGrade('Again')}
            >
              Again
            </button>
            <button
              type="button"
              className="btn-good"
              onClick={() => handleGrade('Good')}
            >
              Good
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
