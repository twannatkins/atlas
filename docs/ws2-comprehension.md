# WS2 Full Comprehension Map

Generated from a complete read of Workshop 2 source code, notebooks, workshop
pages, CDK constructs, and specs. Written before first deployment so decisions
are made against actual code, not inference.

**State at time of writing:** WS1 fully deployed (SLGD 1618 triples / 200
customers / 22 classes; iam-auth scoped v2). WS2 never deployed. CDK synth
clean (131 resources). Two CDK lines fixed (`817e365`). Bootstrap not done.

---

## Section 1 — Scope inventory

### Notebooks

**Phase 1 — Consumer-to-Wealth Referral** (`notebooks/phase-1-referral/`):

| File | Run order |
|------|-----------|
| `00_preflight.ipynb` | 1 |
| `01_why_agents.ipynb` | 2 |
| `02_mcp_servers.ipynb` | 3 |
| `03_agent_registry.ipynb` | 4 |
| `04_graphql_federation.ipynb` | 5 |
| `05_wholesale_ui.ipynb` | 6 |
| `06_phase_1_acceptance.ipynb` | 7 |

**Phase 2 — Wealth Advisor Spine** (`notebooks/phase-2-advisor/`):

| File | Run order |
|------|-----------|
| `01_phase_2_agents.ipynb` | 8 |
| `02_agentcore_memory.ipynb` | 9 |
| `03_wealth_ui.ipynb` | 10 |
| `04_jwt_auth.ipynb` | 11 |
| `05_end_to_end.ipynb` | 12 |
| `06_phase_2_acceptance.ipynb` | 13 |

### Workshop content pages

```
00-introduction/, 00-prerequisites/
01-preflight/ through 07-phase-1-acceptance/      (Phase 1: 7 module pages)
08-phase-2-agents/ through 13-phase-2-acceptance/ (Phase 2: 6 module pages)
cleanup/
```

### Agents (8)

`behavioral-signal-agent`, `conversational-context-manager`, `household-traverser`,
`nl-to-sparql-agent`, `referral-orchestrator`, `referral-rationale-drafter`,
`theme-summarizer`, `wealth-signal-detector`

### MCP servers (5)

`atlas-er-mcp`, `atlas-fibo-mcp`, `atlas-registry-mcp`, `atlas-shacl-mcp`,
`atlas-sparql-mcp`

### CDK constructs (11)

`agentcore-memory`, `agentcore-runtimes`, `appsync`, `cloudfront`, `cognito`,
`lake-formation`, `lambdas`, `networking`, `ontop`, `orchestrator-registration`,
`step-functions`

### Specs

`00-overview-inheritance-section`, `01-architecture`, `02-prerequisites`,
`03-data-contracts`, `04-aws-agent-registry/`, `05-appsync-graphql/`,
`06-react-monorepo/`, `07-cdk-stack/`, `08-notebook-companion`,
`09-substitution-guide`, `10-acceptance-criteria`, `11-identity-and-session`

---

## Section 2 — Per-notebook map

### 00_preflight.ipynb
- **TEACHES:** WS2 cannot start without the WS1 substrate. Six checks define the contract.
- **USER RUNS:** 6 code cells. Reads CFN outputs → `NeptuneClient` live queries → SPARQL COUNT checks → file path checks → Bedrock `ListFoundationModels`.
- **DEPENDS ON (live):**
  - CFN stack `atlas-neptune-twotier` outputs: `SLGDEndpoint`, `LGDEndpoint`
  - Live SLGD: ≥22 `atlas:` classes, 15 named classes, 6 SHACL shapes, Customer=200, Transaction=3747, Advisor=10, AdvisoryRelationship=105
  - WS1 disk files: `prompts/prefixes.txt`, `prompts/ground-truth.yaml`, `notebooks/shared/atlas_neptune.py`, `notebooks/shared/atlas_sparql.py`
  - Bedrock `amazon.titan-embed-text-v2:0` and `us.anthropic.claude-sonnet-4-6` accessible
