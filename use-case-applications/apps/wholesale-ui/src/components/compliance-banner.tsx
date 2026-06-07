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
    <div
      role="alert"
      aria-live="polite"
      className="flex items-center gap-3 rounded-md border px-4 py-3"
      style={{
        backgroundColor: "var(--color-compliance-bg)",
        borderColor: "var(--color-compliance-border)",
        color: "var(--color-compliance-text)",
      }}
    >
      <span aria-hidden="true" className="text-lg">⚠️</span>
      <span className="text-sm font-medium">{message}</span>
      {illustrative && (
        <span className="ml-auto rounded-full bg-neutral-200 px-2 py-0.5 text-xs font-medium text-neutral-600">
          Example
        </span>
      )}
    </div>
  );
}
