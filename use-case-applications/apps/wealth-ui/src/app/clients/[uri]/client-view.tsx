/**
 * Client 360 page — the Wealth Advisor's view of a client.
 *
 * Shows advisory coverage, the client's wealth signals (with provenance), household
 * relationships, themes, and the single-turn conversational surface. Binds to the data
 * CLIENT_360_QUERY already fetches (coverage + nested wealthSignals + household). Same
 * Customer type as the Wholesale UI, surfaced for the advisor's read — and the same
 * warm-paper shell, indigo lens.
 */

"use client";

import React, { useState, useCallback } from "react";
import { useQuery, useMutation } from "@apollo/client";
import { CLIENT_360_QUERY, TAKE_ON_CLIENT_MUTATION } from "../../../graphql/queries";
import { useAuth } from "../../../../../shared/auth/use-auth";
import { useEntityUri } from "../../../../../shared/auth/use-entity-uri";
import { AppShell } from "../../../../../shared/ui/chrome";
import { CoverageStrip } from "../../../components/coverage-strip";
import { ConversationPanel } from "../../../components/conversation-panel";
import { SignalCard } from "../../../components/signal-card";
import { HouseholdStrip } from "../../../components/household-strip";

const NAV = [
  { href: "/", label: "My clients" },
  { href: "/conversations", label: "Ask the graph" },
  { href: "/themes", label: "Themes" },
];

