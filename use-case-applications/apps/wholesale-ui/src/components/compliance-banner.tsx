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
   * When true, the banner is shown to demonstrate the non-tipping-off copy pattern even
   * though the per-entity compliance state is not yet wired to a real GraphQL field. It
   * renders a visible "Example" marker so it is NOT mistaken for a real review state.
   * Wiring a real hasComplianceReview field is a separate item.
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