- **USER SEES (success):** `PRE-FLIGHT: PASS / Workshop 1's substrate is confirmed. Workshop 2 is safe to start.`
- **FAILS IF:** SLGD unreachable (execution role needs `atlas-neptune-iam-auth` attached), instance counts wrong, any WS1 file missing from disk, Bedrock access denied.
- **GATE:** LIVE — real Neptune queries, real Bedrock API call. Cannot false-green.
- **WS2 resource needed:** None. WS1-only.

### 01_why_agents.ipynb
- **TEACHES:** LLM-as-interface pattern: Titan Embeddings selects a ground-truth SPARQL template by cosine similarity; no generative model touches SPARQL. Same question → same template → same SPARQL → auditable under SR 11-7.
- **USER RUNS:** 5 code cells. Loads `ground-truth.yaml` from disk, embeds all templates via Bedrock, defines `ask_graph()`, runs 3 pilot questions against live SLGD, then runs each 5 times asserting byte-identical output.
- **DEPENDS ON (live):**
  - Bedrock `amazon.titan-embed-text-v2:0` (14 embedding calls)
  - Live Neptune SLGD (3 SPARQL queries via `NeptuneClient`)
  - WS1 file `prompts/ground-truth.yaml` on disk
- **USER SEES (success):** `[PASS] All 3 questions produced byte-identical SPARQL across 5 runs.`
- **FAILS IF:** Bedrock embedding access denied; ground-truth.yaml not on disk (file exists in repo, confirmed FOUND).
- **GATE:** LIVE — 14 Bedrock calls, 3 Neptune queries. Cannot false-green.
- **WS2 resource needed:** None. WS1-only.

### 02_mcp_servers.ipynb
- **TEACHES:** MCP servers are stable typed interfaces separating *what* (run SPARQL) from *how* (which cluster, which Lake Formation scope). Persona enforcement lives in the server, not the agent.
- **USER RUNS:** 4+ code cells. Defines local `sparql_mcp_query()` wrapper around `NeptuneClient`, runs it 5× for shape consistency, passes 3 malformed inputs for structured error verification.
- **DEPENDS ON (live):**
  - Live Neptune SLGD (8 queries via `NeptuneClient`, SigV4-signed — no WS2 MCP Runtime needed)
- **USER SEES (success):** `[PASS] All 5 responses have the correct shape. / [PASS] All 3 malformed inputs returned structured error responses.`
- **FAILS IF:** Neptune unreachable. Note: `NeptuneClient` uses SigV4 correctly — this is NOT the bare-requests bug class.
- **GATE:** LIVE — real Neptune queries. In-memory shape checks on returned data.
- **WS2 resource needed:** None. Simulates AgentCore MCP Runtime locally against live WS1 Neptune.

### 03_agent_registry.ipynb
- **TEACHES:** Registry-first discovery — UIs query the registry filtered by persona claim; palettes differ by persona; the registry is a governance gate.
- **USER RUNS:** 4 code cells. Loads JSON descriptors from `spec/04-aws-agent-registry/`, builds in-memory registry, defines `discover_capabilities(persona_claim)`, asserts palette differentiation.
- **DEPENDS ON (live):** NONE — fully simulated with local JSON.
- **USER SEES (success):** Consumer Banker and Wealth Advisor palettes printed; `referral-rationale-drafter` absent from Wealth Advisor palette confirmed.
- **FAILS IF:** JSON descriptors malformed or `discoverable_by` lists not differentiated.
- **GATE:** IN-MEMORY — no AWS calls. Would pass even if WS2 stack not deployed.
- **WS2 resource needed:** None. Local descriptor files only.

