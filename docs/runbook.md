# ATLAS Workshop — CIO Demo Runbook

A step-by-step script for demonstrating the ATLAS architecture to a Chief
Information Officer or Chief Data Officer in 15 minutes.

## Before the demo

- Ensure Neptune clusters are running (`atlas-lgd`, `atlas-slgd`)
- Run Modules 1-8 at least once so the SLGD has promoted data
- Have the Module 8 notebook open to the CIO demo query cell

## The narrative arc (15 minutes)

### Opening (2 minutes)

"ATLAS is a reference architecture that demonstrates how to build an enterprise
semantic layer for Financial Services on AWS. The central commitment is the
deterministic-vs-probabilistic boundary — every component is classified, and
the boundary is enforced by machine-checkable shapes."

Show: The architecture diagram from the README (three layers).

### The data foundation (3 minutes)

"We start with six confirmed enterprise data elements that every bank already
has: customers, deposit balances, advisor assignments, household relationships,
holdings, and referral history. We do not require the bank to curate a new
'wealth signals' dataset — ATLAS computes signals from data they already have."

Show: The synthetic data files (customer-master, advisory-relationships).

### The ontology (3 minutes)

"The ontology defines 22 classes aligned to FIBO — the Financial Industry
Business Ontology. Every class traces to a competency question that a CDO or
compliance officer would actually ask."

Show: The rationale.md table (class → competency question → justification).

### The boundary enforcement (3 minutes)

"Six SHACL shapes enforce the boundary mechanically. A reviewer can run one
validator and produce a report showing exactly where probabilistic outputs
entered the system."

Show: Run the SHACL validator against the counter-example (Module 6 cell 4).
The bad graph fails. The good graph passes.

### The end-to-end workflow (3 minutes)

"When a customer's deposit balance crosses a threshold and they have no wealth
advisor assigned, ATLAS detects the signal, scores it, routes it to an advisor,
and records the full audit trail — queryable in one SPARQL query."

Show: The CIO demo query from Module 8 (one query, full audit trail).

### The coverage question (1 minute)

"The two questions this architecture answers for the business:
1. Which customers cross the threshold and have no wealth advisor?
2. Which households have mixed coverage — some members engaged, others not?"

Show: The Phase 1 pilot queries from the ground-truth file.

## Closing

"This is a reference pattern with runnable code. Every component is classified.
The boundary is enforced in code. The audit trail is queryable. And it runs on
data the bank already has."

## If asked

- "What does it cost?" → $10-18 for a single workshop run (see COST section in README)
- "How long to build?" → 5-6 hours for the workshop; production deployment is
  a separate engagement
- "What about real-time?" → v1 includes the plumbing; deep real-time is a follow-on lab
- "What about external signals?" → Documented extension path in docs/follow-on-labs.md
