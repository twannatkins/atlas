#!/usr/bin/env python3
"""Builds 07_demo_runbook.ipynb — the capstone WS2 demo runbook.

Run: python3 build_07_demo_runbook.py  → writes 07_demo_runbook.ipynb beside it.
This generator keeps the long markdown/code readable in source control; the notebook
is the artifact. Re-run to regenerate.
"""
import json
from pathlib import Path

def md(*lines): return {"cell_type": "markdown", "metadata": {}, "source": _src(lines)}
def code(*lines): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": _src(lines)}
def _src(lines):
    flat = []
    for l in lines:
        flat.extend(l.split("\n") if isinstance(l, str) else l)
    return [x + "\n" for x in flat[:-1]] + [flat[-1]] if flat else []

cells = []

# ── Title + the question ──────────────────────────────────────────────────
cells.append(md(
"# 07 — The ATLAS demo runbook (the culminating event)",
"",
"**Phase 2 · capstone.** You have built the whole stack across Workshops 1 and 2. This",
"notebook is the script for *demonstrating* it — the live walkthrough you give a",
"stakeholder, and the reference a workshop attendee follows to see everything they built",
"actually work, end to end, in a browser.",
"",
"## The question",
"",
"> *\"Everything is deployed. How do I actually show it working — as a story a banking",
"> audience recognises — and prove that every card on the screen is powered by the",
"> semantic layer we built, not a mock-up?\"*",
"",
"This runbook answers that. It (1) recaps what the two workshops built, (2) discovers the",
"live endpoints from your own deployment (nothing hardcoded — so it works in a freshly",
"rebuilt account), (3) walks the **Dana Brooks → Marcus Webb** referral scenario (referring the customer Rachel Kim) across",
"both UIs, explaining every card, and (4) resets the demo so you can run it again.",
))

# ── Section: what we built (the recap) ─────────────────────────────────────
cells.append(md(
"## The concept — what the two workshops built (recap)",
"",
"The demo rests on a deliberate stack. Top to bottom:",
"",
"| Layer | Built in | What it is |",
"|---|---|---|",
"| **Ontology + SHACL + R2RML** | WS1 | The FIBO-aligned contract: 22 `atlas:` classes, 6 SHACL shapes, the two-tier Neptune (LGD → SLGD) and the entity-resolution promotion path. |",
"| **Synthetic data** | WS1 | 200 promoted customers, 428 accounts, 105 advisory relationships, 9 advisors, derived wealth signals — all carrying PROV-O provenance. |",
"| **Agents + MCP servers** | WS2 | nl-to-sparql-agent (template-bounded NL→SPARQL), wealth-signal-detector, referral-rationale-drafter (Bedrock), conversational-context-manager, household-traverser, and the referral-orchestrator (Step Functions). Discoverable through the **Agent Registry**. |",
"| **GraphQL API** | WS2 | AppSync, FIBO-shaped schema, Cognito-group access control (who may call which field), resolvers that query Neptune directly (SigV4, in-VPC) for reads and invoke agents for actions. |",
"| **Two React UIs** | WS2 | The Wholesale (Consumer Banker) and Wealth (Advisor) workbenches — every card powered by a live GraphQL query, capabilities by the live registry. |",
"",
"**The two-driver architecture** is the thing the demo makes visible: *GraphQL drives what",
"DATA renders (the cards); the Agent Registry drives what ACTIONS are available (the",
"capabilities).* Two independent drivers, one screen.",
"",
"**The named protagonists** carry the story:",
"- **Dana Brooks** — the Consumer Banker. She works the Wholesale UI: sees her book, the",
"  wealth-readiness signals the graph derived, and refers a customer to wealth.",
"- **Marcus Webb** — the Wealth Advisor. He works the Wealth UI: sees his covered book,",
"  and *receives* the referral Rachel routes.",
"",
"All synthetic — **Dana Brooks** and **Marcus Webb** are staff (logins); **Rachel Kim** is a",
"the wealth advisor a routed referral lands with — so the handoff is coherent end to end.",
))

