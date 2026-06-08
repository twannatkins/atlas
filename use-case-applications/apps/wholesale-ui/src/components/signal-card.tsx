/**
 * Signal card component.
 *
 * Renders a single wealth signal with its provenance. Provenance is visible —
 * the novice sees which SHACL shape validated the signal and which R2RML
 * mapping produced the underlying triple (the `.prov` line). This is what
 * makes ATLAS auditable.
 *
 * NO strength badge: there is no atlas:signalStrength predicate in the derived
 * data, so any "strong/moderate/gap" badge would be fabricated rather than
 * derived. The left accent only distinguishes a coverage-GAP signal (info) from
 * a positive signal (green) — both facts that exist in the data, not a score.
 */

import React from "react";
import { ProvenanceBadge } from "./provenance-badge";

interface SignalCardProps {
  signalType: string;
  /**
   * Optional and currently unrendered: there is no derived signalStrength in the
   * data, so the strength badge is omitted. Kept on the prop so a future derived
   * strength can reinstate the badge without a signature change.
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
  // A coverage-gap signal reads as an info accent (something to act on), a
  // positive signal as the green default. This keys off the signal's TYPE — a
  // real fact — not a fabricated strength score.
  const isGap = /noadvisor|coverage|gap/i.test(signalType);

  return (
    <div className={isGap ? "sig gap" : "sig"} role="article" aria-label={label}>
      <div className="sig-top">
        <span className="sig-name">{label}</span>
      </div>
      {signalDate && (
        <p className="sig-date">
          Detected: {new Date(signalDate).toLocaleDateString()}
        </p>
      )}
      {provenance && (
        <ProvenanceBadge
          validatedBy={provenance.validatedBy}
          derivedFrom={provenance.derivedFrom}
          generatedBy={provenance.generatedBy}
        />
      )}
    </div>
  );
}