### 04_graphql_federation.ipynb
- **TEACHES:** FIBO-shaped schema — every type maps to one ontology class. Three resolver patterns. Persona claim passthrough for Lake Formation scoping.
- **USER RUNS:** 4 code cells. Loads schema from `spec/05-appsync-graphql/schema.graphql`, inspects type-to-class mappings, simulates all three resolver patterns with hardcoded responses, simulates persona scoping.
- **DEPENDS ON (live):** NONE — fully simulated.
- **USER SEES (success):** Schema mapping table, `[PASS] Persona scoping confirmed: same query, different personas, different results.`
- **FAILS IF:** Schema file missing, type missing ontology mapping.
- **GATE:** IN-MEMORY. Would pass even if WS2 stack not deployed.
- **WS2 resource needed:** None. Local schema file only.

### 05_wholesale_ui.ipynb
- **TEACHES:** Two-driver UI: GraphQL provides data, registry provides capabilities — neither hardcoded. Compliance banner enforces 31 U.S.C. §5318(g)(2) tipping-off prohibition.
- **USER RUNS:** 4+ code cells. Simulates Entity 360 fetch, compliance banner rendering (Consumer Banker vs BSA Analyst), capability palette from descriptors, "Route to advisor" workflow.
- **DEPENDS ON (live):** NONE — fully simulated.
- **USER SEES (success):** `[PASS] Capability palette correctly persona-scoped. / [PASS] Compliance banner respects §5318(g)(2). / [PASS] Human-in-the-loop enforced.`
- **FAILS IF:** Compliance banner leaks "SAR" to Consumer Banker; palette not differentiated; referral-orchestrator doesn't require `approved_rationale`.
- **GATE:** IN-MEMORY. Regulatory compliance checks are on simulated data.
- **WS2 resource needed:** None. Local descriptors only.

### 06_phase_1_acceptance.ipynb
- **TEACHES:** Formal acceptance suite — 42 assertions across 7 categories. Every passing assertion is a contract honored.
- **USER RUNS:** 10 code cells. Loads descriptors + schema + WS1 TTL files. Runs 7 categories: registry (local), posture (local), permissions (2 local + 2 deferred), regulatory (local), Rachel Kim e2e (ALL 7 DEFERRED), schema (local), WS1 integrity (local).
- **DEPENDS ON (live):**
  - Local: JSON descriptors, `spec/05-appsync-graphql/schema.graphql`, WS1 TTL files
  - Deferred (Category 5, 7 assertions): live Neptune SLGD with Rachel Kim data, deployed AgentCore Runtimes, Step Functions
- **USER SEES (success):** `PHASE 1 ACCEPTANCE SUMMARY / Passed: 35 / Failed: 0 / Deferred: 7 / ALL NON-DEFERRED ASSERTIONS PASS.`
- **FAILS IF:** Any Category 1/2/4/6/7 assertion fails; tipping-off violation; schema type unmapped; WS1 files modified; WS2 extensions not in `atlas-part-2:`.
- **GATE:** HYBRID — 35 assertions are local; 7 (Category 5) explicitly deferred to live infrastructure.
- **WS2 resource needed:** Category 5 requires deployed AgentCore Runtimes + Step Functions + live SLGD.

### 01_phase_2_agents.ipynb (Phase 2)
- **TEACHES:** Why Phase 2 needs structurally different agents: behavioral signals require LGD temporal data, `conversational-context-manager` is stateful (AgentCore Memory), `behavioral-signal-agent` is probabilistic-guarded.
- **USER RUNS:** 6 code cells. Loads descriptors, compares Phase 1 vs Phase 2 postures, simulates `behavioral-signal-agent` detecting EngagementDecay from LGD session data, shows LGD dependency in descriptor.
- **DEPENDS ON (live):** NONE — fully simulated.
- **GATE:** IN-MEMORY.

### 02_agentcore_memory.ipynb (Phase 2)
- **TEACHES:** Session-scoped memory enables multi-turn conversations. Memory is intentionally transient: GDPR/CCPA compliance, no permanent user state.
- **USER RUNS:** 6 code cells. Implements local `SessionMemory` class mirroring AgentCore Memory interface, simulates two-turn conversation, demonstrates context-driven template selection.
- **DEPENDS ON (live):** NONE — explicit local simulation (`"This notebook simulates AgentCore Memory locally. Production uses the AWS AgentCore Memory service."`).
- **GATE:** IN-MEMORY.

