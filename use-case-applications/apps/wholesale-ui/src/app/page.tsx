/**
 * Dashboard page — the Consumer Banker's assigned book.
 *
 * Shows customers sorted by signal strength. This page demonstrates
 * that the query is persona-scoped: a Consumer Banker sees their book,
 * a BSA Analyst would see all. The UI code is identical; the
 * difference comes from Lake Formation scoping in the resolver.
 */

"use client";

import React from "react";
import { useQuery } from "@apollo/client";
import { DASHBOARD_QUERY } from "../graphql/queries";
import { AskGraphPanel } from "../components/ask-graph-panel";
import { AppShell, SignInGate } from "../../../shared/ui/chrome";
import { useAuth } from "../../../shared/auth/use-auth";

const NAV = [
  { href: "/", label: "My book" },
];

export default function DashboardPage() {
  const { isAuthenticated, signIn } = useAuth();
  const { data, loading } = useQuery(DASHBOARD_QUERY, {
    variables: { limit: 50 },
    skip: !isAuthenticated,
  });

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
      <div className="page-head">
        <h1>My book</h1>
        <p className="sub">{customers.length} customers · scoped by Lake Formation to your persona</p>
      </div>

      {/* Ask the graph (#2) — real, template-bounded NL query with suggested questions */}
      <AskGraphPanel />

      {loading && <p className="loading-line">Loading your book…</p>}

      <div className="entity-grid">
        {customers.map((customer: any) => {
          const sigs = customer.wealthSignals ?? [];
          return (
            <a
              key={customer.uri}
              href={`/customers/${encodeURIComponent(customer.uri)}`}
              className="entity-card"
            >
              <div className="en">{customer.label}</div>
              <p className="eid">{customer.customerId}</p>
              {sigs.length > 0 && (
                <div className="etags">
                  <span className="mini-sig">
                    {sigs.length} signal{sigs.length === 1 ? "" : "s"}
                  </span>
                </div>
              )}
            </a>
          );
        })}
      </div>
    </AppShell>
  );
}
