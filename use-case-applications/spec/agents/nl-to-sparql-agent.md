# nl-to-sparql-agent

The foundational agent of Workshop 2. Translates a natural-language question from a banker into a SPARQL query against the Semantic Layer Graph (SLGD), executes it, and returns the result. Every other Phase 1 agent builds on the pattern this one establishes.

## Purpose

Bankers do not speak SPARQL. They ask questions like:

- *"Which of my customers had a wire over $500k in the last 30 days?"*
- *"Show me households in the Patel cluster with no advisor coverage."*
- *"Which referrals have I sent that haven't been acted on?"*

Each of these maps to a SPARQL query against the SLGD. `nl-to-sparql-agent` is the translation layer. The agent does not invent the SPARQL — it selects from a curated, validated set of query templates stored in `agentic-semantic-layer/prompts/ground-truth.yaml` and parameterizes them with values extracted from the user's question.

## Posture

**Deterministic-output, audited.** The same natural-language input produces the same SPARQL output every time. The agent's audit record includes the question, the selected query template, the parameter binding, and the SPARQL that was executed.

This is the foundational deterministic agent. If `nl-to-sparql-agent` were probabilistic — if it generated SPARQL freely from the question — every downstream agent that depends on its output would inherit that probabilism, and the entire compliance posture would collapse. The agent is deterministic by construction.

## What it does

1. Receives a natural-language question and the user's persona claim.
2. Matches the question against the templates in `ground-truth.yaml` using semantic similarity (via Bedrock embeddings, not text generation).
3. Selects the best-matching template and extracts parameter values from the question.
4. Substitutes parameters into the template to produce executable SPARQL.
5. Validates the SPARQL against the prefix preamble in `prompts/prefixes.txt`.
6. Submits the SPARQL to `atlas-sparql-mcp` for execution.
7. Returns the result with provenance metadata: which template matched, what parameters were extracted, what SPARQL ran.

## What it does not do

- **Does not generate SPARQL freely.** The agent selects from a pre-validated template set. New queries require adding templates to `ground-truth.yaml`, which goes through the same change-management process as any code change.
- **Does not reason about the result.** The agent returns whatever the SPARQL returned. Narrative interpretation of the result is a separate concern handled by `referral-rationale-drafter`.
- **Does not bypass Lake Formation.** The SPARQL is scoped by the user's persona claim. A Consumer Banker's `nl-to-sparql-agent` invocation sees only Consumer Banking data; a BSA Analyst's sees BSA-scoped data.

## Where the novice meets this

Notebook `01_why_agents.ipynb`. The agent is built and tested in that notebook. The teaching moment is when the novice runs the same question three times and confirms the SPARQL is identical each time — proving the determinism that makes the agent auditable.

## What can go wrong

**The question doesn't match any template.** The agent returns *"I couldn't find a matching query template for that question"* rather than inventing SPARQL. This is the correct behavior — it's better to refuse than to hallucinate a query.

**Parameter extraction fails.** The agent identifies the template but cannot extract a required parameter (e.g., it can't find the dollar amount in *"large wires"*). The agent returns a clarification request: *"Could you specify the amount threshold?"*

**SPARQL execution fails.** The MCP server returns an error. The agent surfaces the error to the user with a remediation suggestion (most common cause: the user's persona doesn't have access to the data the query needs).

## IAM and access

The agent's Lambda execution role has permission to:

- Invoke Bedrock for embedding generation (not for text generation)
- Read `agentic-semantic-layer/prompts/ground-truth.yaml` from S3
- Invoke `atlas-sparql-mcp`
- Write to its own audit log

It has no other permissions. In particular, no direct Neptune access — all SPARQL goes through the MCP server, which enforces Lake Formation scoping.

## Dependencies

- `atlas-sparql-mcp` for query execution
- `agentic-semantic-layer/prompts/ground-truth.yaml` for templates
- `agentic-semantic-layer/prompts/prefixes.txt` for SPARQL prefix preamble
- Bedrock embedding model access in the deployment region
