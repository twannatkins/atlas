/**
 * Coverage strip — shows advisory relationship status for a client.
 *
 * Renders active and historical coverage assignments as the warm-paper
 * coverage rows. The Wealth Advisor uses this to understand who has been
 * covering the client and when. An unassigned client reads as a coverage gap.
 */

import React from "react";

interface AdvisoryRelationship {
  uri: string;
  advisor: { label: string };
  coverageStartDate: string;
  coverageEndDate?: string;
  relationshipType: string;
  isActive: boolean;
}

interface CoverageStripProps {
  relationships: AdvisoryRelationship[];
}

export function CoverageStrip({ relationships }: CoverageStripProps) {
  if (relationships.length === 0) {
    return <p className="empty">No advisory coverage — this client is unassigned.</p>;
  }

  const active = relationships.filter((r) => r.isActive);
  const historical = relationships.filter((r) => !r.isActive);

  return (
    <div>
      {active.map((rel) => (
        <div key={rel.uri} className="cov active">
          <div className="cov-top">
            <span className="cov-name">{rel.advisor.label}</span>
            <span className="cov-state on">active</span>
          </div>
          <p className="cov-dt">
            {rel.relationshipType} · since {new Date(rel.coverageStartDate).toLocaleDateString()}
          </p>
        </div>
      ))}
      {historical.map((rel) => (
        <div key={rel.uri} className="cov hist">
          <div className="cov-top">
            <span className="cov-name">{rel.advisor.label}</span>
            <span className="cov-state off">ended</span>
          </div>
          <p className="cov-dt">
            {rel.coverageStartDate} – {rel.coverageEndDate || "—"}
          </p>
        </div>
      ))}
    </div>
  );
}
