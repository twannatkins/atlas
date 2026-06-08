/**
 * Conversations page — single-turn natural-language query surface.
 *
 * Routes through the conversational-context-manager agent (which wraps nl-to-sparql-agent,
 * so it is template-bounded). It is single-turn today: AgentCore Memory is not wired
 * (the agent's get_memory/put_memory calls no-op), so each question is answered
 * independently. Real multi-turn memory is a separate Phase-2 item.
 */

"use client";

import React from "react";
import { ConversationPanel } from "../../components/conversation-panel";
import { AppShell } from "../../../../shared/ui/chrome";
import { useAuth } from "../../../../shared/auth/use-auth";

const NAV = [
  { href: "/", label: "My clients" },
  { href: "/conversations", label: "Ask the graph" },
  { href: "/themes", label: "Themes" },
];

export default function ConversationsPage() {
  const { personaClaim } = useAuth();

  return (
    <AppShell brandSuffix="Wealth" navLinks={NAV}>
      <div className="page-head">
        <h1>Ask the graph</h1>
        <p className="sub">Single-turn natural-language queries · conversational-context-manager</p>
      </div>
      <ConversationPanel personaClaim={personaClaim} />
    </AppShell>
  );
}
