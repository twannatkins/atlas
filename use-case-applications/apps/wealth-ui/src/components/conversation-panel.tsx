/**
 * Conversation panel — multi-turn conversational surface.
 *
 * Uses the conversational-context-manager agent with AgentCore Memory.
 * Session-scoped: memory clears when the session ends. Follow-up
 * questions like "Of those, which..." resolve via prior context.
 */

import React, { useState, useCallback } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  sparql?: string;
}

interface ConversationPanelProps {
  clientUri?: string;
  personaClaim: string;
}

export function ConversationPanel({ clientUri, personaClaim }: ConversationPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = useCallback(async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // In production: invoke conversational-context-manager via registry
    // Simulated for workshop
    setTimeout(() => {
      const response: Message = {
        role: "assistant",
        content: `Found 3 results for "${input}". The query was scoped to your assigned clients.`,
        sparql: "SELECT ?client WHERE { ... }",
      };
      setMessages((prev) => [...prev, response]);
      setIsLoading(false);
    }, 1500);
  }, [input]);

  return (
    <div className="rounded-lg border border-neutral-200 bg-white">
      {/* Message history */}
      <div className="max-h-96 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-sm text-neutral-400">
            Ask a question about your clients. Follow-up questions will use context from prior turns.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`rounded-md p-3 text-sm ${
              msg.role === "user"
                ? "bg-primary-50 text-primary-900 ml-8"
                : "bg-neutral-50 text-neutral-800 mr-8"
            }`}
          >
            <p>{msg.content}</p>
            {msg.sparql && (
              <pre className="mt-1 text-xs text-neutral-400 font-mono overflow-x-auto">
                {msg.sparql}
              </pre>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="text-sm text-neutral-400 animate-pulse">Thinking...</div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-neutral-200 p-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about your clients..."
          className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          aria-label="Conversation input"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="rounded-md bg-primary-600 px-4 py-2 text-sm text-white font-medium hover:bg-primary-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
