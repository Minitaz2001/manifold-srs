import React, { useState } from 'react';

interface InboxModalProps {
  open: boolean;
  onClose: () => void;
  onSaveNote: (text: string) => Promise<void>;
}

/**
 * Pull-lane "Surprised me" capture modal — the ONLY place keyboard input exists (Design Doc §6).
 */
export function InboxModal({ open, onClose, onSaveNote }: InboxModalProps) {
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    setSaving(true);
    try {
      await onSaveNote(trimmed);
      setText('');
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()} role="dialog" aria-label="Surprised me">
        <div className="drawer-header">
          <h2>Surprised me</h2>
          <button type="button" className="icon-btn" onClick={onClose}>
            Cancel
          </button>
        </div>
        <p className="muted-note">
          Capture a fact, ratio, or rule that broke your intuition. Export from Settings to feed the content pipeline.
        </p>
        <form onSubmit={handleSubmit}>
          <textarea
            className="inbox-textarea"
            rows={4}
            placeholder="e.g. Thought Vietnam was ~50M; actually ~100M..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            autoFocus
          />
          <div className="action-row">
            <button type="submit" className="btn-primary" disabled={saving || !text.trim()}>
              Save to Inbox
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
