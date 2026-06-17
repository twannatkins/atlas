/**
 * Conversations page — single-turn natural-language query surface.
 *
 * Routes through the conversational-context-manager agent (which wraps nl-to-sparql-agent,
 * so it is template-bounded). It is single-turn today: AgentCore Memory is not wired
 * (the agent's get_memory/put_memory calls no-op), so each question is answered
 * independently. Real multi-turn memory is a separate Phase-2 item.
 */

"use client";

import React, { useState, useCallback } from "react";
import { ConversationPanel } from "../../components/conversation-panel";
import { SchemaGraphCard } from "../../../../shared/ui/schema-graph-card";
import {
  deriveSchemaHighlightFromConverse,
  SchemaHighlightState,
} from "../../../../shared/ui/schema-graph-highlight";
import { AppShell } from "../../../../shared/ui/chrome";
import { useAuth } from "../../../../shared/auth/use-auth";

const NAV = [
  { href: "/", label: "My clients" },
  { href: "/conversations", label: "Ask the graph" },
  { href: "/themes", label: "Themes" },
];

export default function ConversationsPage() {
  const { personaClaim } = useAuth();

  // Increment-2 overlay: the schema graph highlights the part of the model the last real
  // converse answer traversed. converse returns no templateId, so we match by SPARQL
  // signature (deterministic, unique-match-only — never guessed).
  const [schemaHighlight, setSchemaHighlight] = useState<SchemaHighlightState | null>(null);
  const onConvResult = useCallback(
    (res: { status?: string | null; sparql?: string | null; result?: unknown } | null) => {
      setSchemaHighlight(deriveSchemaHighlightFromConverse(res));
    },
    [],
  );

  return (
    <AppShell brandSuffix="Wealth" navLinks={NAV}>
      <div className="page-head">
        <h1>Ask the graph</h1>
        <p className="sub">Single-turn natural-language queries · conversational-context-manager</p>
      </div>
      {/* The model — the loaded ATLAS ontology as a node-link diagram, above the asking
          surface (the wealth analogue of the wholesale My-book placement). Shared component,
          advisor's-side framing; loaded-schema visual treatment (no live pill). The highlight
          overlay lights up the part the real converse query traversed. */}
      <SchemaGraphCard perspective="wealth" highlight={schemaHighlight} />
      <ConversationPanel personaClaim={personaClaim} onResult={onConvResult} />
    </AppShell>
  );
}
