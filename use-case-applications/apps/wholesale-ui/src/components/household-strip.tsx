/**
 * Household strip component.
 *
 * Inline graph visualization showing 1-hop neighbors of a household.
 * Data comes from the household-traverser agent via the registry.
 * Limited to 1-hop by design — deeper traversals are explicit user actions.
 */

import React from "react";

interface HouseholdNode {
  uri: string;
  type: string;
  label: string;
  relationship: string;
}

interface HouseholdStripProps {
  nodes: HouseholdNode[];
  onNodeClick?: (uri: string) => void;
  loading?: boolean;
}

/** Type-to-icon mapping for visual differentiation */
const TYPE_ICONS: Record<string, string> = {
  "atlas:Customer": "👤",
  "atlas:Account": "🏦",
  "atlas:Advisor": "🎯",
  "atlas:Household": "🏠",
};

export function HouseholdStrip({
  nodes,
  onNodeClick,
  loading = false,
}: HouseholdStripProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 p-3 text-sm text-neutral-400" aria-busy="true">
        <span className="animate-pulse">Loading relationship strip...</span>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="p-3 text-sm text-neutral-400">
        No relationships found.
      </div>
    );
  }

  return (
    <div
      className="flex flex-wrap items-center gap-2 p-3"
      role="list"
      aria-label="Household relationships (1-hop)"
    >
      {nodes.map((node, index) => {
        const icon = TYPE_ICONS[node.type] || "◆";
        return (
          <React.Fragment key={node.uri}>
            {index > 0 && (
              <span className="text-neutral-300" aria-hidden="true">—</span>
            )}
            <button
              onClick={() => onNodeClick?.(node.uri)}
              className="inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-white px-3 py-1 text-sm transition-colors hover:border-primary-500 hover:bg-primary-50"
              role="listitem"
              aria-label={`${node.label} (${node.type.split(":").pop()})`}
            >
              <span aria-hidden="true">{icon}</span>
              <span>{node.label || node.uri.split("/").pop()}</span>
            </button>
          </React.Fragment>
        );
      })}
    </div>
  );
}
