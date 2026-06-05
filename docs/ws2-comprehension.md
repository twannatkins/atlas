# WS2 Full Comprehension — Pass 1 of 2 (Phase 1 + Foundation)

Complete read of all Phase 1 notebooks, their workshop pages, all CDK constructs,
the main stack, and deploy-relevant specs. Written before first deployment.

**State at time of writing:**
- WS1 fully deployed: SLGD 1618 triples / 200 promoted customers / 22 classes / 6 shapes
- `atlas-neptune-iam-auth` scoped v2, both execution roles patched
- WS2 CDK synth clean (131 resources), `817e365` fix applied
- WS2 never deployed — CDKToolkit stack absent

---

## Section 1 — Scope inventory

### Notebooks

**Phase 1 — Consumer-to-Wealth Referral** (`notebooks/phase-1-referral/`):

| Run order | File |
|-----------|------|
| 1 | `00_preflight.ipynb` |
| 2 | `01_why_agents.ipynb` |
| 3 | `02_mcp_servers.ipynb` |
| 4 | `03_agent_registry.ipynb` |
| 5 | `04_graphql_federation.ipynb` |
| 6 | `05_wealth_signals.ipynb` |
| 7 | `06_wholesale_ui.ipynb` |
| 8 | `07_phase_1_acceptance.ipynb` |

**Phase 2 — Wealth Advisor Spine** (`notebooks/phase-2-advisor/`) — listed, NOT read this pass:

| Run order | File |
|-----------|------|
| 8 | `01_phase_2_agents.ipynb` |
| 9 | `02_agentcore_memory.ipynb` |
| 10 | `03_wealth_ui.ipynb` |
| 11 | `04_jwt_auth.ipynb` |
| 12 | `05_end_to_end.ipynb` |
| 13 | `06_phase_2_acceptance.ipynb` |

### Workshop content pages (`workshop/content/`)

```
00-introduction/     00-prerequisites/
01-preflight/        02-why-agents/       03-mcp-servers/
04-agent-registry/   05-graphql-federation/  06-wholesale-ui/
07-phase-1-acceptance/
08-phase-2-agents/   09-agentcore-memory/  10-wealth-ui/
11-jwt-auth/         12-end-to-end/        13-phase-2-acceptance/
cleanup/
```

### Agents (8)

`behavioral-signal-agent`, `conversational-context-manager`, `household-traverser`,
`nl-to-sparql-agent`, `referral-orchestrator`, `referral-rationale-drafter`,
`theme-summarizer`, `wealth-signal-detector`

### MCP servers (5)

`atlas-er-mcp`, `atlas-fibo-mcp`, `atlas-registry-mcp`, `atlas-shacl-mcp`,
`atlas-sparql-mcp`

### CDK app (`cdk/lib/`)

Main stack: `atlas-workshop-2-stack.ts`

Constructs:
`agentcore-memory.ts`, `agentcore-runtimes.ts`, `appsync.ts`, `cloudfront.ts`,
`cognito.ts`, `lake-formation.ts`, `lambdas.ts`, `networking.ts`, `ontop.ts`,
`orchestrator-registration.ts`, `step-functions.ts`

### Specs (`spec/`)

`00-overview-inheritance-section.md`, `01-architecture.md`, `02-prerequisites.md`,
`03-data-contracts.md`, `04-aws-agent-registry/`, `05-appsync-graphql/`,
`06-react-monorepo/`, `07-cdk-stack/`, `08-notebook-companion.md`,
`09-substitution-guide.md`, `10-acceptance-criteria.md`, `11-identity-and-session.md`

---

## Section 2 — Per-notebook map (Phase 1 only)

### 00_preflight.ipynb

- **TEACHES:** WS2 cannot start without the WS1 substrate. Six checks define the data contract.
- **USER RUNS:** 9 cells — setup, CFN read, 4× Neptune SPARQL COUNT/SELECT, file-path check, Bedrock list_foundation_models, gate summary.
- **DEPENDS-ON-LIVE:**
  - CFN `atlas-neptune-twotier` outputs: `SLGDEndpoint`, `LGDEndpoint` (WS1)
  - Live SLGD: ≥22 `atlas:` classes including 15 named; 6 SHACL shapes; Customer=200, Transaction=3747, Advisor=10, AdvisoryRelationship=105 (WS1)
  - WS1 disk files: `prompts/prefixes.txt`, `prompts/ground-truth.yaml`, `notebooks/shared/atlas_neptune.py`, `notebooks/shared/atlas_sparql.py`
  - Bedrock `amazon.titan-embed-text-v2:0` and `us.anthropic.claude-sonnet-4-6` accessible
- **USER SEES (success):** `PRE-FLIGHT: PASS / Workshop 1's substrate is confirmed. Workshop 2 is safe to start.`
- **FAILS-IF:** SLGD unreachable; any instance count differs from contract; any required class or shape absent; any WS1 file missing from disk; Bedrock models not accessible.
- **GATE:** LIVE — real Neptune queries, real Bedrock API call. Halts at first failure with remediation message. Cannot false-green.
- **WS2 resource needed:** None — WS1 only.

### 01_why_agents.ipynb

- **TEACHES:** LLM-as-interface: Titan Embeddings selects a SPARQL template from a validated ground-truth library by cosine similarity. No LLM generates SPARQL. Same question → same template → same SPARQL → auditable under SR 11-7.
- **USER RUNS:** 7 cells — setup + CFN read, direct Neptune SPARQL baseline, define `ask_graph()` (embed with Bedrock, cosine similarity, execute template SPARQL), 3 pilot questions through `ask_graph()`, determinism test (each question 5 times, assert byte-identical SPARQL).
- **DEPENDS-ON-LIVE:**
  - CFN `atlas-neptune-twotier`: `SLGDEndpoint` (WS1)
  - Bedrock `amazon.titan-embed-text-v2:0` — 9 embedding calls during setup, then per question (WS1)
  - Live Neptune SLGD (WS1)
  - WS1 file `prompts/ground-truth.yaml` on disk
- **USER SEES (success):** `[PASS] All 3 questions produced byte-identical SPARQL across 5 runs. This is the property that makes ATLAS auditable.`
- **FAILS-IF:** Bedrock embedding access denied; `ground-truth.yaml` not found; determinism test fails (indicates text generation in the path).
- **GATE:** LIVE — Bedrock calls, Neptune queries. Cannot false-green.
- **WS2 resource needed:** None — WS1 only.

### 02_mcp_servers.ipynb

- **TEACHES:** MCP servers provide a stable typed contract separating *what* (run SPARQL) from *how* (which cluster, which Lake Formation scope). Persona claim enforcement and structured error returns are the contract the deployed AgentCore Runtimes honor.
- **USER RUNS:** 6 cells — setup + CFN read, direct Neptune query baseline, define `sparql_mcp_query()` (validate SPARQL, enforce persona_claim, call Neptune via NeptuneClient, return `{rows, execution_time_ms}` or `{error, error_type}`), 3 calls for shape demonstration, shape-consistency verification (5 runs same query), error-shape verification (3 malformed inputs → structured error dicts).
- **DEPENDS-ON-LIVE:**
  - Live Neptune SLGD via NeptuneClient (SigV4-signed) (WS1)
- **USER SEES (success):** `[PASS] All 5 responses have the correct shape. / [PASS] All 3 malformed inputs returned structured error responses.`
- **FAILS-IF:** Neptune unreachable; response keys inconsistent; malformed inputs raise exceptions instead of returning error dicts.
- **GATE:** LIVE — 8 Neptune queries. In-memory shape checks on returned data. Cannot false-green for Neptune access.
- **WS2 resource needed:** None — simulates AgentCore MCP contract locally against WS1 Neptune.

### 03_agent_registry.ipynb

- **TEACHES:** Registry-first discovery: UIs never hardcode what agents exist; they query the registry filtered by persona claim. Different personas see different capability palettes from the same codebase.
- **USER RUNS:** 7 cells — setup (no network), load JSON descriptors, register 5 MCP servers, register 5 Phase 1 agents, define `discover_capabilities(persona_claim)`, verify Consumer Banker palette, verify Wealth Advisor palette.
- **DEPENDS-ON-LIVE:** NONE — local JSON descriptor files from `spec/04-aws-agent-registry/` only.
- **USER SEES (success):** Consumer Banker and Wealth Advisor palettes printed; `referral-rationale-drafter` confirmed absent from Wealth Advisor; `referral-orchestrator` confirmed in Consumer Banker.
- **FAILS-IF:** Descriptor JSON malformed; `discoverable_by` lists not correctly differentiated.
- **GATE:** IN-MEMORY — no AWS calls. Would pass even if WS2 not deployed.
- **WS2 resource needed:** None — local descriptors only.

### 04_graphql_federation.ipynb

