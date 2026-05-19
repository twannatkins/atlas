/**
 * Entity 360 page layout component.
 *
 * Two-column layout: main content (signals, accounts, relationships)
 * on the left, capability palette in the sidebar on the right.
 * This is the two-driver architecture made visible: data on the left,
 * capabilities on the right.
 */

import React from "react";

interface Entity360Props {
  /** Customer label for the page header */
  customerLabel: string;
  /** Customer ID for subtitle */
  customerId: string;
  /** Main content area (signals, accounts, household strip) */
  children: React.ReactNode;
  /** Sidebar content (capability palette) */
  sidebar?: React.ReactNode;
}

export function Entity360({
  customerLabel,
  customerId,
  children,
  sidebar,
}: Entity360Props) {
  return (
    <div className="flex min-h-screen">
      {/* Main content area */}
      <main className="flex-1 p-6 space-y-6">
        {/* Identity header */}
        <header>
          <h1 className="text-2xl font-semibold text-neutral-900">
            {customerLabel}
          </h1>
          <p className="text-sm text-neutral-400">{customerId}</p>
        </header>

        {/* Content sections (signals, accounts, household, etc.) */}
        {children}
      </main>

      {/* Sidebar — capability palette */}
      {sidebar && (
        <aside
          className="w-72 border-l border-neutral-200 bg-neutral-50"
          aria-label="Available actions"
        >
          {sidebar}
        </aside>
      )}
    </div>
  );
}
