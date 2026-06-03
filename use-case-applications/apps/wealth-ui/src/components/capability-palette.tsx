/**
 * Capability palette for the Wealth UI.
 *
 * Same component pattern as the Wholesale UI — populated from the registry,
 * filtered by persona. The Wealth Advisor sees different capabilities:
 * theme-summarizer, conversational-context-manager, behavioral-signal-agent.
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

  if (loading) return <div className="p-4 text-sm text-neutral-400">Loading capabilities...</div>;
  if (error) return <div className="p-4 text-sm text-red-600">Failed to load: {error.message}</div>;

  const grouped = groupByTag(capabilities);

  return (
    <nav aria-label="Available actions" className="space-y-4 p-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-400">Actions</h2>
      {Object.entries(grouped).map(([tag, caps]) => (
        <div key={tag} className="space-y-1">
          <h3 className="text-xs font-medium text-neutral-400 capitalize">{tag}</h3>
          {caps.map((cap) => (
            <button
              key={cap.name}
              onClick={() => onInvoke(cap.name)}
              disabled={disabledCapabilities.includes(cap.name)}
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span aria-hidden="true">{ICON_MAP[cap.displayIcon] || "⚡"}</span>
              <span className="flex-1">{cap.displayName}</span>
            </button>
          ))}
        </div>
      ))}
    </nav>
  );
}
