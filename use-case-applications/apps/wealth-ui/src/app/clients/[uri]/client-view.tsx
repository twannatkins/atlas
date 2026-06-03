/**
 * Client 360 page — the Wealth Advisor's view of a client.
 *
 * Shows coverage status, behavioral signals, themes, and the
 * conversational surface. Same Customer type from the GraphQL schema
 * but different fragments than the Wholesale UI.
 */

"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@apollo/client";
import { CLIENT_360_QUERY } from "../../../graphql/queries";
import { useAuth } from "../../../../../shared/auth/use-auth";
import { CapabilityPalette } from "../../../components/capability-palette";
import { CoverageStrip } from "../../../components/coverage-strip";
import { ThemeCard } from "../../../components/theme-card";
import { ConversationPanel } from "../../../components/conversation-panel";

export default function ClientPage() {
  const params = useParams();
  const uri = decodeURIComponent(params.uri as string);
  const { personaClaim } = useAuth();

  const { data, loading } = useQuery(CLIENT_360_QUERY, {
    variables: { uri },
    skip: !uri,
  });

  if (loading) {
    return <div className="p-6 text-neutral-400">Loading client...</div>;
  }

  const client = data?.customer;
  if (!client) {
    return <div className="p-6 text-red-600">Client not found: {uri}</div>;
  }

  return (
    <div className="flex min-h-screen">
      <main className="flex-1 space-y-6 p-6">
        <header>
          <h1 className="text-2xl font-semibold">{client.label}</h1>
          <p className="text-sm text-neutral-400">{client.customerId}</p>
        </header>

        {/* Coverage status */}
        <section>
          <h2 className="text-lg font-semibold mb-3">Advisory coverage</h2>
          <CoverageStrip relationships={client.advisoryRelationships || []} />
        </section>

        {/* Themes */}
        <section>
          <h2 className="text-lg font-semibold mb-3">Market themes</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <ThemeCard theme="ESG Transition" relevance={0.82} />
            <ThemeCard theme="Rate Sensitivity" relevance={0.71} />
            <ThemeCard theme="Tech Concentration" relevance={0.65} />
          </div>
        </section>

        {/* Conversational surface */}
        <section>
          <h2 className="text-lg font-semibold mb-3">Ask about this client</h2>
          <ConversationPanel clientUri={uri} personaClaim={personaClaim} />
        </section>
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
