/**
 * Entity 360 page layout component.
 *
 * The two-driver architecture made visible: GraphQL data on the left (the
 * entity header + content sections), the registry-driven capability palette on
 * the right. The warm-paper `.shell` grid holds the two columns; the entity
 * header is the serif identity card with FIBO-class chips.
 */

import React from "react";

interface Entity360Props {
  /** Customer label for the page header */
  customerLabel: string;
  /** Customer ID for subtitle */
  customerId: string;
  /** Optional FIBO class chip (e.g. "fibo:Party"). */
  classChip?: string;
  /** Main content area (signals, accounts, household strip) */
  children: React.ReactNode;
  /** Sidebar content (capability palette) */
  sidebar?: React.ReactNode;
}

/** First two initials, for the entity avatar. */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "—";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Entity360({
  customerLabel,
  customerId,
  classChip = "fibo:Party",
  children,
  sidebar,
}: Entity360Props) {
  return (
    <div className="shell">
      <div className="shell-main">
        {/* identity header */}
        <div className="card">
          <div className="head">
            <div className="av">{initials(customerLabel)}</div>
            <div className="grow">
              <div className="title-row">
                <span className="name">{customerLabel}</span>
                <span className="chip">{classChip}</span>
                {customerId && <span className="chip">{customerId}</span>}
              </div>
              <p className="sub">Full entity view · data and provenance from the graph</p>
            </div>
          </div>
        </div>

        {children}
      </div>

      {sidebar && <div>{sidebar}</div>}
    </div>
  );
}