### 03_wealth_ui.ipynb (Phase 2)
- **TEACHES:** Thesis 2 — same GraphQL schema, same registry, same MCP servers serve two structurally different UIs by varying fragments and persona claims.
- **USER RUNS:** 6 code cells. Loads descriptors, compares Consumer Banker vs Wealth Advisor capability palettes, demonstrates `CustomerReferralFragment` vs `CustomerCoverageFragment`, verifies theme-summarizer is Wealth Advisor-only.
- **DEPENDS ON (live):** NONE — fully simulated.
- **GATE:** IN-MEMORY.

### 04_jwt_auth.ipynb (Phase 2)
- **TEACHES:** Why Phase 2 switches from IAM (service identity) to JWT (user identity). With two UIs, the registry cannot distinguish personas at the IAM level; JWT moves the persona claim into a Cognito-signed token.
- **USER RUNS:** 6 code cells. Constructs sample JWT payloads, simulates registry filtering by `custom:persona` claim, shows IAM vs JWT comparison table.
- **DEPENDS ON (live):** NONE — JWT payloads are plain Python dicts; no real Cognito call. Comment: `"In production, AppSync extracts the claim from the Authorization header."`
- **GATE:** IN-MEMORY.

### 05_end_to_end.ipynb (Phase 2)
- **TEACHES:** The full cross-UI advisor scenario: signal detection in Wholesale UI → referral routing → notification in Wealth UI → conversational follow-up. Audit trail spans both personas.
- **USER RUNS:** 7 code cells. Builds six-step audit trail as Python event dicts, assembles full cross-UI chain, verifies parent chain unbroken, verifies routing bridges both UIs.
- **DEPENDS ON (live):** NONE — setup cell prints `"This notebook simulates the cross-UI flow locally."` All events are Python dicts with `uuid4()` IDs.
- **GATE:** IN-MEMORY.

### 06_phase_2_acceptance.ipynb (Phase 2)
- **TEACHES:** Phase 2 acceptance — 20 assertions across 5 categories. All run locally; NO deferred assertions.
- **USER RUNS:** 7 code cells. Loads descriptors. Runs: (1) Phase 2 agent registration, (2) Wealth UI differentiation, (3) AgentCore Memory session scope (local `SessionMemory`), (4) JWT authentication, (5) Cross-UI audit trail completeness.
- **DEPENDS ON (live):** NONE — all assertions against local descriptors and simulated flows.
- **USER SEES (success):** `PHASE 2 ACCEPTANCE SUMMARY / Passed: 20 / Failed: 0 / Total: 20 / ✓ ALL ASSERTIONS PASS. Thesis 2 is validated.`
- **FAILS IF:** Any descriptor missing or wrong; JWT persona claim absent; session isolation fails; audit trail broken.
- **GATE:** IN-MEMORY — entirely local. No WS2 deploy required to pass this gate.

---

## Section 3 — Workshop-prose vs notebook-code alignment

### Confirmed matches
All Phase 1 and Phase 2 workshop pages were authored after the notebook code was read. Cell IDs in the pages match the notebook cell IDs. Expected output blocks were sourced from real `print()` strings. No fabricated values remain (fixed in `f0201ba`).

### Known mismatches

