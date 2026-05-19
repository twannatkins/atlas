/**
 * Rationale editor component.
 *
 * This is the human-in-the-loop pattern. The agent drafts; the human
 * approves. The "Approve and route" button is the gate. No path exists
 * to auto-route without the banker clicking this button.
 * This is what makes the probabilistic agent compliant with SR 11-7.
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

  // Update text when a new draft arrives
  React.useEffect(() => {
    if (initialDraft) {
      setText(initialDraft);
      setHasBeenReviewed(false); // New draft needs fresh review
    }
  }, [initialDraft]);

  const handleFocus = useCallback(() => {
    // The banker has engaged with the text — mark as reviewed
    setHasBeenReviewed(true);
  }, []);

  const handleApprove = useCallback(() => {
    if (text.trim() && hasBeenReviewed) {
      onApprove(text);
    }
  }, [text, hasBeenReviewed, onApprove]);

  const canApprove = text.trim().length > 0 && hasBeenReviewed && !isGenerating;

  return (
    <div className="space-y-3 rounded-lg border border-neutral-200 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-800">
          Referral rationale
        </h3>
        {/* Probabilistic flags — always visible */}
        <div className="flex gap-2">
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
            probabilistic
          </span>
          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
            requires review
          </span>
        </div>
      </div>

      {!text && !isGenerating && (
        <button
          onClick={onGenerateDraft}
          className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700"
        >
          Generate draft
        </button>
      )}

      {isGenerating && (
        <div className="flex items-center gap-2 py-4 text-sm text-neutral-400" aria-busy="true">
          <span className="animate-spin">⏳</span>
          Generating rationale draft...
        </div>
      )}

      {text && (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onFocus={handleFocus}
            rows={6}
            className="w-full rounded-md border border-neutral-200 p-3 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            aria-label="Referral rationale text (editable)"
            placeholder="The drafted rationale will appear here for your review..."
          />

          <div className="flex items-center justify-between">
            <p className="text-xs text-neutral-400">
              {hasBeenReviewed
                ? "✓ Reviewed — you may approve and route"
                : "Click into the text to mark as reviewed"}
            </p>

            <button
              onClick={handleApprove}
              disabled={!canApprove}
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
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
