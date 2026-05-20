/**
 * Advisor dashboard — the Wealth Advisor's coverage book.
 *
 * Shows assigned clients with behavioral signals, engagement scores,
 * and theme relevance. Same GraphQL schema as the Wholesale UI but
 * different fragments — this is Thesis 2 made visible.
 */

"use client";

import React from "react";
import { useQuery } from "@apollo/client";
import { ADVISOR_DASHBOARD_QUERY } from "../graphql/queries";
import { CapabilityPalette } from "../components/capability-palette";
import { useAuth } from "../../../shared/auth/use-auth";

export default function AdvisorDashboard() {
  const { personaClaim, displayName, isAuthenticated, signIn } = useAuth();
  const { data, loading } = useQuery(ADVISOR_DASHBOARD_QUERY, {
    variables: { limit: 30 },
    skip: !isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <button
          onClick={signIn}
          className="rounded-md bg-primary-600 px-6 py-3 text-white font-medium hover:bg-primary-700"
        >
          Sign in as Wealth Advisor
        </button>
      </div>
    );
  }

  const clients = data?.searchCustomers ?? [];

  return (
    <div className="flex min-h-screen">
      <main className="flex-1 p-6">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold">My clients</h1>
          <p className="text-sm text-neutral-400">
            {displayName} · {personaClaim} · {clients.length} clients
          </p>
        </header>

        {loading && <p className="text-neutral-400">Loading...</p>}

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {clients.map((client: any) => (
            <a
              key={client.uri}
              href={`/clients/${encodeURIComponent(client.uri)}`}
              className="block rounded-lg border border-neutral-200 bg-white p-4 transition-shadow hover:shadow-md"
            >
              <h2 className="font-medium text-neutral-800">{client.label}</h2>
              <p className="text-xs text-neutral-400">{client.customerId}</p>
              {client.advisoryRelationships?.length > 0 && (
                <p className="mt-1 text-xs text-green-600">Active coverage</p>
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