- **TEACHES:** FIBO-shaped GraphQL schema: every type maps to one ontology class. Three resolver patterns (SPARQL/Ontop for entity data, direct Neptune for graph-native, Entity Resolution for IDs). Persona claim passthrough at the resolver level is how Lake Formation scoping works without the UI knowing which pattern runs.
- **USER RUNS:** 9 cells — setup + schema load, inspect type-to-class mappings from docstrings, simulate Pattern 1/2/3 resolvers with hardcoded responses, simulate persona scoping, verify schema mapping, verify resolver shapes, verify persona scoping.
- **DEPENDS-ON-LIVE:** NONE — reads `spec/05-appsync-graphql/schema.graphql` from disk; all resolver calls simulated.
- **USER SEES (success):** `✓ Every entity type in the schema maps to an ontology class. / ✓ Persona scoping confirmed: same query, different personas, different results.`
- **FAILS-IF:** Schema file missing; type missing ontology mapping docstring.
- **GATE:** IN-MEMORY — no AWS calls. Would pass even if WS2 not deployed.
- **WS2 resource needed:** None — local schema file.

### 06_wholesale_ui.ipynb

- **TEACHES:** Two-driver UI architecture: GraphQL provides data, Agent Registry provides capabilities — neither hardcoded. Compliance banner enforces 31 U.S.C. §5318(g)(2) tipping-off prohibition. Human-in-the-loop: `referral-orchestrator` requires `approved_rationale`.
- **USER RUNS:** 8 cells — setup, simulate Entity 360 for Patel household, render compliance banner (Consumer Banker vs BSA Analyst), populate capability palettes from descriptors, simulate Route to advisor workflow, verify palette persona-scoping, verify banner tipping-off compliance, verify human-in-loop.
- **DEPENDS-ON-LIVE:** NONE — local descriptors only.
- **USER SEES (success):** `[PASS] Capability palette correctly persona-scoped. / [PASS] Compliance banner respects §5318(g)(2). / [PASS] Human-in-the-loop enforced.`
- **FAILS-IF:** Banner leaks "SAR" to Consumer Banker; palettes identical across personas; `approved_rationale` absent from orchestrator required fields.
- **GATE:** IN-MEMORY — no AWS calls. Regulatory compliance checks on local simulation.
- **WS2 resource needed:** None — local descriptors only.

### 07_phase_1_acceptance.ipynb

- **TEACHES:** The formal Phase 1 acceptance suite — 36 assertions across 7 categories. Every passing assertion is a contract honored.
- **USER RUNS:** 9 cells — setup (defines `check()` and `defer()`), then one cell per category: Cat 1 Registry (6 assertions, local), Cat 2 Posture (7 assertions, local), Cat 3 Permissions (2 local + 2 deferred), Cat 4 Regulatory (4 assertions, local), Cat 5 E2E Rachel Kim (7 DEFERRED), Cat 6 Schema (4 assertions, local), Cat 7 WS1 Integrity (4 assertions, local + file-read), summary.
- **DEPENDS-ON-LIVE:**
  - Local: JSON descriptors, `schema.graphql`, WS1 TTL files (`atlas-core.ttl`, `atlas-shapes.ttl`)
  - Deferred: Cats 3.3+3.4 (Lake Formation scoping, requires live Neptune) + Cat 5 (all 7, requires live Neptune + deployed AgentCore Runtimes + Step Functions)
- **USER SEES (success — no live Neptune):** `Passed: 27 / Failed: 0 / Deferred: 9 / ALL NON-DEFERRED ASSERTIONS PASS.`
- **USER SEES (success — live Neptune):** `Passed: 36 / Failed: 0 / Deferred: 0`
- **FAILS-IF:** Any Category 1/2/4/6/7 assertion fails; tipping-off violation; schema unmapped; WS1 files modified; WS2 extensions not in `atlas-part-2:`.
- **GATE:** HYBRID — 27 assertions local, 9 explicitly deferred. **Deferred assertions do NOT auto-run after deploy.** User must manually re-run the notebook with live Neptune. The exact deferred condition (quoted from cell-07-cat5-e2e):
  ```python
  defer("5.1", "Patel household exists in SLGD", "Requires running Neptune")
  defer("5.2", "wealth-signal-detector detects signal for Patel household", "Requires running Neptune")
  defer("5.3", "household-traverser returns >= 2 nodes for Patel household", "Requires running Neptune")
  defer("5.4", "referral-rationale-drafter produces non-empty draft", "Requires Bedrock access")
  defer("5.5", "referral-orchestrator routes successfully", "Requires Step Functions")
  defer("5.6", "AuditRecord exists after routing", "Requires running Neptune")
  defer("5.7", "Audit record carries PROV-O attribution", "Requires running Neptune")
  ```
  To flip deferred→live: deploy WS2 (`cdk deploy`), then **manually re-run this notebook** from the top. The `defer()` calls check no ARN or flag — they always defer unconditionally. There is no env var or context switch that flips them. Re-running with live resources means 5.1-5.7 will execute (they are separate `check()` calls that the cell replaces `defer()` calls with if the resources exist).

  Wait — correcting: looking at the code, all Category 5 assertions are unconditionally `defer()` calls, not conditional checks. To get them to run, the notebook code itself would need to be edited to replace the `defer()` calls with real `check()` calls. **This is a structural gap: Category 5 will never pass in the current notebook even with live infrastructure, because the `defer()` calls are unconditional.**

- **WS2 resource needed for Cat 5:** Deployed `wealth-signal-detector`, `household-traverser`, `referral-rationale-drafter`, `referral-orchestrator` AgentCore Runtimes + Step Functions state machine + live SLGD with Patel household data.

---

## Section 3 — Prose vs code alignment (Phase 1 pages)

### 01-preflight ↔ 00_preflight.ipynb: ALIGNED

Every page step references the correct cell ID, every expected output block matches the notebook's actual print strings. Troubleshooting entries match real failure conditions. No mismatches found.

### 02-why-agents ↔ 01_why_agents.ipynb: ALIGNED

Cell IDs (`cell-03-setup`, `cell-06-ask-graph`, `cell-09-determinism`) all correct. Determinism gate output quoted correctly. Concept section references are accurate.

### 03-mcp-servers ↔ 02_mcp_servers.ipynb: **1 MISMATCH**

| Location | Prose says | Code does |
|----------|-----------|-----------|
| `03-mcp-servers/index.md` Step 7 "Expected output" block | `{error: "persona_claim required", code: 401}` | `{"error": str(exc), "error_type": "persona_error"}` — key is `error_type`, not `code`; no numeric code field exists |

The page shows a `code` field with an HTTP status integer. The notebook's `cell-10-error-shape` verifies for `error` and `error_type` keys only. A novice following the page will expect `result["code"]` to exist and be confused when it does not.

### 04-agent-registry ↔ 03_agent_registry.ipynb: ALIGNED

Registry registration output, discovery function demonstration, and palette verification all match. Cell IDs correct.

### 05-graphql-federation ↔ 04_graphql_federation.ipynb: ALIGNED

Schema inspection, three resolver pattern demonstrations, and persona scoping verification all align. Cell IDs correct.

### 06-wholesale-ui ↔ 06_wholesale_ui.ipynb: ALIGNED

Entity 360 simulation, compliance banner rendering, capability palettes, and human-in-loop assertion all match the notebook code.

### 07-phase-1-acceptance ↔ 07_phase_1_acceptance.ipynb: ALIGNED

All 36 assertion IDs and categories are correctly documented. Deferred assertion behavior (DEFERRED vs PASS vs FAIL) is accurately described. The two expected output blocks (with and without live Neptune) match the actual summary print logic. One structural gap noted: Category 5 `defer()` calls are unconditional — see Section 6.

---

## Section 4 — WS1→WS2 handoff contract

| WS2 expects | Source | Status |
|-------------|--------|--------|
| CFN output `SLGDEndpoint` | `atlas-neptune-twotier` | **CONFIRMED** — `atlas-slgd.cluster-c0bie06scpwu.us-east-1.neptune.amazonaws.com` |
| CFN output `LGDEndpoint` | `atlas-neptune-twotier` | **CONFIRMED** — `atlas-lgd.cluster-c0bie06scpwu.us-east-1.neptune.amazonaws.com` |
| SLGD: ≥22 `atlas:` classes (15 named required) | WS1 Module 3 | **CONFIRMED** — 22 classes present |
| SLGD: 6 SHACL NodeShapes (6 named required) | WS1 Module 6 | **CONFIRMED** — 6 shapes present |
| SLGD: Customer=200, Transaction=3747, Advisor=10, AdvisoryRelationship=105 | WS1 Module 4/5 | **CONFIRMED** — verified 2026-05-30 |
| SLGD: 200 promoted entities with `promotedFrom` + `promotedBy` | WS1 Module 5 | **CONFIRMED** — live SLGD query: 200/200 |
| WS1 disk file `prompts/ground-truth.yaml` | Repo clone | **CONFIRMED** — exists at `agentic-semantic-layer/prompts/ground-truth.yaml` |
| WS1 disk file `prompts/prefixes.txt` | Repo clone | **CONFIRMED** — exists |
| WS1 disk file `notebooks/shared/atlas_neptune.py` | Repo clone | **CONFIRMED** — exists |
| WS1 disk file `notebooks/shared/atlas_sparql.py` | Repo clone | **CONFIRMED** — exists |
| Bedrock `amazon.titan-embed-text-v2:0` ACTIVE | Account | **CONFIRMED** — ACTIVE in us-east-1 |
| Bedrock `us.anthropic.claude-sonnet-4-6` inference profile ACTIVE | Account | **CONFIRMED** — ACTIVE in us-east-1 |
| `atlas-neptune-iam-auth` policy on both execution roles | Done during WS1 | **CONFIRMED** — scoped v2, non-regression verified 2026-05-31 |
| Bedrock InvokeModel policy on both execution roles | Done during WS1 | **CONFIRMED** — `atlas-workshop-bedrock-access` inline policy on both roles |
| S3 `atlas-ontology-staging-981814817046/prompts/ground-truth.yaml` | Needs upload | **NOT YET UPLOADED** — file exists locally; upload is Step 2 of deploy sequence, approved, awaiting go |
| S3 `atlas-ontology-staging-981814817046/prompts/prefixes.txt` | Needs upload | **NOT YET UPLOADED** — same |
| AWS Entity Resolution workflow `atlas-entity-resolution` | Manual or CDK | **UNVERIFIED** — hardcoded name in `agentcore-runtimes.ts:219`; no CDK construct; spec/02 says create manually if absent; not verified to exist in account |

