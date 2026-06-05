# referral-orchestrator

Orchestrates the state-changing workflow that routes an approved referral to a Wealth Advisor. The only agent in Phase 1 that changes state. Backed by Step Functions for auditability.

## Purpose

Once a Consumer Banker has reviewed and approved a referral (including the human-approved rationale draft), the referral needs to be *routed*. Routing involves selecting the appropriate advisor based on geography, specialization, current load, and historical fit; writing the routing decision to the graph; notifying the advisor; and updating the Consumer Banker's view to confirm handoff.

`referral-orchestrator` runs this workflow via Step Functions. Each step is a separate Lambda; the state machine is the audit trail.

## Posture

**Workflow, Step Functions, fully audited.** Every state transition is recorded. Every Lambda invocation produces a CloudWatch log. Failures roll back to the last consistent state. The state machine definition is versioned and reviewed.

## What it does

1. Receives an approved referral payload (household URI, signal URIs, approved rationale, originating Consumer Banker).
2. Invokes `select-advisor` Lambda: queries the SLGD for advisors with capacity, specialization match, and geographic proximity. Returns ranked candidates.
3. Invokes `validate-routing` Lambda: confirms the selected advisor's `atlas:AdvisoryRelationship` capacity, checks for any active compliance review on the household, applies `atlas:RoutingPolicyShape` validation.
4. Invokes `write-routing-decision` Lambda: writes the `atlas:RoutingDecision` to the SLGD with full PROV-O attribution.
5. Invokes `notify-advisor` Lambda: sends notification (in workshop, a CloudWatch event; in production, integration with the advisor's CRM or notification system).
6. Invokes `audit-write` Lambda: writes the complete handoff record to `atlas:AuditRecord`.

## What it does not do

- Does not auto-route without approval. The approved-referral payload is the input; no path bypasses this.
- Does not reason about the advisor selection — it queries SPARQL and applies SHACL. The selection logic is auditable code, not LLM output.
- Does not retry blindly on failure. Failures are surfaced to the Consumer Banker for re-approval, not silently retried.

## Where the novice meets this

Notebook `06_wholesale_ui.ipynb` walks through a complete routing flow. The novice triggers it through the UI's *Route to advisor* capability.

## Dependencies

- `atlas-sparql-mcp` for advisor queries and routing decision writes
- `atlas-shacl-mcp` for `atlas:RoutingPolicyShape` validation
- Step Functions service for orchestration
