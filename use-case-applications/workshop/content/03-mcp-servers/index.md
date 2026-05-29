---
title: "Module 3 — MCP Servers: The Capability Surface"
weight: 30
---

# Module 3 — MCP Servers: The Capability Surface

## Learning Objectives

- Explain why ATLAS uses MCP servers rather than having agents call AWS services
  directly — and why that indirection matters for regulated deployments
- Implement `sparql_mcp_query()` as a local function that honours the operation
  contract the production AgentCore Runtime enforces
- Verify that the function rejects anonymous calls and invalid SPARQL before
  touching the network
- Understand how all five MCP servers map to the capability surface the Agent
  Registry will enumerate in Module 4

## Time Estimate

25–30 minutes.

## Prerequisites

- [Module 2 — Why Agents at All?](../02-why-agents/) complete
- `ask_graph()` working and returning `template_id` audit anchors

## What You Will Build

A local implementation of `sparql_mcp_query(sparql, persona_claim, graph_tier)`
that honours the same contract as the production AgentCore Runtime: validates SPARQL
via `atlas_sparql.validate()` before network contact, enforces `persona_claim`
presence, and returns a response shaped as `{rows, execution_time_ms}`.

The notebook is `notebooks/phase-1-referral/02_mcp_servers.ipynb`.

## Why MCP Servers — and Why AgentCore Runtimes

Before running the notebook, read this section carefully. It is the single most
important concept in Phase 1.

Notebook 02 built `ask_graph()`: a function that translates a natural-language
question into a SPARQL query and runs it against the Neptune knowledge graph. That
function works correctly — but it carries a hidden cost. Inside `ask_graph()`,
there is a `NeptuneClient` constructed with a specific endpoint, a specific port,
and specific error-handling assumptions. If the Neptune cluster moves — if a new
endpoint is deployed, if the connection pattern switches, if the graph tier changes
from the SLGD to the LGD for a diagnostic query — every agent that contains that
connection logic must be updated. That is the first problem an MCP server solves:
it separates the *what* (run a SPARQL query) from the *how* (which cluster, which
tier, which connection pattern).

The second problem is persona enforcement. The `atlas-sparql-mcp` server accepts a
`persona_claim` parameter on every operation. That claim is translated, inside the
server, into a Lake Formation scope that filters which rows and columns the query
is allowed to return. A Consumer Banker's claim covers their assigned book of
clients. A BSA Analyst's claim includes compliance-restricted fields the Consumer
Banker cannot see. If every agent enforced this scope independently, the enforcement
would be inconsistent. The MCP server is the single place where that enforcement
lives, so it can be tested once and trusted everywhere.

This is why ATLAS has five MCP servers rather than five agents that each call AWS
services directly. Each server wraps one capability: SPARQL over Neptune, SHACL
validation, Entity Resolution identity lookup, FIBO class introspection, and
registry discovery. Together they form the capability surface that every Phase 1
agent operates against. The agents are thin: they receive a request, identify which
MCP operations to call, call them in sequence, and return the assembled result. The
agents do not know which Neptune cluster is running, which Lake Formation tags are
in effect, or which version of the FIBO ontology is loaded. The MCP servers know
those things. The agents know only the operation schemas.

The production MCP servers in ATLAS are **AgentCore Runtimes**, not plain Lambda
functions. An AgentCore Runtime runs the same thin Python handler — but inside the
AWS Bedrock AgentCore service, which assigns each server a stable ARN address and
exposes invocation metrics through CloudWatch. Every caller — every agent, every
AppSync proxy — uses the same SDK call regardless of which server it is invoking:

```python
response = boto3.client("bedrock-agentcore").invoke_agent_runtime(
    agentRuntimeArn=SPARQL_MCP_ARN,
    payload=json.dumps({"operation": "query", ...}).encode(),
    contentType="application/json",
)
result = json.loads(response["response"].read())
```

The ARN is the only thing that changes per server. That uniformity means a new MCP
server can be integrated by any agent that already calls an existing one — with no
new SDK pattern to learn. This notebook does not deploy the Runtimes; it verifies
the contract they will honour.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1
(`cell-01-terms`). The Key Terms table defines "operation contract," "persona
enforcement," and "AgentCore Runtime."

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-1-referral/02_mcp_servers.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It expands on the two problems above with
concrete examples from the Rachel Kim referral scenario, and explains how the
AgentCore Runtime makes the invocation surface uniform across all five servers.

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load shared helpers and retrieve Neptune
endpoints.

Expected output:

