---
title: "Module 2 — Why Agents at All?"
weight: 20
---

# Module 2 — Why Agents at All?

## Learning Objectives

- Explain why a direct SPARQL query against Neptune is insufficient for a regulated
  banking application, and what an agent adds
- Trace the path a natural-language question takes through the `ask_graph()` function:
  embedding, cosine similarity, template selection, SPARQL execution
- Verify that the agent's output is deterministic — the same question produces the
  same SPARQL, every time, because no LLM text generation is in the path
- Articulate the architectural boundary that makes ATLAS auditable under SR 11-7

## Time Estimate

20–25 minutes.

## Prerequisites

- [Module 1 — Pre-flight](../01-preflight/) complete with all six checks passing
- The `atlas-workshop` kernel registered and the Workshop 2 virtual environment active

## What You Will Build

The `ask_graph()` function: a question-answering interface over Neptune that is
driven by cosine similarity over a ground-truth SPARQL template library, not by
LLM text generation. It returns rows and a `template_id` that serves as the
audit anchor for every answer.

The notebook is `notebooks/phase-1-referral/01_why_agents.ipynb`.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1
(`cell-01-terms`) — the Key Terms table defines "deterministic-audited posture,"
"NL-to-SPARQL agent," and "audit anchor" as they are used throughout Workshop 2.

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-1-referral/01_why_agents.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains:
- Why the Wholesale UI cannot ship a SPARQL editor to bankers
- Why the LLM-generates-SPARQL pattern is insufficient for SR 11-7 compliance
- Why cosine similarity over a template library is the deterministic alternative

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load shared helpers and retrieve Neptune
endpoints from the Workshop 1 CloudFormation stack.

Expected output (first few lines):

```
Shared helpers loaded.
Neptune SLGD endpoint: atlas-slgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
Ground-truth library loaded: N templates
Titan Embeddings v2 client ready.
```

![Setup output](/static/images/02-step-03-setup-output.png)

### Step 4 — Run the direct SPARQL baseline (cell 4)

Run cell 4 (`cell-04-direct-query`) to execute a raw SPARQL query directly
against the SLGD. This shows what an unmediated query looks like — the banker
would need to write this string themselves.

Expected output:

```
Direct SPARQL — 5 rows returned
  CUST-001  ...
  CUST-002  ...
  ...
(template_id: None — no audit anchor)
```

### Step 5 — Run ask_graph() (cell 6)

Run cell 6 (`cell-06-ask-graph`) to see the same question routed through the
`ask_graph()` function. Watch how the function:
1. Calls Titan Embeddings v2 to embed the question
2. Computes cosine similarity against every template embedding in the library
3. Selects the closest template and executes its SPARQL verbatim

Expected output:

```
ask_graph("Which customers have active wealth signals?")
  → template selected: WS-LIST-BY-SIGNAL-TYPE (similarity: 0.94)
  → SPARQL executed (deterministic)
  → 5 rows returned
  → audit anchor: template_id=WS-LIST-BY-SIGNAL-TYPE
```

![ask_graph output](/static/images/02-step-05-ask-graph-output.png)

### Step 6 — Run three pilot questions (cell 7)

Run cell 7 (`cell-07-three-questions`) to send three different natural-language
questions through `ask_graph()`. Each returns rows and a `template_id`.

Expected output:

```
Q1: "Which customers have active wealth signals?"
  → template: WS-LIST-BY-SIGNAL-TYPE  rows: N

Q2: "How many advisory relationships does Anjali Patel have?"
  → template: ADVISORY-REL-COUNT       rows: 1

Q3: "What transactions has household 9c2a1e made in the last 90 days?"
  → template: TXN-BY-HOUSEHOLD-RECENT  rows: N
```

### Step 7 — Verify determinism (cell 9)

Run cell 9 (`cell-09-determinism`) to confirm that running the same question
five times produces byte-identical SPARQL strings. This is the structural
guarantee that SR 11-7 compliance audits require.

Expected output:

```
Determinism check — 5 runs of the same question
  Run 1: template=WS-LIST-BY-SIGNAL-TYPE  sparql_hash=a3f8...
  Run 2: template=WS-LIST-BY-SIGNAL-TYPE  sparql_hash=a3f8...
  Run 3: template=WS-LIST-BY-SIGNAL-TYPE  sparql_hash=a3f8...
  Run 4: template=WS-LIST-BY-SIGNAL-TYPE  sparql_hash=a3f8...
  Run 5: template=WS-LIST-BY-SIGNAL-TYPE  sparql_hash=a3f8...
[PASS] All 5 runs produced identical SPARQL.
```

### Step 8 — Read "What just changed" (cell 10)

Read cell 10 (`cell-10-changed`). It explains what `ask_graph()` gives you
that a direct SPARQL query cannot: a `template_id` audit anchor that ties every
answer to a version-controlled, human-readable template — not to whatever the
LLM happened to generate that day.

## Expected Outputs

- `ask_graph()` returns rows and a `template_id` for every question
- Five runs of the same question produce byte-identical SPARQL hashes
- No Bedrock text-generation model is called at any point
- Determinism check prints `[PASS] All 5 runs produced identical SPARQL`

## Troubleshooting

**Cell 3 fails: "Stack atlas-neptune-twotier not found"**

The Workshop 1 Neptune stack is not running. Return to
[Module 1 — Pre-flight](../01-preflight/) and complete the stack-not-found
troubleshooting entry before continuing.

**Cell 3 fails: "Ground-truth library is empty"**

`prompts/ground-truth.yaml` was not found or is zero bytes. Verify that the
Workshop 1 file path is correct and that the `atlas-workshop` kernel is using
the `use-case-applications/.venv` environment where `pyyaml` is installed.

**Cell 6 fails: "Titan Embeddings v2 not accessible"**

The SageMaker execution role lacks `bedrock:InvokeModel` for
`amazon.titan-embed-text-v2:0`. Add the permission, wait 30 seconds for
propagation, and re-run cell 3 and cell 6. The pre-flight Check 6 should have
caught this — if Check 6 passed, verify you are running in `us-east-1`.

**Determinism check fails: hashes differ across runs**

The only source of non-determinism in `ask_graph()` is embedding API
variability. Titan Embeddings v2 is deterministic for a fixed input; if the
hashes differ, the input string changed between runs. Check that no cell
earlier in the notebook mutated the question string.

## What's Next

`ask_graph()` talks directly to Neptune. [Module 3 — MCP Servers](../03-mcp-servers/)
introduces the indirection layer that separates *what* to query from *how* to
reach the graph — and explains why that indirection is the reason agents in
ATLAS can be deployed to AgentCore Runtimes without rewriting any agent code.
