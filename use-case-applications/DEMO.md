# ATLAS — the demo story (Consumer → Wealth referral)

This is the narrative for demoing the two UIs. One story, told in order, where every
"Ask the graph" question is the banker's *next natural question* — building the case for a
referral, then closing the loop with an auditable handoff to the wealth advisor.

---

## Access card

| | URL | Login | Password |
|---|---|---|---|
| **Wholesale UI** (Consumer Banker) | https://d2u767clefsqd0.cloudfront.net | `dana.brooks@atlas.demo` | `password123` |
| **Wealth UI** (Wealth Advisor) | https://d1n2v02lda72pi.cloudfront.net | `marcus.webb@atlas.demo` | `password123` |

- **Dana Brooks** — the Consumer Banker. Works the Wholesale UI.
- **Marcus Webb** — the Wealth Advisor. Works the Wealth UI; receives the referral.
- **Rachel Kim** — a *customer* (not staff). She is the referral subject in the story.

### Warm up before you present (30 seconds)

The data **reads** are fast (the resolver queries Neptune directly, in-VPC, ~1 s warm).
The **actions** — *Ask the graph*, *Generate draft*, *Converse* — invoke an AgentCore agent
that cold-starts the first time after idle (~10 s). So once, before the room is watching:
sign in as Dana, run **Ask the graph** question 1, and click **Generate draft** on any
customer. That pays the cold-start tax off-stage; every action is snappy during the demo.
Switching personas later is just **Sign out** (top-right) → sign in as the other user.

### How to read what's on screen (the kinds of truth)

Every beat below is tagged with *where the number comes from*, so you can answer "is this
real?" honestly. The tags:

| Tag | Means |
|---|---|
| **LIVE — direct read** | Read straight from Neptune by the resolver (in-VPC, SigV4). No agent, no fabrication. The fast path. |
| **DERIVED** | An ATLAS *output* computed from the data (e.g. a wealth signal), not an input someone typed. See [`05_wealth_signals.ipynb`](notebooks/phase-1-referral/05_wealth_signals.ipynb). |
| **DETERMINISTIC — SHACL** | A pass/fail gate decided by a SHACL shape, not a model. See [`06_shacl_boundary.ipynb`](../agentic-semantic-layer/notebooks/06_shacl_boundary.ipynb). |
| **REGISTRY** | Read live from the Agent Registry, never hardcoded. See [`03_agent_registry.ipynb`](notebooks/phase-1-referral/03_agent_registry.ipynb). |
| **PROBABILISTIC** | A Bedrock-drafted narrative — badged *requires human review*; the model drafts, the human decides. |
| **FIBO** | The type is FIBO-grounded in Workshop 1. See [`02_fibo_alignment.ipynb`](../agentic-semantic-layer/notebooks/02_fibo_alignment.ipynb). |

> The full read-vs-action topology behind these tags is taught in
> [`04_graphql_federation.ipynb`](notebooks/phase-1-referral/04_graphql_federation.ipynb).

---

## The cast and the question

Dana Brooks is a consumer banker. Her job is **not** wealth management — but she sees, in
her book, customers whose in-bank behaviour suggests they're ready for a wealth advisor.
ATLAS surfaces those customers as **wealth-readiness signals** derived from the graph, and
lets Dana hand the strongest candidates to the wealth team — with a full, auditable trail.

> **Depth — the signals are DERIVED, not inputs.** A *Large Deposit Pattern* fires when a
> customer makes a deposit ≥ $250,000 with no active advisory coverage; *No Advisor
> Coverage* only fires for an already-signalled, uncovered customer. Nobody types these in —
> ATLAS computes them from the graph and validates each one against a SHACL shape before it
> is written. The full derivation, with the $250,000 threshold and the SR 11-7 framing, is
> in [`05_wealth_signals.ipynb`](notebooks/phase-1-referral/05_wealth_signals.ipynb) (built
> in [`05a_wealth_signals_build.ipynb`](notebooks/phase-1-referral/05a_wealth_signals_build.ipynb)).

