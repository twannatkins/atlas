// NOTE: shares the render contract with apps/wholesale-ui's component of the same
// name (one source of truth for how this renders). Kept as a wealth-local copy to
// keep this a wealth-render-only change; a future pass can consolidate both into
// apps/shared/ui/. Do not let the two drift.
/**
 * Household strip component.
 *
 * Inline graph visualization showing 1-hop neighbors of a household — rendered
 * as the warm-paper relationship chips. Data comes from the live graph
 * (household members via atlas:memberOf). Limited to 1-hop by design — deeper
 * traversals are explicit user actions.
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

/** Accounts read with the green "acct" accent; everyone else as a party chip. */
function chipClass(type: string): string {
  return /account/i.test(type) ? "rel acct" : "rel party";
}

export function HouseholdStrip({
  nodes,
  onNodeClick,
  loading = false,
}: HouseholdStripProps) {
  if (loading) {
    return <p className="loading-line">Loading relationship strip…</p>;
  }

  if (nodes.length === 0) {
    return <p className="empty">No relationships found.</p>;
  }

  return (
    <div className="rel-chips" role="list" aria-label="Household relationships (1-hop)">
      {nodes.map((node) => (
        <button
          key={node.uri}
          onClick={() => onNodeClick?.(node.uri)}
          className={chipClass(node.type)}
          role="listitem"
          aria-label={`${node.label} (${node.type.split(":").pop()})`}
        >
          <svg
            className="i"
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
          >
            {/category|account/i.test(node.type) ? (
              <>
                <rect x="3" y="6" width="18" height="13" rx="2" />
                <path d="M3 10h18" />
              </>
            ) : (
              <>
                <circle cx="12" cy="8" r="3.2" />
                <path d="M5 20c0-3.5 3-6 7-6s7 2.5 7 6" />
              </>
            )}
          </svg>
          <span>{node.label || node.uri.split("/").pop()}</span>
        </button>
      ))}
    </div>
  );
}