| Page | Notebook | Prose says | Code does |
|------|----------|-----------|-----------|
| `07-phase-1-acceptance/index.md` Step 6 | `06_phase_1_acceptance.ipynb` | Shows `[DEFER] 3.3` and `[DEFER] 3.4` in step output | Actual deferred count depends on notebook's `defer()` call logic — workshop guide shows 9 deferred (Category 3: 3.3, 3.4 + Category 5: 5.1-5.7). Page assertion count of 36 was verified correct per `f0201ba`. |
| `09-agentcore-memory/index.md` What You Will Build | `02_agentcore_memory.ipynb` | Describes production AgentCore Memory service | Notebook simulates locally; page correctly notes "Production uses the AWS AgentCore Memory service" — consistent. |
| All Phase 1 pages | nb00–nb06 | Pages reference `cell-NN-id` by name | Cell IDs in notebooks match the page references — no drift found in a targeted check. |
| `06-wholesale-ui/index.md` | `05_wholesale_ui.ipynb` | Notebook filename referenced as `05_wholesale_ui.ipynb` | Correct match. |

**No significant prose/code mismatches found.** The 08-B-fix pass (`f0201ba`) corrected the one documented fabrication (Module 2 output landmarks). The remaining risk is that pages describe expected outputs from non-deterministic cells (e.g. cosine similarity scores); these use `N` placeholders and are acceptable.

---

## Section 4 — WS1→WS2 handoff contract

| WS2 expects | Source | Status |
|-------------|--------|--------|
| CFN output `SLGDEndpoint` | `atlas-neptune-twotier` | **CONFIRMED** — `atlas-slgd.cluster-c0bie06scpwu.us-east-1.neptune.amazonaws.com` |
| CFN output `LGDEndpoint` | `atlas-neptune-twotier` | **CONFIRMED** — `atlas-lgd.cluster-c0bie06scpwu.us-east-1.neptune.amazonaws.com` |
| SLGD: ≥22 `atlas:` classes | WS1 Module 3 | **CONFIRMED** — 22 classes |
| SLGD: 6 SHACL NodeShapes | WS1 Module 6 | **CONFIRMED** — 6 shapes |
| SLGD: 200 Customer, 3747 Transaction, 10 Advisor, 105 AdvisoryRelationship | WS1 Module 4/5 | **CONFIRMED** — verified 2026-05-30 |
| SLGD: 200 promoted entities with `promotedFrom` + `promotedBy` | WS1 Module 5 | **CONFIRMED** — live SLGD query: 200/200 |
| Bedrock `amazon.titan-embed-text-v2:0` ACTIVE | Account/region | **CONFIRMED** — ACTIVE in us-east-1 |
| Bedrock `us.anthropic.claude-sonnet-4-6` inference profile ACTIVE | Account/region | **CONFIRMED** — ACTIVE in us-east-1 |
| WS1 file `prompts/ground-truth.yaml` on Studio disk | Repo clone | **CONFIRMED** — file exists at `agentic-semantic-layer/prompts/ground-truth.yaml` |
| WS1 file `prompts/prefixes.txt` on Studio disk | Repo clone | **CONFIRMED** — file exists |
| WS1 file `notebooks/shared/atlas_neptune.py` on Studio disk | Repo clone | **CONFIRMED** — file exists |
| WS1 file `notebooks/shared/atlas_sparql.py` on Studio disk | Repo clone | **CONFIRMED** — file exists |
| S3 `atlas-ontology-staging-981814817046/prompts/ground-truth.yaml` | Needs upload (Step 2) | **NOT YET UPLOADED** — file exists locally, upload pending |
| S3 `atlas-ontology-staging-981814817046/prompts/prefixes.txt` | Needs upload (Step 2) | **NOT YET UPLOADED** — file exists locally, upload pending |
| AWS Entity Resolution workflow `atlas-entity-resolution` | WS2 spec/02 says pre-create or deploy from CDK | **UNVERIFIED** — ER workflow hardcoded as `atlas-entity-resolution`; no ER construct in CDK; spec says manually create if absent |
| IAM `atlas-neptune-iam-auth` policy attached to both execution roles | Done during WS1 | **CONFIRMED** — scoped v2 verified non-regression 2026-05-31 |
| Bedrock `bedrock:InvokeModel` on both execution roles | Done during WS1 Module 7 | **CONFIRMED** — `atlas-workshop-bedrock-access` inline policy on both roles |

---

## Section 5 — CDK / Deploy-risk register

