// NOTE: shares the render contract with apps/wholesale-ui's component of the same
// name (one source of truth for how this renders). Kept as a wealth-local copy to
// keep this a wealth-render-only change; a future pass can consolidate both into
// apps/shared/ui/. Do not let the two drift.
/**
 * Signal card component.
 *
 * Renders a single wealth signal with its strength indicator and provenance.
 * Provenance is visible — the novice sees which SHACL shape validated the
 * signal and which R2RML mapping produced the underlying triple.
 */

import React from "react";
import { ProvenanceBadge } from "./provenance-badge";

interface SignalCardProps {
  signalType: string;
  /**
   * Optional and currently unrendered: there is no derived signalStrength in the
   * data, so the strength badge is omitted (see render below). Kept on the prop so
   * a future derived strength can reinstate the badge without a signature change.
   */
  strength?: "strong" | "moderate" | "weak" | "gap";
  signalDate?: string;
  provenance?: {
    validatedBy?: string;
    derivedFrom?: string;
    generatedBy?: string;
  };
}

/**
 * UI-side fallback labels for signal types. The resolver now returns the SKOS
 * prefLabel for loaded concepts (so signalType usually arrives human-readable);
 * this map is a fallback for the short WS2 type names when the label is absent.
 */
const SIGNAL_LABELS: Record<string, string> = {
  LargeInboundWireSignal: "Large inbound wire",
  // SegmentShiftSignal: deferred to the session-intelligence phase — not derived from
  // Phase-1 data (no segment/tier model or temporal dimension), so it does not render
  // today. Label kept so it displays correctly once that phase derives it honestly.
  SegmentShiftSignal: "Segment shift",
  NoAdvisorCoverageSignal: "No advisor coverage",
  EngagementDecaySignal: "Engagement decay",
  NetworkInfluenceSignal: "Network influence",
};

export function SignalCard({
  signalType,
  signalDate,
  provenance,
}: SignalCardProps) {
  const label = SIGNAL_LABELS[signalType] || signalType;

  // Strength badge intentionally omitted: there is no atlas:signalStrength predicate
  // in the derived data, so any badge ("strong"/"moderate"/"gap") would be fabricated
  // rather than derived. Reinstate it only once a strength is genuinely derived
  // (e.g. via atlas:Score). A neutral accent replaces the former strength-keyed color.
  return (
    <div
      className="rounded-lg border-l-4 p-4 shadow-sm"
      style={{
        borderLeftColor: "var(--color-signal-neutral, #64748b)",
        borderRadius: "var(--signal-card-radius)",
        padding: "var(--signal-card-padding)",
        boxShadow: "var(--signal-card-shadow)",
      }}
      role="article"
      aria-label={label}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-800">{label}</h3>
      </div>

      {signalDate && (
        <p className="mt-1 text-xs text-neutral-400">
          Detected: {new Date(signalDate).toLocaleDateString()}
        </p>
      )}

      {provenance && (
        <div className="mt-2">
          <ProvenanceBadge
            validatedBy={provenance.validatedBy}
            derivedFrom={provenance.derivedFrom}
            generatedBy={provenance.generatedBy}
          />
        </div>
      )}
    </div>
  );
}
