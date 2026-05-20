/**
 * Coverage strip — shows advisory relationship status for a client.
 *
 * Renders active and historical coverage assignments. The Wealth Advisor
 * uses this to understand who has been covering the client and when.
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
    return (
      <p className="text-sm text-red-600">
        No advisory coverage — this client is unassigned.
      </p>
    );
  }

  const active = relationships.filter((r) => r.isActive);
  const historical = relationships.filter((r) => !r.isActive);

  return (
    <div className="space-y-2">
      {active.map((rel) => (
        <div
          key={rel.uri}
          className="flex items-center justify-between rounded-md border border-green-200 bg-green-50 p-3"
        >
          <div>
            <span className="text-sm font-medium">{rel.advisor.label}</span>
            <span className="ml-2 text-xs text-neutral-400">
              {rel.relationshipType} · since {new Date(rel.coverageStartDate).toLocaleDateString()}
            </span>
          </div>
          <span className="text-xs font-medium text-green-600">Active</span>
        </div>
      ))}
      {historical.length > 0 && (
        <details className="text-sm text-neutral-400">
          <summary className="cursor-pointer">
            {historical.length} historical relationship{historical.length > 1 ? "s" : ""}
          </summary>
          <ul className="mt-1 space-y-1 pl-4">
            {historical.map((rel) => (
              <li key={rel.uri}>
                {rel.advisor.label} ({rel.coverageStartDate} – {rel.coverageEndDate})
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