```
Shared helpers loaded.
Neptune SLGD endpoint: atlas-slgd.cluster-XXXXX.us-east-1.neptune.amazonaws.com:8182
atlas_sparql validator ready.
```

### Step 4 — Run the direct query baseline (cell 4)

Run cell 4 (`cell-04-direct-query`) to see what a direct SPARQL call looks like
before any MCP wrapper — no persona enforcement, no validation, no structured
response shape.

### Step 5 — Implement sparql_mcp_query() (cell 6)

Run cell 6 (`cell-06-mcp-wrapper`) to define `sparql_mcp_query()`. Read the
cell source before running — the implementation is 15 lines and every line is
commented with its purpose.

Expected output:

```
sparql_mcp_query() defined.
Test run (Consumer Banker persona):
  rows: 5
  execution_time_ms: 42
  response shape: {rows, execution_time_ms}
```

![sparql_mcp_query output](/static/images/03-step-05-mcp-wrapper-output.png)

### Step 6 — Verify response shape consistency (cell 9)

Run cell 9 (`cell-09-shape-consistency`) to confirm that five successive calls
return identically shaped responses — proving the MCP contract is stable under
repetition.

Expected output:

```
Shape consistency check — 5 runs
  Run 1: keys={rows, execution_time_ms}  ✓
  Run 2: keys={rows, execution_time_ms}  ✓
  Run 3: keys={rows, execution_time_ms}  ✓
  Run 4: keys={rows, execution_time_ms}  ✓
  Run 5: keys={rows, execution_time_ms}  ✓
[PASS] All 5 runs returned the declared shape.
```

### Step 7 — Verify error handling (cell 10)

Run cell 10 (`cell-10-error-shape`) to confirm that three invalid inputs each
return a structured error dict rather than raising an exception. The contract
requires `{error, code}` on failure — not Python tracebacks — so agents can
handle errors programmatically.

Expected output:

```
Error shape check — 3 bad inputs
  Input 1 (no persona_claim):  {error: "persona_claim required", code: 401}
  Input 2 (invalid SPARQL):    {error: "SPARQL validation failed: ...", code: 400}
  Input 3 (wrong graph_tier):  {error: "unknown graph_tier: ...", code: 400}
[PASS] All 3 error responses match the declared shape.
```

### Step 8 — Read "What just changed" (cell 11)

Read cell 11 (`cell-11-what-changed`). It explains the transition from a local
Python function to an AgentCore Runtime ARN — the code is the same, the
invocation mechanism changes, and the agents never notice.

## Expected Outputs

- `sparql_mcp_query()` returns `{rows, execution_time_ms}` for valid inputs
- Five successive calls return identically shaped responses
- Three invalid inputs return structured `{error, code}` dicts, not exceptions
- Shape consistency check prints `[PASS] All 5 runs returned the declared shape`

## Troubleshooting

**Cell 6 fails: "atlas_sparql validator not found"**

The `sys.path` insert in cell 3 must point at
`../../../agentic-semantic-layer/notebooks/shared`. If the path is wrong,
`import atlas_sparql` will silently fail with a ModuleNotFoundError at first use.
Verify the repo root is one level above `use-case-applications/` and re-run cell 3.

**Cell 9 shape check fails: "execution_time_ms missing"**

The `sparql_mcp_query()` implementation is missing the timing logic. The response
dict must be built as `{"rows": rows, "execution_time_ms": elapsed_ms}` where
`elapsed_ms` is measured with `time.time()` around the Neptune call. Check cell 6.

**Cell 10 error check fails: function raised an exception instead of returning `{error, code}`**

The MCP contract requires error returns, not raises. Wrap the entire body of
`sparql_mcp_query()` in a try/except block and return `{"error": str(e), "code": 400}`
from the except clause. The pre-flight Check does not verify this — it is an MCP
contract requirement that first surfaces here.

**Neptune call succeeds but rows are empty for the Consumer Banker persona**

Lake Formation row filtering is working correctly — the Consumer Banker's assigned
book of clients may not include the specific household in the test query. Change the
test `persona_claim` to `"atlas-bsa-analyst"` to confirm the query returns data,
then switch back.

## What's Next

The five MCP servers form the capability surface. [Module 4 — Agent Registry](../04-agent-registry/)
loads the JSON descriptors that make each capability *enumerable* — so the Agent
Registry knows what exists, which personas may discover it, and what schema each
operation accepts. That enumeration is what allows the Wholesale UI to render a
dynamic capability palette instead of hardcoded buttons.