/** First two initials, for the client avatar. */
function initials(name: string): string {
  const parts = (name || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "—";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function ClientPage() {
  // Read the real client URI from the path (static export serves a shared _placeholder
  // doc for every /clients/* path, so useParams() can't be trusted here).
  const uri = useEntityUri("/clients/");
  const { personaClaim } = useAuth();

  const { data, loading, refetch } = useQuery(CLIENT_360_QUERY, {
    variables: { uri },
    skip: !uri,
  });

  // Take-on — accept a routed client. Writes a real atlas:takenOnAt fact (clears the
  // "new client" banner). Refetch after so the banner updates from the real new state.
  const [takeOn, { loading: takingOn }] = useMutation(TAKE_ON_CLIENT_MUTATION);
  const handleTakeOn = useCallback(async () => {
    try {
      await takeOn({ variables: { customerUri: uri } });
      await refetch();
    } catch (e) {
      console.error("take-on failed:", e);
    }
  }, [takeOn, uri, refetch]);

  if (loading) {
    return (
      <AppShell brandSuffix="Wealth" navLinks={NAV}>
        <p className="loading-line">Loading client…</p>
      </AppShell>
    );
  }

  const client = data?.customer;
  if (!client) {
    return (
      <AppShell brandSuffix="Wealth" navLinks={NAV}>
        <p className="loading-line" style={{ color: "var(--rust-ink)" }}>
          Client not found: {uri}
        </p>
      </AppShell>
    );
  }

  const signals = client.wealthSignals ?? [];
  // "New client" — this client was routed to the advisor by the referral workflow
  // (routedByWorkflow) and has NOT yet been taken on (no takenOnAt). Real graph state,
  // not a timer: it clears only when takeOnClient writes atlas:takenOnAt. (isActive /
  // coverage are unchanged — this is parallel state.)
  const rels = client.advisoryRelationships ?? [];
  const isNewlyRouted = rels.some((r: any) => r.routedByWorkflow && !r.takenOnAt);

  return (
    <AppShell brandSuffix="Wealth" navLinks={NAV}>
      {/* client header */}
      <div className="card">
        <div className="head">
          <div className="av">{initials(client.label)}</div>
          <div className="grow">
            <div className="title-row">
              <span className="name">{client.label}</span>
              <span className="chip">fibo:Party</span>
              {client.customerId && <span className="chip">{client.customerId}</span>}
            </div>
            <p className="sub">Advisory coverage and signals from the graph</p>
          </div>
        </div>
      </div>

      {/* "New client" banner — shows while routed-to-you AND not-yet-taken-on; the
          Take-on button writes a real atlas:takenOnAt fact that clears it (not a timer). */}
      {isNewlyRouted && (
        <div className="banner" role="status" style={{ background: "var(--indigo-bg)", borderColor: "var(--indigo)" }}>
          <svg className="ic i" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" style={{ color: "var(--indigo)" }}>
            <path d="M12 3l7 3v6c0 4-3 7-7 8-4-1-7-4-7-8V6l7-3z" /><path d="M9 12l2 2 4-4" />
          </svg>
          <div className="tx" style={{ color: "var(--indigo)" }}>
            <b>New — routed to you.</b> This client was referred from Consumer Banking and is
            awaiting your take-on.
          </div>
          <button className="btn accent" style={{ marginLeft: "auto" }} onClick={handleTakeOn} disabled={takingOn}>
            {takingOn ? "Taking on…" : "Take on client"}
          </button>
        </div>
      )}

      {/* two columns: coverage + signals (both real) */}
      <div className="two">
        <div className="card">
          <div className="card-h">
            <span className="t">Advisory coverage</span>
            <span className="meta">
              <span className="lab-live">live</span> advisoryRelationships
            </span>
          </div>
          <CoverageStrip relationships={client.advisoryRelationships || []} />
        </div>

        {/* Wealth signals — already fetched by CLIENT_360_QUERY (nested
            Customer.wealthSignals, resolved via the Pass-2c resolver), now surfaced here.
            Real signals for a signalled client, honest empty state otherwise. No strength
            badge — there is no derived strength in the data. */}
        <div className="card">
          <div className="card-h">
            <span className="t">Wealth-readiness signals</span>
            <span className="meta">
              <span className="lab-live">live</span> derived · SHACL
            </span>
          </div>
          {signals.length > 0 ? (
            <>
              {signals.map((sig: any) => (
                <SignalCard
                  key={sig.uri}
                  signalType={sig.signalType}
                  signalDate={sig.signalDate}
                  provenance={sig.provenance}
                />
              ))}
              <p className="card-note">
                Already selected by the client-360 query — surfaced here to enrich the
                screen with real graph data.
              </p>
            </>
          ) : (
            <p className="empty">No signals derived for this client yet.</p>
          )}
        </div>
      </div>

      {/* Household — the real members from CLIENT_360_QUERY's household selection */}
      {client.household && (
        <div className="card">
          <div className="card-h">
            <span className="t">Household</span>
            <span className="meta">
              <span className="lab-live">live</span> memberOf
            </span>
          </div>
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
        </div>
      )}

      {/* Themes — no per-client themes are derived yet (the theme corpus is empty: see
          ontology-extensions/themes.ttl). Rather than invent ESG/rate/tech themes with
          fabricated relevance scores, show the honest empty state. */}
      <div className="card">
        <div className="card-h">
          <span className="t">Market themes</span>
          <span className="meta">
            <span className="lab-live">live</span> themes · SKOS
          </span>
        </div>
        <p className="empty">
          No themes tracked for this client yet — the theme corpus is empty; nothing is
          invented to fill it.
        </p>
      </div>

      {/* Conversational surface */}
      <ConversationPanel clientUri={uri} personaClaim={personaClaim} />

      {/* Roadmap — explicitly NOT live */}
      <div className="future-band">
            <div className="future-h">
              <svg className="i" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--future)" strokeWidth="1.7">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
              <span className="lab">Possible next — RM session intelligence</span>
              <span className="note">roadmap — not shown as live</span>
            </div>
            <div className="froadmap">
              <div className="fitem">
                <div className="ft">
                  Portfolio &amp; AUM <span className="ftier data">needs data</span>
                </div>
                <div className="fd">
                  Holdings, AUM trend, asset allocation, concentration — requires position/balance
                  data not in the graph today.
                </div>
              </div>
              <div className="fitem">
                <div className="ft">
                  Behavioral signals <span className="ftier data">needs data</span>
                </div>
                <div className="fd">
                  Engagement decay, network influence, transaction-derived segment shift —
                  clickstream / network / temporal data the graph doesn&apos;t yet hold.
                </div>
              </div>
              <div className="fitem">
                <div className="ft">
                  Multi-turn memory <span className="ftier build">buildable</span>
                </div>
                <div className="fd">
                  Carry context across turns — rewrite to CreateEvent / RetrieveMemoryRecords;
                  no new data needed.
                </div>
              </div>
              <div className="fitem">
                <div className="ft">
                  Per-advisor scoping <span className="ftier build">buildable</span>
                </div>
                <div className="fd">
                  &quot;My clients&quot; instead of &quot;the book&quot; — advisor-identity
                  parameter + scoped templates over existing data.
                </div>
              </div>
            </div>
          </div>
    </AppShell>
  );
}
