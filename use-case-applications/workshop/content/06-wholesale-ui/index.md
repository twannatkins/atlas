---
title: "Module 6 — Wholesale UI: The Two-Driver Architecture"
weight: 60
---

# Module 6 — Wholesale UI: The Two-Driver Architecture

## Learning Objectives

- Explain the two-driver architecture: GraphQL drives what data is rendered, the
  Agent Registry drives what actions are available — and neither is hardcoded
- Implement and verify the compliance banner that respects the tipping-off
  prohibition under 31 U.S.C. §5318(g)(2)
- Confirm that the "Route to advisor" action requires an `approved_rationale`
  before the `referral-orchestrator` agent will accept the invocation
- Trace the complete Rachel Kim scenario from signal detection through routing
- Read the Semantic grounding card as a worked example of the semantic layer made
  visible — and of the kind-of-truth discipline (a live instance vs. a loaded
  schema; a real lineage vs. an unbound target)
- Read a knowledge graph for the first time through two node-link graphs — the
  instance graph (this customer's real neighborhood) and the schema graph (the loaded
  ontology model) — and explain why one is "live" and the other is not
- Explain why the question-driven schema-graph highlight is honest: template-bounded
  queries make the traversal knowable, counts are shown only where the answer carries
  them, and the highlight is an overlay on the loaded model, not a live reclassification

## Time Estimate

25–30 minutes.

## Prerequisites

- [Module 5 — GraphQL Federation](../05-graphql-federation/) complete
- All three resolver patterns verified

## What You Will Build

A simulated Wholesale UI that demonstrates the two-driver architecture:
`entity_360_data` (from GraphQL), a persona-scoped capability palette (from the
Agent Registry), a compliant compliance banner (tipping-off safe), and the
human-in-the-loop routing gate.

The notebook is `notebooks/phase-1-referral/06_wholesale_ui.ipynb`.

## Steps

Before running any code, read cell 0 (`cell-00-title`) and cell 1
(`cell-01-terms`). The Key Terms table defines "two-driver architecture,"
"capability palette," and "human-in-the-loop" as used in this notebook.

### Step 1 — Open the notebook and select the kernel

Open `notebooks/phase-1-referral/06_wholesale_ui.ipynb` in SageMaker Studio.
Select the **ATLAS Workshop 2 (Python 3.12)** kernel.

### Step 2 — Read the concept section (cell 2)

Read cell 2 (`cell-02-concept`). It explains the two-driver pattern:

Most enterprise applications have one driver: an API that returns data, and the
UI renders it. The set of actions available to the user is hardcoded in the UI
code — a button exists because a developer put it there. The Wholesale UI has two
drivers. The first is the FIBO-shaped GraphQL API — it provides entity data for
the Entity 360 panel. The second is the Agent Registry — it provides a
persona-scoped capability palette that tells the UI what actions the current user
is allowed to invoke. Neither is hardcoded; both are queried live. A new agent
registered in the registry appears in the palette automatically.

The concept section also explains the regulatory constraint that governs the
compliance banner.

### Step 3 — Run setup (cell 3)

Run cell 3 (`cell-03-setup`) to load shared helpers and agent descriptors.

Expected output:

```
Shared helpers loaded.
Agent descriptors loaded: N
```

### Step 4 — Simulate the Entity 360 data fetch (cell 4)

Run cell 4 (`cell-04-entity-360`) to build the `entity_360_data` dict that
the GraphQL API would return for the Patel household. Read the simulated response —
it shows which fields come from Ontop (entity data in Iceberg) and which come from
direct Neptune SPARQL (WealthSignal instances).

Expected output:

```
Entity 360 — Patel household
  uri: atlas:hh/9c2a1e
  label: Patel Household
  members: [Anjali Patel, ...]
  wealth_signals: [LargeDepositPattern, ...]
  compliance_review: True
```

### Step 5 — Implement the compliance banner (cell 5)

Run cell 5 (`cell-05-compliance-banner`) to implement `render_compliance_banner()`.
Read the cell comment carefully — it explains why the banner text must say
"Active compliance review — contact BSA team before client outreach" and must
never say "SAR filed."

The tipping-off prohibition (31 U.S.C. §5318(g)(2)) makes it a federal crime to
disclose to a customer or a non-BSA employee that a SAR has been filed. The
Consumer Banker is outside the BSA function. The banner tells them only what they
are allowed to know.

Expected output:

```
Consumer Banker banner: "Active compliance review — contact BSA team before client outreach"
BSA Analyst banner:     "SAR draft in progress — BSA team review required"
No banner (no review):  None
```