# ── Section: the real topology (what powers each beat) ─────────────────────
cells.append(md(
"## The real topology — what actually powers each card",
"",
"Before the walkthrough, fix the mental model of *what runs when you click*. The running",
"system has **two paths**, and the demo touches both — be honest about which is which:",
"",
"| Path | Used for | How it runs | Latency |",
"|---|---|---|---|",
"| **Read — direct Neptune** | the dashboard, Client 360, signals, coverage, audit trail | resolver Lambda queries Neptune **directly** (SigV4, in-VPC). **No agent.** | ~1 s warm |",
"| **Action — resolver → agent** | *Ask the graph*, *Generate draft*, *Converse* | resolver invokes an **AgentCore Runtime** (`invoke_agent_runtime`) | ~10 s cold, then fast |",
"| **Action — routing (SFN)** | *Approve and route* | resolver starts the `referral-orchestrator` **Step Functions** workflow | a few seconds |",
"| **Gate — SHACL** | every `RoutingDecision`, every signal write | a **SHACL shape** decides pass/fail — deterministic, not a model | instant |",
"",
"This is why you **warm up the actions** before presenting: the read path is always quick,",
"but the first agent call after idle pays a cold-start. The full teaching of this split —",
"and the honest note that **per-row Lake Formation scoping is roadmap, not enforced** — is",
"in [`04_graphql_federation.ipynb`](../phase-1-referral/04_graphql_federation.ipynb). The",
"agents' refuse-to-invent behaviour is in",
"[`04a_how_agents_work.ipynb`](../phase-1-referral/04a_how_agents_work.ipynb); the SHACL gate",
"is in [`06_shacl_boundary.ipynb`](../../../agentic-semantic-layer/notebooks/06_shacl_boundary.ipynb);",
"the FIBO grounding of the types you'll see is in",
"[`02_fibo_alignment.ipynb`](../../../agentic-semantic-layer/notebooks/02_fibo_alignment.ipynb);",
"and the signals are *derived outputs* (not inputs) per",
"[`05_wealth_signals.ipynb`](../phase-1-referral/05_wealth_signals.ipynb).",
))

# ── Section: discover the live deployment ──────────────────────────────────
cells.append(md(
"## The build — discover YOUR live deployment",
"",
"Every value below is read from your deployed stack's CloudFormation outputs and Cognito",
"pool — never hardcoded. This is the habit that makes the runbook portable: **the deployed",
"stack is the source of truth.** Run these cells in a fresh account after `08_deploy` and",
"they resolve to that account's URLs, pool, and endpoint.",
))

cells.append(code(
"import subprocess, json, os",
"",
"REGION = 'us-east-1'        # WS2 is pinned to us-east-1",
"STACK  = 'AtlasWorkshop2'",
"",
"def _aws(args):",
"    p = subprocess.run(['aws', *args, '--region', REGION], capture_output=True, text=True)",
"    if p.returncode != 0:",
"        raise RuntimeError(p.stderr.strip())",
"    return p.stdout",
"",
"def stack_outputs(stack=STACK):",
"    out = _aws(['cloudformation', 'describe-stacks', '--stack-name', stack,",
"                '--query', 'Stacks[0].Outputs', '--output', 'json'])",
"    return {o['OutputKey']: o['OutputValue'] for o in json.loads(out or '[]')}",
"",
"out = stack_outputs()",
"WHOLESALE_URL = out.get('WholesaleUiUrl', '(not found)')",
"WEALTH_URL    = out.get('WealthUiUrl', '(not found)')",
"APPSYNC       = out.get('AppSyncEndpoint', '(not found)')",
"POOL_ID       = out.get('CognitoUserPoolId', '(not found)')",
"CLIENT_ID     = out.get('CognitoUserPoolWebClientId', '(not found)')",
"",
"print('Wholesale UI :', WHOLESALE_URL)",
"print('Wealth UI    :', WEALTH_URL)",
"print('AppSync      :', APPSYNC)",
"print('Cognito pool :', POOL_ID)",
))

