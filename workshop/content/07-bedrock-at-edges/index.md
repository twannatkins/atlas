---
title: "Module 7 — Bedrock at the Edges"
weight: 70
---

# Module 7 — Bedrock at the Edges: NL↔SPARQL with Guardrails

## Learning Objectives

- Build a few-shot NL-to-SPARQL component grounded in the FIBO-aligned ontology
- Validate every LLM-generated query against SHACL shapes before execution
- Explain why the LLM is confined to translation (not reasoning) in ATLAS
- Ask the seven competency questions in plain English and get correct SPARQL queries

## Time Estimate

30 to 45 minutes.

## Prerequisites

- Module 6 complete (SHACL shapes in place)
- Amazon Bedrock enabled in us-east-1 with access to Anthropic Claude models
- The SageMaker execution role has `bedrock:InvokeModel` permission

## What You Will Build

This module produces:

- A working NL-to-SPARQL translation function with SHACL pre-check
- `prompts/ground-truth.yaml` — few-shot competency-question/SPARQL pairs
- `prompts/tips.yaml` — FIBO-specific hints for the LLM
- `prompts/prefixes.txt` — standard SPARQL prefix block
- All seven competency questions answerable in plain English

The notebook is `notebooks/07_bedrock_at_edges.ipynb`.

## Steps

### Step 1 — Open the notebook and configure Bedrock

Open `notebooks/07_bedrock_at_edges.ipynb`. Run cell 2 to initialize the Bedrock
client and load the SPARQL prefix block.

Run cell 2. Expected output:

```
Module 7 — Bedrock at the Edges
SPARQL validator loaded: atlas_sparql.validate()
Bedrock model: us.anthropic.claude-sonnet-4-6

SPARQL prefixes loaded (8 lines)
```

### Step 2 — Read the ground-truth pairs explanation

Read cell 3. It explains why few-shot prompting works and why ground-truth pairs
are essential for grounding the LLM in the correct ontology vocabulary.

### Step 3 — Load the ground-truth pairs

Run cell 4 to load the seven competency-question/SPARQL pairs.

Run cell 4. Expected output:

```
Ground-truth pairs loaded: 7
  CQ1: Which customers have generated a wealth signal in the la...
  CQ2: For a given signal, what observations support it and wha...
  ...
  CQ7: What specific transactions were used to surface this cus...
```

### Step 4 — Read the NL-to-SPARQL component explanation

Read cell 5. It explains the translation function's architecture:
1. Build a prompt with few-shot examples
2. Send to Bedrock
3. Extract SPARQL from response
4. Validate syntax
5. SHACL pre-check (reject any write queries)

### Step 5 — Define the translation function

Run cell 6 to define `nl_to_sparql()`.

### Step 6 — Test all seven competency questions

Run cell 8 to send each competency question through the NL-to-SPARQL component.

Run cell 8. Expected output:

```
NL-to-SPARQL Translation Test
============================================================

CQ1: Which customers have generated a wealth signal in the last 90 days?
  [PASS] Valid SPARQL generated (245 chars)
CQ2: For signal S-001, what observations support it...
  [PASS] Valid SPARQL generated (198 chars)
...
CQ7: What specific transactions were used to surface customer C-001...
  [PASS] Valid SPARQL generated (210 chars)

Results: 7/7 questions translated successfully
```

### Step 7 — Run the validation gate

Run cell 10 (Module 7 validation gate).

Run cell 10. Expected output:

```
============================================================
MODULE 7 VALIDATION GATE
============================================================
[PASS] Gate 1 - nl_to_sparql() function is defined and callable
[PASS] Gate 2 - 7/7 questions produce valid SPARQL (threshold: 5)
[PASS] Gate 3 - No INSERT/UPDATE queries generated (SHACL pre-check active)
[PASS] Gate 4 - 7 ground-truth pairs defined (threshold: 7)
[PASS] Gate 5 - Bedrock accessible (us.anthropic.claude-sonnet-4-6)

MODULE 7 VALIDATION: PASS
You may proceed to Module 8.
```

## Expected Outputs

- `nl_to_sparql()` function defined and working
- 7/7 competency questions produce valid SPARQL
- No write queries generated (SHACL pre-check active)
- Module 7 validation gate prints `MODULE 7 VALIDATION: PASS`

## Troubleshooting

**Bedrock returns AccessDeniedException**

The SageMaker execution role is missing `bedrock:InvokeModel` permission. Add the
inline policy from the Prerequisites page and restart the kernel.

**Gate 2 fails with fewer than 5/7 questions passing**

The LLM may generate slightly different SPARQL across runs. If 5+ pass, the gate
succeeds. If fewer than 5 pass, check that the ground-truth pairs in cell 4 use
the correct `atlas:` property names from the ontology.

**Generated query uses wrong property names (e.g., atlas:hasWealth)**

This is a hallucination. The fix is to add more ground-truth pairs that demonstrate
the correct vocabulary. The LLM learns from examples, not from instructions alone.

## What's Next

Module 7 put the LLM in the architecture — in a sharply circumscribed role. Module 8
stitches everything together into the capstone demo: detect a signal, score it, route
it through a bounded agent, surface it to a human reviewer, mint an advisory coverage
relationship, and record the full audit trail queryable in one SPARQL query.