### Step 6 — Implement the capability palette (cell 6)

Run cell 6 (`cell-06-capability-palette`) to implement `get_capability_palette()`.
This calls `discover_capabilities()` from Module 4 and returns the persona-scoped
action list.

Expected output:

```
Consumer Banker palette: N capabilities
  - nl-to-sparql-agent
  - wealth-signal-detector
  - household-traverser
  - referral-rationale-drafter
  - referral-orchestrator
Wealth Advisor palette:  M capabilities (referral-rationale-drafter absent)
```

![Capability palette by persona](/static/images/06-step-06-capability-palette.png)

### Step 7 — Simulate Route to advisor (cell 7)

Run cell 7 (`cell-07-route-to-advisor`) to simulate the complete "Route to
advisor" flow: the Consumer Banker selects the Patel household, the
`referral-rationale-drafter` agent drafts a narrative, the banker reviews and
approves the draft, and the `referral-orchestrator` agent routes the referral.

Expected output:

```
Route to advisor — Patel household
  Step 1: wealth-signal-detector → signals detected: N
  Step 2: referral-rationale-drafter → draft created (is_probabilistic: True)
  Step 3: [Human review gate] approved_rationale: "..."
  Step 4: referral-orchestrator → routed
  AuditRecord written: atlas:audit/...
```

### The demo loop — Dana's half

In the live demo, this is the first half of the route → banner → take-on → reset
loop. As **Dana Brooks (the Consumer Banker)** you: open the signalled customer
**Rachel Kim**, click **Route referral → Generate draft** (grounded, probabilistic,
requires review), then **Approve and route**. The outcome you trigger: Rachel lands
in **Marcus Webb (the Wealth Advisor)**'s book flagged **"New — routed to you."**
Marcus's half — the banner, **Take on client** (a real `takenOnAt` that clears it),
and **Reset** — is in [Module 10 — The Wealth UI](../10-wealth-ui/) and the full
walk in [Module 12 — End-to-End](../12-end-to-end/). Switching personas is just
**Sign out** (top-right). The canonical script is `use-case-applications/DEMO.md`.

### The Semantic grounding card — the semantic layer made visible

The customer-360 page opens with a **Semantic grounding** card (the first card under
the entity header). It is the one place in the UI where a banking audience can *see*
that the data they are looking at is FIBO-grounded, not bespoke — and it is built to
teach the kind-of-truth discipline this whole workshop turns on. The card itself is
the lesson, so read it carefully.

#### Read the model before the mechanism — four ideas this card makes visible

Workshop 2 stands on Workshop 1, so it has been *using* four ideas without re-explaining
them. The Semantic grounding card — and the two node-link graphs described below — exist
to make those ideas something you can *see*, not just read. If any feels abstract, this
card is where it becomes concrete. (Each was taught in Workshop 1; this is the on-ramp,
not a re-teach.)

1. **A knowledge graph is not a table.** A table stores rows of a single kind (all
   customers, all accounts). A knowledge graph stores *things* as **nodes** and the
   *relationships between them* as **edges** — so "this customer holds this account" is a
   drawn connection, not a foreign-key column you have to join. The node-link graphs on
   this page literally draw that: circles and rectangles for things, labelled lines for
   relationships.
2. **An ontology is the model; an instance is one customer's data.** The *ontology* is the
   set of classes and how they may relate (`Customer`, `Account`, `hasAccount`…) — the
   same for everyone. An *instance* is one real customer and their actual accounts. Hold
   onto this distinction: the **schema graph** below draws the ontology (the model), and
   the **instance graph** draws one customer (their data). Two graphs, because they are two
   different kinds of thing.
