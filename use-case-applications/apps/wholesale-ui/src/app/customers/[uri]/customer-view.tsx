/**
 * Customer Entity 360 page.
 *
 * Full detail for a single customer: accounts, signals with provenance,
 * household membership, advisory relationships. The capability palette
 * in the sidebar shows context-specific actions based on entity state.
 */

"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useCustomer } from "../../../hooks/use-customer";
import { useSignals } from "../../../hooks/use-signals";
import { useAuth } from "../../../../../shared/auth/use-auth";
import { Entity360 } from "../../../components/entity-360";
import { SignalCard } from "../../../components/signal-card";
import { HouseholdStrip } from "../../../components/household-strip";
import { CapabilityPalette } from "../../../components/capability-palette";
import { ComplianceBanner } from "../../../components/compliance-banner";

export default function CustomerPage() {
  const params = useParams();
  const uri = decodeURIComponent(params.uri as string);
  const { personaClaim } = useAuth();
  const { customer, loading: customerLoading } = useCustomer(uri);
  const { signals, loading: signalsLoading } = useSignals(uri);

  if (customerLoading) {
    return <div className="p-6 text-neutral-400">Loading customer...</div>;
  }

  if (!customer) {
    return <div className="p-6 text-red-600">Customer not found: {uri}</div>;
  }

  // Determine if capabilities should be disabled based on entity state
  const hasAdvisor = customer.advisoryRelationships?.some(
    (r: any) => r.isActive,
  );
  const disabledCaps = hasAdvisor
    ? ["referral-orchestrator", "referral-rationale-drafter"]
    : [];

  return (
    <Entity360
      customerLabel={customer.label || "Unknown"}
      customerId={customer.customerId}
      sidebar={
        <CapabilityPalette
          personaClaim={personaClaim}
          onInvoke={(name) => console.log("Invoke:", name)}
          disabledCapabilities={disabledCaps}
        />
      }
    >
      {/* Compliance banner — respects tipping-off prohibition. Illustrative (marked
          "Example"): no per-entity compliance state exists to drive it (hasComplianceHold
          is undefined + never persisted; see ComplianceBanner's illustrative prop doc +
          04a). Do NOT wire to a fabricated field. */}
      <ComplianceBanner
        hasComplianceReview={true}
        personaClaim={personaClaim}
        illustrative={true}
      />

      {/* Wealth signals with provenance */}
      <section>
        <h2 className="text-lg font-semibold text-neutral-800 mb-3">
          Wealth signals
        </h2>
        {signalsLoading ? (
          <p className="text-neutral-400">Loading signals...</p>
        ) : signals.length === 0 ? (
          <p className="text-neutral-400">No signals detected.</p>
        ) : (
          <div className="space-y-3">
            {signals.map((sig: any) => (
              <SignalCard
                key={sig.uri}
                signalType={sig.signalType}
                strength={sig.strength}
                signalDate={sig.signalDate}
                provenance={sig.provenance}
              />
            ))}
          </div>
        )}
      </section>

      {/* Household relationship strip */}
      {customer.household && (
        <section>
          <h2 className="text-lg font-semibold text-neutral-800 mb-3">
            Household
          </h2>
          <HouseholdStrip
            nodes={
              customer.household.members?.map((m: any) => ({
                uri: m.uri,
                type: "atlas:Customer",
                label: m.label,
                relationship: "atlas:memberOf",
              })) ?? []
            }
            onNodeClick={(nodeUri) =>
              (window.location.href = `/customers/${encodeURIComponent(nodeUri)}`)
            }
          />
        </section>
      )}

      {/* Advisory relationships */}
      <section>
        <h2 className="text-lg font-semibold text-neutral-800 mb-3">
          Advisory coverage
        </h2>
        {customer.advisoryRelationships?.length > 0 ? (
          <ul className="space-y-2">
            {customer.advisoryRelationships.map((rel: any) => (
              <li
                key={rel.uri}
                className="flex items-center justify-between rounded-md border border-neutral-200 p-3"
              >
                <span className="text-sm font-medium">
                  {rel.advisor?.label}
                </span>
                <span
                  className={`text-xs ${rel.isActive ? "text-green-600" : "text-neutral-400"}`}
                >
                  {rel.isActive ? "Active" : "Ended"}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-neutral-400">
            No active advisory relationship — coverage gap.
          </p>
        )}
      </section>
    </Entity360>
  );
}
