/**
 * Theme card component — renders a market or portfolio theme.
 *
 * Themes are informational, not action-driving. The agent that produces
 * them (theme-summarizer) is probabilistic and carries is_probabilistic: true.
 */

import React from "react";

interface ThemeCardProps {
  theme: string;
  summary?: string;
}

// No relevance score is rendered: there is no derived per-theme relevance in the data,
// so showing a percentage would be fabricated (the same reason the signal card omits the
// strength badge). The card shows the theme label + summary + the probabilistic flag.
export function ThemeCard({ theme, summary }: ThemeCardProps) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-800">{theme}</h3>
      </div>
      {summary && (
        <p className="mt-2 text-sm text-neutral-600">{summary}</p>
      )}
      <span className="mt-2 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
        probabilistic
      </span>
    </div>
  );
}