3. **FIBO alignment means we speak the regulator's vocabulary.** `atlas:Customer` is not a
   bespoke invention — it is declared a *subclass of* `fibo:IndependentParty` (the Financial
   Industry Business Ontology's term). When someone asks "where does `Customer` come from?",
   the answer is a published industry standard, not "we made it up." Taught in Workshop 1's
   FIBO-alignment module.
4. **The LLM translates; it does not reason.** When you "ask the graph" in natural language,
   the language model does *not* invent an answer — it matches your question to one of a
   fixed, pre-validated set of SPARQL queries and runs that. This is the SR 11-7 boundary,
   built in [Module 5 — GraphQL Federation](../05-graphql-federation/). It is also *why* the
   schema-graph highlight (below) can be trusted — more on that there.

With those four in hand, the card and its graphs read as one idea made visible: a customer,
grounded in a published model, whose real data is a graph you can explore — and whose model
lights up when you ask it a real question.

**Where it lives.** One shared component,
`apps/shared/ui/semantic-grounding-card.tsx`, with two call sites: the Wholesale
customer view (`apps/wholesale-ui/src/app/customers/[uri]/customer-view.tsx`) and the
Wealth client view (`apps/wealth-ui/src/app/clients/[uri]/client-view.tsx`, with
`perspective="wealth"`). It is **shared, not mirrored** on purpose: the atlas → FIBO
mapping is the contract between Workshop 1 and the apps, and a single component means
that mapping cannot drift between the two UIs. (Contrast the per-app *copies* of
`signal-card`/`household-strip`, which carry an explicit "do not let the two drift"
comment — the grounding card removes that risk by construction.)

**What it shows — the real loaded model, not an idealized one.** Every class and edge
on the card traces to an actual Workshop 1 ontology file:

- The FIBO alignment — `atlas:Customer ⊑ fibo:IndependentParty`,
  `atlas:Account ⊑ fibo:FinancialAccount`, `atlas:Advisor ⊑ fibo:FunctionalRole` — is
  exactly bindings 1, 2 and 5 in
  [`atlas-fibo-alignment.ttl`](../../../agentic-semantic-layer/ontology/atlas-fibo-alignment.ttl)
  (all `rdfs:subClassOf`, FIBO 2024 Q3 Production Release).
- The relationships — `hasAccount`, `memberOf`, `producesSignal`, and the advisory
  edge (`coveringAdvisor` / `advisesCustomer`) — are the object properties declared in
  [`atlas-core.ttl`](../../../agentic-semantic-layer/ontology/atlas-core.ttl).
- `atlas:WealthSignal` and `atlas:Household` are shown as **bank-specific, no FIBO
  counterpart** — which is exactly how `atlas-fibo-alignment.ttl` documents them. The
  signal's SHACL attribution (the `validatedBy` line, reusing the existing
  `ProvenanceBadge`) points at the shapes in
  [`atlas-shapes.ttl`](../../../agentic-semantic-layer/ontology/atlas-shapes.ttl) —
  e.g. `atlas:WealthSignalTypeShape`.

If a class is not in those files, the card does not render it. That is the corpus-honesty
rule made structural.

**Render-from-fetched — UI without a data-layer change.** The card adds no query. It
reads only fields `CUSTOMER_360_QUERY` already fetches (`accounts`, `household`,
`wealthSignals.provenance`, `advisoryRelationships.advisor`) and pairs each with its
static atlas → FIBO entry. A row appears only when that data is present for the
customer — the same conditional discipline as the cards below it. The teaching point:
making the semantic layer visible was a render addition, not a new resolver.

#### The kind-of-truth distinction (why the labels are precise)

A card that teaches kind-of-truth must be honest about *its own* truth, and this one
holds two distinct kinds side by side — do not flatten them into "here's a card":

- **Live instance** — *which* accounts, household members, signals, and advisor **this**
  customer has. Fetched per-customer from the graph, so it wears the green `live` pill
  (the same `.lab-live` label the signals/accounts/household cards use).
- **Loaded schema** — the `atlas → FIBO rdfs:subClassOf` alignment. This is the *same
  for every customer*; it is the loaded ontology, **not** queried live per customer. So
  it is labelled with its ontology-version provenance (`model FIBO 2024 Q3`), and the
  card explicitly says the alignment is the loaded schema, not a live lookup. Putting a
  "live" pill on the alignment would overclaim — it would imply the app re-derives FIBO
  membership per request, which it does not.

This mirrors the workshop's existing honesty conventions: the `live derived · SHACL`
note on the signals card, and the **live now / possible next** legend in the app
chrome. The grounding card is a worked example of that same discipline applied to the
ontology itself.

#### The instance graph — the same truth, drawn as a graph

At the top of the card, above those rows, is a **node-link graph of this customer** — and
it is not new information. It is the *same live-instance facts* the rows state, drawn the
other way: this customer at the centre, with edges out to their accounts, household,
advisor, and signals. **The rows give you the precise facts; the graph gives you the
shape.** A novice meeting "knowledge graph" for the first time can finally see one — and
it is this customer's real neighbourhood, not a diagram of the idea.

It is render-from-fetched, exactly like the rows: the centre node is the fetched customer,
and a neighbour node appears **only if that data was fetched** — so a customer with no
household simply has no household node. Nothing is invented. Every node is a `kind: "live"`
node (the green treatment) because every node is a per-customer fetched fact — the same
"live instance" truth the green pill marks. Trace:
[`node-link-graph.tsx`](../../../apps/shared/ui/node-link-graph.tsx) (the hand-rolled SVG
renderer — no charting library) and
[`semantic-grounding-card.tsx`](../../../apps/shared/ui/semantic-grounding-card.tsx) (which
builds the neighbourhood from the fetched fields and marks every node `live`). You can
**drag any node** to explore the layout; it resets to the clean arrangement on reload
(exploration, not saved state).

