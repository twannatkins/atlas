/**
 * Compliance banner component.
 *
 * 31 U.S.C. §5318(g)(2) makes it a federal crime to disclose to anyone
 * outside the BSA function that a SAR has been filed. The Consumer Banker
 * is outside the BSA function. This banner tells them what they are
 * allowed to know — that a review is active — without disclosing what
 * kind of review it is.
 */

import React from "react";

interface ComplianceBannerProps {
  hasComplianceReview: boolean;
  personaClaim: string;
  /**
   * When true, the banner demonstrates the non-tipping-off copy pattern and renders a
   * visible "Example" marker so it is NOT mistaken for a real review state.
   *
   * Why this is illustrative and not wired to real data: there is no per-entity
   * compliance state in the graph to drive it. atlas:hasComplianceHold is an undefined
   * predicate (declared in no ontology, zero triples); validate-routing ASK-checks it
   * transiently during the routing workflow (always false today) but never persists a
   * queryable per-entity fact, and there is no compliance field in the read schema. A
   * real banner is therefore deferred until that data exists — do NOT wire this to a
   * fabricated/backfilled field (a manufactured compliance status, on a regulatory
   * subject, would be a worse defect than the honest "Example"). See 04a forward-pointers.
   */
  illustrative?: boolean;
}

export function ComplianceBanner({
  hasComplianceReview,
  personaClaim,
  illustrative = false,
}: ComplianceBannerProps) {
  if (!hasComplianceReview) return null;

  // BSA Analysts are inside the BSA function — they can see SAR detail
  const isBSA = personaClaim === "atlas-bsa-analyst";

  const message = isBSA
    ? "SAR draft in progress — BSA team review required before filing"
    : "Active compliance review — contact BSA team before client outreach";

  return (
    <div className="banner" role="alert" aria-live="polite">
      <svg
        className="ic i"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      >
        <path d="M12 3l7 3v6c0 4-3 7-7 8-4-1-7-4-7-8V6l7-3z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
      <div className="tx">
        <b>{message.split(" — ")[0]}</b>
        {message.includes(" — ") ? ` — ${message.split(" — ")[1]}` : ""}
        {illustrative && <span className="pill-ex">Example</span>}
      </div>
    </div>
  );
}
