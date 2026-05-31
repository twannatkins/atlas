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
| 6 | `05_wholesale_ui.ipynb` |
| 7 | `06_phase_1_acceptance.ipynb` |

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

### 05_wholesale_ui.ipynb

- **TEACHES:** Two-driver UI architecture: GraphQL provides data, Agent Registry provides capabilities — neither hardcoded. Compliance banner enforces 31 U.S.C. §5318(g)(2) tipping-off prohibition. Human-in-the-loop: `referral-orchestrator` requires `approved_rationale`.
- **USER RUNS:** 8 cells — setup, simulate Entity 360 for Patel household, render compliance banner (Consumer Banker vs BSA Analyst), populate capability palettes from descriptors, simulate Route to advisor workflow, verify palette persona-scoping, verify banner tipping-off compliance, verify human-in-loop.
- **DEPENDS-ON-LIVE:** NONE — local descriptors only.
- **USER SEES (success):** `[PASS] Capability palette correctly persona-scoped. / [PASS] Compliance banner respects §5318(g)(2). / [PASS] Human-in-the-loop enforced.`
- **FAILS-IF:** Banner leaks "SAR" to Consumer Banker; palettes identical across personas; `approved_rationale` absent from orchestrator required fields.
- **GATE:** IN-MEMORY — no AWS calls. Regulatory compliance checks on local simulation.
- **WS2 resource needed:** None — local descriptors only.

### 06_phase_1_acceptance.ipynb

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

### 06-wholesale-ui ↔ 05_wholesale_ui.ipynb: ALIGNED

Entity 360 simulation, compliance banner rendering, capability palettes, and human-in-loop assertion all match the notebook code.

### 07-phase-1-acceptance ↔ 06_phase_1_acceptance.ipynb: ALIGNED

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
| R15 | nb06 Category 5 `defer()` calls are unconditional — will never auto-run after deploy | `06_phase_1_acceptance.ipynb:cell-07-cat5-e2e` | **MEDIUM** | The `defer()` function is called unconditionally regardless of whether Neptune is available. Re-running the notebook after deploy does NOT flip these to live checks; the code would need to be changed to replace `defer()` with `check()`. This means 5.1–5.7 will permanently show as DEFERRED. |

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