#### The schema graph — the model itself, drawn as a graph

The instance graph draws *one customer*. On the **My book** page (above Ask-the-graph)
there is a second node-link graph that draws *the model* — the **schema graph**. This is
the on-ramp's idea #2 made literal: same node-link drawing, but the nodes are the ontology
**classes** (`atlas:Customer`, `atlas:Account`, `atlas:Household`, `atlas:WealthSignal`,
`atlas:Advisor`) and the edges are the relationships *the model allows between them*
(`hasAccount`, `memberOf`, `producesSignal`, the advisory edge).

The crucial difference is honesty about *what kind of truth it is*. The schema graph is the
**loaded model** — the same for every customer, not a per-customer query — so it wears **no
green `live` pill**; it is labelled `model · FIBO 2024 Q3`, its ontology-version provenance.
The instance graph is live (this customer); the schema graph is the loaded schema (everyone).
That is the same live-instance-vs-loaded-schema distinction from the rows, now drawn as two
different graphs. Trace:
[`schema-graph-card.tsx`](../../../apps/shared/ui/schema-graph-card.tsx) (the five real
type-nodes + edges, traced to the same TTLs as the rows; deliberately no `lab-live`).

#### The highlight — ask a real question, watch the model light up

Here the arc pays off. On **My book**, when you ask a real question in **Ask the graph**,
the schema graph above **highlights the classes and edges that question actually traversed**
— and annotates honest counts where the answer carries them. Ask *"What accounts and
balances does this customer hold?"* and `atlas:Customer` → `atlas:Account` lights up with a
"N results" badge; ask *"What kinds of wealth signals are most common?"* and
`atlas:WealthSignal` lights up with the real per-type counts. The model stops being a static
diagram and becomes a map of what your question touched.

The three things that make this **honest, not decorative**, are the heart of the lesson:

- **Why you can trust the highlight — the query is knowable.** Recall on-ramp idea #4: the
  agent never free-generates SPARQL. It matches your question to **one of ten fixed,
  pre-validated templates** in
  [`ground-truth.yaml`](../../../agents/nl-to-sparql-agent/ground-truth.yaml) and returns
  *that template's* real SPARQL plus its `templateId`. Because the query is one of a known
  set, **the path it traverses through the model is knowable in advance** — so the highlight
  reflects the query that genuinely ran, not a guess. A free-generating black box could not
  be highlighted honestly; a template-bounded one can. The map from template to highlighted
  elements lives in
  [`schema-graph-highlight.ts`](../../../apps/shared/ui/schema-graph-highlight.ts)
  (`CURATED_MAP`), and it cross-checks the returned SPARQL against the expected tokens before
  lighting anything up — if they don't match, it shows the honest no-map note instead.
- **Why the counts are selective — count only what the answer means.** Some questions return
  a real count: *"most common signal types"* runs a SPARQL `GROUP BY` (`COUNT(?sig)`), so the
  per-type numbers are genuine and the card annotates them. Other questions return *join
  rows* — *"what transactions surfaced this customer?"* returns one row per
  customer×signal×transaction combination. Counting those rows as "transactions" would
  **invent a number the query never computed**, so the card shows **no count** there. The
  restraint is the honest choice, and it is encoded as a per-template `countKind`
  (`groupby` / `rowtotal` / `none`) in `schema-graph-highlight.ts`. Teaching point: an honest
  UI counts what the answer means, and stays silent where a number would mislead.
- **Why the highlight is an overlay, not "live" — the distinction, one more time.** The
  highlight does **not** turn the schema graph into a live, per-customer view. The schema graph
  is still the loaded model (`FIBO 2024 Q3`); the highlight is a *query-response overlay* that
  shows *which part of the loaded model a real question traversed*. The model didn't change;
  your question lit up a path through it. If a real answer doesn't map to the five-type model
  (e.g. the routing/audit questions, which traverse `RoutingDecision` — not a node on this
  graph), the card says so honestly and highlights nothing. This is the live-instance (the
  green instance graph) vs. loaded-schema (the neutral, highlightable model) distinction stated
  one final way — and it is the single idea this whole card exists to teach.

#### The lineage strip (real path live, external systems shaded)

The bottom of the card shows lineage, and it draws the same honest line:

