/**
 * Capability palette for the Wealth UI.
 *
 * Same component pattern as the Wholesale UI — populated from the registry,
 * filtered by persona. The Wealth Advisor sees different capabilities
 * (theme-summarizer, conversational-context-manager) because the registry
 * returns a different set for the wealth-advisor persona, not because the UI
 * hardcodes anything. This is Thesis 1: registry-first agent discovery.
 */

"use client";

import React from "react";
import { useCapabilities, Capability } from "../hooks/use-capabilities";

interface CapabilityPaletteProps {
  personaClaim: string;
  onInvoke: (capabilityName: string) => void;
  disabledCapabilities?: string[];
}

const ICON_MAP: Record<string, string> = {
  search: "🔍",
  radar: "📡",
  "message-2": "💬",
  affiliate: "🔗",
  route: "➡️",
  activity: "📊",
  newspaper: "📰",
  messages: "💭",
};

const TAG_LABELS: Record<string, string> = {
  deterministic: "Deterministic",
  workflow: "Workflow",
  "human-in-loop": "Human-in-loop",
  conversational: "Conversational",
  informational: "Informational",
  other: "Other",
};

function groupByTag(capabilities: Capability[]): Record<string, Capability[]> {
  return capabilities.reduce(
    (groups, cap) => {
      const tag = cap.capabilityTag || "other";
      if (!groups[tag]) groups[tag] = [];
      groups[tag].push(cap);
      return groups;
    },
    {} as Record<string, Capability[]>,
  );
}

export function CapabilityPalette({
  personaClaim,
  onInvoke,
  disabledCapabilities = [],
}: CapabilityPaletteProps) {
  const { capabilities, loading, error } = useCapabilities(personaClaim);

  if (loading) {
    return (
      <aside className="palette" aria-busy="true">
        <p className="loading-line">Loading capabilities…</p>
      </aside>
    );
  }
  if (error) {
    return (
      <aside className="palette">
        <p className="loading-line" role="alert">
          Failed to load: {error.message}
        </p>
      </aside>
    );
  }

  const grouped = groupByTag(capabilities);

  return (
    <aside className="palette">
      <nav aria-label="Available actions">
        <h2 className="palette-h">
          <svg className="i" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path d="M9 7V4M15 7V4M7 7h10v4a5 5 0 01-10 0z M12 16v4" />
          </svg>
          Actions
        </h2>
        {Object.entries(grouped).map(([tag, caps]) => (
          <div key={tag} className="palette-group">
            <h3 className="palette-group-h">{TAG_LABELS[tag] || tag}</h3>
            {caps.map((cap) => (
              <button
                key={cap.name}
                onClick={() => onInvoke(cap.name)}
                disabled={disabledCapabilities.includes(cap.name)}
                className="nav-cap"
                aria-label={cap.displayName}
              >
                <span className="ci" aria-hidden="true">
                  {ICON_MAP[cap.displayIcon] || "⚡"}
                </span>
                <span className="cn">{cap.displayName}</span>
              </button>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