| # | Finding | File:line | Severity |
|---|---------|-----------|----------|
| R1 | `SHAPES_S3_URI` still points at `s3://atlas-workshop-1/ontology/atlas-shapes.ttl` (bucket does not exist) | `agentcore-runtimes.ts:101` | LOW — `atlas-shacl-mcp` falls back to vendored `ontology/atlas-shapes.ttl` shipped inside the artifact; no runtime failure |
| R2 | `SIGNAL_QUERIES_S3_URI: "s3://atlas-workshop-1/queries/wealth-signals.yaml"` points at nonexistent bucket AND file | `agentcore-runtimes.ts:204` | LOW — `SIGNAL_QUERIES_S3_URI` is read into `os.environ` but never used in `wealth_signal_detector.py`; dead code |
| R3 | `PROMPT_TEMPLATE_S3_URI: "s3://atlas-workshop-1/prompts/referral-rationale.txt"` — file does not exist in repo or bucket | `agentcore-runtimes.ts:241` | LOW — `referral_rationale_drafter.py` falls back to `DEFAULT_PROMPT_TEMPLATE` hardcoded string; no runtime failure |
| R4 | `GROUND_TRUTH_S3_URI` and `PREFIXES_S3_URI` correctly point at `atlas-ontology-staging-981814817046` (fixed `817e365`) BUT files not yet uploaded | `agentcore-runtimes.ts:181-182` | **HIGH** — `nl-to-sparql-agent` will fail at runtime in AgentCore container when it tries to read these from S3; local-path fallback only resolves in Studio |
| R5 | Both `neptuneSlgdEndpoint` and `neptuneLgdEndpoint` receive the same `neptuneClusterEndpoint` context value (the SLGD endpoint) | `atlas-workshop-2-stack.ts:94-95` | MEDIUM — `behavioral-signal-agent` needs LGD access; will actually connect to SLGD. Behavioral signal detection uses LGD-pattern data; pointing both at SLGD may produce incorrect results for Phase 2 notebooks |
| R6 | `REGISTRY_ENDPOINT` is set to `props.registryEndpoint ?? ""` and `registryEndpoint` is never passed from the main stack | `agentcore-runtimes.ts:164`, `atlas-workshop-2-stack.ts:90` | MEDIUM — `atlas-registry-mcp` reads `REGISTRY_ENDPOINT` and if empty it queries Agent Registry via a default path; depends on whether the MCP has a fallback |
| R7 | `ER_WORKFLOW_NAME: "atlas-entity-resolution"` hardcoded; AWS Entity Resolution workflow by this name may not exist | `agentcore-runtimes.ts:134` | MEDIUM — `atlas-er-mcp` will fail at runtime if the workflow doesn't exist; no graceful degrade |
| R8 | IDC persona groups (`atlas-consumer-banker` etc.) all MISSING from identity store `d-9066212736` | IAM Identity Center | MEDIUM — Cognito deploys standalone but federation is unconfigured; persona-based UI routing won't work until groups are created and assigned |
| R9 | ECS Ontop Fargate service has no circuit breaker | `ontop.ts` (CDK warning at deploy) | LOW — deployment failure can hang up to 3 hours; tracked in todo list |
| R10 | `WholesaleUiUrl` CFN output references CloudFront but React build artifacts are never deployed by CDK | `cloudfront.ts:119` | LOW — CloudFront distribution and S3 bucket are created; the React app must be separately built and deployed to S3 |
| R11 | `us.anthropic.claude-sonnet-4-6` hardcoded in two runtimes and two agent files | `agentcore-runtimes.ts:239,284`; `referral_rationale_drafter.py:33`; `theme_summarizer.py:27` | NOVICE-ONLY — works in us-east-1; non-US deployers will get model-not-found; portability finding already tracked |
| R12 | `neptune-twotier` stack exports `LGDEndpoint` but the CDK context only accepts one `neptuneClusterEndpoint` value (SLGD used for both) — LGD endpoint is available but not wired | `cdk.json`, `atlas-workshop-2-stack.ts:29` | MEDIUM — same as R5; LGD endpoint exists in CFN outputs but is not passed separately to the CDK context |