cells.append(md(
"### The workshop logins",
"",
"The two protagonists are seeded as Cognito users by `scripts/setup_workshop_users.sh`",
"(run once after deploy). Both use the workshop password `password123`. The login id is",
"an email (the pool uses email-as-username); the display name (\"Dana Brooks\") comes from",
"the user's `name` attribute and flows to the app bar.",
"",
"| UI | Login | Password | Persona (cognito:group) |",
"|---|---|---|---|",
"| Wholesale | `dana.brooks@atlas.demo` | `password123` | `atlas-consumer-banker` |",
"| Wealth | `marcus.webb@atlas.demo` | `password123` | `atlas-wealth-advisor` |",
"",
"> If the users don't exist yet (fresh account), run from `use-case-applications/`:",
"> `POOL_ID=<CognitoUserPoolId> ./scripts/setup_workshop_users.sh`",
))

cells.append(code(
"# Confirm the two protagonists exist + are in the right groups (read-only check).",
"def user_groups(username):",
"    out = _aws(['cognito-idp', 'admin-list-groups-for-user', '--user-pool-id', POOL_ID,",
"                '--username', username, '--query', 'Groups[].GroupName', '--output', 'json'])",
"    return json.loads(out or '[]')",
"",
"for u in ['dana.brooks@atlas.demo', 'marcus.webb@atlas.demo']:",
"    try:",
"        print(f'{u:42} -> {user_groups(u)}')",
"    except Exception as e:",
"        print(f'{u:42} -> NOT FOUND  (run setup_workshop_users.sh)')",
))

# ── A tiny live-query helper for the verification cells ────────────────────
cells.append(md(
"### A helper to query the live API as a persona",
"",
"So the runbook can *show* the data behind each card (not just describe it), this helper",
"authenticates as a protagonist and runs a GraphQL query against the live AppSync endpoint",
"— exactly what the browser does. It is the same auth path (Cognito `USER_PASSWORD_AUTH`)",
"and the same persona scoping.",
))

cells.append(code(
"import urllib.request",
"",
"def login(username, password='password123'):",
"    out = _aws(['cognito-idp', 'initiate-auth', '--auth-flow', 'USER_PASSWORD_AUTH',",
"                '--client-id', CLIENT_ID,",
"                '--auth-parameters', f'USERNAME={username},PASSWORD={password}',",
"                '--query', 'AuthenticationResult.AccessToken', '--output', 'text'])",
"    return out.strip()",
"",
"def gql(token, query, variables=None):",
"    body = json.dumps({'query': query, 'variables': variables or {}}).encode()",
"    req = urllib.request.Request(APPSYNC, data=body, method='POST',",
"                                 headers={'Authorization': token, 'Content-Type': 'application/json'})",
"    with urllib.request.urlopen(req, timeout=40) as r:",
"        return json.loads(r.read())",
"",
"DANA = login('dana.brooks@atlas.demo')",
"MARCUS = login('marcus.webb@atlas.demo')",
"print('Authenticated as Dana (banker) and Marcus (advisor).')",
))

# ── The demo script ────────────────────────────────────────────────────────
cells.append(md(
"## The demo — Dana Brooks refers a customer to Marcus Webb, card by card",
"",
"Run the demo in a browser; use the cells here to *show the data behind each card* as you",
"narrate. The flow is six beats.",
))

