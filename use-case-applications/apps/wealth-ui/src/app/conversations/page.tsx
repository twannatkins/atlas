/**
 * Conversations page — multi-turn conversational surface.
 *
 * Uses the conversational-context-manager agent with AgentCore Memory.
 * Session-scoped: memory clears when the session ends.
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
          Multi-turn conversation · session-scoped memory · powered by conversational-context-manager
        </p>
      </header>

      <ConversationPanel personaClaim={personaClaim} />
    </main>
  );
}
