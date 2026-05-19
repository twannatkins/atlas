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
  strength: "strong" | "moderate" | "weak" | "gap";
  signalDate?: string;
  provenance?: {
    validatedBy?: string;
    derivedFrom?: string;
    generatedBy?: string;
  };
}

/** Human-readable labels for signal types (from SKOS prefLabel) */
const SIGNAL_LABELS: Record<string, string> = {
  LargeInboundWireSignal: "Large inbound wire",
  SegmentShiftSignal: "Segment shift",
  NoAdvisorCoverageSignal: "No advisor coverage",
  EngagementDecaySignal: "Engagement decay",
  NetworkInfluenceSignal: "Network influence",
};

/** Strength descriptions for accessibility */
const STRENGTH_LABELS: Record<string, string> = {
  strong: "Strong signal",
  moderate: "Moderate signal",
  weak: "Weak signal",
  gap: "Coverage gap",
};

export function SignalCard({
  signalType,
  strength,
  signalDate,
  provenance,
}: SignalCardProps) {
  const label = SIGNAL_LABELS[signalType] || signalType;
  const strengthLabel = STRENGTH_LABELS[strength] || strength;

  return (
    <div
      className="rounded-lg border-l-4 p-4 shadow-sm"
      style={{
        borderLeftColor: `var(--color-signal-${strength})`,
        borderRadius: "var(--signal-card-radius)",
        padding: "var(--signal-card-padding)",
        boxShadow: "var(--signal-card-shadow)",
      }}
      role="article"
      aria-label={`${label} — ${strengthLabel}`}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-800">{label}</h3>
        <span
          className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
          style={{ color: `var(--color-signal-${strength})` }}
        >
          {strengthLabel}
        </span>
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
