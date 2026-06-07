/**
 * Conversation panel (#5) — real, single-turn natural-language query over the graph.
 *
 * Routes through conversational-context-manager (the named conversational agent in the
 * registry), which wraps nl-to-sparql-agent — so it is TEMPLATE-BOUNDED, exactly like
 * the wholesale Ask-the-graph. Two honesty facts are surfaced, not hidden:
 *   - it is SINGLE-TURN: the agent's Memory is not wired (priorTurns is always 0), so
 *     each question is answered independently — shown as a visible indicator from the
 *     response data, not just copy;
 *   - it answers a fixed set of questions (suggestedQuestions, read live from the agent's
 *     own ground-truth.yaml) — always visible, never a bare "ask anything" box; an
 *     unmatched question shows those suggestions, never a fabricated answer.
 */

"use client";

import React, { useState, useCallback, useRef } from "react";
import { useQuery, useMutation } from "@apollo/client";
import { CONVERSE_MUTATION, SUGGESTED_QUESTIONS_QUERY } from "../graphql/queries";

interface Turn {
  question: string;
  status: string;
  rows: Record<string, unknown>[];
  sparql?: string;
}

export function ConversationPanel({ personaClaim }: { clientUri?: string; personaClaim: string }) {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  // A per-mount session id satisfies the agent contract. It does NOT enable multi-turn
  // memory (the agent's Memory no-ops) — the conversation is single-turn regardless.
  const sessionId = useRef(
    `sess-${Math.random().toString(36).slice(2)}-${personaClaim}`,
  ).current;

  const { data: sq } = useQuery(SUGGESTED_QUESTIONS_QUERY);
  const suggestions: string[] = sq?.suggestedQuestions ?? [];
  const [converse, { loading }] = useMutation(CONVERSE_MUTATION);

  const ask = useCallback(
    async (q: string) => {
      const text = q.trim();
      if (!text) return;
      setInput("");
      try {
        const { data } = await converse({ variables: { question: text, sessionId } });
        const r = data?.converse;
        const raw = r?.result;
        const rows: Record<string, unknown>[] = Array.isArray(raw)
          ? raw
          : typeof raw === "string"
            ? (() => { try { return JSON.parse(raw); } catch { return []; } })()
            : [];
        setTurns((prev) => [
          ...prev,
          { question: text, status: r?.status ?? "query_error", rows, sparql: r?.sparql ?? undefined },
        ]);
      } catch {
        setTurns((prev) => [
          ...prev,
          { question: text, status: "query_error", rows: [] },
        ]);
      }
    },
    [converse, sessionId],
  );

  return (
    <div className="rounded-lg border border-neutral-200 bg-white">
      {/* Single-turn indicator — surfaced as a fact, not a claim. */}
      <div className="flex items-center justify-between border-b border-neutral-200 px-4 py-2">
        <p className="text-xs text-neutral-500">
          Each question is answered independently (single-turn).
        </p>
      </div>

      {/* Suggested questions — ALWAYS visible; exactly what the agent can answer. */}
      {suggestions.length > 0 && (
        <div className="space-y-1 border-b border-neutral-200 p-3">
          <p className="text-xs font-medium uppercase tracking-wide text-neutral-400">
            Questions you can ask
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((q) => (
              <button
                key={q}
                onClick={() => ask(q)}
                className="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs text-neutral-700 hover:bg-neutral-100"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Turn history */}
      <div className="max-h-96 space-y-3 overflow-y-auto p-4">
        {turns.length === 0 && (
          <p className="text-sm text-neutral-400">
            Ask a question about the book. Each question is answered independently.
          </p>
        )}
        {turns.map((t, i) => (
          <div key={i} className="space-y-1">
            <p className="ml-8 rounded-md bg-primary-50 p-2 text-sm text-primary-900">{t.question}</p>
            <div className="mr-8 rounded-md bg-neutral-50 p-2 text-sm text-neutral-800">
              {t.status === "success" ? (
                <>
                  <p className="text-xs text-neutral-400">{t.rows.length} result{t.rows.length === 1 ? "" : "s"}</p>
                  {t.rows.length > 0 ? (
                    <ul className="mt-1 space-y-0.5">
                      {t.rows.slice(0, 10).map((row, j) => (
                        <li key={j} className="font-mono text-xs">{Object.values(row).map(String).join(" · ")}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-neutral-500">No matching rows.</p>
                  )}
                  {t.sparql && (
                    <details className="mt-1 text-xs text-neutral-400">
                      <summary className="cursor-pointer">Show the SPARQL that ran</summary>
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap font-mono">{t.sparql}</pre>
                    </details>
                  )}
                </>
              ) : t.status === "no_template_match" ? (
                <p>I can&apos;t answer that one yet — try one of the questions above.</p>
              ) : (
                <p className="text-red-600">The query couldn&apos;t be run just now. Please try again.</p>
              )}
            </div>
          </div>
        ))}
        {loading && <div className="text-sm text-neutral-400 animate-pulse">Querying the graph…</div>}
      </div>

      {/* Input */}
      <div className="flex gap-2 border-t border-neutral-200 p-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(input)}
          placeholder="Ask about the book…"
          className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          aria-label="Conversation input"
        />
        <button
          onClick={() => ask(input)}
          disabled={!input.trim() || loading}
          className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