# Beat 1
cells.append(md(
"### Beat 1 — Rachel's dashboard (\"My book\")",
"",
f"Open the **Wholesale UI** and sign in as **Dana Brooks** (the consumer banker).",
"",
"**What you see:** a grid of customer cards. Each shows the customer's name, id, a **signal",
"count**, and a **coverage tag** (`✓ <advisor>` if they already have a wealth advisor, or",
"**No advisor** if they're an open referral candidate). The dashboard leads with the",
"**signalled, uncovered** customers — Rachel's actionable book.",
"",
"**Teaching point — the two drivers.** The cards are GraphQL (`searchCustomers`, served by",
"the **direct-Neptune read path** — the resolver queries Neptune in-VPC over SigV4, no agent",
"in the loop); the actions in each customer's detail come from the Agent Registry.",
"",
"**Teaching point — what persona does, honestly.** The Cognito group decides *which fields a",
"caller may invoke* (access control — enforced today). It does **not** yet scope *which rows*",
"come back: the direct read path returns the same rows regardless of persona. Per-row Lake",
"Formation scoping is **roadmap, not enforced** — don't claim the book is row-filtered. The",
"full read-vs-action topology is in",
"[`04_graphql_federation.ipynb`](../phase-1-referral/04_graphql_federation.ipynb).",
"",
"**Teaching point — honest empties.** A customer with no derived signal shows no signal",
"tag; nothing is fabricated to fill the screen.",
))
cells.append(code(
"# The data behind Beat 1: the same query the dashboard runs (signalled-first, batched).",
"q = '''query { searchCustomers(query:\"\", limit:6) {",
"  label customerId",
"  wealthSignals { signalType }",
"  advisoryRelationships { isActive advisor { label } }",
"} }'''",
"rows = gql(DANA, q)['data']['searchCustomers']",
"for c in rows:",
"    cov = next((r for r in c['advisoryRelationships'] if r['isActive']), None)",
"    cov_s = f\"covered by {cov['advisor']['label']}\" if cov else 'NO ADVISOR (referral candidate)'",
"    print(f\"{c['label']:18} {len(c['wealthSignals'])} signal(s) · {cov_s}\")",
))

# Beat 2 — signals
cells.append(md(
"### Beat 2 — Ask the graph, and read a signal",
"",
"Click a suggested question (e.g. *\"Which customers have generated a wealth signal in the",
"last 90 days?\"*). Real rows return, with **\"Show the SPARQL that ran\"** — the template-",
"bounded query the nl-to-sparql-agent matched. It never free-generates SPARQL; that is the",
"SR 11-7 posture (the LLM is the *interface*, not the *reasoner*).",
"",
"Then open a signalled customer (e.g. **Riley Kim**). Her **Wealth-readiness signals** card",
"shows each signal with its **provenance line**: `validatedBy <shape> · derivedFrom <txn>`.",
"That provenance is the whole point — every signal traces to a SHACL shape that validated",
"it and the in-bank transaction that evidenced it.",
"",
"#### The wealth signal definitions (the v1.0 taxonomy)",
"",
"These are the five signal *types* defined in the ontology's SKOS scheme",
"(`atlas:WealthSignalTypeScheme`). Each is a **deterministic rule with a threshold your",
"risk team owns** — not an LLM judgement:",
"",
"| Signal | Definition | Threshold (default) |",
"|---|---|---|",
"| **Large Deposit Pattern** | A deposit-balance trajectory that crosses the large-deposit threshold within the observation window. | USD 250,000 |",
"| **Household Aggregation Signal** | The household's combined investable balance crosses the threshold while no individual member's balance does. | USD 1,000,000 |",
"| **Equity Event Signal** | A sale of a position in a connected brokerage account exceeding the threshold. | USD 100,000 |",
"| **Retirement Rollover Signal** | An inbound transfer from a recognised retirement-plan custodian exceeding the threshold. | USD 50,000 |",
"| **Business Sale Liquidity Signal** | A single deposit from a business account associated with the customer exceeding the threshold. | USD 500,000 |",
"",
"**Honest scope:** with the current synthetic data, only **Large Deposit Pattern** and",
"**Household Aggregation Signal** are actually derived (plus a *No Advisor Coverage* marker",
"that flags an uncovered signalled customer). The other three are defined in the taxonomy",
"but not derived — there is no equity / retirement / business-sale source data to derive",
"them from. The card never shows a signal type that wasn't derived from real data.",
"",
"**Why no \"signal strength\"?** There is no derived strength value in the data, so the card",
"deliberately omits one — showing a strength would be fabrication. Every shape validates",
"that a signal carries exactly one type (`atlas:WealthSignalTypeShape`) before it enters",
"the graph.",
))
cells.append(code(
"# The data behind Beat 2: a signalled customer's signals + provenance.",
"# (Pick the first signalled customer from Beat 1.)",
"signalled = next((c['customerId'] for c in rows if c['wealthSignals']), None)",
"uri = f'https://github.com/your-org/atlas/instance#customer-{signalled}-resolved'",
"q = '''query($u: ID!) { customer(uri:$u) {",
"  label",
"  wealthSignals { signalType provenance { validatedBy derivedFrom } }",
"} }'''",
"c = gql(DANA, q, {'u': uri})['data']['customer']",
"print(c['label'])",
"for s in c['wealthSignals']:",
"    p = s['provenance'] or {}",
"    print(f\"  {s['signalType']:28} validatedBy={p.get('validatedBy')}  derivedFrom={(p.get('derivedFrom') or '—')[-28:]}\")",
))