---

## Section 5 — CDK / Deploy-risk register

All 11 CDK constructs and the main stack were read in full. Findings below are in addition to the committed `817e365` fix (GROUND_TRUTH_S3_URI and PREFIXES_S3_URI repointed to WS1 staging bucket).

| # | Finding | File:line | Severity | Why |
|---|---------|-----------|----------|-----|
| R1 | `SHAPES_S3_URI: "s3://atlas-workshop-1/ontology/atlas-shapes.ttl"` — bucket does not exist | `agentcore-runtimes.ts:186` | LOW | `atlas-shacl-mcp` falls back to vendored `ontology/atlas-shapes.ttl` shipped inside the Runtime artifact — no runtime failure |
| R2 | `SIGNAL_QUERIES_S3_URI: "s3://atlas-workshop-1/queries/wealth-signals.yaml"` — bucket AND file do not exist | `agentcore-runtimes.ts:289` | LOW | `wealth_signal_detector.py` reads this into `os.environ` but never uses it; dead code confirmed |
| R3 | `PROMPT_TEMPLATE_S3_URI: "s3://atlas-workshop-1/prompts/referral-rationale.txt"` — bucket AND file do not exist | `agentcore-runtimes.ts:326` | LOW | `referral_rationale_drafter.py` falls back to `DEFAULT_PROMPT_TEMPLATE` hardcoded string — no runtime failure |
| R4 | Both `neptuneSlgdEndpoint` and `neptuneLgdEndpoint` receive the same `neptuneClusterEndpoint` context value | `atlas-workshop-2-stack.ts:94-95` | **MEDIUM** | `behavioral-signal-agent` is designed for LGD access; it will query SLGD instead. Phase 2 behavioral signal detection may return incorrect results. LGD endpoint is available from WS1 CFN outputs but not passed separately. |
| R5 | `REGISTRY_ENDPOINT: props.registryEndpoint ?? ""` — `registryEndpoint` is never passed from the main stack (optional prop, no caller) | `agentcore-runtimes.ts:249`, `atlas-workshop-2-stack.ts:90` | **MEDIUM** | `atlas-registry-mcp` reads `REGISTRY_ENDPOINT` env var. If empty, behavior depends on whether `atlas_registry_mcp.py` queries the AWS Agent Registry control plane via boto3 (likely correct fallback) or needs an HTTP endpoint (would fail silently). Needs verification against `atlas_registry_mcp.py` source. |
| R6 | `ER_WORKFLOW_NAME: "atlas-entity-resolution"` hardcoded; no CDK construct creates this workflow | `agentcore-runtimes.ts:219` | **MEDIUM** | `atlas-er-mcp` calls `boto3.client("entityresolution").start_matching_job(workflowName=ER_WORKFLOW_NAME)`. If workflow doesn't exist in account, the MCP will hard-fail at runtime. No graceful degrade found. |
| R7 | Cognito callback URL hardcoded as `https://atlas.example.com/callback` when no `productionCallbackUrl` is passed | `cognito.ts:684` | **MEDIUM** | The OAuth callback will point at a non-existent domain. Authentication flows requiring code exchange will fail. CloudFront URL (from `WholesaleUiUrl` output) should be used but isn't wired. |
| R8 | Ontop ECS FargateService has no circuit breaker | `ontop.ts:1001-1007` | LOW | A bad deployment can hang for up to 3 hours. CDK emits a warning at synth. Tracked in todo list. |
| R9 | `ONTOP_MAPPING_FILE: "/opt/ontop/mappings/atlas.obda"` — the `.obda` file must exist inside the `ontop/ontop:5` container image | `ontop.ts:988` | **HIGH** | The official `ontop/ontop:5` Docker image does not bundle ATLAS-specific mapping files. The `/opt/ontop/mappings/` path is empty in the base image. At startup, Ontop will fail to find the mapping file and crash. No volume mount, no ConfigMap, no file-copy step is present in the construct. **This is the most critical hidden deploy risk: Ontop will start, fail to load mappings, and the health check will fail, causing the ECS service to loop in crash-restart.** |
| R10 | `ONTOP_PROPERTIES_FILE: "/opt/ontop/mappings/atlas.properties"` — same missing-file problem as R9 | `ontop.ts:989` | **HIGH** | Same root cause as R9. Ontop requires a JDBC properties file at this path to connect to Neptune. File does not exist in the base image. |
| R11 | `JDBC_URL: jdbc:neptune:sparql://${neptuneEndpoint}:8182/sparql` — Ontop uses a SPARQL JDBC driver; must be present in the image | `ontop.ts:990` | **MEDIUM** | The Neptune Sparql JDBC driver (`sparql-driver.jar`) must be present in the Ontop classpath. The official `ontop/ontop:5` image does not include it. Whether the image bundles it or requires a custom build is unclear from the code alone. |
| R12 | LakeFormation construct creates LF-Tags but applies no tag associations — comment says "configured manually" | `lake-formation.ts:744-748` | **MEDIUM** | Tags `atlas:persona` and `atlas:sensitivity` are created but not associated with any Iceberg table or column. Lake Formation row/column scoping will not work until tag associations are applied. This is acknowledged in a comment but not documented in any workshop step. |
| R13 | `WholesaleUiUrl` CFN output exists but React build artifacts are never deployed by CDK | `cloudfront.ts`, `atlas-workshop-2-stack.ts:118` | **MEDIUM** | CloudFront distribution and S3 bucket are created; the React app must be separately built (`npm run build`) and synced to S3. CDK does not do this. Workshop pages describe clicking through the UI but it won't render with an empty S3 bucket. |
| R14 | `BEDROCK_TEXT_MODEL_ID: "us.anthropic.claude-sonnet-4-6"` hardcoded in two runtimes | `agentcore-runtimes.ts:324,369` | LOW | Works in us-east-1 where the inference profile is ACTIVE. Non-US deployers will get model-not-found. Portability item, not a deploy blocker. |
| R15 | nb06 Category 5 `defer()` calls are unconditional — will never auto-run after deploy | `07_phase_1_acceptance.ipynb:cell-07-cat5-e2e` | **MEDIUM** | The `defer()` function is called unconditionally regardless of whether Neptune is available. Re-running the notebook after deploy does NOT flip these to live checks; the code would need to be changed to replace `defer()` with `check()`. This means 5.1–5.7 will permanently show as DEFERRED. |

---

## Section 6 — Phase 1 deferred assertions and post-deploy verification

### nb06 `defer()` function (from cell-02-setup)

```python
def defer(assertion_id, description, reason):
    """Defer an assertion that requires live infrastructure."""
    results["deferred"] += 1
    results["details"].append({"id": assertion_id, "desc": description, "status": "DEFERRED"})
    print(f"  ⊘ [{assertion_id}] {description} — DEFERRED: {reason}")
```

### Deferred assertions (exact calls from cell-07-cat5-e2e)

```python
defer("5.1", "Patel household exists in SLGD", "Requires running Neptune")
defer("5.2", "wealth-signal-detector detects signal for Patel household", "Requires running Neptune")
defer("5.3", "household-traverser returns >= 2 nodes for Patel household", "Requires running Neptune")
defer("5.4", "referral-rationale-drafter produces non-empty draft", "Requires Bedrock access")
defer("5.5", "referral-orchestrator routes successfully", "Requires Step Functions")
defer("5.6", "AuditRecord exists after routing", "Requires running Neptune")
defer("5.7", "Audit record carries PROV-O attribution", "Requires running Neptune")
```

Plus from cell-05-cat3-permissions:
```python
defer("3.3", "Consumer Banker query returns fewer customers than BSA Analyst", "Requires Lake Formation")
defer("3.4", "Consumer Banker cannot traverse BSA-restricted named graphs", "Requires Lake Formation")
```

**Total: 9 deferred (7 in Cat 5, 2 in Cat 3)**

### Auto-run or manual change required?

**Manual change required.** The `defer()` calls are unconditional — they always defer regardless of what is deployed. After `cdk deploy`, a user who re-runs nb06 will still see 9 deferred assertions. To make them live, the notebook cells must be edited to replace `defer()` with actual `check()` logic that invokes the deployed AgentCore Runtimes.

### What live WS2 resources each deferred assertion needs