- The **real ATLAS path** — `data load → LGD → Entity Resolution → SLGD →
  SHACL-validated WealthSignals` — is shown **live/unshaded**. This is the genuine
  two-tier topology Workshop 1 builds and the read path
  [Module 5 — GraphQL Federation](../05-graphql-federation/) federates over.
- The bank's **systems of record** — CIF, nCino, Snowflake — are shown **shaded**, in
  the `.future-band` diagonal-hatch treatment with the "Possible next — roadmap, not
  shown as live" label. They are named as a *target* the FIBO-aligned model could bind
  to, and explicitly marked **not bound** in this demo.

The rule, the same one the **Live today vs. possible next** discipline enforces
everywhere: the real path is drawn live; an unbound system is drawn shaded and never
presented as working.

![Semantic grounding card](/static/images/06-step-08-semantic-grounding-card.png)

![Schema graph highlighting a real question's traversal on My book](/static/images/06-step-09-schema-graph-highlight.png)

### Step 8 — Verify persona-scoped palette (cell 9)

Run cell 9 (`cell-09-verify-palette`) to assert the two palette assertions from
the acceptance criteria: Consumer Banker sees `referral-orchestrator`, and Wealth
Advisor does not see `referral-rationale-drafter`.

Expected output:

```
[PASS] Consumer Banker palette contains referral-orchestrator.
[PASS] Wealth Advisor palette does not contain referral-rationale-drafter.
```

### Step 9 — Verify compliance banner (cell 10)

Run cell 10 (`cell-10-verify-banner`) to assert that the banner for non-BSA
personas never contains the strings "SAR" or "filed."

Expected output:

```
Checking non-BSA personas: atlas-consumer-banker, atlas-wealth-advisor, atlas-ontology-steward
  atlas-consumer-banker: no SAR/filed strings  ✓
  atlas-wealth-advisor:  no SAR/filed strings  ✓
  atlas-ontology-steward: no SAR/filed strings  ✓
[PASS] Tipping-off prohibition respected for all non-BSA personas.
```

### Step 10 — Verify human-in-the-loop (cell 11)

Run cell 11 (`cell-11-verify-human-in-loop`) to assert that the
`referral-orchestrator` descriptor's `input_schema` declares `approved_rationale`
as a required field — the structural guarantee that no auto-routing can occur.

Expected output:

```
[PASS] referral-orchestrator requires approved_rationale (human-in-the-loop enforced).
```

## Expected Outputs

- Entity 360 data includes both GraphQL entity fields and Neptune WealthSignal instances
- Compliance banner never contains "SAR" or "filed" for non-BSA personas
- Capability palette differs by persona; Wealth Advisor lacks `referral-rationale-drafter`
- Route to advisor simulation writes an `AuditRecord` with PROV-O attribution
- All three verify cells print `[PASS]`

## Troubleshooting

**Cell 5 banner contains "SAR" for a non-BSA persona**

The `render_compliance_banner()` implementation returned the wrong branch for the
persona. Check the conditional logic: only `"atlas-bsa-analyst"` should receive the
SAR-containing message. Every other persona — including `"atlas-ontology-steward"` —
is outside the BSA function and must receive the generic compliance message.

**Cell 7 raises KeyError on approved_rationale**

The Route to advisor simulation passes an `approved_rationale` string to
`simulate_route_to_advisor()`. If the parameter name does not match the function
signature, Python raises KeyError when the orchestrator checks the required field.
Verify that the function signature uses `approved_rationale` (not `rationale` or
`approved_narrative`).

**Cell 9 fails: Wealth Advisor sees referral-rationale-drafter**

Return to [Module 4 — Agent Registry](../04-agent-registry/) and verify that the
`referral-rationale-drafter` descriptor lists only `"atlas-consumer-banker"` in
`discoverable_by`. Then re-run cell 3 in this notebook (which reloads the
descriptors) before re-running cell 9.

**Cell 11 fails: approved_rationale not in required fields**

The `referral-orchestrator` descriptor's `input_schema.required` must include
`"approved_rationale"`. Open
`spec/04-aws-agent-registry/phase-1-agents/referral-orchestrator.json` and verify
the schema. This is also an acceptance criteria check (assertion 2.6).

## What's Next

Phase 1 is assembled. [Module 7 — Phase 1 Acceptance](../07-phase-1-acceptance/)
runs the full acceptance suite from `spec/10-acceptance-criteria.md`: 24 assertions
across seven categories. Every assertion that passes is a contract honored — a
piece of the architecture that works as specified. If all non-deferred assertions
pass, Phase 1 is complete and you may proceed to Phase 2.