# Beat 2b — the 10 questions as a coherent story
cells.append(md(
"### Beat 2b — \"Ask the graph\": the ten questions tell one story",
"",
"The suggested-question chips are not a random grab-bag — they are the **Dana Brooks",
"referral journey**, in order. Each answers a real question a banker asks next, and each",
"is a template-bounded SPARQL query (the agent matches the question to a validated",
"template; it never free-generates). Walk them top to bottom and they build the case for a",
"referral, then close the loop with the audit trail.",
"",
"| # | Question | What it returns | Why it's next in the story |",
"|---|---|---|---|",
"| 1 | Which customers have generated a wealth signal…? | Every signalled customer + signal type | **The opportunity** — who to look at. |",
"| 2 | What specific transactions surfaced this customer? | The evidencing transactions (date, amount) | **The evidence** — provenance behind the signal. |",
"| 3 | What kinds of wealth signals are most common? | Signal-type counts across the book | **Size it** — which plays are biggest. |",
"| 4 | Which customers have no wealth advisor assigned? | Uncovered customers + balance | **Who's actionable** — uncovered = referable. |",
"| 5 | Which households have mixed wealth coverage? | Households w/ covered + uncovered members | **Household play** — bring the whole household. |",
"| 6 | Which household relationships does this customer have? | A customer's household members | **Map the household** you'll refer. |",
"| 7 | What accounts and balances does this customer hold? | Accounts + balances | **The financial picture** justifying wealth. |",
"| 8 | Who was this customer's advisor 18 months ago? | Coverage history (start/end) | **History** — temporal coverage, prior advisors. |",
"| 9 | Which routing decisions have human review? | Routing decisions + target advisor | **The decision record** — *empty until you route.* |",
"| 10 | What is the full audit trail…? | Routing → household → advisor → rationale | **End-to-end provenance** — *empty until you route.* |",
"",
"**Questions 9 and 10 are intentionally empty at the start of the demo** — there are no",
"routing decisions until a referral is routed. That is the teaching beat: *the audit trail",
"exists only because a governed, human-approved action happened.* After Beat 4 (route the",
"referral), come back and ask 9 and 10 — now they return the decision you just made, with",
"its PROV-O attribution. Run the cell to see all ten answered live (8 with rows now, 9–10",
"filling in after you route in Beat 4).",
))
cells.append(code(
"# Beat 2b: run every suggested question through the live agent, in story order.",
"questions = gql(DANA, 'query { suggestedQuestions }')['data']['suggestedQuestions']",
"for i, qtext in enumerate(questions, 1):",
"    r = gql(DANA, 'query($q: String!){ askGraph(question:$q){ status templateId result } }', {'q': qtext})['data']['askGraph']",
"    res = r.get('result')",
"    rown = len(json.loads(res)) if isinstance(res, str) and res.strip().startswith('[') else (len(res) if isinstance(res, list) else 0)",
"    tail = '  <- populates after you route a referral (Beat 4)' if rown == 0 else ''",
"    print(f\"{i:2}. {rown:>4} rows · {qtext[:52]}{tail}\")",
))