| Assertion | Live WS2 resource needed | CFN output that provides it |
|-----------|------------------------|---------------------------|
| 3.3 | Lake Formation row filtering on Iceberg tables | Lake Formation tags (created) but associations not applied (R12) |
| 3.4 | Named graph scoping via SHACL | Requires `atlas-sparql-mcp` Runtime + Lake Formation |
| 5.1 | SLGD with `atlas:hh/9c2a1e` Patel household | `AtlasSparqlMcpArn` output |
| 5.2 | `wealth-signal-detector` AgentCore Runtime | `AtlasSparqlMcpArn` (dependency) |
| 5.3 | `household-traverser` AgentCore Runtime | `AtlasSparqlMcpArn` (dependency) |
| 5.4 | `referral-rationale-drafter` Runtime + Bedrock Claude Sonnet | Bedrock (confirmed active) |
| 5.5 | `referral-orchestrator` Step Functions + all 5 step Lambdas | `StateMachineArn` output |
| 5.6 | Live SLGD write via `audit-write` Lambda | `StateMachineArn` (dependency) |
| 5.7 | PROV-O attribution in written AuditRecord | Same as 5.6 |

**Cross-check with CFN outputs:** The stack exports `AtlasSparqlMcpArn` and `StateMachineArn` — these cover 5.1–5.7 as the anchor resources. However, the `defer()` calls in the notebook do not read any CFN output; they would need to be replaced with code that invokes the Runtime ARNs. The ARNs are not passed into the notebook via env var or context.

---

## Section 7 — Gap list / work queue (Phase 1 + foundation)

### PRE-DEPLOY

| # | Gap | Decision / Fix needed |
|---|-----|----------------------|
| **G1** | **CDK bootstrap not done** — `CDKToolkit` stack absent; `cdk deploy` hard-fails without it | Run `cdk bootstrap aws://981814817046/us-east-1` — one-time mutating action |
| **G2** | **2 S3 files not yet uploaded** — `nl-to-sparql-agent` will fail at runtime in AgentCore container reading `ground-truth.yaml` and `prefixes.txt` | `aws s3 cp` ×2 to `atlas-ontology-staging-981814817046/prompts/` — approved, awaiting go |
| **G3** | **Entity Resolution workflow `atlas-entity-resolution` existence unverified** — `atlas-er-mcp` will hard-fail if absent, no graceful degrade | `aws entityresolution list-matching-workflows` to verify; create if absent |
| **G4** | **5 IDC persona groups missing** from identity store — Cognito deploys standalone but federation is unconfigured | Create 5 groups via `aws identitystore create-group --identity-store-id d-9066212736` ×5; can be done post-deploy (not needed for notebooks 00–05) |

### AT-DEPLOY

| # | Gap | Decision / Fix needed |
|---|-----|----------------------|
| **G5** | **Ontop mapping files missing from container** (R9, R10 — CRITICAL) — `atlas.obda` and `atlas.properties` do not exist in `ontop/ontop:5` base image; Ontop will crash-loop at startup | Either build a custom Ontop image that bundles these files, or mount them via ECS task definition environment or S3. Mapping files exist locally at `agentic-semantic-layer/mappings/`; a custom Dockerfile or ECS volume is required |
| **G6** | **Both Neptune endpoints wired to SLGD** (R4) — `behavioral-signal-agent` needs LGD access | Add `neptuneLgdEndpoint` context key (use `LGDEndpoint` from WS1 CFN) and pass separately in `atlas-workshop-2-stack.ts:95` |
| **G7** | **`REGISTRY_ENDPOINT` never passed** (R5) — `atlas-registry-mcp` gets empty string | Read `atlas_registry_mcp.py` to confirm whether boto3 fallback is sufficient; if not, pass the Agent Registry endpoint |
| **G8** | **Cognito callback URL hardcoded as `atlas.example.com`** (R7) — authentication flows will fail | Wire `WholesaleUiUrl` CloudFront output as the `productionCallbackUrl` to the Cognito construct |
| **G9** | **Lake Formation tag associations not applied** (R12) — LF-Tags created but not associated with any table | Document manual association step or add CDK `CfnTagAssociation` resources for the Iceberg tables |
| **G10** | **ECS circuit breaker missing on Ontop** (R8) — 3-hour hang on failed deploy | Add `circuitBreaker: { rollback: true }` to `ontop.ts:1001` FargateService — tracked in todo list |
| **G11** | **Neptune Sparql JDBC driver may be absent from Ontop image** (R11) | Verify whether `ontop/ontop:5` bundles the Neptune JDBC driver; if not, custom image build required |

### POST-DEPLOY / PER-NOTEBOOK

| # | Gap | Decision / Fix needed |
|---|-----|----------------------|
| **G12** | **nb06 Category 5 `defer()` calls are unconditional** (R15) — 5.1–5.7 will always show DEFERRED even after deploy | Replace `defer()` calls in `cell-07-cat5-e2e` with conditional `check()` logic that invokes deployed Runtime ARNs; requires reading deployed CFN outputs into the notebook |
| **G13** | **React UI apps not built or deployed** (R13) — CloudFront distributions created with empty S3 buckets | Build `apps/wholesale-ui` and `apps/wealth-ui` (`npm run build`) and sync artifacts to S3; CDK does not do this |
| **G14** | **Workshop prose page 03-mcp-servers shows `code: 401` error key** (Section 3 mismatch) — actual implementation uses `error_type: "persona_error"` | Fix page to show `{error: "...", error_type: "persona_error"}` — wording-only fix |
| **G15** | **nb06 Cat 3 deferred assertions** (3.3, 3.4) — Lake Formation scoping not verifiable until LF tag associations applied | Depends on G9 resolution |

### PORTABILITY (deferred until both workshops fully deployed)

| # | Gap |
|---|-----|
| G16 | `us-east-1` hardcoded in register.py defaults and test mock ARNs |
| G17 | `us.anthropic.claude-sonnet-4-6` US-only inference profile hardcoded in two Runtimes |
| G18 | Bedrock/Neptune/IAM policies are LIVE-STATE only — not in CDK; fresh-account redeploy would miss them |
| G19 | WS1 CFN VPC CIDR default `10.0.0.0/16` — wrong for any VPC using different CIDR |
| G20 | Cleanup page lists 8 phantom stack names; real command is `cdk destroy AtlasWorkshop2` — tracked in todo list |

---

## Section 8 — Pass 2 placeholder

Phase 2 (notebooks `01_phase_2_agents.ipynb` through `06_phase_2_acceptance.ipynb`, workshop pages `08-phase-2-agents` through `13-phase-2-acceptance`) deferred to Pass 2.

---

*Read in full this pass: all 7 Phase 1 notebooks, all 7 corresponding workshop pages, all 11 CDK constructs, the main stack (`atlas-workshop-2-stack.ts`), and `spec/07-cdk-stack/README.md`. The Phase 2 notebooks were listed but not read. All claims in Sections 2–6 trace to specific files read completely.*

*Critical new finding not in prior ws2-comprehension.md: **Ontop mapping files (R9/R10/G5)** — the `atlas.obda` and `atlas.properties` files do not exist in the official `ontop/ontop:5` Docker image. This will cause Ontop to crash-loop on deploy. This is the most significant deploy risk discovered in this pass.*

---

# PASS 2 — Phase 2 (Wealth Advisor Spine)

Complete read of all 6 Phase 2 notebooks and their 6 workshop pages. Appended after Pass 1.

---

## P2-Section A — Per-notebook map (Phase 2)

### 01_phase_2_agents.ipynb (Module 8)

- **TEACHES:** Why Phase 2 agents are structurally different: `behavioral-signal-agent` queries the LGD for temporal behavioral data (EngagementDecay, NetworkInfluence); `conversational-context-manager` is stateful via AgentCore Memory; postures include `probabilistic-guarded`.
- **USER RUNS:** 6 code cells — setup (load descriptors), posture comparison (Phase 1 vs 2), EngagementDecay simulation against hardcoded LGD session data, MCP dependency inspection, verify 3 Phase 2 agents registered, verify LGD graph_tiers declared.
- **DEPENDS-ON-LIVE:** NONE — local descriptor JSON files from `spec/04-aws-agent-registry/agents/` only.
- **USER SEES (success):** `[PASS] behavioral-signal-agent declares LGD access. Behavioral signals (EngagementDecay, NetworkInfluence) can be detected.`
- **FAILS-IF:** Descriptor JSON malformed; Phase 2 agents missing `"phase": 2`; `behavioral-signal-agent` missing `"lgd"` in `graph_tiers`.
- **GATE:** IN-MEMORY — unconditional assertions. No deferred checks.
- **SIMULATED-vs-LIVE:** Fully simulated. WS2 resource needed: None.

### 02_agentcore_memory.ipynb (Module 9)

- **TEACHES:** Session-scoped memory enables multi-turn conversations. Session scope is a compliance decision: permanent storage creates GDPR/CCPA obligations.
- **USER RUNS:** 6 code cells — setup, define local `SessionMemory` class mirroring AgentCore Memory interface (put/get/end_session), two-turn conversation simulation (resolves "those" from memory), context-driven template selection (scoped vs broad), verify session scope, verify session isolation.
- **DEPENDS-ON-LIVE:** NONE — `SessionMemory` is a local Python class. Notebook comment: "This notebook simulates AgentCore Memory locally. Production uses the AWS AgentCore Memory service."
- **USER SEES (success):** `[PASS] Memory is session-scoped: data cleared after end_session(). / [PASS] Sessions are fully isolated. No context leakage between sessions.`
- **FAILS-IF:** `end_session()` doesn't clear session data; sessions leak data across each other.
- **GATE:** IN-MEMORY — unconditional assertions. No deferred checks.
- **SIMULATED-vs-LIVE:** Fully simulated. WS2 resource needed: None.

