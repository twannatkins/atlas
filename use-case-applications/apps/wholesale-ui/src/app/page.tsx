/**
 * Dashboard page — the Consumer Banker's assigned book.
 *
 * Shows customers sorted by signal strength. This page demonstrates
 * that the query is persona-scoped: a Consumer Banker sees 45 clients,
 * a BSA Analyst would see all 200. The UI code is identical; the
 * difference comes from Lake Formation scoping in the resolver.
 */

"use client";

import React from "react";
import { useQuery } from "@apollo/client";
import { DASHBOARD_QUERY } from "../graphql/queries";
import { SignalCard } from "../components/signal-card";
import { CapabilityPalette } from "../components/capability-palette";
import { useAuth } from "../../../shared/auth/use-auth";

export default function DashboardPage() {
  const { personaClaim, displayName, isAuthenticated, signIn } = useAuth();
  const { data, loading } = useQuery(DASHBOARD_QUERY, {
    variables: { limit: 50 },
    skip: !isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <button
          onClick={signIn}
          className="rounded-md bg-primary-600 px-6 py-3 text-white font-medium hover:bg-primary-700"
        >
          Sign in as Consumer Banker
        </button>
      </div>
    );
  }

  const customers = data?.searchCustomers ?? [];

  return (
    <div className="flex min-h-screen">
      <main className="flex-1 p-6">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold">My book</h1>
          <p className="text-sm text-neutral-400">
            {displayName} · {personaClaim} · {customers.length} clients
          </p>
        </header>

        {loading && <p className="text-neutral-400">Loading...</p>}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {customers.map((customer: any) => (
            <a
              key={customer.uri}
              href={`/customers/${encodeURIComponent(customer.uri)}`}
              className="block rounded-lg border border-neutral-200 bg-white p-4 transition-shadow hover:shadow-md"
            >
              <h2 className="font-medium text-neutral-800">{customer.label}</h2>
              <p className="text-xs text-neutral-400">{customer.customerId}</p>
              {customer.wealthSignals?.length > 0 && (
                <div className="mt-2 space-y-1">
                  {customer.wealthSignals.slice(0, 2).map((sig: any) => (
                    <SignalCard
                      key={sig.uri}
                      signalType={sig.signalType}
                      strength={sig.strength}
                      signalDate={sig.signalDate}
                    />
                  ))}
                </div>
              )}
            </a>
          ))}
        </div>
      </main>

      <aside className="w-72 border-l border-neutral-200 bg-neutral-50">
        <CapabilityPalette
          personaClaim={personaClaim}
          onInvoke={(name) => console.log("Invoke:", name)}
        />
      </aside>
    </div>
  );
}