# Beat 3 — capabilities
cells.append(md(
"### Beat 3 — the Capabilities card (the second driver)",
"",
"On a customer/referral detail screen, the **Capabilities** card lists the actions",
"available — **read live from the Agent Registry**, not hardcoded. Each carries a tag for",
"*what kind* of action it is. This is the registry-first discovery thesis: register a new",
"agent and it appears here with no UI change.",
"",
"| Capability | Agent | Tag | What it means |",
"|---|---|---|---|",
"| Traverse household | household-traverser | **deterministic** | 1-hop household graph traversal — safe, repeatable. |",
"| Ask the graph | nl-to-sparql-agent | **deterministic** | NL → one of 10 validated SPARQL templates. Never free-generates. |",
"| Detect wealth signals | wealth-signal-detector | **deterministic** | Runs the SHACL-gated signal derivation. |",
"| Draft referral rationale | referral-rationale-drafter | **human-in-loop** | Bedrock drafts a rationale; a human must approve before it can drive routing. |",
"| Route to advisor | referral-orchestrator | **workflow** | Starts the 5-step Step Functions routing workflow. |",
"",
"The tags teach the **posture taxonomy**: *deterministic* (graph-grounded, reproducible),",
"*human-in-loop* (probabilistic output, gated by a person), *workflow* (a multi-step,",
"audited process). The dashed **\"Invoke from palette · next\"** row is honest about the",
"roadmap: the palette is a registry *display* today; click-to-invoke is future work.",
))
cells.append(code(
"# The data behind Beat 3: the live registry, persona-scoped.",
"q = '''query { capabilities(personaClaim:\"atlas-consumer-banker\") {",
"  displayName name capabilityTag posture } }'''",
"for c in gql(DANA, q)['data']['capabilities']:",
"    print(f\"{c['displayName']:26} {c['capabilityTag']:14} ({c['posture']:8}) · {c['name']}\")",
))

# Beat 4 — draft + route
cells.append(md(
"### Beat 4 — Draft the rationale, then Route the referral (human-in-the-loop)",
"",
"On the referral detail screen:",
"",
"1. **Generate draft** — invokes `referral-rationale-drafter` (Bedrock). The draft is a",
"   real, grounded narrative citing the customer's actual signals. It is badged",
"   **probabilistic — model-generated** and **requires human review**.",
"2. **Approve and route** — *this is the gate.* No path routes without a human clicking it.",
"   That click starts the `referral-orchestrator` Step Functions workflow:",
"   `select_advisor → validate (SHACL) → write_routing_decision → notify → audit`.",
"",
"**What happens, and the answer to \"does it go to Marcus?\":** yes. `select_advisor`",
"deterministically selects **Marcus Webb** (he is *the* wealth advisor). `write_routing_",
"decision` writes a `RoutingDecision` (PROV-O attributed, SHACL-validated against the",
"closed route set) **and** assigns Marcus to the customer via a new advisory relationship.",
"So the routed customer then shows as **covered by Marcus** on the Wealth side — the loop",
"closes. The UI shows a persistent **\"✓ Referral routed to Marcus Webb\"** confirmation.",
"",
"**Run the route below** (the cell does what the *Approve and route* button does).",
))
cells.append(code(
"# Beat 4: route Riley Kim's household to wealth (what 'Approve and route' does).",
"# Get the household uri first.",
"q = '''query($u: ID!) { customer(uri:$u) { label household { uri } } }'''",
"cust = gql(DANA, q, {'u': uri})['data']['customer']",
"hh = cust['household']['uri']",
"",
"m = '''mutation($h: ID!) { routeReferral(",
"  householdUri:$h, signalUris:[], approvedRationale:\"Demo: grounded in derived signals\",",
"  originatingBankerId:\"rachel-kim\") { routingDecision { selectedRoute targetAdvisorLabel } } }'''",
"res = gql(DANA, m, {'h': hh})['data']['routeReferral']['routingDecision']",
"print(f\"Routed: {res['selectedRoute']} -> {res['targetAdvisorLabel']}\")",
"print('The Step Functions workflow assigns the advisor; coverage lands in a few seconds.')",
))