### 03_wealth_ui.ipynb (Module 10)

- **TEACHES:** Thesis 2 — same GraphQL schema and registry serve two structurally different UIs via persona-specific fragments (`CustomerReferralFragment` vs `CustomerCoverageFragment`) and capability palettes.
- **USER RUNS:** 6 code cells — setup, simulate `capabilities(personaClaim)` resolver for both personas, simulate `theme-summarizer` output, print both fragments side-by-side, verify Wealth Advisor vs Consumer Banker palettes differ, verify `theme-summarizer` is Wealth Advisor-only.
- **DEPENDS-ON-LIVE:** NONE — local descriptor files only.
- **USER SEES (success):** `[PASS] Themes are accessible to the Wealth Advisor persona. The Wealth UI can render market themes for client portfolios.`
- **FAILS-IF:** Descriptor `discoverable_by` lists not differentiated; `theme-summarizer` descriptor missing.
- **GATE:** IN-MEMORY — unconditional assertions. No deferred checks.
- **SIMULATED-vs-LIVE:** Fully simulated. WS2 resource needed: None.

### 04_jwt_auth.ipynb (Module 11)

- **TEACHES:** Why Phase 2 switches from IAM (service identity) to JWT (user identity). With two UIs, IAM cannot distinguish personas at the service level; JWT moves the `custom:persona` claim into a Cognito-signed token.
- **USER RUNS:** 6 code cells — setup, construct sample JWT payloads with `custom:persona`, simulate registry filtering by JWT claim, print IAM vs JWT comparison table, verify both tokens carry correct persona claim, verify different tokens produce different capability sets and no-persona token returns empty.
- **DEPENDS-ON-LIVE:** NONE — JWT payloads are local Python dicts; no Cognito call made. Comment: "In production, AppSync extracts the claim from the Authorization header."
- **USER SEES (success):** `[PASS] Registry correctly filters by JWT persona claim. Per-request authorization works without IAM role assumption per user.`
- **FAILS-IF:** `custom:persona` missing from token; filter returns same set for different personas; no-persona token returns non-empty capabilities.
- **GATE:** IN-MEMORY — unconditional assertions. No deferred checks.
- **SIMULATED-vs-LIVE:** Fully simulated. WS2 resource needed: None.

### 05_end_to_end.ipynb (Module 12)

- **TEACHES:** The full cross-UI advisor scenario — signal detection in Wholesale UI through routing to Wealth UI, with a PROV-O audit trail spanning both personas. Proves Thesis 2 at the workflow level.
- **USER RUNS:** 7 code cells — setup, build Step 1 (signal detection event dict), build Steps 2–3 (rationale drafted + referral routed), build Steps 4–6 (advisor receives notification + opens profile + asks follow-up), assemble full 6-event audit trail, verify trail spans both personas with unbroken parent chain, verify routing bridges both UIs bidirectionally.
- **DEPENDS-ON-LIVE:** NONE — explicitly: "This notebook simulates the cross-UI flow locally." All events are Python dicts; all audit_ids are `uuid4()`.
- **USER SEES (success):** `[PASS] Routing decision correctly links both UIs. The cross-UI workflow is fully traceable.`
- **FAILS-IF:** Audit trail missing a persona; parent_audit_id chain broken; routing event not linked bidirectionally.
- **GATE:** IN-MEMORY — unconditional assertions. No deferred checks.
- **SIMULATED-vs-LIVE:** Fully simulated. WS2 resource needed: None.

### 06_phase_2_acceptance.ipynb (Module 13)

- **TEACHES:** The formal Phase 2 acceptance suite — 20 assertions across 5 categories. Notebook explicitly states: "all 20 assertions across five categories, all running locally — no live infrastructure required. Unlike the Phase 1 acceptance suite (Module 7), there are no deferred assertions."
- **USER RUNS:** 7 code cells — setup + results tracker, Category 1 Registration (5 assertions), Category 2 Wealth UI (4 assertions), Category 3 AgentCore Memory (4 assertions), Category 4 JWT (3 assertions), Category 5 Cross-UI Audit Trail (4 assertions), summary.
- **DEPENDS-ON-LIVE:** NONE — all 20 assertions run against local descriptors, local `SessionMemory` class, locally constructed JWTs, locally simulated audit trails.
- **USER SEES (success):** `✓ ALL ASSERTIONS PASS. / Thesis 2 is validated: two structurally different UIs consume the same backbone with correct persona-scoped behavior.`
- **FAILS-IF:** Any descriptor incorrect; SessionMemory doesn't isolate sessions; JWT filter wrong; audit trail simulation broken.
- **GATE:** IN-MEMORY — all 20 assertions unconditional. No deferred checks.
- **SIMULATED-vs-LIVE:** Fully simulated. WS2 resource needed: None.

---

## P2-Section B — The defer pattern (critical capstone audit)

### Finding: ALL Phase 2 notebooks are pure local simulation — pattern (c)

Every Phase 2 notebook follows pattern **(c): pure local simulation with no live assertion**. None follow (a) unconditional defer/skip, none follow (b) conditional live check.

The three patterns for reference:
- (a) Unconditional defer — marks assertion as skipped; counter shows DEFERRED; user must re-run manually post-deploy
- (b) Conditional live check — runs if resource available, skips gracefully if not
- (c) Pure local simulation — always runs; always passes if code is correct; never touches deployed infrastructure

**All six Phase 2 notebooks are (c).** The deciding evidence from each:

**nb01–nb04:** All verification cells load JSON descriptors or operate on local Python objects. No AgentCore Runtime ARN is read or called. No AWS API is invoked.

**nb05 (end-to-end) — the critical one:**
```python
# cell-03-setup
print("Setup complete.")
print("This notebook simulates the cross-UI flow locally.")
```
```python
# cell-04 through cell-07
signal_event = { ... "audit_id": str(uuid.uuid4()), ... }
# No AgentCore invoke_agent_runtime() call anywhere in the file
# No boto3.client("bedrock-agentcore") call anywhere
# All events are Python dicts constructed inline
```
```python
# cell-09-verify-trail (unconditional)
assert expected_personas.issubset(personas_in_trail)
print("[PASS] Audit trail spans both personas with unbroken parent chain.")
# No condition guards this — runs regardless of deployment state
```

**nb06 (phase_2_acceptance) — the formal acceptance gate:**
```python
# cell-01-concept (markdown)
# "all 20 assertions across five categories, all running locally —
#  no live infrastructure required. Unlike the Phase 1 acceptance suite
#  (Module 7), there are no deferred assertions."
```
```python
# cell-05-cat3-memory
mem = SessionMemory()  # local Python class, not AWS AgentCore Memory service
check("3.1", "Memory stores values during active session", mem.get(s1, "data") == [1, 2, 3])
# No connection to deployed Memory store; no MemoryId CFN output read
```
```python
# cell-06-cat4-jwt
jwt_banker = create_jwt_payload("atlas-consumer-banker")  # local dict construction
# No Cognito UserPool called; no JWT signature verification
check("4.1", "JWT tokens contain custom:persona claim", "custom:persona" in jwt_banker)
```
```python
# cell-07-cat5-audit
# Audit trail is a hardcoded list built inline in this cell:
audit_trail = [
    {"step": 1, "persona": "atlas-consumer-banker", "ui": "Wholesale UI",
     "action": "signal_detected", "audit_id": audit_ids[0], "parent_audit_id": None},
    ...
]
check("5.1", "Audit trail spans both personas", ...)
# No Neptune query; no AgentCore invoke; just checking the local list
```

### Implication for the capstone

**The capstone (WS2) proves Thesis 1 and Thesis 2 through local simulation only.** After a successful `cdk deploy`:

- Phase 2 nb06 will still print `✓ ALL ASSERTIONS PASS` — because all 20 assertions check local data structures.
- Phase 1 nb06 Category 5 (`defer()` calls, 7 assertions) will still print DEFERRED — because the `defer()` calls are unconditional; the notebook code would need to be edited to flip them to live checks.
- **No notebook in either phase will automatically exercise the deployed AgentCore Runtimes, Step Functions, Memory store, AppSync endpoint, or Cognito pool.**

The two CFN outputs that ARE the capstone proof points — `AtlasSparqlMcpArn` and `ConversationalContextManagerArn` — are never read by any Phase 1 or Phase 2 notebook. They exist as stack outputs but nothing consumes them in the notebook path.

**This is gap G12 elevated to CAPSTONE-CRITICAL:** The fix requires writing a new "live integration" cell (or modifying Phase 1 nb06 Cat 5 cells) that reads the deployed CFN outputs and invokes the AgentCore Runtimes, rather than simulating locally. Without this fix, running the full 13-notebook workshop proves the architecture is correctly described but does not prove it runs.

---

## P2-Section C — Prose vs code alignment (Phase 2 pages)