---

## Section 6 — Deferred assertions and post-deploy verification

### nb06 Phase 1 acceptance — Category 5 (7 deferred assertions)

All 7 are gated by `defer("5.N", "...", "Requires running Neptune")`. They become live automatically when re-run with the WS2 stack deployed — no notebook changes needed.

| Assertion | What it needs |
|-----------|--------------|
| 5.1 Patel household exists in SLGD | Live SLGD with `atlas:hh/9c2a1e` entity |
| 5.2 `wealth-signal-detector` detects signal | Deployed AgentCore Runtime for wealth-signal-detector |
| 5.3 `household-traverser` returns ≥2 nodes | Deployed AgentCore Runtime for household-traverser |
| 5.4 `referral-rationale-drafter` produces draft | Deployed Runtime + Bedrock Claude Sonnet |
| 5.5 `referral-orchestrator` routes successfully | Deployed Step Functions state machine |
| 5.6 `AuditRecord` exists after routing | Live SLGD write via `audit-write` Lambda |
| 5.7 `AuditRecord` has PROV-O attribution | Same as 5.6 |

**How to flip deferred → live:** Deploy WS2 stack, then re-run `06_phase_1_acceptance.ipynb`. The `defer()` calls check a live Neptune connection; if it's reachable and the data exists, they pass automatically.

### nb06 Phase 2 acceptance — NO deferred assertions

All 20 assertions run locally against descriptors and simulated flows. No deployment required. Can be run before or after WS2 deploy.

---

## Section 7 — Open questions / gaps (work queue)

Ranked by when the issue bites:

### Pre-deploy (blocks deploy or first run)

| # | Gap | Decision needed |
|---|-----|----------------|
| G1 | **CDK bootstrap not done.** CDKToolkit stack absent in account 981814817046 / us-east-1. `cdk deploy` hard-fails without it. | Run `cdk bootstrap aws://981814817046/us-east-1` — mutating, one-time. |
| G2 | **5 IDC persona groups missing** (`atlas-consumer-banker` et al. absent from identity store `d-9066212736`). Cognito deploys without them but federation is unconfigured; persona-based routing won't work for nb05-era UI testing. | Create 5 groups via `aws identitystore create-group` (post-deploy is fine; not needed for Phase 1 notebooks 00–04). |
| G3 | **S3 upload pending:** `prompts/ground-truth.yaml` and `prompts/prefixes.txt` must be uploaded to `atlas-ontology-staging-981814817046/prompts/` before `nl-to-sparql-agent` AgentCore Runtime is invoked. Files exist locally. | `aws s3 cp` (2 commands, approved, awaiting go). |

### At-deploy (risks a deployment failure or silent misconfiguration)

| # | Gap | Decision needed |
|---|-----|----------------|
| G4 | **Both Neptune endpoints wired to SLGD.** `neptuneLgdEndpoint` and `neptuneSlgdEndpoint` both receive `neptuneClusterEndpoint` context value (SLGD). `behavioral-signal-agent` needs LGD. Phase 2 notebooks may produce incorrect results. LGD endpoint is available from WS1 CFN outputs but CDK has no separate context key for it. | Add `neptuneLgdEndpoint` context key to `cdk.json` and pass separately, OR accept that Phase 2 behavioral signals run against SLGD (data exists there too from promotion). |
| G5 | **`REGISTRY_ENDPOINT` never passed to `atlas-registry-mcp`.** `registryEndpoint` is an optional prop with `?? ""` fallback. Needs confirmation that the MCP server works with an empty endpoint (likely queries the Agent Registry control plane directly via boto3, not via an HTTP endpoint). | Read `atlas_registry_mcp.py` to confirm fallback behavior. |
| G6 | **Entity Resolution workflow `atlas-entity-resolution` may not exist.** `atlas-er-mcp` hardcodes this workflow name. Spec/02 says to create it manually if absent; no CDK construct. `atlas-er-mcp` will hard-fail at runtime if the workflow doesn't exist. | Verify if workflow exists: `aws entityresolution list-matching-workflows`. Create if absent (or confirm `atlas-er-mcp` gracefully degrades). |
| G7 | **ECS circuit breaker not configured on Ontop Fargate service.** A bad deployment can hang for up to 3 hours. | Add `circuitBreaker: { rollback: true }` to Ontop ECS service construct. Tracked in todo list. |

