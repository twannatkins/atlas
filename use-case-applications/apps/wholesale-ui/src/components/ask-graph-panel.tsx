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

import React, { useState, useCallback } from "react";
import { useQuery, useLazyQuery } from "@apollo/client";
import { ASK_GRAPH_QUERY, SUGGESTED_QUESTIONS_QUERY } from "../graphql/queries";

export function AskGraphPanel() {
  const [question, setQuestion] = useState("");
  const { data: sq } = useQuery(SUGGESTED_QUESTIONS_QUERY);
  const [run, { data, loading }] = useLazyQuery(ASK_GRAPH_QUERY, {
    fetchPolicy: "no-cache",
  });

  const suggestions: string[] = sq?.suggestedQuestions ?? [];
  const res = data?.askGraph;

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
    <div className="space-y-4 rounded-lg border border-neutral-200 p-4">
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(question)}
          placeholder="Ask a question about the graph…"
          className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          aria-label="Ask the graph"
        />
        <button
          onClick={() => ask(question)}
          disabled={!question.trim() || loading}
          className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
        >
          Ask
        </button>
      </div>

      {/* Suggested questions — ALWAYS visible. These are exactly what the agent can answer
          (read from its own templates), so expectations are set honestly. */}
      {suggestions.length > 0 && (
        <div className="space-y-1">
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

      {loading && <p className="text-sm text-neutral-400" aria-busy="true">Querying the graph…</p>}

      {res && !loading && res.status === "success" && (
        <div className="space-y-2">
          <p className="text-xs text-neutral-400">
            {rows.length} result{rows.length === 1 ? "" : "s"} · template {res.templateId} · {res.executionTimeMs}ms
          </p>
          {rows.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-neutral-200">
                    {columns.map((c) => (
                      <th key={c} className="py-1 pr-4 font-medium text-neutral-600">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} className="border-b border-neutral-100">
                      {columns.map((c) => (
                        <td key={c} className="py-1 pr-4 text-neutral-800">{String(row[c] ?? "")}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-neutral-500">The query matched but returned no rows.</p>
          )}
          {res.sparql && (
            <details className="text-xs text-neutral-400">
              <summary className="cursor-pointer">Show the SPARQL that ran</summary>
              <pre className="mt-1 overflow-x-auto whitespace-pre-wrap font-mono">{res.sparql}</pre>
            </details>
          )}
        </div>
      )}

      {/* Honest no-match: NOT a fabricated answer — point back at the answerable questions. */}
      {res && !loading && res.status === "no_template_match" && (
        <p className="text-sm text-neutral-600">
          I can&apos;t answer that one yet. Try one of the questions above — those are the
          queries I can run today.
        </p>
      )}

      {res && !loading && res.status === "execution_error" && (
        <p className="text-sm text-red-600" role="alert">
          The query couldn&apos;t be run (a system error reaching the graph). Please try again.
        </p>
      )}
    </div>
  );
}