# Beat 5 — wealth side
cells.append(md(
"### Beat 5 — Switch to Marcus: the referral arrived",
"",
"**Sign out** (top-right) on the Wholesale UI, then sign in as **Marcus Webb** on the Wealth",
"UI. The customer Rachel just routed now appears in his book flagged **\"New — routed to",
"you\"**. That banner is **LIVE, not a timer**: it shows precisely while the relationship was",
"created by the routing workflow (`routedByWorkflow`) **and** Marcus has not yet accepted it",
"(`takenOnAt` is null). Open the client to see the **Client 360**: advisory coverage, the",
"same wealth signals (now from the advisor's lens), the household, market themes (honest",
"empty — no theme corpus yet), and the single-turn conversational surface (`converse` →",
"`conversational-context-manager`; `priorTurns` is always 0 — AgentCore Memory is not wired,",
"surfaced honestly in the data).",
"",
"**This is the cross-persona handoff** — the whole point of the scenario. One graph, two",
"personas, a governed workflow moving a customer between them, every step provenance-",
"stamped. Run the cell to confirm the coverage landed.",
))
cells.append(code(
"import time",
"time.sleep(8)  # let the Step Functions workflow finish writing the assignment",
"q = '''query($u: ID!) { customer(uri:$u) {",
"  label advisoryRelationships { isActive advisor { label } coverageStartDate } } }'''",
"c = gql(MARCUS, q, {'u': uri})['data']['customer']",
"cov = [(r['advisor']['label'], r['coverageStartDate'][:10] if r['coverageStartDate'] else None)",
"       for r in c['advisoryRelationships'] if r['isActive']]",
"print(f\"{c['label']} is now covered by: {cov or 'NOBODY (workflow may still be running — re-run)'}\")",
))

# Beat 5.5 — take on the client (clears the banner)
cells.append(md(
"### Beat 5.5 — Take on the client (the banner clears, for real)",
"",
"On the routed client's **Client 360**, Marcus clicks **Take on client**. This is a real",
"accept transition, not a fake: it writes an `atlas:takenOnAt` timestamp to the routed",
"relationship via the `takeOnClient` mutation, and the **\"New — routed to you\"** banner",
"**clears** because its condition (`routedByWorkflow && !takenOnAt`) is no longer true.",
"",
"It is deliberately **additive**: taking on a client writes only `takenOnAt`. It does **not**",
"touch `isActive` or `coverageStartDate` — the coverage was already active at routing and",
"stays exactly as it was. So the banner is a genuine inbox-style \"new vs. accepted\" state on",
"top of unchanged coverage. (The mutation is idempotent — taking on twice is a no-op.)",
"",
"Run the cell to take Rachel on as Marcus (what the button does), then confirm the banner",
"condition has flipped.",
))
cells.append(code(
"# Beat 5.5: Marcus accepts the routed client (what 'Take on client' does).",
"m = '''mutation($u: ID!) { takeOnClient(customerUri:$u) { status takenOnAt message } }'''",
"r = gql(MARCUS, m, {'u': uri})['data']['takeOnClient']",
"print(f\"take-on: {r['status']} · takenOnAt={r['takenOnAt']}\")",
"",
"# Confirm the banner condition flipped: routedByWorkflow stays true, takenOnAt now set,",
"# so (routedByWorkflow && !takenOnAt) -> False -> banner clears. Coverage is unchanged.",
"q = '''query($u: ID!) { customer(uri:$u) {",
"  label advisoryRelationships { isActive routedByWorkflow takenOnAt } } }'''",
"c = gql(MARCUS, q, {'u': uri})['data']['customer']",
"for rel in c['advisoryRelationships']:",
"    if rel.get('routedByWorkflow'):",
"        shows = rel.get('routedByWorkflow') and not rel.get('takenOnAt')",
"        print(f\"routed rel · isActive={rel['isActive']} · takenOnAt={rel['takenOnAt']} · banner shows? {shows}\")",
))

