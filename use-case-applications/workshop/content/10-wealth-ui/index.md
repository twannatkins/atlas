---
title: "Module 10 — The Wealth UI"
weight: 100
---

# Module 10 — The Wealth UI

## Learning Objectives

- Explain Thesis 2 of the ATLAS architecture: two structurally different UIs
  consuming the same GraphQL schema, agent registry, and MCP servers
- Compare `CustomerReferralFragment` (Wholesale UI) and `CustomerCoverageFragment`
  (Wealth UI) to show how persona-specific field selection produces different
  applications from the same `Customer` type
- Verify that the Wealth Advisor sees a different capability palette than the
  Consumer Banker — including `theme-summarizer` and `conversational-context-manager`
- Explain how adding a third UI (e.g., a BSA compliance dashboard) would require
  only new fragments and a new persona claim, not schema or registry changes
- Recognize the Semantic grounding card as the second call site of one shared
  component — the same ontology truth, the advisor's-side framing — and why sharing
  it (not mirroring) keeps the atlas → FIBO mapping from drifting between the two apps
- Explain how the schema-graph highlight stays honest on the wealth conversation path,
  which returns no template id — it matches the real query by its SPARQL signature
  (unique match or an honest no-map), reaching the same bar a different way

## Time Estimate

20–25 minutes.

## Prerequisites

- [Module 9 — AgentCore Memory](../09-agentcore-memory/) complete
- Session-scoped memory verified

## What You Will Build

A demonstration of Thesis 2: simulated capability queries for Consumer Banker and
Wealth Advisor personas showing different palettes from the same registry endpoint,
and side-by-side comparison of the two GraphQL fragments. The `theme-summarizer`
output is verified as Wealth Advisor-only.

The notebook is `notebooks/phase-2-advisor/03_wealth_ui.ipynb`.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1 (`cell-01-terms`).
The Key Terms table defines "Thesis 2," "GraphQL fragment," "lens," and
"conversational surface."

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-2-advisor/03_wealth_ui.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains:
- Why the schema is persona-neutral at the type level — `Customer` has fields for
  both referral and wealth data
- How `CustomerReferralFragment` and `CustomerCoverageFragment` select different
  subsets of the same type
- Why the architecture scales by addition: a third UI needs only a new fragment
  and a new persona claim

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load all agent descriptors.

Expected output:

```
Agents loaded: N
Setup complete.
```

### Step 4 — Compare capability palettes (cell 4)

Run cell 4 (`cell-04-same-query-different-data`) to simulate `capabilities(personaClaim)`
for both personas. The same registry endpoint; different results.

Expected output:

```
Wholesale UI — Consumer Banker capabilities:
--------------------------------------------------
  nl-to-sparql-agent                  (deterministic-audited)
  ...
Wealth UI — Wealth Advisor capabilities:
--------------------------------------------------
  behavioral-signal-agent             (probabilistic-guarded)
  ...
Consumer Banker sees N capabilities.
Wealth Advisor sees N capabilities.
```

![Capability palettes by persona](/static/images/10-step-04-capability-palettes.png)

### Step 5 — Inspect the theme-summarizer (cell 5)

Run cell 5 (`cell-05-theme-summarizer`) to see example `theme-summarizer` output:
market themes relevant to a client's portfolio, returned as a structured dict
with `is_probabilistic: true` and `requires_human_review: false`.

Expected output:

```
Theme summarizer output (Wealth UI only):
{
  "client_uri": "atlas:client-rachel-kim",
  "themes": [...],
  "is_probabilistic": true,
  "requires_human_review": false
}
```

### Step 6 — Compare the two GraphQL fragments (cell 6)

Run cell 6 (`cell-06-fragments`) to print both fragments side by side. Read the
field lists carefully — this is the concrete expression of "same schema, different
lens."

Expected output:

```
Wholesale UI fragment (Consumer Banker):

fragment CustomerReferralFragment on Customer {
  uri
  customerId
  fullName
  signals { signalType, detectedDate, evidence }
  household { members { fullName, relationship } }
  coverageGap
}

Wealth UI fragment (Wealth Advisor):

fragment CustomerCoverageFragment on Customer {
  uri
  customerId
  fullName
  aum
  themes { themeName, relevanceScore, summary }
  engagementScore
  behavioralSignals { signalType, decayRatio, fired }
  advisor { fullName, teamId }
}
Same Customer type. Different fields. Different application.
```

