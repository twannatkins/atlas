---
title: "Module 9 — AgentCore Memory"
weight: 90
---

# Module 9 — AgentCore Memory

## Learning Objectives

- Explain why session-scoped memory is a compliance decision, not just an
  engineering convenience — and why permanent storage would trigger GDPR and
  CCPA data retention obligations
- Implement a `SessionMemory` class that mirrors the AgentCore Memory interface:
  `put()`, `get()`, `end_session()`
- Trace how the conversational-context-manager resolves anaphoric references
  ("those", "them") by looking up the prior turn's results in memory
- Verify that memory is session-scoped (cleared at `end_session()`) and that
  sessions are fully isolated from each other

## Time Estimate

20–25 minutes.

## Prerequisites

- [Module 8 — Phase 2 Agents](../08-phase-2-agents/) complete
- The three Phase 2 agents registered with correct postures

## What You Will Build

A local `SessionMemory` implementation that has the same interface as the AWS
AgentCore Memory service, a two-turn conversation simulation that resolves "those"
from prior context, and verification that the session lifecycle — store, retrieve,
clear — behaves as specified.

The notebook is `notebooks/phase-2-advisor/02_agentcore_memory.ipynb`.

This notebook simulates AgentCore Memory locally. Production uses the AWS
AgentCore Memory service; the interface (`put`, `get`, `end_session`) is identical.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1 (`cell-01-terms`).
The Key Terms table defines "session scope," "context resolution," and "anaphoric
reference."

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-2-advisor/02_agentcore_memory.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains:
- Why Phase 1 agents are stateless and why that breaks the Wealth Advisor workflow
- How the conversational-context-manager resolves "those" by looking up the prior
  turn in memory
- Why memory is session-scoped: permanent storage creates GDPR/CCPA data retention
  obligations. The conversational-context-manager is not a knowledge base — each
  session starts fresh.

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load helpers and initialize the memory store.

Expected output:

```
Setup complete.
This notebook simulates AgentCore Memory locally.
Production uses the AWS AgentCore Memory service.
```

### Step 4 — Initialize the memory store (cell 4)

Run cell 4 (`cell-04-memory-store`) to define the `SessionMemory` class and
confirm the interface.

Expected output:

```
SessionMemory initialized.
Interface: put(session_id, key, value), get(session_id, key), end_session(session_id)
```

### Step 5 — Simulate a two-turn conversation (cell 5)

Run cell 5 (`cell-05-multi-turn`) to walk the two-turn scenario: Turn 1 asks
"Show me clients with engagement decay" and stores the results; Turn 2 asks
"Of those, which have AUM above 2M?" and resolves "those" from memory.

Expected output:

```
Session started: XXXXXXXX...

Turn 1: "Show me clients with engagement decay"
Results stored in memory: 3 clients

Turn 2: "Of those, which have AUM above 2M?"
Resolved 'those' from memory: 3 clients
After AUM filter: 2 clients

  Rachel Kim           AUM: $3,200,000
  Sarah Patel          AUM: $4,500,000
```

![Two-turn conversation output](/static/images/09-step-05-multi-turn.png)

### Step 6 — Observe context-driven template selection (cell 6)

Run cell 6 (`cell-06-template-selection`) to see how the presence of prior
context changes which SPARQL template is selected. With memory, the selector
chooses `aum_filter_scoped` (a VALUES clause over the prior URIs). Without
memory, it chooses `aum_filter_broad` (a full-graph filter).

Expected output:

```
With memory active:
  Template: aum_filter_scoped
  Params:   {'uris': [...], 'threshold': 2000000}

Without memory (new session):
  Template: aum_filter_broad
  Params:   {'threshold': 2000000}
```

### Step 7 — Verify session scope (cell 8)

Run cell 8 (`cell-08-verify-session-scope`) to assert that memory is cleared
when `end_session()` is called.

Expected output:

```
Verifying session-scoped memory behavior...

Before end_session: memory.get('test_key') = test_value
After end_session:  memory.get('test_key') = None

[PASS] Memory is session-scoped: data cleared after end_session().
```

### Step 8 — Verify session isolation (cell 9)

Run cell 9 (`cell-09-verify-isolation`) to assert that ending one session does
not affect another.

Expected output:

```
Verifying session isolation...

Session A clients: ['Rachel Kim', 'James Chen']
Session B clients: ['Sarah Patel']

After ending session A:
  Session A clients: None
  Session B clients: ['Sarah Patel']

[PASS] Sessions are fully isolated. No context leakage between sessions.
```

## Expected Outputs

- `SessionMemory` initialized with `put/get/end_session` interface
- Two-turn conversation resolves "those" from memory; second turn returns 2 clients
- `aum_filter_scoped` selected when memory has prior context; `aum_filter_broad` without
- Session scope check prints `[PASS] Memory is session-scoped`
- Isolation check prints `[PASS] Sessions are fully isolated`

## Troubleshooting

**Cell 8 fails: "Memory persists after session end"**

The `end_session()` method must call `self._sessions.pop(sid, None)` to remove the
session's key-value store entirely. If the method only clears individual keys, `get()`
may still find the session dict and return `None` for missing keys rather than
confirming the session is gone. Add a check that `session_id not in self._sessions`
after `end_session()`.

**Cell 9 fails: "Ending session A affected session B"**

Sessions are stored in a shared dict keyed by session ID. If `end_session()` clears
the entire `_sessions` dict (e.g., `self._sessions = {}`) instead of removing only
the specified session, it will destroy all sessions. The fix is
`self._sessions.pop(sid, None)`, not `self._sessions.clear()`.

**Cell 5 AUM filter returns 0 clients instead of 2**

The simulated client data has two clients with AUM above 2M (`atlas:client-rachel-kim`
at $3.2M and `atlas:client-sarah-patel` at $4.5M). If the filter returns 0, check
that Turn 1 is storing results to memory before Turn 2 runs. The cells must be run
in order; re-run cell 4 first to reset the memory store.

**Cell 6 shows `aum_filter_broad` even when memory has context**

The template selector checks `memory_store.get(session_id, "last_results")` and
`any(w in question.lower() for w in ["those", "them", "these"])`. Both must be
true to select `aum_filter_scoped`. If the question in cell 5 was changed, the
anaphora check may not match. Use "Of those, which have AUM above 2M?" verbatim.

## What's Next

Memory enables multi-turn conversations. The Wealth Advisor's UI also needs to
render a different lens on the same data — behavioral signals, themes, and a
conversational surface that the Wholesale UI does not have.
[Module 10 — Wealth UI](../10-wealth-ui/) shows how the same GraphQL schema serves
both applications through persona-specific fragments, validating Thesis 2 of the
ATLAS architecture.
