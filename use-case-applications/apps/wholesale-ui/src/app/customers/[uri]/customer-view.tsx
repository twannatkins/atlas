/**
 * Customer Entity 360 page.
 *
 * Full detail for a single customer: signals with provenance, household
 * membership, advisory relationships. The capability palette in the sidebar
 * shows context-specific actions based on entity state (a customer who already
 * has an advisor disables the referral capabilities).
 */

"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useCustomer } from "../../../hooks/use-customer";
import { useSignals } from "../../../hooks/use-signals";
import { useAuth } from "../../../../../shared/auth/use-auth";
import { AppShell } from "../../../../../shared/ui/chrome";
import { Entity360 } from "../../../components/entity-360";
import { SignalCard } from "../../../components/signal-card";
import { HouseholdStrip } from "../../../components/household-strip";
import { CapabilityPalette } from "../../../components/capability-palette";
import { ComplianceBanner } from "../../../components/compliance-banner";

const NAV = [{ href: "/", label: "My book" }];

export default function CustomerPage() {
  const params = useParams();
  const uri = decodeURIComponent(params.uri as string);
  const { personaClaim } = useAuth();
  const { customer, loading: customerLoading } = useCustomer(uri);
  const { signals, loading: signalsLoading } = useSignals(uri);

  if (customerLoading) {
    return (
      <AppShell brandSuffix="Wholesale" navLinks={NAV}>
        <p className="loading-line">Loading customer…</p>
      </AppShell>
    );
  }

  if (!customer) {
    return (
      <AppShell brandSuffix="Wholesale" navLinks={NAV}>
        <p className="loading-line" style={{ color: "var(--rust-ink)" }}>
          Customer not found: {uri}
        </p>
      </AppShell>
    );
  }

  // Determine if capabilities should be disabled based on entity state
  const hasAdvisor = customer.advisoryRelationships?.some((r: any) => r.isActive);
  const disabledCaps = hasAdvisor
    ? ["referral-orchestrator", "referral-rationale-drafter"]
    : [];

  const relationships = customer.advisoryRelationships ?? [];

  return (
    <AppShell brandSuffix="Wholesale" navLinks={NAV}>
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
        {/* Compliance banner — illustrative (marked "Example"): no per-entity compliance
            state exists to drive it (hasComplianceHold undefined + never persisted; see
            ComplianceBanner's illustrative prop doc + 04a). Do NOT wire to a fabricated field. */}
        <ComplianceBanner hasComplianceReview={true} personaClaim={personaClaim} illustrative={true} />

        {/* Wealth signals with provenance */}
        <div className="card">
          <div className="card-h">
            <span className="t">Wealth signals</span>
            <span className="meta">
              <span className="lab-live">live</span> derived · SHACL
            </span>
          </div>
          {signalsLoading ? (
            <p className="loading-line">Loading signals…</p>
          ) : signals.length === 0 ? (
            <p className="empty">No signals detected.</p>
          ) : (
            signals.map((sig: any) => (
              <SignalCard
                key={sig.uri}
                signalType={sig.signalType}
                signalDate={sig.signalDate}
                provenance={sig.provenance}
              />
            ))
          )}
        </div>

        {/* Household relationship strip */}
        {customer.household && (
          <div className="card">
            <div className="card-h">
              <span className="t">Household</span>
              <span className="meta">
                <span className="lab-live">live</span> memberOf
              </span>
            </div>
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
          </div>
        )}

        {/* Advisory relationships */}
        <div className="card">
          <div className="card-h">
            <span className="t">Advisory coverage</span>
            <span className="meta">
              <span className="lab-live">live</span> advisoryRelationships
            </span>
          </div>
          {relationships.length > 0 ? (
            relationships.map((rel: any) => (
              <div key={rel.uri} className={rel.isActive ? "cov active" : "cov hist"}>
                <div className="cov-top">
                  <span className="cov-name">{rel.advisor?.label}</span>
                  <span className={rel.isActive ? "cov-state on" : "cov-state off"}>
                    {rel.isActive ? "active" : "ended"}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <p className="empty">No active advisory relationship — coverage gap.</p>
          )}
        </div>
      </Entity360>
    </AppShell>
  );
}