# Beat 6 — reset
cells.append(md(
"### Beat 6 — Reset the demo (so you can run it again)",
"",
"Because this is a workshop demo shown repeatedly, the Wholesale dashboard has a **\"↺ Reset",
"demo\"** button. It removes **only** what the demo created — the advisory relationships",
"stamped `atlas:demoRoutingGenerated` (including the `takenOnAt` you wrote in Beat 5.5) and",
"the `RoutingDecision` nodes — and leaves all seed coverage untouched. Because the \"New —",
"routed to you\" banner is driven by those routed relationships, the reset also **clears the",
"banner** on the Wealth side. After a reset, the routed customer is an open referral",
"candidate again and the walkthrough is ready to repeat.",
"",
"Run the cell to reset (what the button does), then re-confirm the customer is uncovered.",
))
cells.append(code(
"m = '''mutation { resetDemoRoutings { advisoryRelationshipsRemoved routingDecisionsRemoved message } }'''",
"r = gql(DANA, m)['data']['resetDemoRoutings']",
"print(r['message'])",
"",
"# Confirm back to default.",
"q = '''query($u: ID!) { customer(uri:$u) { label advisoryRelationships { advisor { label } } } }'''",
"c = gql(DANA, q, {'u': uri})['data']['customer']",
"print(f\"{c['label']} coverage after reset: {c['advisoryRelationships'] or 'UNCOVERED (back to default)'}\")",
))

# ── Verification / troubleshooting ─────────────────────────────────────────
cells.append(md(
"## The verification — is the demo environment healthy?",
"",
"Run this before a live demo. It checks the three things that, if wrong, break the",
"walkthrough — each with a remediation note.",
))
cells.append(code(
"checks = []",
"# 1) Both protagonists exist.",
"try:",
"    g1 = user_groups('dana.brooks@atlas.demo')",
"    g2 = user_groups('marcus.webb@atlas.demo')",
"    checks.append(('Logins exist + grouped', g1 == ['atlas-consumer-banker'] and g2 == ['atlas-wealth-advisor']))",
"except Exception:",
"    checks.append(('Logins exist + grouped', False))",
"# 2) The dashboard returns signalled customers.",
"try:",
"    n = len([c for c in gql(DANA, 'query{ searchCustomers(query:\"\",limit:10){ wealthSignals{ signalType } } }')['data']['searchCustomers'] if c['wealthSignals']])",
"    checks.append(('Signalled customers present', n > 0))",
"except Exception:",
"    checks.append(('Signalled customers present', False))",
"# 3) Marcus has a seed book (covered clients).",
"try:",
"    mk = gql(MARCUS, 'query{ searchCustomers(query:\"\",limit:10){ advisoryRelationships{ isActive } } }')['data']['searchCustomers']",
"    checks.append(('Marcus has covered clients', any(any(r['isActive'] for r in c['advisoryRelationships']) for c in mk)))",
"except Exception:",
"    checks.append(('Marcus has covered clients', False))",
"",
"for name, ok in checks:",
"    print(('PASS' if ok else 'FAIL'), '·', name)",
"if not all(ok for _, ok in checks):",
"    print()",
"    print('Remediation:')",
"    print(' - Logins: run scripts/setup_workshop_users.sh with POOL_ID set.')",
"    print(' - No signalled customers / no Marcus book: re-run the WS1 promotion + WS2')",
"    print('   scripts/load_display_labels.py (gives names + Marcus his seed coverage).')",
"    print(' - Stale routings from a prior demo: run resetDemoRoutings (Beat 6).')",
))

# ── What just changed ──────────────────────────────────────────────────────
cells.append(md(
"## What just changed",
"",
"You now have a **repeatable, provenance-true demo** of the entire ATLAS stack: a Consumer",
"Banker surfaces a graph-derived wealth signal, reviews a model-drafted rationale, and",
"routes a customer through a governed, audited workflow to a Wealth Advisor — who sees the",
"customer arrive in his book. Every card on both screens is powered by the live semantic",
"layer (GraphQL + the Agent Registry), every signal carries its SHACL/PROV-O provenance,",
"and the human-in-the-loop gate and the closed routing set make it defensible under SR",
"11-7. The Reset button means you can tell the story as many times as the room needs.",
"",
"That is the workshop's thesis, made tangible: **the LLM is the interface; the graph is the",
"reasoner; governance is structural, not bolted on.**",
))

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out_path = Path(__file__).parent / "07_demo_runbook.ipynb"
out_path.write_text(json.dumps(nb, indent=1))
print(f"wrote {out_path}  ({len(cells)} cells)")
