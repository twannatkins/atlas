/**
 * Conversation panel (#5) — real, single-turn natural-language query over the graph.
 *
 * Routes through conversational-context-manager (the named conversational agent in the
 * registry), which wraps nl-to-sparql-agent — so it is TEMPLATE-BOUNDED, exactly like
 * the wholesale Ask-the-graph. Two honesty facts are surfaced, not hidden:
 *   - it is SINGLE-TURN: the agent's Memory is not wired (priorTurns is always 0), so
 *     each question is answered independently — shown as a visible "single-turn" pill;
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

/**
 * onResult (optional) lifts the REAL converse result (status + sparql + rows) up to the
 * page so the adjacent Schema-graph card can highlight the part of the model the query
 * traversed. converse returns no templateId, so the page matches by SPARQL signature
 * (deriveSchemaHighlightFromConverse). The panel's own behaviour is unchanged.
 */
export function ConversationPanel({
  personaClaim,
  onResult,
}: {
  clientUri?: string;
  personaClaim: string;
  onResult?: (res: { status?: string | null; sparql?: string | null; result?: unknown } | null) => void;
}) {
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
        // Lift the real result so the adjacent schema graph can highlight the traversal.
        if (onResult) onResult(r ? { status: r.status, sparql: r.sparql, result: raw } : null);
      } catch {
        setTurns((prev) => [
          ...prev,
          { question: text, status: "query_error", rows: [] },
        ]);
        if (onResult) onResult(null);
      }
    },
    [converse, sessionId, onResult],
  );

  return (
    <div className="card">
      <div className="conv-h">
        <span className="t">Ask about the book</span>
        <span className="meta">
          <span className="single">single-turn</span> conversational-context-manager · priorTurns 0
        </span>
      </div>

      {/* Suggested questions — ALWAYS visible; exactly what the agent can answer. */}
      {suggestions.length > 0 && (
        <>
          <p className="qlabel">Questions you can ask</p>
          <div className="chips">
            {suggestions.map((q) => (
              <button key={q} className="qchip" onClick={() => ask(q)}>
                {q}
              </button>
            ))}
          </div>
        </>
      )}

      {/* Turn history */}
      <div style={{ marginTop: 12 }}>
        {turns.length === 0 && (
          <p className="empty">Ask a question about the book. Each question is answered independently.</p>
        )}
        {turns.map((t, i) => (
          <React.Fragment key={i}>
            <div className="turn">
              <span className="role">advisor</span>
              <div className="bubble q">{t.question}</div>
            </div>
            <div className="turn">
              <span className="role">atlas</span>
              <div className="bubble a">
                {t.status === "success" ? (
                  <>
                    {t.rows.length > 0 ? (
                      <ul className="rows">
                        {t.rows.slice(0, 10).map((row, j) => (
                          <li key={j}>{Object.values(row).map(String).join(" · ")}</li>
                        ))}
                      </ul>
                    ) : (
                      <span>No matching rows.</span>
                    )}
                    {t.sparql && (
                      <details className="sparql-toggle">
                        <summary>Show the SPARQL that ran</summary>
                        <pre>{t.sparql}</pre>
                      </details>
                    )}
                  </>
                ) : t.status === "no_template_match" ? (
                  <span>I can&apos;t answer that one yet — try one of the questions above.</span>
                ) : (
                  <span>The query couldn&apos;t be run just now. Please try again.</span>
                )}
              </div>
            </div>
          </React.Fragment>
        ))}
        {loading && <p className="loading-line" aria-busy="true">Querying the graph…</p>}
      </div>

      {/* Input */}
      <div className="convinput">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(input)}
          placeholder="Ask about the book…"
          aria-label="Conversation input"
        />
        <button
          className="btn accent"
          onClick={() => ask(input)}
          disabled={!input.trim() || loading}
        >
          Send
        </button>
      </div>
      <p className="card-note">
        Each question is answered independently — answers come from the graph (not scoped per
        advisor). Template-bounded: a fixed set of deterministic SPARQL queries.
      </p>
    </div>
  );
}