### The demo loop — Marcus's half (the "New — routed to you" banner → take-on)

In the live demo, the Wealth UI is where the referral lands. After Dana routes from
the Wholesale UI ([Module 6](../06-wholesale-ui/)), sign in as **Marcus Webb (the
Wealth Advisor)** and you will see the routed customer **Rachel Kim** flagged **"New
— routed to you."** That banner is a *real* state — shown while the relationship was
created by the workflow and not yet accepted (`routedByWorkflow && !takenOnAt`), not
a timer. Open her **Client 360** and click **Take on client**: it writes a real
`atlas:takenOnAt` (the `takeOnClient` mutation) and the banner clears. Taking on is
*parallel* to coverage — it does not change `isActive` or `coverageStartDate`
(coverage was already active at routing). The conversational surface here is
single-turn (`priorTurns` is always 0; AgentCore Memory is not wired). The full
cross-persona walk and the **Reset** are in [Module 12 — End-to-End](../12-end-to-end/)
and `use-case-applications/DEMO.md`.

### The Semantic grounding card — Thesis 2, made literal

Thesis 2 ("two UIs, one backbone") is usually shown through *fragments* — same
`Customer` type, different field selection. The **Semantic grounding** card on the
Client 360 page makes the thesis literal at the *component* level: it is the **same
shared component** the Wholesale UI uses
(`apps/shared/ui/semantic-grounding-card.tsx`), called here from
`apps/wealth-ui/src/app/clients/[uri]/client-view.tsx` with `perspective="wealth"`.

Two call sites, one source of ontology truth. The advisor's-side framing flips the
advisory edge label to `advisesCustomer` (vs. `coveringAdvisor` in the wholesale
view), but the FIBO alignment, the relationships, and the SHACL attribution are the
**same loaded model** — because they come from the same component, which traces to the
same Workshop 1 files (see [Module 6 — Wholesale UI](../06-wholesale-ui/) for the full
file trace to `atlas-fibo-alignment.ttl`, `atlas-core.ttl`, and `atlas-shapes.ttl`).
Sharing the card rather than mirroring it is the point: the atlas → FIBO mapping is the
WS1 → WS2 contract, and one component means it cannot drift between the banker's lens
and the advisor's.

The same kind-of-truth discipline applies here too: the green `live` pill marks this
client's actual per-customer instance data (coverage, signals, household), while the
`atlas → FIBO` alignment is labelled `model FIBO 2024 Q3` as the loaded schema — not a
live-per-client lookup. One honest difference to notice: the wealth `CLIENT_360_QUERY`
does **not** select `accounts`, so the `atlas:Account ⊑ fibo:FinancialAccount` row
simply does not render in this app — nothing is invented to fill it. That is
render-from-fetched being honest about what each lens actually fetches.

#### The graphs and the highlight — the same arc, the advisor's lens

The two node-link graphs and the question-driven highlight carry over here exactly as
[Module 6 — Wholesale UI](../06-wholesale-ui/) teaches them in full (the concept on-ramp,
the instance-vs-schema distinction, and the three reasons the highlight is honest are all
there — read that first if you skipped it). They are the *same shared components*
([`node-link-graph.tsx`](../../../apps/shared/ui/node-link-graph.tsx),
[`schema-graph-card.tsx`](../../../apps/shared/ui/schema-graph-card.tsx)), so the model is
identical — only the lens differs:

- The **instance graph** on the Client 360 draws *this client's* fetched neighbourhood,
  advisor's-side (the advisory edge reads `advisesCustomer`). As in the wholesale lens, a
  node appears only if that data was fetched — and because the wealth query doesn't fetch
  `accounts`, there is honestly **no account node** here.
- The **schema graph** sits above the conversation surface on the **Ask the graph**
  (`/conversations`) page — the wealth analogue of the wholesale My-book placement. It is the
  same loaded model (`model · FIBO 2024 Q3`, no live pill).

