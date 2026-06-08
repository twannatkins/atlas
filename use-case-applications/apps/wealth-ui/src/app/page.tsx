/**
 * Advisor dashboard — the Wealth Advisor's coverage book.
 *
 * Shows assigned clients with their coverage status. Same GraphQL schema as the
 * Wholesale UI but a different lens — this is Thesis 2 made visible: same
 * backbone, the warm-paper shell with an indigo accent instead of blue.
 */

"use client";

import React from "react";
import { useQuery } from "@apollo/client";
import { ADVISOR_DASHBOARD_QUERY } from "../graphql/queries";
import { CapabilityPalette } from "../components/capability-palette";
import { AppShell, SignInGate } from "../../../shared/ui/chrome";
import { useAuth } from "../../../shared/auth/use-auth";

const NAV = [
  { href: "/", label: "My clients" },
  { href: "/conversations", label: "Ask the graph" },
  { href: "/themes", label: "Themes" },
];

export default function AdvisorDashboard() {
  const { personaClaim, isAuthenticated, signIn } = useAuth();
  const { data, loading } = useQuery(ADVISOR_DASHBOARD_QUERY, {
    variables: { limit: 30 },
    skip: !isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <AppShell brandSuffix="Wealth" navLinks={NAV}>
        <SignInGate
          label="Sign in as Wealth Advisor"
          blurb="The advisor workbench. Sign in to see your client coverage, the wealth-readiness signals derived from the graph, and the single-turn conversational surface over the book."
          signIn={signIn}
        />
      </AppShell>
    );
  }

  const clients = data?.searchCustomers ?? [];

  return (
    <AppShell brandSuffix="Wealth" navLinks={NAV}>
      <div className="shell">
        <div className="shell-main">
          <div className="page-head">
            <h1>My clients</h1>
            <p className="sub">{clients.length} clients · coverage and signals from the graph</p>
          </div>

          {loading && <p className="loading-line">Loading your clients…</p>}

          <div className="entity-grid">
            {clients.map((client: any) => {
              const covered = client.advisoryRelationships?.length > 0;
              return (
                <a
                  key={client.uri}
                  href={`/clients/${encodeURIComponent(client.uri)}`}
                  className="entity-card"
                >
                  <div className="en">{client.label}</div>
                  <p className="eid">{client.customerId}</p>
                  <div className="etags">
                    {covered ? (
                      <span className="mini-sig">Active coverage</span>
                    ) : (
                      <span className="mini-gap">Coverage gap</span>
                    )}
                  </div>
                </a>
              );
            })}
          </div>
        </div>

        <CapabilityPalette
          personaClaim={personaClaim}
          onInvoke={(name) => console.log("Invoke:", name)}
        />
      </div>
    </AppShell>
  );
}