The whole demo answers one question: **"Which of my customers should I refer to wealth,
why, and how do I prove the referral was made correctly?"**

---

## Act 1 — Find the opportunity (Wholesale UI, as Dana Brooks)

**My book.** Dana signs in and sees her book: customer cards, each showing a **signal
count** and a **coverage tag** (`✓ Advisor` if they already have one, **No advisor** if
they're an open candidate). The actionable customers — signalled *and* uncovered — lead.

Now she uses **Ask the graph** *(action path — resolver → `nl-to-sparql-agent`)*. The ten
suggested questions are the story, in order. The agent matches each to a *validated SPARQL
template* (cosine ≥ 0.75) and runs that — it **never free-writes SPARQL**, so an unmatched
question honestly returns "no match" rather than a guess. The graph is the reasoner; the
LLM is just the interface. Why it refuses to invent queries is in
[`04a_how_agents_work.ipynb`](notebooks/phase-1-referral/04a_how_agents_work.ipynb); how the
resolver reaches the agent (vs. the direct-Neptune read path) is in
[`04_graphql_federation.ipynb`](notebooks/phase-1-referral/04_graphql_federation.ipynb).
Walk the questions top to bottom:

| # | Question | What it shows | The banker's reasoning |
|---|---|---|---|
| **1** | Which customers have generated a wealth signal in the last 90 days? | Every signalled customer + signal type | *"Who should I even be looking at?"* — the opportunity list. |
| **2** | What specific transactions were used to surface this customer? | The actual deposits/balances behind a signal | *"Why did the system flag them?"* — the evidence. Provenance, not a black box. |
| **3** | What kinds of wealth signals are most common across the book? | Signal-type counts | *"What's driving my book — big deposits, or household wealth?"* — sizes the play. |
| **4** | Which customers have no wealth advisor assigned? | Uncovered customers + balance | *"Of the signalled, who is actually referable?"* — covered customers don't need a referral. |
| **5** | Which households have mixed wealth coverage? | Households w/ some covered, some not | *"Where's the household upsell?"* — bring the whole family to wealth. |
| **6** | Which household relationships does this customer have? | A customer's household members | *"Who else is in this household I'd be referring?"* — map it. |
| **7** | What accounts and balances does this customer hold? | Accounts + balances | *"What's the financial picture that justifies wealth?"* — the dollars. |
| **8** | Who was this customer's advisor 18 months ago? | Coverage history (start/end dates) | *"Has anyone covered them before?"* — temporal history, no stale assumptions. |

By question 8, Dana has a defensible case: a specific customer (say **Rachel Kim**) has a
**Large Deposit Pattern** and **No Advisor Coverage**, sits in a household with mixed
coverage, holds a high-balance retirement account, and has never had a wealth advisor. She
is the textbook referral.

---

## Act 2 — Make the referral (the human-in-the-loop gate)

Dana opens the customer (Rachel Kim) → **Client 360** *(LIVE — direct read; the `Customer`
type is FIBO-grounded as `fibo-fnd-pty-pty:IndependentParty`, see
[`02_fibo_alignment.ipynb`](../agentic-semantic-layer/notebooks/02_fibo_alignment.ipynb))*:
the signals with their provenance (`validatedBy <SHACL shape> · derivedFrom <transaction>`),
the accounts, the household, and "No advisory coverage." Because there's no coverage, a
**Route referral** button appears.

She clicks it → the **Referral detail** screen:
- **Generate draft** *(action path — `referral-rationale-drafter`, Bedrock; **PROBABILISTIC**)*
  → the agent writes a rationale grounded in Rachel's *actual* signals (and, if a household
  has no signals yet, from its real members — never fabricated; if there is nothing real to
  ground on it returns an honest *insufficient-context*, not an invented story). It is badged
  **probabilistic — requires human review**. The model drafts; it does not decide.
