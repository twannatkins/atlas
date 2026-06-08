/**
 * Theme card component — renders a market or portfolio theme.
 *
 * Themes are informational, not action-driving. The agent that produces them
 * (theme-summarizer) is probabilistic and carries is_probabilistic: true, so
 * the probabilistic flag is always shown.
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
    <div className="card" style={{ marginBottom: 0 }}>
      <div className="card-h">
        <span className="t">{theme}</span>
        <span className="badge prob">probabilistic</span>
      </div>
      {summary && <p className="sub">{summary}</p>}
    </div>
  );
}
