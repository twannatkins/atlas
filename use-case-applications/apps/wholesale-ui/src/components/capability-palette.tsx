/**
 * Capability palette component.
 *
 * The palette is populated from the registry, not hardcoded. When a new agent
 * is registered, this palette updates automatically. This is Thesis 1:
 * registry-first agent discovery. Each capability's tag (deterministic /
 * workflow / human-in-loop) is read from the registry record and shown so the
 * novice sees what KIND of action each one is.
 */

import React from "react";
import { useCapabilities, Capability } from "../hooks/use-capabilities";

interface CapabilityPaletteProps {
  personaClaim: string;
  onInvoke: (capabilityName: string) => void;
  /** Optional: disable capabilities that require unmet prerequisites */
  disabledCapabilities?: string[];
}

/** Icon mapping from registry display_icon to emoji (workshop simplification) */
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

/** Human label for a capability tag (the group heading in the palette). */
const TAG_LABELS: Record<string, string> = {
  deterministic: "Deterministic",
  workflow: "Workflow",
  "human-in-loop": "Human-in-loop",
  conversational: "Conversational",
  informational: "Informational",
  other: "Other",
};

/** Group capabilities by their tag for visual organization */
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
          Failed to load capabilities: {error.message}
        </p>
      </aside>
    );
  }

  const grouped = groupByTag(capabilities);

  return (
    <aside className="palette">
      <nav aria-label="Available actions">
        <h2 className="palette-h">
          <svg
            className="i"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
          >
            <path d="M9 7V4M15 7V4M7 7h10v4a5 5 0 01-10 0z M12 16v4" />
          </svg>
          Actions
        </h2>

        {Object.entries(grouped).map(([tag, caps]) => (
          <div key={tag} className="palette-group">
            <h3 className="palette-group-h">{TAG_LABELS[tag] || tag}</h3>
            {caps.map((cap) => {
              const isDisabled = disabledCapabilities.includes(cap.name);
              const icon = ICON_MAP[cap.displayIcon] || "⚡";
              return (
                <button
                  key={cap.name}
                  onClick={() => onInvoke(cap.name)}
                  disabled={isDisabled}
                  className="nav-cap"
                  aria-label={`${cap.displayName} (${cap.posture})`}
                >
                  <span className="ci" aria-hidden="true">
                    {icon}
                  </span>
                  <span className="cn">{cap.displayName}</span>
                </button>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