### Module 8 (08-phase-2-agents): FULLY ALIGNED
All cell IDs, expected outputs, and resource names match.

### Module 9 (09-agentcore-memory): FULLY ALIGNED
All cell IDs match. Multi-turn conversation output (Rachel Kim AUM $3.2M, Sarah Patel AUM $4.5M after filter) matches notebook print strings.

### Module 10 (10-wealth-ui): FULLY ALIGNED
Fragment field lists, capability palette counts, and theme-summarizer verification outputs all match.

### Module 11 (11-jwt-auth): FULLY ALIGNED
JWT payload fields, IAM vs JWT comparison table, and filtering verification outputs all match.

### Module 12 (12-end-to-end): ALIGNED with one cosmetic mismatch

| Location | Prose says | Code does |
|----------|-----------|-----------|
| `12-end-to-end/index.md` Step 5 expected output | `Routed to: advisor-alex-morgan` | `cell-05-step2-draft` prints `Routed to: advisor-michael-ross` |

Not load-bearing — the advisor name is a simulation artifact. The workshop concept (routing event carries advisor identifier) is identical.

### Module 13 (13-phase-2-acceptance): FULLY ALIGNED
All 20 assertion IDs and category names match. Summary output format matches exactly.

---

## P2-Section D — Phase 2 live-resource dependencies

| P2 resource | P2 notebook that needs it | Actually called live? | WS2 CFN output |
|-------------|--------------------------|----------------------|----------------|
| AgentCore Memory store (`atlas_workshop_memory`) | nb02 uses SessionMemory interface | **NO** — local `SessionMemory` class only | `MemoryId` (exported but never read by any notebook) |
| `conversational-context-manager` Runtime | nb02 teaches it, nb06 verifies descriptor | **NO** — descriptor check only | `ConversationalContextManagerArn` (exported, never called) |
| `behavioral-signal-agent` Runtime + LGD | nb01 simulates EngagementDecay | **NO** — hardcoded session data | Not exported |
| `theme-summarizer` Runtime + Bedrock Claude | nb03 simulates output | **NO** — hardcoded theme dict | Not exported |
| Cognito User Pool + JWT | nb04 constructs local JWT dicts | **NO** — no Cognito call | `CognitoUserPoolId` (exported, never read) |
| AppSync GraphQL API | nb04 mentions in concept | **NO** — no AppSync call | `AppSyncEndpoint` (exported, never read) |
| Wealth UI (CloudFront) | nb03 describes, nb13 page links to | **NO** | **NOT EXPORTED** — `WealthUiUrl` exists in `cloudfront.ts` but the main stack only exports `WholesaleUiUrl` |
| Step Functions (`atlas-referral-orchestrator`) | Phase 1 nb06 Cat 5 deferred | **NO (deferred)** | `StateMachineArn` (exported, not consumed by notebooks) |
| `atlas-sparql-mcp` Runtime | Phase 1 nb06 Cat 5 deferred | **NO (deferred)** | `AtlasSparqlMcpArn` (exported, not consumed) |

**Resources Phase 2 needs that the stack does NOT export:**
- `WealthUiUrl` — CloudFront distribution URL for Wealth UI. `wealthUiUrl` field exists in `CloudFrontConstruct` but the main stack only has `new cdk.CfnOutput(this, "WholesaleUiUrl", ...)`. The Wealth UI CloudFront URL is inaccessible without stack output or direct CloudFormation query. This is a **new gap** (G-P2-1).
- Individual AgentCore Runtime ARNs for Phase 2 agents (`behavioral-signal-agent`, `household-traverser`, `referral-rationale-drafter`, `theme-summarizer`, `wealth-signal-detector`) — none exported. Only `AtlasSparqlMcpArn` and `ConversationalContextManagerArn` are exported.

---

## P2-Section E — Updated unified gap queue

The Phase 1 gaps (G1–G20) from Pass 1 Section 7 are merged below with Phase 2 gaps. New Phase 2 gaps prefixed P2.

### PRE-DEPLOY

| # | Gap | Action | Capstone impact |
|---|-----|--------|-----------------|
| **G1** | CDK bootstrap not done | `cdk bootstrap aws://981814817046/us-east-1` | Blocks all |
| **G2** | 2 S3 files not yet uploaded (ground-truth.yaml, prefixes.txt) | `aws s3 cp` ×2 (approved, awaiting go) | Blocks nl-to-sparql-agent at runtime |
| **G3** | ER workflow `atlas-entity-resolution` unverified | `aws entityresolution list-matching-workflows` | Blocks atlas-er-mcp at runtime |
| **G4** | 5 IDC persona groups missing | `aws identitystore create-group` ×5 (post-deploy OK) | Blocks Cognito federation |

### AT-DEPLOY ⚠️

| # | Gap | Action | Capstone impact |
|---|-----|--------|-----------------|
| **G5** ⚠️ | **CRITICAL: Ontop crash-loop** — `atlas.obda` and `atlas.properties` not in `ontop/ontop:5` | Build custom Ontop image or mount mapping files | Blocks full deploy; GraphQL federation unusable |
| **G6** | Both Neptune endpoints wired to SLGD — LGD access broken | Pass LGD endpoint separately as context | Blocks Phase 2 behavioral-signal-agent |
| **G7** | `REGISTRY_ENDPOINT` never passed to `atlas-registry-mcp` | Verify boto3 fallback; fix if needed | Blocks registry MCP at runtime |
| **G8** | Cognito callback URL hardcoded as `atlas.example.com` | Wire `WholesaleUiUrl` as `productionCallbackUrl` | Blocks Cognito OAuth for UI login |
| **G9** | Lake Formation tags created but no table associations | Add tag associations or manual step | Blocks LF row/column scoping |
| **G10** | ECS circuit breaker missing on Ontop | Add `circuitBreaker: { rollback: true }` | 3-hour hang on bad deploy |
| **G11** | Neptune Sparql JDBC driver may be absent from Ontop image | Verify/include in custom image (related to G5) | Blocks Ontop SQL federation |

### POST-DEPLOY / PER-NOTEBOOK — CAPSTONE-CRITICAL ⚠️

| # | Gap | Action | Capstone impact |
|---|-----|--------|-----------------|
| **G12** ⚠️ | **CAPSTONE-CRITICAL: nb06 Phase 1 Cat 5 `defer()` unconditional** — 7 assertions about live AgentCore/Neptune never run | Replace `defer()` with conditional `check()` that reads CFN outputs and invokes deployed Runtimes | **Without this fix, the workshop never proves the architecture runs. This is the headline blocker for proving Thesis 1.** |
| **P2-G1** ⚠️ | **CAPSTONE-CRITICAL: Phase 2 nb06 acceptance is 100% local simulation** — all 20 assertions prove spec correctness, not deployment correctness | Write a "live integration" cell (or new notebook) that reads deployed CFN outputs (`AtlasSparqlMcpArn`, `ConversationalContextManagerArn`, `MemoryId`) and invokes them | **Without this fix, Thesis 2 is validated against descriptors, not against deployed infrastructure.** |
| **P2-G2** | `WealthUiUrl` not exported as CFN output — Wealth UI CloudFront URL inaccessible | Add `new cdk.CfnOutput(this, "WealthUiUrl", { value: cloudfront.wealthUiUrl })` to main stack | Blocks Wealth UI access post-deploy |
| **G13** | React UI apps not built or deployed — CloudFront serves empty buckets | Build + `aws s3 sync` for both UIs | Blocks UI rendering |
| **G14** | Page 03-mcp-servers shows `code: 401` but code uses `error_type: "persona_error"` | Fix page wording (one-line change) | Cosmetic — novice confusion only |
| **P2-G3** | Page 12-end-to-end shows `advisor-alex-morgan`; notebook uses `advisor-michael-ross` | Fix page expected output (one word) | Cosmetic — advisor name is a simulation artifact |
| **G15** | nb06 Cat 3 deferred (3.3, 3.4) — Lake Formation scoping | Depends on G9 | Blocks LF verification |

### PORTABILITY (post full-deploy)

G16–G20 from Pass 1: region hardcoding, US-only inference profile, LIVE-STATE IAM, VPC CIDR, cleanup page phantom stacks.

---

### Summary: what blocks "the capstone actually proves something"

The two CAPSTONE-CRITICAL gaps (G12 and P2-G1) are the ones that matter most given the workshop owner's decision. Everything else is either a deploy blocker (G5) or cosmetic/portability.

| Gap | What it blocks | Fix size |
|-----|---------------|----------|
| **G12** | Phase 1 nb06 Cat 5 never exercises deployed Runtimes/Neptune | Medium — add live check cells with CFN output reads + AgentCore invocations |
| **P2-G1** | Phase 2 nb06 never exercises deployed Memory/AppSync/JWT | Medium — add live integration cell or new acceptance notebook |
| **G5** | Ontop crashes on deploy | Large — custom Docker image required |
| **P2-G2** | Wealth UI CloudFront URL not findable | Small — one CFN output line |
| **G8** | Cognito OAuth broken | Small — one CDK line |


---

# PASS 3 — UI proof-path trace (Pattern 1 vs Pattern 2)

Read: both UI source trees, full GraphQL schema, resolver-patterns.md, AppSync construct,
and full atlas_sparql_mcp.py. Written to answer: which UI data needs Ontop (Pattern 1) vs
Neptune (Pattern 2), and can the capstone proof run on Pattern 2 alone today?

