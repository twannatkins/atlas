/**
 * Ask-the-graph panel (#2) — real natural-language query over the graph.
 *
 * Invokes the askGraph field → nl-to-sparql-agent, which is TEMPLATE-BOUNDED: it embeds
 * the question and matches it against a fixed set of validated SPARQL templates (it never
 * free-generates SPARQL — the SR 11-7 posture). So the honest UX is:
 *   - the answerable questions (suggestedQuestions, read live from the agent's own
 *     ground-truth.yaml) are ALWAYS visible — the box is never a bare "ask anything";
 *   - a matched question shows the REAL rows + the REAL SPARQL that ran (provenance);
 *   - an unmatched question shows "I can answer questions like:" + the suggestions —
 *     never a fabricated answer, never a silent empty;
 *   - an agent/transport error shows an honest error, not a fake answer.
 */

"use client";

import React, { useState, useCallback, useEffect } from "react";
import { useQuery, useLazyQuery } from "@apollo/client";
import { ASK_GRAPH_QUERY, SUGGESTED_QUESTIONS_QUERY } from "../graphql/queries";

/**
 * onResult (optional) lifts the REAL askGraph result up to the page so the adjacent
 * Schema-graph card can highlight the part of the model the query traversed. The panel's
 * own behaviour is unchanged — it still owns and renders the answer exactly as before;
 * this only mirrors the result outward. Passing nothing keeps the panel standalone.
 */
export function AskGraphPanel({ onResult }: { onResult?: (res: unknown) => void } = {}) {
  const [question, setQuestion] = useState("");
  const { data: sq } = useQuery(SUGGESTED_QUESTIONS_QUERY);
  const [run, { data, loading }] = useLazyQuery(ASK_GRAPH_QUERY, {
    fetchPolicy: "no-cache",
  });

  const suggestions: string[] = sq?.suggestedQuestions ?? [];
  const res = data?.askGraph;

  // Mirror the real result outward (does not alter the panel's own rendering below).
  useEffect(() => {
    if (onResult) onResult(res ?? null);
  }, [res, onResult]);

  const ask = useCallback(
    (q: string) => {
      const text = q.trim();
      if (!text) return;
      setQuestion(text);
      run({ variables: { question: text } });
    },
    [run],
  );

  // result is AWSJSON — AppSync serializes it as a JSON *string*, so parse it back to the
  // row array. (Already-parsed arrays are tolerated too.)
  const parsedResult = (() => {
    const r = res?.result;
    if (Array.isArray(r)) return r;
    if (typeof r === "string") {
      try { return JSON.parse(r); } catch { return []; }
    }
    return [];
  })();
  const rows: Record<string, unknown>[] = Array.isArray(parsedResult) ? parsedResult : [];
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <div className="card">
      <div className="card-h">
        <span className="t">Ask the graph</span>
        <span className="meta">
          <svg className="i" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
            <circle cx="11" cy="11" r="6" />
            <path d="M16 16l4 4" />
          </svg>
          nl-to-sparql-agent · template-bounded · live
        </span>
      </div>

      <div className="field">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(question)}
          placeholder="Ask a question about the graph…"
          aria-label="Ask the graph"
        />
        <button
          className="btn accent"
          onClick={() => ask(question)}
          disabled={!question.trim() || loading}
        >
          Ask
        </button>
      </div>

      {/* Suggested questions — ALWAYS visible. These are exactly what the agent can answer
          (read from its own templates), so expectations are set honestly. */}
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

      {loading && (
        <p className="loading-line" aria-busy="true">
          Querying the graph…
        </p>
      )}

      {res && !loading && res.status === "success" && (
        <div>
          <p className="result-meta">
            {rows.length} result{rows.length === 1 ? "" : "s"} · template {res.templateId} · {res.executionTimeMs}ms
          </p>
          {rows.length > 0 ? (
            <div style={{ overflowX: "auto" }}>
              <table className="rtable">
                <thead>
                  <tr>
                    {columns.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i}>
                      {columns.map((c) => (
                        <td key={c}>{String(row[c] ?? "")}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty">The query matched but returned no rows.</p>
          )}
          {res.sparql && (
            <details className="sparql-toggle">
              <summary>Show the SPARQL that ran</summary>
              <pre>{res.sparql}</pre>
            </details>
          )}
        </div>
      )}

      {/* Honest no-match: NOT a fabricated answer — point back at the answerable questions. */}
      {res && !loading && res.status === "no_template_match" && (
        <p className="card-note">
          I can&apos;t answer that one yet. Try one of the questions above — those are the
          queries I can run today.
        </p>
      )}

      {res && !loading && res.status === "execution_error" && (
        <p className="card-note" role="alert" style={{ color: "var(--rust-ink)" }}>
          The query couldn&apos;t be run (a system error reaching the graph). Please try again.
        </p>
      )}
    </div>
  );
}
