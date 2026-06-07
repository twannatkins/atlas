/**
 * Client 360 page — the Wealth Advisor's view of a client.
 *
 * Shows advisory coverage, the client's wealth signals (with provenance), household
 * relationships, themes, and the single-turn conversational surface. Binds to the data
 * CLIENT_360_QUERY already fetches (coverage + nested wealthSignals + household). Same
 * Customer type as the Wholesale UI, surfaced for the advisor's read.
 */

"use client";

import React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@apollo/client";
import { CLIENT_360_QUERY } from "../../../graphql/queries";
import { useAuth } from "../../../../../shared/auth/use-auth";
import { CapabilityPalette } from "../../../components/capability-palette";
import { CoverageStrip } from "../../../components/coverage-strip";
import { ConversationPanel } from "../../../components/conversation-panel";
import { SignalCard } from "../../../components/signal-card";
import { HouseholdStrip } from "../../../components/household-strip";

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

        {/* Wealth signals — already fetched by CLIENT_360_QUERY (nested
            Customer.wealthSignals, resolved via the Pass-2c resolver), now surfaced here.
            Real signals for a signalled client, honest empty state otherwise. No strength
            badge — there is no derived strength in the data. */}
        <section>
          <h2 className="text-lg font-semibold mb-3">Wealth signals</h2>
          {client.wealthSignals && client.wealthSignals.length > 0 ? (
            <div className="space-y-3">
              {client.wealthSignals.map((sig: any) => (
                <SignalCard
                  key={sig.uri}
                  signalType={sig.signalType}
                  signalDate={sig.signalDate}
                  provenance={sig.provenance}
                />
              ))}
            </div>
          ) : (
            <p className="text-sm text-neutral-400">No signals derived for this client yet.</p>
          )}
        </section>

        {/* Household — the real members from CLIENT_360_QUERY's household selection,
            clickable to navigate. Only rendered when the client belongs to a household. */}
        {client.household && (
          <section>
            <h2 className="text-lg font-semibold mb-3">Household</h2>
            <HouseholdStrip
              nodes={
                client.household.members?.map((m: any) => ({
                  uri: m.uri,
                  type: "atlas:Customer",
                  label: m.label,
                  relationship: "atlas:memberOf",
                })) ?? []
              }
              onNodeClick={(nodeUri) =>
                (window.location.href = `/clients/${encodeURIComponent(nodeUri)}`)
              }
            />
          </section>
        )}

        {/* Themes — no per-client themes are derived yet (the theme corpus is empty: see
            ontology-extensions/themes.ttl). Rather than invent ESG/rate/tech themes with
            fabricated relevance scores, show the honest empty state. The /themes page runs
            the real (currently empty) themes query; this client view will surface real
            client-linked themes once the corpus is populated. */}
        <section>
          <h2 className="text-lg font-semibold mb-3">Market themes</h2>
          <p className="text-sm text-neutral-400">
            No themes tracked for this client yet.
          </p>
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
