/**
 * Rationale editor component.
 *
 * This is the human-in-the-loop pattern. The agent drafts; the human approves.
 * The "Approve and route" button is the gate — no path exists to auto-route
 * without the banker clicking it, and it stays disabled until the banker has
 * actually engaged with the text. The probabilistic / requires-review badges
 * are ALWAYS visible. This is what makes the probabilistic agent compliant
 * with SR 11-7.
 */

import React, { useState, useCallback } from "react";

interface RationaleEditorProps {
  /** Initial draft from referral-rationale-drafter (may be empty) */
  initialDraft?: string;
  /** Whether a draft is currently being generated */
  isGenerating?: boolean;
  /** Called when the banker requests a new draft */
  onGenerateDraft: () => void;
  /** Called when the banker approves the rationale and triggers routing */
  onApprove: (approvedText: string) => void;
}

export function RationaleEditor({
  initialDraft = "",
  isGenerating = false,
  onGenerateDraft,
  onApprove,
}: RationaleEditorProps) {
  const [text, setText] = useState(initialDraft);
  const [hasBeenReviewed, setHasBeenReviewed] = useState(false);

  React.useEffect(() => {
    if (initialDraft) {
      setText(initialDraft);
      setHasBeenReviewed(false); // a new draft needs fresh review
    }
  }, [initialDraft]);

  const handleFocus = useCallback(() => {
    setHasBeenReviewed(true); // the banker has engaged with the text
  }, []);

  const handleApprove = useCallback(() => {
    if (text.trim() && hasBeenReviewed) onApprove(text);
  }, [text, hasBeenReviewed, onApprove]);

  const canApprove = text.trim().length > 0 && hasBeenReviewed && !isGenerating;

  return (
    <div className="editor">
      <div className="badges">
        <span className="badge prob">probabilistic — model-generated</span>
        <span className="badge rev">requires human review</span>
      </div>

      {!text && !isGenerating && (
        <button className="btn accent" onClick={onGenerateDraft}>
          Generate draft
        </button>
      )}

      {isGenerating && (
        <div className="loading-line" aria-busy="true">
          Generating rationale draft…
        </div>
      )}

      {text && (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onFocus={handleFocus}
            rows={6}
            className="draft-input"
            aria-label="Referral rationale text (editable)"
            placeholder="The drafted rationale will appear here for your review…"
          />
          <div className="editor-actions">
            <p className="review-hint">
              {hasBeenReviewed
                ? "✓ Reviewed — you may approve and route"
                : "Click into the text to mark as reviewed"}
            </p>
            <button
              className="btn go"
              onClick={handleApprove}
              disabled={!canApprove}
              aria-label="Approve rationale and route referral to advisor"
            >
              Approve and route
            </button>
          </div>
        </>
      )}
    </div>
  );
}