The one genuine mechanism difference is worth teaching, because it shows the honesty rule
holding under a harder constraint. The wholesale **Ask the graph** returns a `templateId`,
so the highlight looks the template up directly. The wealth **conversation** path
(`converse`, through `conversational-context-manager`) returns the real SPARQL **but no
`templateId`**. So the highlight recognises the query **by its SPARQL signature** instead:
it matches the returned SPARQL against the curated templates' required-and-forbidden token
sets, and lights up **only on a unique match** — if the signature is ambiguous or unknown,
it shows the honest no-map note rather than guess. Same bar (real query → knowable
traversal → honest highlight, or nothing), reached without the convenience of a template id.
Trace: `deriveSchemaHighlightFromConverse` and `matchEntryBySparql` in
[`schema-graph-highlight.ts`](../../../apps/shared/ui/schema-graph-highlight.ts).

![Semantic grounding card — advisor lens](/static/images/10-step-06-semantic-grounding-card.png)

![Schema graph — advisor lens, highlighting a real conversation query](/static/images/10-step-07-schema-graph-highlight.png)

### Step 7 — Verify palette differentiation (cell 8)

Run cell 8 (`cell-08-verify-different-caps`) to assert that the two personas see
different capability sets.

Expected output:

```
Verifying capability palette differentiation...

Consumer Banker capabilities: [...]
Wealth Advisor capabilities:  [...]

Consumer Banker only: [...]
Wealth Advisor only:  [...]
Shared:               [...]

[PASS] Wealth Advisor sees different capabilities than Consumer Banker.
```

### Step 8 — Verify theme-summarizer accessibility (cell 9)

Run cell 9 (`cell-09-verify-themes`) to assert that `theme-summarizer` is
discoverable by Wealth Advisor and not by Consumer Banker.

Expected output:

```
theme-summarizer discoverable_by: ['atlas-wealth-advisor']

Wealth Advisor can discover: True
Consumer Banker cannot:      True

[PASS] Themes are accessible to the Wealth Advisor persona.
The Wealth UI can render market themes for client portfolios.
```

## Expected Outputs

- Consumer Banker and Wealth Advisor see different capability counts
- Both GraphQL fragments printed; field lists differ for the same `Customer` type
- `theme-summarizer` discoverable only by Wealth Advisor
- Both verify cells print `[PASS]`

## Troubleshooting

**Cell 4 shows identical capabilities for both personas**

The registry filters by `discoverable_by` in each agent descriptor. If both palettes
are identical, every descriptor has both `"atlas-consumer-banker"` and
`"atlas-wealth-advisor"` in its `discoverable_by` list. Open the Phase 2 descriptors
in `spec/04-aws-agent-registry/agents/` and verify that `theme-summarizer`,
`conversational-context-manager`, and `behavioral-signal-agent` list only
`"atlas-wealth-advisor"`.

**Cell 9 fails: theme-summarizer not found**

The `theme-summarizer` descriptor must exist in `spec/04-aws-agent-registry/agents/`
as a JSON file. Check that the filename is `theme-summarizer.json` and that
`agent_name` inside it matches exactly.

**Cell 6 fragment fields do not match the schema**

The fragments are hardcoded in cell 6 for illustration. If the GraphQL schema at
`spec/05-appsync-graphql/schema.graphql` has different field names, the fragments
will not be executable against the real schema. This is a notebook illustration —
the spec schema is authoritative for production resolvers.

**Consumer Banker sees `theme-summarizer` in cell 8**

Open `spec/04-aws-agent-registry/agents/theme-summarizer.json` and remove
`"atlas-consumer-banker"` from `registry_metadata.discoverable_by`. Re-run cell 3
to reload descriptors, then re-run cells 4 and 8.

## What's Next

The Wealth UI introduces a second authentication requirement: two UIs, two personas,
one registry endpoint. IAM-based auth (Phase 1) cannot enforce per-user persona
boundaries at the IAM level. [Module 11 — JWT Authorization](../11-jwt-auth/)
explains why switching to JWT-based auth solves this — and why the persona claim
must travel in a Cognito-signed token rather than a request body parameter.
