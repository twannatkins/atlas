/**
 * Capability cards — the inline "Capabilities" card used in the referral/360 two-column
 * layout (matches the design template: each capability is a .cap block with a tag showing
 * its KIND — deterministic / workflow / human-in-loop). Registry-driven, persona-scoped
 * (Thesis 1): the list comes from the live Agent Registry, not hardcoded. A trailing dashed
 * .cap.future row names the click-to-invoke roadmap so the palette's current scope (a
 * registry display) is honest.
 */

import React from "react";
import { useCapabilities, Capability } from "../hooks/use-capabilities";

/** Map a capability tag to the template's tag class. */
function tagClass(tag: string): string {
  if (/human/i.test(tag)) return "tag hil";
  if (/workflow|flow/i.test(tag)) return "tag flow";
  return "tag det";
}

export function CapabilityCards({ personaClaim }: { personaClaim: string }) {
  const { capabilities, loading, error } = useCapabilities(personaClaim);

  return (
    <div className="card">
      <div className="card-h">
        <span className="t">Capabilities</span>
        <span className="meta">
          <svg className="i" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path d="M9 7V4M15 7V4M7 7h10v4a5 5 0 01-10 0z M12 16v4" />
          </svg>
          registry · live
        </span>
      </div>

      {loading && <p className="loading-line">Loading capabilities…</p>}
      {error && (
        <p className="loading-line" role="alert">
          Failed to load capabilities: {error.message}
        </p>
      )}

      {capabilities.map((cap: Capability) => (
        <div className="cap" key={cap.name}>
          <div className="cap-top">
            <span className="cap-name">{cap.displayName}</span>
            <span className={tagClass(cap.capabilityTag)}>{cap.capabilityTag}</span>
          </div>
          <p className="cap-sub">{cap.name} · live</p>
        </div>
      ))}

      {/* Roadmap row — the palette is a registry DISPLAY today; click-to-invoke is next. */}
      <div className="cap future">
        <div className="cap-top">
          <span className="cap-name" style={{ color: "var(--ink-2)" }}>
            Invoke from palette
          </span>
          <span className="tag soon">next</span>
        </div>
        <p className="cap-sub">palette is a registry display today; click-to-invoke is roadmap</p>
      </div>
    </div>
  );
}
