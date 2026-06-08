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

> Tip: the very first page load after an idle period can take a few seconds (the query
> service is a VPC Lambda that cold-starts). It warms up immediately after.

---

## The cast and the question

Dana Brooks is a consumer banker. Her job is **not** wealth management — but she sees, in
her book, customers whose in-bank behaviour suggests they're ready for a wealth advisor.
ATLAS surfaces those customers as **wealth-readiness signals** derived from the graph, and
lets Dana hand the strongest candidates to the wealth team — with a full, auditable trail.

The whole demo answers one question: **"Which of my customers should I refer to wealth,
why, and how do I prove the referral was made correctly?"**

---

## Act 1 — Find the opportunity (Wholesale UI, as Dana Brooks)

**My book.** Dana signs in and sees her book: customer cards, each showing a **signal
count** and a **coverage tag** (`✓ Advisor` if they already have one, **No advisor** if
they're an open candidate). The actionable customers — signalled *and* uncovered — lead.

Now she uses **Ask the graph**. The ten suggested questions are the story, in order. The
agent matches each to a *validated SPARQL template* (it never free-writes SPARQL — the
graph is the reasoner, the LLM is just the interface). Walk them top to bottom:

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

Dana opens the customer (Rachel Kim) → **Client 360**: the signals with their provenance
(`validatedBy <SHACL shape> · derivedFrom <transaction>`), the accounts, the household, and
"No advisory coverage." Because there's no coverage, a **Route referral** button appears.

She clicks it → the **Referral detail** screen:
- **Generate draft** → the `referral-rationale-drafter` agent (Bedrock) writes a rationale
  grounded in Rachel's *actual* signals. It is badged **probabilistic — requires human
  review**. The model drafts; it does not decide.
- **Approve and route** → *this is the gate.* Nothing routes without Dana's click. That
  click starts the `referral-orchestrator` workflow (Step Functions):
  `select advisor → validate (SHACL) → write routing decision → notify → audit`.

The screen shows a persistent **"✓ Referral routed to Marcus Webb"** confirmation. Under
the hood the workflow (a) wrote a `RoutingDecision` (PROV-O attributed, SHACL-validated
against the closed route set `ROUTE_ADVISOR_QUEUE`), and (b) assigned Marcus as Rachel's
advisor.

---

## Act 3 — The handoff lands (Wealth UI, as Marcus Webb)

Sign out, sign in as **Marcus Webb** on the Wealth UI. Rachel Kim now appears in his book
as **covered by Marcus Webb**. Open her **Client 360**: advisory coverage (the relationship
just created), the same wealth signals from the advisor's lens, the household, and the
single-turn conversational surface.

This is the point of the whole system: **one graph, two personas, a governed workflow
moving a customer between them — every step provenance-stamped.**

---

## Act 4 — Prove it (back on the Wholesale UI, Ask the graph)

Now the last two questions — which were **empty in Act 1** — return rows, because a
governed action finally happened:

| # | Question | What it shows now |
|---|---|---|
| **9** | Which routing decisions have human review and what was the outcome? | The routing decision Dana just made → target advisor Marcus Webb. |
| **10** | What is the full audit trail from customer to advisor approval? | The end-to-end record: routing → household → advisor → approved rationale. |

The teaching beat: **the audit trail exists *only because* a human-approved, governed
action happened.** Before the referral, questions 9–10 are honestly empty. After it,
they're the compliance record — defensible under SR 11-7.

---

## Act 5 — Reset (so you can do it again)

On Dana's dashboard, **↺ Reset demo** removes exactly what the demo created — the advisory
relationship assigning Marcus to Rachel, and the routing decision — and leaves all seed
coverage untouched. Rachel is an open referral candidate again, questions 9–10 are empty
again, and the story is ready for the next run.

---

## One-line summary for the room

> *"A consumer banker spots a customer who's ready for wealth — surfaced by signals the
> graph derived from real transactions, not a guess — reviews an AI-drafted rationale,
> and routes them to a wealth advisor through a workflow that records every step. The LLM
> is the interface; the graph is the reasoner; the audit trail is structural."*