- **Approve and route** → *this is the gate.* Nothing routes without Dana's click. That
  click starts the `referral-orchestrator` workflow (Step Functions):
  `select advisor → validate (SHACL) → write routing decision → notify → audit`.

The screen shows a persistent **"✓ Referral routed to Marcus Webb"** confirmation. Under
the hood the workflow (a) wrote a `RoutingDecision` *(**DETERMINISTIC — SHACL**: validated
against the closed route set `ROUTE_ADVISOR_QUEUE`; a shape, not a model, decides
pass/fail — see
[`06_shacl_boundary.ipynb`](../agentic-semantic-layer/notebooks/06_shacl_boundary.ipynb))*,
PROV-O attributed, and (b) assigned Marcus as Rachel's advisor.

---

## Act 3 — The handoff lands (Wealth UI, as Marcus Webb)

**Sign out** (top-right) on the Wholesale UI, then sign in as **Marcus Webb** on the Wealth
UI. Rachel Kim now appears in his book flagged **"New — routed to you"** *(LIVE — direct
read)*. This banner is not a timer or a mock: it shows precisely while the relationship was
**created by the routing workflow** (`routedByWorkflow`) **and the advisor has not yet
accepted it** (`takenOnAt` is null). It is the advisor's inbox of governed handoffs.

Marcus opens her **Client 360** and clicks **Take on client**. That writes a *real*
`atlas:takenOnAt` timestamp to the routed relationship — a genuine accept transition, not a
fake — and the banner **clears**. (It is additive: taking on a client does not touch the
coverage that was already active at routing.) From here he sees advisory coverage, the same
wealth signals from the advisor's lens, the household, and the single-turn conversational
surface *(action path — `converse` → `conversational-context-manager`; honestly single-turn,
`priorTurns` is always 0 because AgentCore Memory is not wired)*.

This is the point of the whole system: **one graph, two personas, a governed workflow
moving a customer between them — and a real accept step the advisor takes — every step
provenance-stamped.**

---

## Act 4 — Prove it (back on the Wholesale UI, Ask the graph)

Now the last two questions — which were **empty in Act 1** — return rows, because a
governed action finally happened:

| # | Question | What it shows now |
|---|---|---|
| **9** | Which routing decisions have human review and what was the outcome? | The routing decision Dana just made → target advisor Marcus Webb. |
| **10** | What is the full audit trail from customer to advisor approval? | The end-to-end record: routing → household → advisor → approved rationale. |

The teaching beat: **the audit trail exists *only because* a human-approved, governed
action happened** *(LIVE — direct read of the `RoutingDecision` / `AuditRecord` the workflow
wrote)*. Before the referral, questions 9–10 are honestly empty. After it, they're the
compliance record — defensible under SR 11-7, the regulatory anchor taught in
[`03_agent_registry.ipynb`](notebooks/phase-1-referral/03_agent_registry.ipynb) and
[`05_wealth_signals.ipynb`](notebooks/phase-1-referral/05_wealth_signals.ipynb).

---

## Act 5 — Reset (so you can do it again)

On Dana's dashboard, **↺ Reset demo** removes exactly what the demo created — the advisory
relationship assigning Marcus to Rachel, and the routing decision — and leaves all seed
coverage untouched. Because the "New — routed to you" banner is driven by those same routed
relationships, **resetting also clears the banner** in Marcus's book. Rachel is an open
referral candidate again, questions 9–10 are empty again, and the story is ready for the
next run.

---

## One-line summary for the room

> *"A consumer banker spots a customer who's ready for wealth — surfaced by signals the
> graph derived from real transactions, not a guess — reviews an AI-drafted rationale,
> and routes them to a wealth advisor through a workflow that records every step. The LLM
> is the interface; the graph is the reasoner; the audit trail is structural."*