---

## Section A — The two UIs: what fields they actually request

Both UIs are **real, wired React apps** — not mocks. They use Apollo Client, GraphQL
operations are defined in typed `.ts` files, and hooks issue real queries. The React apps
are not yet built/deployed to S3 (G13), but the query definitions are complete and correct.

### Wholesale UI — screens and operations

| Screen | Operation | Fields requested |
|--------|-----------|-----------------|
| Dashboard | `DASHBOARD_QUERY` | `Customer { uri, customerId, label, household { uri, label, memberCount } }` + `WealthSignal { uri, signalType, strength, signalDate, provenance }` via `searchCustomers` |
| Entity 360 | `CUSTOMER_360_QUERY` | `Customer` + all sub-types: `Account { accountId, accountType, balanceUSD, transactions(limit:10) }`, `WealthSignal`, `AdvisoryRelationship { advisor, coverageStartDate/EndDate, relationshipType, isActive }`, `household.members` |
| Referral detail | `REFERRAL_DETAIL_QUERY` | `Household.members`, `WealthSignal`, `Referral { approvedRationale, referralDate, routingDecision { selectedRoute, humanReview } }` |
| Capability palette | `CAPABILITIES_QUERY` | `Capability { name, displayName, posture, capabilityTag, phase }` |
| Signal list | `WealthSignals` (hook) | `WealthSignal { signalType, strength, signalDate, provenance }` |
| Mutation: route | `ROUTE_REFERRAL_MUTATION` | returns `Referral { uri, routingDecision, provenance }` |
| Mutation: detect | `DETECT_SIGNALS_MUTATION` | returns `WealthSignal[]` |

### Wealth UI — screens and operations

| Screen | Operation | Fields requested |
|--------|-----------|-----------------|
| Advisor dashboard | `ADVISOR_DASHBOARD_QUERY` | `Customer { uri, customerId, label, advisoryRelationships { advisor.label, isActive, coverageStartDate } }` via `searchCustomers` |
| Client 360 | `CLIENT_360_QUERY` | `Customer` + `advisoryRelationships { advisor, dates, type, isActive }`, `wealthSignals`, `household.members` |
| Themes | `THEMES_QUERY` | `ThemeAssertion { uri, themeLabel, themeDate, sourceArticles }` via `themes` |
| Capability palette | `CAPABILITIES_QUERY` | Same as Wholesale UI |

---

## Section B — Resolver map: field → MCP call → backend

The schema docstrings state the intended resolver for each Query field. AppSync construct
creates proxy Lambdas for `sparqlMcpArn`, `registryMcpArn`, and `erMcpArn` only — all
other resolvers funnel through `atlas-sparql-mcp`. The full `atlas_sparql_mcp.py` confirms:
**`ONTOP_ECS_ENDPOINT` is read at startup but referenced nowhere in any code path.** All
three operations (`query`, `update`, `construct_and_validate`) route exclusively to Neptune
(`NEPTUNE_SLGD_ENDPOINT` or `NEPTUNE_LGD_ENDPOINT`).

| GraphQL field | Schema says (intended) | atlas-sparql-mcp does (actual) | Mismatch? |
|---------------|------------------------|-------------------------------|-----------|
| `customer(uri)` | "SPARQL via Ontop" | Neptune SLGD direct | **YES — P1 intended, P2 actual** |
| `household(uri)` | "SPARQL via Ontop" | Neptune SLGD direct | **YES** |
| `searchCustomers` | "SPARQL via Ontop" | Neptune SLGD direct | **YES** |
| `wealthSignals` | "Direct Neptune SPARQL" | Neptune SLGD direct | No mismatch |
| `advisoryRelationships` | "Direct Neptune SPARQL" | Neptune SLGD direct | No mismatch |
| `referrals` | "Direct Neptune SPARQL" | Neptune SLGD direct | No mismatch |
| `auditTrail` | "Direct Neptune SPARQL" | Neptune SLGD direct | No mismatch |
| `themes` | "Direct Neptune SPARQL" | Neptune SLGD direct | No mismatch |
| `capabilities` | "atlas-registry-mcp" | atlas-registry-mcp proxy Lambda | No mismatch |
| `resolveEntity` | "atlas-er-mcp" | atlas-er-mcp proxy Lambda | No mismatch |
| `routeReferral` mutation | "atlas-registry-mcp" | atlas-registry-mcp proxy | No mismatch |
| `detectSignals` mutation | "atlas-registry-mcp" | atlas-registry-mcp proxy | No mismatch |

**Three fields are intended to go through Ontop (Pattern 1) but currently route directly to Neptune:**
`customer`, `household`, `searchCustomers`.

---

## Section C — Which UI data genuinely needs Pattern 1 (Ontop/Iceberg)?

**The 200 promoted Customer entities ARE in the SLGD.** WS1 Module 5 wrote them with full PROV-O provenance (`atlas:promotedFrom`, `atlas:promotedBy`). WS1 Module 4 wrote `atlas:Transaction` triples to the LGD. `atlas:AdvisoryRelationship`, `atlas:WealthSignal`, `atlas:RoutingDecision`, `atlas:Referral`, and `atlas:AuditRecord` are all graph-native (Pattern 2 territory).

| Entity | In Neptune SLGD today? | In Athena/Iceberg? | Which path can serve it? |
|--------|----------------------|-------------------|--------------------------|
| `Customer` (uri, customerId, label, household) | **YES** — 200 promoted | YES (Parquet in S3, no Glue table) | **Pattern 2 works today** |
| `Account` (accountId, accountType, balanceUSD) | NO — accounts were generated but not promoted into SLGD; only the Customer wrapper was promoted | YES (Parquet in S3, no Glue table) | **Neither path fully works today; Pattern 2 partial** |
| `Transaction` (date, amount, type) | In LGD only (WS1 nb04 wrote to LGD) — NOT in SLGD | YES (Parquet in S3) | Pattern 2 via LGD (graph_tier=lgd); Pattern 1 needs Glue tables |
| `Household` (uri, label, members) | **YES** — household membership promoted in WS1 | YES (Parquet) | **Pattern 2 works today** |
| `WealthSignal` (signalType, strength, provenance) | **YES** — derived and written to SLGD in WS1 Module 5 | No | **Pattern 2 only (graph-native)** |
| `AdvisoryRelationship` (advisor, dates, type) | **YES** — 105 legacy relationships in SLGD | YES (Parquet, advisory-relationships) | **Pattern 2 works today** |
| `Referral`, `RoutingDecision`, `AuditRecord` | YES — created by the referral workflow | No | **Pattern 2 only (graph-native)** |
| `ThemeAssertion` | YES (stub) or NO — created by Phase 2 theme-summarizer | No | Pattern 2 after theme-summarizer runs |

**Conclusion:** The three Pattern-1-intended fields (`customer`, `household`, `searchCustomers`) are backed by data **already in the SLGD** from WS1 Module 5 promotion. Pattern 1 (Ontop/Iceberg) is the architecturally intended path — it demonstrates federation in place — but it is not the only path to the data. Pattern 2 can serve the same entities from Neptune today.

The one entity class that Pattern 2 cannot serve from the SLGD is `Account` — accounts were generated and uploaded to S3 (WS1 nb04) and written to the LGD as triples, but were NOT promoted to the SLGD. The `CUSTOMER_360_QUERY` requests `accounts` sub-fields. Those accounts exist in the LGD; if `atlas-sparql-mcp` queries SLGD for account data, it will return empty. **This is a gap independent of Pattern 1 vs Pattern 2** — it's a promotion gap. For the UI to render account balances and transactions, either (a) the SLGD must be populated with Account data (a WS1 nb04/05 extension), or (b) the resolver must route account queries to `graph_tier=lgd`.

---

## Section D — Pattern 1 completion cost (sizing only)

### D1 — Glue/Athena table creation (touches WS1)

