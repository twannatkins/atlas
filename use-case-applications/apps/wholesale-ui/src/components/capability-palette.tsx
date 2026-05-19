/**
 * Capability palette component.
 *
 * The palette is populated from the registry, not hardcoded.
 * When a new agent is registered, this palette updates automatically.
 * This is Thesis 1: registry-first agent discovery.
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
      <div className="p-4 text-sm text-neutral-400" aria-busy="true">
        Loading capabilities...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-sm text-red-600" role="alert">
        Failed to load capabilities: {error.message}
      </div>
    );
  }

  const grouped = groupByTag(capabilities);

  return (
    <nav aria-label="Available actions" className="space-y-4 p-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-400">
        Actions
      </h2>

      {Object.entries(grouped).map(([tag, caps]) => (
        <div key={tag} className="space-y-1">
          <h3 className="text-xs font-medium text-neutral-400 capitalize">
            {tag}
          </h3>
          {caps.map((cap) => {
            const isDisabled = disabledCapabilities.includes(cap.name);
            const icon = ICON_MAP[cap.displayIcon] || "⚡";

            return (
              <button
                key={cap.name}
                onClick={() => onInvoke(cap.name)}
                disabled={isDisabled}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-50"
                style={{
                  height: "var(--palette-item-height)",
                  borderRadius: "var(--palette-item-radius)",
                }}
                aria-label={`${cap.displayName} (${cap.posture})`}
              >
                <span
                  aria-hidden="true"
                  style={{ fontSize: "var(--palette-icon-size)" }}
                >
                  {icon}
                </span>
                <span className="flex-1">{cap.displayName}</span>
              </button>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
