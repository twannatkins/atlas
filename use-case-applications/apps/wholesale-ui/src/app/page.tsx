/**
 * Dashboard page — the Consumer Banker's assigned book.
 *
 * Shows customers sorted by signal strength. This page demonstrates
 * that the query is persona-scoped: a Consumer Banker sees their book,
 * a BSA Analyst would see all. The UI code is identical; the
 * difference comes from Lake Formation scoping in the resolver.
 */

"use client";

import React, { useState, useCallback } from "react";
import { useQuery, useMutation } from "@apollo/client";
import { DASHBOARD_QUERY } from "../graphql/queries";
import { RESET_DEMO_ROUTINGS_MUTATION } from "../graphql/mutations";
import { AskGraphPanel } from "../components/ask-graph-panel";
import { AppShell, SignInGate } from "../../../shared/ui/chrome";
import { useAuth } from "../../../shared/auth/use-auth";

const NAV = [
  { href: "/", label: "My book" },
];

export default function DashboardPage() {
  const { isAuthenticated, signIn } = useAuth();
  const { data, loading, refetch } = useQuery(DASHBOARD_QUERY, {
    variables: { limit: 50 },
    skip: !isAuthenticated,
  });

  // Workshop Reset — removes the demo-created routings so the walkthrough can be re-run.
  const [resetDemo] = useMutation(RESET_DEMO_ROUTINGS_MUTATION);
  const [resetMsg, setResetMsg] = useState("");
  const [resetting, setResetting] = useState(false);
  const handleReset = useCallback(async () => {
    setResetting(true);
    setResetMsg("");
    try {
      const { data: r } = await resetDemo();
      setResetMsg(r?.resetDemoRoutings?.message || "Reset complete.");
      await refetch();
    } catch {
      setResetMsg("Reset could not be completed just now.");
    } finally {
      setResetting(false);
    }
  }, [resetDemo, refetch]);

  if (!isAuthenticated) {
    return (
      <AppShell brandSuffix="Wholesale" navLinks={NAV}>
        <SignInGate
          label="Sign in as Consumer Banker"
          blurb="The consumer-to-wealth referral workbench. Sign in to see your book, the wealth-readiness signals derived from the graph, and the actions the registry makes available."
          signIn={signIn}
        />
      </AppShell>
    );
  }

  const customers = data?.searchCustomers ?? [];

  return (
    <AppShell brandSuffix="Wholesale" navLinks={NAV}>
      <div className="page-head" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h1>My book</h1>
          <p className="sub">{customers.length} customers · scoped by Lake Formation to your persona</p>
        </div>
        {/* Workshop control — reset the demo-created routings (advisory relationships +
            routing decisions) back to the seed default so the walkthrough can repeat. */}
        <button className="btn" onClick={handleReset} disabled={resetting} title="Remove demo-created referrals and return the graph to its seed state">
          {resetting ? "Resetting…" : "↺ Reset demo"}
        </button>
      </div>
      {resetMsg && <p className="card-note" style={{ marginBottom: 12 }}>{resetMsg}</p>}

      {/* Ask the graph (#2) — real, template-bounded NL query with suggested questions */}
      <AskGraphPanel />

      {loading && <p className="loading-line">Loading your book…</p>}

      <div className="entity-grid">
        {customers.map((customer: any) => {
          const sigs = customer.wealthSignals ?? [];
          const activeCoverage = (customer.advisoryRelationships ?? []).find((r: any) => r.isActive);
          return (
            <a
              key={customer.uri}
              href={`/customers/${encodeURIComponent(customer.uri)}`}
              className="entity-card"
            >
              <div className="en">{customer.label}</div>
              <p className="eid">{customer.customerId}</p>
              <div className="etags">
                {sigs.length > 0 && (
                  <span className="mini-sig">
                    {sigs.length} signal{sigs.length === 1 ? "" : "s"}
                  </span>
                )}
                {/* Coverage status — covered customers already have a wealth advisor (don't
                    re-refer); uncovered + signalled are the referral candidates. */}
                {activeCoverage ? (
                  <span className="mini-sig" title="Already has a wealth advisor">
                    ✓ {activeCoverage.advisor?.label || "Advised"}
                  </span>
                ) : (
                  <span className="mini-gap">No advisor</span>
                )}
              </div>
            </a>
          );
        })}
      </div>
    </AppShell>
  );
}