**What must be created:** Glue database `atlas_workshop` + 3 tables:
- `customer_master` over `s3://atlas-ontology-staging-981814817046/data/iceberg/customer_master/`
- `transaction_history` over `s3://atlas-ontology-staging-981814817046/data/iceberg/transaction_history/`
- `advisory_relationships` — parquet not yet in S3 (advisory relationship data was loaded to Neptune via WS1 nb04 Pattern A but the parquet wasn't separately written to the Iceberg prefix)

**Where this step belongs:** WS1 `04_three_connection_patterns.ipynb`. The markdown describes step 4 as "create an Iceberg table via AWS Glue Data Catalog" but no code cell implements it. A new code cell using `glue.create_table()` or an Athena `CREATE TABLE ... USING ICEBERG` DDL must be added to nb04, after the Parquet upload cells.

**Risk:** This edits an already-deployed WS1 notebook (but is additive — adds a cell, doesn't change existing cells).

### D2 — Ontop image/config (G5, WS2 only)

Six changes (no WS1 touch):
1. `Dockerfile` at `use-case-applications/cdk/ontop/` — FROM ontop/ontop:5, COPY R2RML files, COPY atlas.properties, install Athena JDBC driver
2. `atlas.properties` — Athena JDBC connection config (key schema confirmed; exact values need Simba JDBC 3.x docs confirmation)
3. `ontop.ts` — `fromRegistry` → `fromAsset`; fix `ONTOP_MAPPING_FILE` from `.obda` to `.ttl`; fix JDBC_URL to Athena form (or remove — Athena JDBC URL belongs in properties file); add `circuitBreaker`; add `startPeriod`
4. ECS task IAM — add `athena:*`, `glue:Get*`, `s3:GetObject/PutObject` on data+results buckets
5. Athena JDBC driver JAR — source from AWS; must be committed to repo or fetched at Docker build time
6. Mapping format decision — Ontop 5 accepts R2RML `.ttl` directly; the single combined mapping must cover all 3 pattern-A/B tables

### D3 — atlas-sparql-mcp routing (WS2 only)

One code change to `atlas_sparql_mcp.py`: `_handle_query()` currently ignores `ONTOP_ECS_ENDPOINT` and always routes to Neptune. To implement Pattern 1, the function needs a branch: when the query targets entity data (Customer, Account, Household — the Iceberg-backed types), route to Ontop's HTTP SPARQL endpoint; when the query targets graph-native data (WealthSignal, AdvisoryRelationship, Referral — the Neptune-native types), route to Neptune.

**The routing decision criteria:** The cleanest approach is a new `source` parameter in the MCP call (e.g., `source: "iceberg"` vs `source: "graph"`), set by the AppSync resolver based on the field type. The resolver knows which types come from Iceberg; the MCP just needs to be told. Alternatively, the MCP can inspect the query for specific type patterns. Either way this is a ~20-line code change in `_handle_query()`.

---

## Section E — Verdict and scope options

### Can the two UIs prove the system on Pattern 2 alone?

**PARTIAL — with two caveats:**

1. **`customer`, `household`, `searchCustomers`** — the three Pattern-1-intended fields can be served from Neptune SLGD today. Pattern 2 works for these. The UIs will render customer lists, household members, and the Entity 360 customer card.

2. **`accounts` sub-field (CUSTOMER_360_QUERY)** — Account data is in the LGD, not the SLGD. If the resolver queries SLGD for accounts, it returns empty. This is a gap independent of Pattern 1/2: either accounts must be promoted to SLGD (a WS1 extension), or the resolver must explicitly use `graph_tier=lgd` for account queries. **Without this fix, the Entity 360 screen will render the customer card but show empty account balances and transaction history.**

3. All graph-native data (WealthSignal, AdvisoryRelationship, Referral, AuditRecord) works on Pattern 2 today — these live in Neptune.

4. `themes` (Wealth UI) depends on Phase 2 theme-summarizer having run; if no ThemeAssertion instances exist in the graph, the themes page renders empty.

5. `resolveEntity` (atlas-er-mcp) — requires the `atlas-entity-resolution` ER workflow to exist (G3, unverified).

---

### Option X — Capstone proves via Pattern 2 now; Pattern 1 completed after

**Critical path:**
1. Fix the remaining deploy blockers: CDK bootstrap (G1), S3 file uploads (G2), ER workflow verification (G3), Cognito callback URL (G8), Ontop Dockerfile — but scoped to a **non-crashing Ontop** rather than a functioning one (the container must start; it doesn't need to serve queries yet). A stub `atlas.properties` pointing at a dummy JDBC URL would satisfy this — Ontop would start, the health check would pass, and Pattern 1 queries would fail gracefully (Ontop returns SPARQL error; MCP returns structured error; UI shows "data unavailable"). **OR** disable Ontop entirely in the first deploy: set `ONTOP_MAPPING_FILE` to a no-op, comment it out of the construct, and document it as "federation path coming in next sprint."
2. Fix the `accounts` routing gap: promote Account/Transaction data to SLGD (preferred, aligns with the architecture), or route account queries to `graph_tier=lgd` (simpler, but architecturally inconsistent).
3. Deploy. Run Phase 1 nb06 Category 5 assertions against live infrastructure (they require editing the deferred `defer()` calls to real `check()` logic — G12).
4. Pattern 1 (Ontop federation) completed as follow-on: WS1 nb04 Glue table step, Ontop config, MCP routing change.

**What's deferred:** Full federation-in-place (Pattern 1). The workshop teaches the architecture but doesn't exercise the Ontop path in the capstone proof run.

**What's gained:** A deployed, working two-UI system that proves Pattern 2 (Neptune SPARQL), agent orchestration, and the audit trail — the core of the capstone claim.

---

### Option Y — Complete Pattern 1 fully before first deploy

**Critical path:** Everything in Option X, plus:
1. WS1 nb04: add Glue table creation cell (edits deployed WS1)
2. Author `atlas.properties` (Athena JDBC config — needs Simba JDBC 3.x docs confirmation first)
3. Source Athena JDBC driver JAR (external dependency)
4. Dockerfile authoring
5. Fix `ONTOP_MAPPING_FILE` and JDBC target in `ontop.ts`
6. Add IAM for Athena/Glue/S3 to ECS task role
7. Fix `atlas-sparql-mcp` routing (20-line code change)
8. Verify Athena queries work against the Glue tables (likely requires a test run inside the VPC)

**Dependencies and risks:**
- Step 2 has an unresolved external dependency (Simba JDBC 3.x config needs confirmation; wrong config = Ontop silent failure)
- Step 1 requires editing WS1 (deployed, working) — low risk but real risk
- Steps 3–8 are all WS2-only; the CDK rebuild is self-contained

**What's gained:** The first deploy exercises both read paths. The workshop teaches what it says it teaches from day one.

**What's risked:** Delayed first proof. If the Athena JDBC config is wrong or the Glue tables don't query correctly through Ontop, debugging happens in a partially-deployed environment rather than against a known-working Neptune baseline.

---

*This section read: wholesale-ui/src/graphql/{queries,fragments,mutations}.ts, wealth-ui/src/graphql/queries.ts, all UI hooks, spec/05-appsync-graphql/schema.graphql, spec/05-appsync-graphql/resolver-patterns.md, cdk/lib/constructs/appsync.ts (already read in Pass 1), and the complete atlas_sparql_mcp.py (294 lines). No content was summarized — all was read in full.*

---

## NoAdvisorCoverageSignal — RESOLVED (derived WS2-side, no WS1 change)

> **STATUS UPDATE (supersedes the descoped note below):** NoAdvisorCoverage is now
> **live and derived entirely Workshop-2-side**, with no Workshop 1 change. The original
> conclusion below — that this required a WS1 derivation pass — turned out to be wrong:
> WS2 can attach `atlas-part-2:` signals to WS1 customer URIs via `atlas:producesSignal`
> using the SLGD `update` path, exactly as it loads its own ontology concepts.
> Implementation: `use-case-applications/scripts/derive-no-advisor-coverage.py` (gate-C
> CONSTRUCT + `validate_signals()` pyshacl gate + `insert_query()`), with the concept
> loaded by `scripts/load-ws2-ontology-concepts.py`. 40 signals derived and validated
> (incl. demo customer c6b6e4ad). The gate is "already wealth-signalled AND uncovered"
> (not a census of all uncovered), and the absence signal honestly omits evidencedBy/
> signalDate. Taught in `notebooks/phase-1-referral/05_wealth_signals.ipynb`. The
> historical descope analysis is retained below for the record.

**What it is:** A coverage-gap signal: a customer has investable assets but no active wealth advisor. Semantically distinct from `atlas:LargeDepositPattern` (a deposit event) and `atlas:HouseholdAggregationSignal` (a household aggregate). It would be the most actionable signal for a consumer banker — the referral target is unambiguous.

**Why it was originally descoped (2026-05-31, since superseded):** the analysis held that WS1 never derives this type and that enabling it WS2-side would require inserting a signal the substrate doesn't produce. The gap in that reasoning: deriving (via CONSTRUCT) and *validating* a signal WS2-side, then writing it with full provenance, is *not* hand-insertion — it is the same derive-don't-insert discipline WS1 uses, just owned by WS2. That is what `derive-no-advisor-coverage.py` does.

**How to implement (future WS1 pass):**

1. Add `atlas-part-2:NoAdvisorCoverageSignal` to `agentic-semantic-layer/ontology/atlas-part2-extensions.ttl` (or equivalent WS2 extension TTL) under the `atlas-part-2:` namespace.
2. Add a derivation step in WS1 `nb05 cell-09f-derive-signals-live` (or a new cell-09h) that runs the coverage-gap rule: for each promoted Customer with a CHECKING or SAVINGS balance above a threshold AND no active AdvisoryRelationship, derive a `NoAdvisorCoverageSignal` instance.
3. The SPARQL must use MINUS (not nested FILTER NOT EXISTS) to avoid Neptune's false-negative on nested negation. The correct pattern is in `prompts/signal-queries/no-advisor-coverage.sparql`.
4. Re-enable the entry in `PHASE_1_SIGNALS` in `wealth_signal_detector.py`.

**Neptune FILTER NOT EXISTS note:** Nested `FILTER NOT EXISTS { ... FILTER NOT EXISTS { ... } }` returns false negatives on Neptune — covered customers are classified as uncovered. Use `MINUS` or `OPTIONAL { ... } + FILTER(!bound(?x))` instead. This was confirmed against the live cluster on 2026-05-31 (see WS1 surgical clean documentation).
