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
import { useAuth } from "../../../../shared/auth/use-auth";

export default function ConversationsPage() {
  const { personaClaim } = useAuth();

  return (
    <main className="p-6 max-w-3xl mx-auto">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">Ask the graph</h1>
        <p className="text-sm text-neutral-400">
          Single-turn natural-language queries · powered by conversational-context-manager
        </p>
      </header>

      <ConversationPanel personaClaim={personaClaim} />
    </main>
  );
}
