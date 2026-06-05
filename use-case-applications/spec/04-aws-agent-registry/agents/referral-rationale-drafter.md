# referral-rationale-drafter

Drafts the narrative rationale that accompanies a referral when it is routed to a Wealth Advisor. The most regulatorily sensitive agent in Phase 1 because it is probabilistic.

## Purpose

When a Consumer Banker decides to route a wealth-eligible household to an advisor, the advisor needs context: *why* is this household being routed, *what* should they say in the first conversation, *what* are the relevant facts. The rationale narrative is the bridge between the structured signals and the conversational handoff.

`referral-rationale-drafter` produces this narrative by reading the structured signals and writing a short paragraph in plain English. It uses Bedrock for the generation. This is the first probabilistic agent the workshop introduces — and the first one that requires the human-in-the-loop pattern.

## Posture

**Probabilistic, human-in-the-loop.** The agent produces a *draft*. The draft is shown to the Consumer Banker. The Banker reviews, edits if needed, and approves. Only the approved version is sent to the advisor and written to the graph. The agent has no path to bypass human review.

## What it does

1. Receives a referral target (household URI) and the set of wealth signals that justify the referral.
2. Queries the SLGD for additional context (household composition, advisor coverage history, transaction patterns).
3. Prompts Bedrock with the structured context and a tight prompt template that constrains output format.
4. Returns the drafted narrative with required metadata flags: `is_probabilistic: true`, `requires_human_review: true`.
5. The UI presents the draft for review; the human approves or edits.
6. Only on approval is the narrative committed to the referral record.

## What it does not do

- Does not auto-send. Drafts are never delivered to advisors without human approval.
- Does not write to the graph directly. The UI's approval action writes; the agent only drafts.
- Does not reason about new facts. The agent works from the signals and context it is given. If the signals are wrong, the rationale is wrong; the agent does not invent supporting evidence.

## The regulatory framing

This agent is where SR 11-7 / OCC 2011-12 explicitly applies. Probabilistic output that affects a customer-facing decision must be:

- Documented (the prompt template is versioned and reviewed)
- Validated (the human review is the validation)
- Explainable (the signals and context that informed the draft are surfaced alongside it)

The human-in-the-loop pattern is what makes the agent compliant. Without it, the agent would be unauditable.

## Where the novice meets this

Notebook `01_why_agents.ipynb` introduces the pattern. The agent is exercised in Phase 1's UI walkthrough in `06_wholesale_ui.ipynb`, where the novice sees the drafted rationale appear in the UI with the *Edit and approve* control.

## Dependencies

- `atlas-sparql-mcp` for context queries
- Bedrock text generation model access (Claude on Bedrock)
- `agentic-semantic-layer/ontology/atlas-shapes.ttl` — specifically `atlas:BoundaryShape`, which validates that probabilistic output carries the required flags