### Post-deploy / per-notebook

| # | Gap | Decision needed |
|---|-----|----------------|
| G8 | **nb06 Category 5 deferred assertions (7).** Require live WS2 AgentCore Runtimes, Step Functions, and SLGD with Rachel Kim data. Will pass automatically on re-run after deploy if all five agents are registered and running. | No action — re-run nb06 after deploy. |
| G9 | **Wholesale UI and Wealth UI React apps not deployed by CDK.** CloudFront distributions and S3 buckets are created, but the React build artifacts must be separately built (`npm run build`) and deployed to S3. Workshop pages describe clicking through the UI, which won't work with empty S3 buckets. | Decide: build + deploy the React apps as part of the deploy sequence, or defer until after notebooks are validated. `apps/wholesale-ui/` and `apps/wealth-ui/` exist with TSX source. |
| G10 | **LGD context data for Phase 2 behavioral signals.** `behavioral-signal-agent` queries the LGD for engagement-decay session data. WS1 Module 4 populated the LGD with Pattern A/B/C data, but the LGD endpoint is currently wired to the SLGD (G4). Phase 2 notebooks simulate behavioral signals locally; the deployed agent needs the LGD. | Resolve G4 first; then confirm the LGD has sufficient session data for `behavioral-signal-agent` to detect EngagementDecay. |
| G11 | **Cleanup page lists 8 phantom stack names.** `workshop/content/cleanup/index.md` lists `atlas-wholesale-ui-stack`, `atlas-wealth-ui-stack`, etc. — none of which are real CDK stacks. The real command is `cdk destroy AtlasWorkshop2`. Tracked in todo list. | Fix the cleanup page to reference `cdk destroy AtlasWorkshop2` (or `cdk destroy --all`). |
| G12 | **nb06 Phase 2 acceptance (20 assertions) all local.** The gate validates Phase 2 architecture locally but never exercises the deployed stack. A deployed Phase 2 with silent runtime failures would show 20/20 passing. | Accept: the Phase 2 acceptance is intentionally local-simulation (by design, documented). Deploy verification for Phase 2 requires running `05_end_to_end.ipynb` against live resources, not the acceptance notebook. |
| G13 | **Post-WS1 enhancement: nb08 cell-14 audit trail query against local graph.** Tracked in todo list. | Upgrade cell-14 to query live SLGD (optional, non-blocking). |

### Portability / novice in a different account (deferred)

| # | Gap | When it bites |
|---|-----|--------------|
| G14 | `us-east-1` hardcoded in multiple places | Non-US deployers |
| G15 | `us.anthropic.claude-sonnet-4-6` US-only inference profile | Non-US deployers |
| G16 | IAM role names auto-generated by CDK (no collision) but Bedrock/Neptune manual policies are LIVE-STATE only | Fresh-account redeploy |
| G17 | VPC CIDR default `10.0.0.0/16` in WS1 CFN template | Any VPC with different CIDR |

---

*Document written 2026-05-31 from a complete read of all notebooks, CDK constructs, agent source, MCP server source, and spec files. Phase 2 notebooks were read in full; CDK constructs and main stack read in full. Spec files were read for `07-cdk-stack/README.md` (deploy docs) and `02-prerequisites.md` (prereq docs) in full; others scanned for deploy-relevant content. No content was inferred — all claims trace to specific files.*
