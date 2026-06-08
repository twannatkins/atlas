# ATLAS Deployment Findings

## Module completion log

| Module | Status | Notes |
|--------|--------|-------|
| WS1 Module 3 — Two-Tier Neptune | COMPLETE | All 4 validation gates pass. 22 atlas: classes, 415 triples in SLGD. LGD empty. |
| WS1 Module 4 — Three Connection Patterns | COMPLETE | No errors. All 3 patterns generated triples; LGD populated. SigV4 signing fix applied pre-run. |
| WS1 Module 5 — Entity Resolution | COMPLETE | cell-06 SigV4 fix required (bare requests.post() silently wrote 0 triples; gate passed anyway via in-memory list). After fix: 200 promoted Customers, 1203 triples, all with PROV-O. SLGD: 1618 total triples. |
| WS1 Module 5 — Entity Resolution (live SLGD verify) | VALIDATED | Live SPARQL check: 1618 total triples, 200 promoted Customers, 200 with promotedBy, 22 ontology classes. All counts match. |
| WS1 Module 6 — SHACL Boundary | COMPLETE | Pure-local. All gates pass. Print summary + gate comment cosmetic fix applied (98945af). |
| WS1 Module 7 — Bedrock at the Edges | COMPLETE | Gate PASS at 6/7 (threshold 5). bedrock:InvokeModel added to both roles (LIVE-STATE — see Bedrock access entry). CQ6 deterministically fails (5/5). See CQ6 analysis below. |
| WS1 Module 8 — Wealth Signal Demo | COMPLETE | All 11 gates PASS. Audit trail complete: WealthSignal, Score (SHAP), RoutingDecision, HumanReview, AdvisoryRelationship, PROV-O provenance. CIO demo query returns results. See cell-14 engagement note below. |
| **WS1 ALL MODULES** | **COMPLETE** | **Modules 1–8 all gates green. SLGD: 1618 triples (ontology + 200 promoted customers). LGD populated (3 patterns). SHACL, NL→SPARQL, XGBoost scoring, and full audit narrative verified.** |

---

Issues found during the first live deployment of Workshop 1 (Modules 3–4)
and a subsequent novice-portability audit. Every finding is classified by
status so the distinction between "already fixed in code" and "only patched
in the live environment" is never ambiguous.

**Environment where findings were observed:**
Account `981814817046`, region `us-east-1`, SageMaker Unified Studio domain
`d-sifftmz3z1kz`, VPC `vpc-0ab6e0fb6982db7b6` (SageMakerUnifiedStudioVPC).
Two execution roles are active in this environment:
- `datazone_usr_role_4lfleqcmcaukvb_c030flvw7w5tlz` — the role the notebook
  kernel actually runs as (discovered mid-session; different from the domain
  default role)
- `datazone_usr_role_c2yrafi5xtlt7r_4wht3vjkoqsylj` — the domain default role

**All manual permission changes were applied to both roles.**

---

## Status legend

| Tag | Meaning |
|-----|---------|
| `FIXED` | Corrected and committed to the repo (include SHA) |
| `LIVE-STATE` | Applied to the running AWS environment but NOT in the repo — will not survive a fresh-account redeploy |
| `SELF-BITING` | Will break our own next redeploy in this or any account, not just a novice's first run |
| `NOVICE-ONLY` | Works for us in this account; blocks a cold novice in a different account |
| `CARRIES-TO-WS2` | Same pattern near-certainly recurs in the WS2 CDK stack; fix must cover both workshops |

Tags combine: e.g. `SELF-BITING + CARRIES-TO-WS2`.

---

## Module 8 — cell-14 CIO demo: illustrative graph, not live SLGD query

**Finding:** cell-14 ("The CIO Demo Query") builds a local `rdflib` graph (`g_demo`) from the `audit_triples` list constructed in cell-12, then runs the audit-trail SPARQL against that local graph. It does **not** query the live SLGD and does **not** use NL→SPARQL translation. The data is a single synthetic workflow (one customer, one signal, one routing decision) constructed entirely in memory.

**This is by design for the teaching narrative** — and it's consistent with the CQ6 decision: the audit-trail query is a pinned, version-controlled SPARQL artifact, not an LLM output. cell-14 demonstrates exactly that artifact against illustrative data.

**Engagement framing (have this ready):** When presenting Module 8 to a CIO or MRM reviewer, frame cell-14 as "here's the shape and completeness of the audit trail the system produces" — not "here's a live query against our populated graph." The distinction matters for credibility. The stronger version of this demo — running the same pinned query against the 200 real promoted customers in the live SLGD — is a post-WS1 enhancement (tracked in todo list).

**Connection to CQ6:** The same query that deterministically failed NL→SPARQL translation in Module 7 succeeds here precisely because it's a pinned artifact, not generated. The two modules are consistent: LLM translation is appropriate for conversational queries; compliance provenance chains are not.

**Tags:** `ENGAGEMENT-READINESS` + `POST-WS1-ENHANCEMENT` (upgrade cell-14 to query live SLGD; tracked)

---

## Module 7 — CQ6 (audit-trail query): deliberate LLM-at-the-edges boundary

**Verdict: DETERMINISTIC FAILURE — 5/5 runs fail, same syntax error (char ~1325, line 23, col 5).**

**Root cause (by design):** CQ6 is held out of the few-shot set. `nl_to_sparql()` uses `GROUND_TRUTH[:5]`; CQ6 is position 5 (never shown). It is also the most complex query — a 4-hop chain using `atlas:triggersRouting` and `atlas:conductedBy`, both absent from all five shown examples. The model has no pattern to match against.

**Decision: NOT adding CQ6 to few-shot examples.**
- Adding it would inflate the score from 6/7 to 7/7 by testing the model on a question it was handed. That proves memorization, not generalization.
- More importantly: the audit-trail query is compliance-critical. It should be a pinned, version-controlled SPARQL artifact — not something regenerated by an LLM on each invocation. CQ6 failing few-shot correctly marks the LLM-at-the-edges boundary: translation for conversational queries is appropriate; compliance provenance chains are not.

**Question-text mismatch (flagged, not fixed):**
- Test text: `"What is the audit trail from signal detection to advisor approval for customer C-001?"`
- Ground-truth text (position 5): `"What is the full audit trail from customer to advisor approval?"`
These differ — the test is more specific and adds "C-001." Aligning these (without changing the `[:5]` split) is a legitimate future tune that could help CQ6 pass without touching the few-shot architecture. Deferred.

**Framing for customer demos:** present CQ6 as a deliberate design choice — "The audit-trail query is a fixed, auditable SPARQL artifact managed in version control, not an LLM output. We apply the LLM only where natural-language variance is acceptable; compliance provenance chains are not that place."

**Tags:** `ENGAGEMENT-READINESS` + `CARRIES-TO-WS2` (WS2 NL→SPARQL inherits the same `[:5]` few-shot design and will face the same boundary on complex audit queries).

**Future tune (optional, not now):** Align CQ6 test-question phrasing to ground-truth phrasing. May resolve CQ6 without altering the few-shot split.

---

## Cross-cutting pattern: notebooks assume ambient state a clean run does not provide

**This is a class of defect, not isolated incidents.** Three observed instances share a root cause: notebook cells were authored assuming names/packages/helpers are already in scope, with no import cell that a top-to-bottom run reliably executes first.

| Instance | Notebook(s) | Symptom | Status |
|----------|-------------|---------|--------|
| (a) Unsigned Neptune calls | nb03, nb04, nb05 | `requests.post()` silently 403s under IAM auth; gates print PASS via in-memory data | `FIXED` `f908971` / `da828cb` / `f4b6ace` |
| (b) Kernel-isolated pip setup | All WS1 notebooks | `pip install` in terminal installs to wrong Python; `rdflib` not found in kernel | `FIXED` `4ce1d36` (cell-00-setup pattern) |
| (c) Missing import cell | nb06 only | `Graph`, `ATLAS`, `INST`, `pyshacl`, etc. never imported anywhere; NameError on cell-04 for every user | `FIXED` this commit (cell-02-imports added) |

**Tags:** `NOVICE-WOULD-HIT` + `CARRIES-TO-WS2` — WS2 agents and notebooks may carry the same patterns; audit each before first run.

**nb06 static validation (post-fix):** PASS — all watched names defined before first use across all 15 cells (corrected checker handles tuple unpacks and string literals).

**nb08 pre-run audit (all-uses logic, not first-use):** PASS — no names used before definition. Structurally sound.

---

## Cross-cutting pattern: bare `requests.post()` to Neptune under IAM auth

**This is a class of bug, not three coincidences.** Every notebook that writes or reads Neptune was authored with bare `requests.post()`. Under `IamAuthEnabled: true`, every such call silently 403s. The validation gates still print PASS because they check in-memory Python data structures, not the live graph.

| Notebook | Cell | Status | SHA |
|----------|------|--------|-----|
| `03_two_tier_neptune.ipynb` | `cell-07-load-neptune` | `FIXED` | `f908971` |
| `04_three_connection_patterns.ipynb` | `cell-10-write-lgd` | `FIXED` | `da828cb` |
| `05_entity_resolution.ipynb` | `cell-06` | `FIXED` | `f4b6ace` |
| `06_shacl_boundary.ipynb` | N/A | `PURE-LOCAL` — never touches Neptune; no fix needed |
| `07_bedrock_at_edges.ipynb` | Not yet audited | Pre-check before running |
| `08_wealth_signal_demo.ipynb` | Not yet audited — **pre-check before running** | |

**Tags:** `NOVICE-WOULD-HIT` + `CARRIES-TO-WS2` (WS2 agents do the same Neptune writes via MCP servers — expect the pattern there too; the SigV4 signing in `atlas_neptune.NeptuneClient` is correct but any notebook that bypasses it by calling `requests.post()` directly will 403 silently).

**The fix pattern** (same in all three fixed cells): replace bare `requests.post()` with `AWSRequest` + `SigV4Auth` + `requests.Request(..., headers=dict(aw.headers)).prepare()` + `Session.send()`. This preserves signed headers without letting `requests` rewrite them. See `cell-07-load-neptune` in nb03 for the canonical implementation.

---

## Findings — Runtime issues (Module 3 live deploy)

| # | Finding | Root cause | Status | Fix | Location |
|---|---------|-----------|--------|-----|----------|
| R1 | CFN stack rolled back on first deploy | `Description: >` on IAM ManagedPolicy folds to a string with a trailing `\n`; IAM description regex rejects newline characters | `FIXED` `5e2fb35` | Changed `>` to `>-` | `agentic-semantic-layer/infrastructure/atlas-neptune-twotier.yaml` |
| R2 | Neptune IAM policy ARN used logical ID instead of cluster resource ID | `!Sub '${LGDCluster}/*'` resolves to the CFN logical resource name, not the `cluster-XXXX` resource ID that Neptune IAM auth requires | `FIXED` `983e54d` | Changed to `!GetAtt LGDCluster.ClusterResourceId` inside a `!Sub` map | `atlas-neptune-twotier.yaml` lines 181–186 |
| R3 | `rdflib` / `pyshacl` not found in notebook kernel | SageMaker Unified Studio `project.python` kernel is isolated from the terminal Python; `pip install` in terminal installs to the wrong interpreter | `FIXED` `4ce1d36` | Added `cell-00-setup` to all 7 WS1 notebooks; installs via `sys.executable` | All `agentic-semantic-layer/notebooks/*.ipynb` |
| R4 | Setup cell `pip` crashed with `FileNotFoundError: os.getcwd()` | SageMaker virtualfs makes `os.getcwd()` fail inside a subprocess launched from the notebook kernel | `FIXED` `8235da9` | Pass `cwd='/tmp'` to `subprocess.check_call()`; resolve requirements path in parent process | `cell-00-setup` in all WS1 notebooks |
| R5 | Dependency conflict warnings from `requirements.txt` | `boto3`, `botocore`, `pandas`, `pyarrow`, `numpy`, `requests` were pinned to Workshop-era versions that SageMaker Distribution ships newer | `FIXED` `adf2edd` | Unpinned SageMaker-provided packages; only `rdflib`, `pyshacl`, `faker`, `xgboost`, `scikit-learn` remain pinned | `notebooks/shared/requirements.txt` |
| R6 | Neptune SPARQL calls returned 403 `Missing Authentication Token` | SigV4 signing bug: (a) `requests.post()` rewrites the `Host` header, invalidating the signature; (b) `aws_req.prepare()` returns `AWSPreparedRequest` which `requests.Session.send()` cannot consume | `FIXED` `f908971` | Sign with `AWSRequest`, then convert to `requests.PreparedRequest` via `requests.Request(..., headers=dict(aws_req.headers)).prepare()`, then send with `Session.send()` | `notebooks/03_two_tier_neptune.ipynb` `cell-07-load-neptune` |
| R7 | Validation gate Gate 4 failed: `rds:DescribeDBClusters` AccessDenied | Neptune management API uses `rds:` IAM namespace; the inline policy added `neptune:DescribeDBClusters` which does not match | `LIVE-STATE` | Added `rds:DescribeDBClusters` scoped to both cluster ARNs in the inline policy `atlas-workshop-notebook-access` on both execution roles. **Not yet in repo — a fresh deploy would fail Gate 4.** Proposed fix: add `rds:DescribeDBClusters` to the `atlas-neptune-iam-auth` managed policy in `atlas-neptune-twotier.yaml` | Both execution roles (live environment only) |
| R8 | Two execution roles; only one initially patched | SageMaker Unified Studio has a domain default role and a separate role used by the running kernel. Permissions applied to the wrong role silently did nothing. | `LIVE-STATE` | Applied all permission changes to both roles. **This account-specific fact must be remembered for every future permission change (Bedrock InvokeModel in Modules 7–8 especially).** Not declarative — a fresh deploy creates one role and the two-role split would need to be re-discovered. | `datazone_usr_role_4lfleqcmcaukvb_c030flvw7w5tlz` and `datazone_usr_role_c2yrafi5xtlt7r_4wht3vjkoqsylj` |

---

## Findings — Live-state permissions (not yet in repo)

These were applied manually to the running environment and will not survive a fresh-account redeploy.

| # | Finding | What was applied | Status | Proposed declarative fix |
|---|---------|-----------------|--------|-------------------------|
| L1 | `atlas-neptune-iam-auth` not auto-attached by CFN | The CFN template creates the managed policy but does not attach it to any role. Must be manually attached to the Studio execution role(s) after stack deploy. | `LIVE-STATE` `SELF-BITING` | Add attachment instructions to prerequisites page as a step that runs after Module 3 CFN deploy. Long-term: a post-deploy Lambda custom resource could attach it automatically, but that's WS2-era complexity. |
| L2 | `cloudformation:DescribeStacks` on stack ARN | Added via inline policy `atlas-workshop-notebook-access` on both roles | `LIVE-STATE` | Add to prerequisites page IAM setup instructions |
| L3 | `s3:PutObject / GetObject / ListBucket` on staging bucket | Added via inline policy `atlas-workshop-notebook-access` on both roles | `LIVE-STATE` | Same as L2 |
| L4 | `rds:DescribeDBClusters` on both cluster ARNs | Added via inline policy `atlas-workshop-notebook-access` on both roles | `LIVE-STATE` | Add to `atlas-neptune-iam-auth` managed policy in CFN template so it ships with the policy automatically (see R7) |
| L5 | `atlas-neptune-iam-auth` v3 uses `neptune-db:*` on `*` | Set during debugging; not the intended scoped policy | `FIXED` | Restored to scoped v2: 4 actions (`ReadDataViaQuery`, `WriteDataViaQuery`, `GetQueryStatus`, `CancelQuery`) on 2 cluster ARNs. v3 deleted. Non-regression verified: 1618 triples / 200 promoted customers / 22 classes. Live policy now matches CFN template. |

---

## Findings — Portability (novice in a different account)

| # | Finding | Root cause | Status | Proposed fix |
|---|---------|-----------|--------|-------------|
| P1 | `us-east-1` hardcoded in CFN deploy instructions, notebook `boto3.client()` calls, and prerequisites page | No region parameterization; Bedrock cross-region inference profile IDs are also US-only | `NOVICE-ONLY` `CARRIES-TO-WS2` | Add `REGION` constant read from boto3 session at top of each notebook; note in prerequisites that `us.anthropic.claude-sonnet-4-6` requires a US region |
| P2 | VPC CIDR default `10.0.0.0/16` in CFN template | If attendee's VPC is `172.31.0.0/16` (the AWS default VPC), the Neptune security group ingress rule blocks all traffic | `NOVICE-ONLY` `SELF-BITING` | Prerequisites should instruct attendee to provide their VPC CIDR; CFN parameter default should be removed or changed to `0.0.0.0/0` (allow within VPC via security group, not CIDR) |
| P3 | Attendee must discover their Studio domain's VPC ID manually | Prerequisites page says "SageMaker console → Domains → VPC" but Unified Studio domain VPC is not shown in the console the same way; VpcOnly domains may show `None` in `list-domains` | `NOVICE-ONLY` | Add a setup cell to nb03 that calls `sagemaker.list_domains()` + `describe_domain()` to auto-detect VPC and subnet IDs |
| P4 | `atlas-neptune-s3-access` and `atlas-neptune-iam-auth` are hardcoded names | If these names already exist (account reuse, multi-user, prior failed deploy), CFN CREATE fails with "already exists" | `SELF-BITING` `NOVICE-ONLY` | Add `DeletionPolicy: Delete` and `UpdateReplacePolicy: Delete` to both IAM resources, or add a stack-name prefix to the resource names |
| P5 | `atlas-neptune-iam-auth` attach ordering is wrong in prerequisites | The prerequisites page describes attaching the policy before Module 3 is run, but the policy doesn't exist until after Module 3 deploys the CFN stack | `NOVICE-ONLY` | Rewrite IAM section in prerequisites: initial permissions only, then after Module 3 CFN deploy, add the Neptune policy attachment as Step X.5 in the Module 3 notebook guide |
| P6 | Execution role discovery instructions assume classic SageMaker domain | Prerequisites says find execution role at "Domains → Execution role" but Unified Studio uses a DataZone-managed role with a non-standard name pattern | `NOVICE-ONLY` | Add a terminal command to auto-identify the execution role: `aws sts get-caller-identity --query Arn` run from the Studio terminal |
| P7 | `ROLLBACK_COMPLETE` state not handled in notebook | If CFN deploy fails and rolls back, the notebook cell raises a confusing `ClientError` with no remediation guidance | `SELF-BITING` `NOVICE-ONLY` | Add `ROLLBACK_COMPLETE` to the exception handler in `cell-03-stack-outputs` with a clear message: "Your stack failed to deploy. Delete it with `aws cloudformation delete-stack --stack-name atlas-neptune-twotier` and redeploy." |

---

## Deferred work — portability refactor

The full novice-portability refactor (P1–P7 above) is **deferred until WS1 Modules 1–8 and WS2
are both fully deployed and verified** in this environment. Reasons:

1. Several fixes require changes to notebooks that have not yet been run live (Modules 4–8). Fixing
   before running risks introducing regressions in untested code paths.
2. The WS2 CDK stack has analogous issues (hardcoded regions, `${AWS::AccountId}` bucket names,
   inference profile IDs). The portability pass should cover both workshops in a single sweep so
   fixes are consistent.

**Scope of the deferred portability pass:**
- All WS1 notebooks: region parameterization, VPC auto-discovery helper, IAM section rewrite in prerequisites
- WS2 CDK `cdk.json` context params: document the required values (Neptune endpoints, VPC ID, subnet IDs) as outputs from WS1 CFN stack
- WS2 inference profile IDs: `us.anthropic.claude-sonnet-4-6` is US cross-region only — add a non-US fallback or a clear region requirement
- Both workshops: update the portability note in the top-level README

---

## WS2 Deployment fixes — resolved issues

| # | Issue | Resolution | Status |
|---|-------|-----------|--------|
| G1 | **AgentCore entrypoint** — `["opentelemetry-instrument","main.py"]` failed at runtime (OTEL exe not in raw source ZIP). `["python","main.py"]` rejected by AgentCore server-side validator (system executables blocked as launchers). | Changed to `["main.py"]` — the managed PYTHON_3_12 runtime invokes the script directly. Confirmed via live API probe: passes entrypoint validation, advances to S3 check. | `FIXED` |
| G1-OBS | **Observability accuracy** — prior tracking overstated the gap as "removes distributed tracing (publication blocker)." Research confirmed: AgentCore provides **native CloudWatch observability automatically** (per-invocation metrics, spans, logs, trace IDs) without bundling OTEL. `opentelemetry-instrument` is optional enhancement for *custom framework-level traces* (LangGraph reasoning steps, GenAI semantic convention spans) — not required for SR 11-7 baseline audit coverage. | No action needed for capstone. If richer framework tracing is desired, bundle ADOT via `BundlingOptions` + Docker or a pre-built container image in a future pass. | `INFORMATIONAL` |
| G2 | **Memory rollback-race** — AgentCore Memory orphaned (billing) during rollback because CFN could provision Memory while runtimes were still creating; a runtime failure then left Memory in CREATING state (cannot delete mid-transition). | Added 33-entry `DependsOn` on Memory construct: all 11 non-CCM runtimes + their roles/policies. CCM excluded (would cycle via `grantFullAccess` token). Memory now creates only after 11 runtimes succeed. Confirmed working: zero Memory CREATE_FAILED on the race-fix deploy. | `FIXED` (partial — CCM-specific failure residual risk remains; see comment in `agentcore-runtimes.ts`) |
| G3 | **Runtime dependency packaging** — all 12 `main.py` files import `from bedrock_agentcore.runtime import BedrockAgentCoreApp` (a ~600-line Starlette/uvicorn ASGI server for the AgentCore `/invocations` + `/ping` HTTP contract). `bedrock-agentcore` was missing from every `requirements.txt` and `fromCodeAsset` ships a raw source ZIP with no `pip install`. Runtimes fail on import → 30s timeout. CREATE_COMPLETE is deceptive: the runtimes provision green but crash at first invocation. | Added `bedrock-agentcore==1.11.0` to all 12 `requirements.txt`. Added gated `bundleRuntimeDeps` flag (default OFF) to `agentcore-runtimes.ts`: when `true`, Docker BundlingOptions pip-install the requirements into the ZIP at synth time. **Flag is OFF by default** — committed repo still ships raw ZIPs (Studio-safe). Enable with `-c bundleRuntimeDeps=true` for environments with Docker at synth. See below for the publication fix. | `PARTIAL` — capstone works with flag ON; publication requires Option C (see below) |

**G3 — Runtime packaging: publication fix required (PUBLICATION BLOCKER)**

The gated Docker BundlingOptions closes the gap for local development (Docker running), but is **self-biting for the published workshop**: SageMaker Studio / SageMaker Unified Studio notebook kernels have no Docker daemon. A runner following the workshop from Studio (the intended environment) cannot run `cdk synth` with `bundleRuntimeDeps=true` — it fails immediately.

**Option C — portable pre-bundled ZIPs (the publication fix, no Docker at synth):**

Create `scripts/build-runtimes.sh`. For each of the 12 runtimes:
```bash
cd <runtime-dir>
pip install -r requirements.txt -t ./build --quiet
cp *.py ./build/
zip -r runtime-<name>.zip build/
aws s3 cp runtime-<name>.zip s3://<staging-bucket>/runtimes/<name>.zip
```
Then update `agentcore-runtimes.ts` to use `AgentRuntimeArtifact.fromS3(...)` referencing the pre-built ZIPs in the staging bucket. CDK synth needs no Docker — it just reads the S3 key. The build script is a documented workshop prerequisite (run once after deploying WS1, before deploying WS2).

**Option B — ECR images (AWS-canonical pattern, production-shape):**
Per `agentcore-samples` CDK examples: build a Docker image per runtime (or a shared base), push to ECR, reference via `fromImageUri`. CodeBuild + ECR is the AWS-recommended path. Requires a build pipeline but zero Docker at `cdk synth`. This is the right long-term answer if the workshop evolves toward production-shaped deployment.

**Status:** Option C is the PUBLICATION BLOCKER — the workshop cannot be published without it or Option B. Tracked here; the gated flag is the capstone-proof bridge.

---

## WS2 watch-list (predicted, unverified)

Based on WS1 findings, watch for these in the WS2 CDK deploy:

| Item | Predicted issue | Based on |
|------|----------------|----------|
| CDK context params | `cdk.json` requires `neptuneClusterEndpoint`, `neptuneClusterArn`, `vpcId`, `privateSubnetIds` — all currently empty strings; must be filled from WS1 CFN outputs before `cdk deploy` | WS1 CFN outputs |
| S3 bucket naming | `atlas-wholesale-ui-${ACCOUNT_ID}` and `atlas-wealth-ui-${ACCOUNT_ID}` use the same `${ACCOUNT_ID}` pattern; same naming-policy risk as the staging bucket | R2 analogue |
| Inference profile IDs | `us.anthropic.claude-sonnet-4-6` is a US cross-region inference profile. CDK stack, notebooks, and WS2 prereqs all hardcode it. Non-US deployers will get model-not-found errors | P1 |
| Cleanup page phantom stacks | `workshop/content/cleanup/index.md` references 8 CDK stack names (`atlas-wholesale-ui-stack`, etc.) but the CDK app defines exactly one stack (`AtlasWorkshop2`). `cdk destroy --all` is the correct command; the named stacks are stale. | Cleanup page audit |
| Bedrock InvokeModel on both roles | WS2 notebooks call Bedrock (Titan Embeddings, Claude Sonnet). Both execution roles will need `bedrock:InvokeModel`. The two-role split (R8) means both must be patched. | R8 |
| CDK `CAPABILITY_NAMED_IAM` equivalent | CDK stacks with named IAM resources sometimes need `--require-approval never` or explicit capability acknowledgement; check CDK deploy flags | R1 analogue |

---

## Fresh-account readiness — WS0 account-prep package requirements

This section captures every gap between "works in this account" and "works in a fresh AWS account."
It was produced from a live deployment audit of both workshops and is the requirements input for the
WS0 account-prep package. The full specification (including the networking baseline already documented)
lives in `docs/ws0-foundation-spec.md`; this section is the findings log cross-reference.

Items are tagged by delivery path: `[AUTOMATABLE]` (can be expressed in CFN/CDK), `[MANUAL]`
(requires a human console or CLI action; not CFN-expressible), or `[TOOLCHAIN]` (runner's local
environment, not the AWS account).

---

### FA1 — VPC, subnets, NAT gateway `[AUTOMATABLE]`

**Finding:** WS1's CFN template takes `VpcId` and `SubnetIds` as required parameters and creates
neither. WS2 CDK imports the VPC by ID. Neither workshop provisions networking. In this account the
SageMaker Unified Studio domain VPC served as the shared baseline. In a fresh account no such VPC
exists.

WS2 additionally requires a NAT gateway (or equivalent VPC endpoints) for private-subnet resources
to reach the internet: ECS Fargate tasks need NAT to pull ECR images; Lambda functions need NAT for
Bedrock API calls; without it, WS2 Modules 7–8 fail silently with no useful error.

**VpcCidr alignment hazard:** WS1's `NeptuneSecurityGroup` ingress uses `VpcCidr` (default
`10.0.0.0/16`). The AWS default VPC is `172.31.0.0/16`. A runner who supplies their default VPC
without updating `VpcCidr` will deploy successfully but Neptune will be unreachable — no error at
deploy time, silent 403 at query time. `[SELF-BITING NOVICE-ONLY]`

**Proposed fix:** Foundation template provisions VPC with CIDR `10.0.0.0/16` (non-default, avoids
collision), 2 public + 2+ private subnets across AZs, NAT gateway, and exports `atlas-foundation-vpc-id`,
`atlas-foundation-private-subnet-ids`, `atlas-foundation-vpc-cidr`. Full spec in
`docs/ws0-foundation-spec.md §What the Foundation template must provision`.

---

### FA2 — SageMaker Studio domain and the two-execution-role problem `[AUTOMATABLE]` (if Studio required)

**Finding:** WS1 and WS2 notebooks run inside SageMaker Unified Studio. The domain, user profile, and
execution role(s) must pre-exist. SageMaker Unified Studio (DataZone-backed) creates **two separate
DataZone-managed execution roles**: a domain default role and a kernel-running role. The notebook kernel
actually runs as the kernel role. Applying IAM permissions only to the domain default role does nothing.

This was discovered mid-session (finding R8). Both roles must receive every permission below. Until
the Foundation template provisions an explicit execution role and configures Studio to use it, any
permission change must be applied twice — and the second role is not obvious from the console.

**Consequence:** any single-role permission grant silently fails for notebook cells. Gates print PASS
from in-memory data; actual Neptune/Bedrock writes return 403.

**Open question:** if Studio is no longer required (runners use JupyterHub or Cloud9), this item drops.
See `docs/ws0-foundation-spec.md §Open questions`.

---

### FA3 — WS1 does not attach its own IAM policy `[AUTOMATABLE]` post-WS1

**Finding (L1, `LIVE-STATE SELF-BITING`):** WS1 CFN creates `atlas-neptune-iam-auth` but never
attaches it to any role. A fresh deploy leaves the policy orphaned. The notebook execution role cannot
reach Neptune with IAM auth until the policy is manually attached to both execution roles.

**Additional permissions not granted by WS1 CFN (L2–L4, `LIVE-STATE`):**
- `cloudformation:DescribeStacks` — notebooks read their own CFN outputs
- `s3:PutObject / GetObject / ListBucket` on the staging bucket — bulk load and artifact reads
- `rds:DescribeDBClusters` on both Neptune cluster ARNs — WS1 Gate 4

**Also required for WS1 Modules 7–8 and WS2:**
- `bedrock:InvokeModel` on Titan Embeddings and Claude Sonnet ARNs

**Consequence:** WS1 Gate 4 fails silently. Neptune writes 403 with no useful error. WS1 Modules 7–8
fail with `AccessDeniedException`. WS2 agents that call Bedrock error or return empty responses.

**Proposed fix:** Foundation runbook step (after WS1 CFN deploy): attach `atlas-neptune-iam-auth` to
both execution roles and add an inline policy covering the above actions. Long-term: Foundation template
provisions a single explicit role with all required permissions; Studio domain uses that role.

---

### FA4 — IDC persona groups for WS2 `[AUTOMATABLE]` (if IDC enabled)

**Finding:** WS2 Cognito federates from IAM Identity Center. Five groups must exist before WS2 deploys:
`atlas-consumer-banker`, `atlas-wealth-advisor`, `atlas-bsa-analyst`, `atlas-ontology-steward`,
`atlas-auditor`. If they are absent, WS2 CDK deploy succeeds but all authenticated users receive the
default (no-persona) policy — the four-layer permission model collapses silently.

**Automatable via CFN Custom Resource** once IDC is enabled (see FB2 below). Group creation uses the
`aws identitystore` API, which is callable from Lambda.

**Consequence:** persona gating non-functional. Consumer Banker sees all customers. Regulatory teaching
story breaks. Not caught at deploy time — a subtle runtime failure.

---

### FA5 — Lake Formation admin grant `[AUTOMATABLE]`

**Finding:** WS2's `LakeFormationConstruct` (currently commented out) requires `lakeformation:CreateLFTag`
on the catalog. The CDK CFN execution role is not an LF admin by default. Fresh account deploy fails
with `AccessDenied`.

`put-data-lake-settings` grants the CDK execution role LF admin rights. Can be delivered as a
CFN Custom Resource Lambda in the Foundation template.

**Current status:** `LakeFormationConstruct` commented out — not exercised in Phase 1 capstone. Must
be re-enabled before persona-scoped data access (Layer 3 of the four-layer model) is demonstrated.
Full detail in `docs/ws0-foundation-spec.md §Lake Formation admin grant`.

---

### FA6 — CDK bootstrap `[AUTOMATABLE]` (one-time CLI)

**Finding:** WS2 deploys via CDK. `cdk bootstrap aws://<account>/us-east-1` must be run once in the
target account/region before `cdk deploy`. This creates `CDKToolkit`, the CDK assets bucket, and the
CDK execution role. Without it, `cdk deploy` fails immediately.

This is idempotent and safe to re-run. It should be step 1 in the WS0 runbook.

---

### FB1 — Bedrock model access enablement `[MANUAL]`

**Finding:** `bedrock:InvokeModel` in IAM is necessary but not sufficient. Model access is an
account-level entitlement enabled via the Bedrock console "Model access" page. There is no CFN
resource or API for this step. Required models:

- `amazon.titan-embed-text-v2:0` (WS1 Module 7, WS2 nl-to-sparql-agent)
- `us.anthropic.claude-sonnet-4-6` (WS1 Module 7–8, WS2 referral-rationale-drafter, theme-summarizer)

**Non-US runners** must use `global.anthropic.claude-sonnet-4-6`. Currently hardcoded throughout
(portability refactor deferred — see FC2).

**Consequence:** WS1 Modules 7–8 fail with `AccessDeniedException`. Three WS2 agents return errors
or empty responses.

---

### FB2 — IAM Identity Center enablement `[MANUAL]`

**Finding:** IDC persona groups (FA4) require IAM Identity Center to be enabled. A fresh AWS account
has IDC available but not active. Enabling IDC is a one-time console action with no CFN equivalent.

**Operator step:** IAM Identity Center console → Enable. Takes ~60 seconds; irreversible for the
account.

**Consequence if skipped:** IDC group creation fails. Cognito federation configuration fails at the
WS2 CDK deploy step that creates the Cognito–IDC federation.

---

### FC1 — Docker required at `cdk synth` time `[TOOLCHAIN]`

**Finding:** WS2's `OrchestratorRegistrationConstruct` uses `Code.fromAsset` with Docker
`BundlingOptions` to pip-install `boto3>=1.43` into the Lambda ZIP. If Docker is not running on the
machine executing `cdk synth`, synth fails with a Docker daemon connection error before any CloudFormation
call is made.

A runner using a browser-based Cloud9 environment, a SageMaker terminal, or any environment without
Docker will be blocked.

**Options for a future pass (not solved now):**
- Pre-build the Lambda ZIP and commit or store it as a static asset (eliminates Docker at synth)
- Use a Lambda layer pinning boto3 (no per-function bundling)
- Replace the custom resource with a CDK `AwsCustomResource` that uses the CDK provider's built-in
  boto3 (which is always current in the provider Lambda runtime)

**Consequence:** `cdk synth` and `cdk deploy` both fail before reaching CloudFormation.

---

### FC2 — Region hardcoding: `us-east-1` and `us.` inference profile `[TOOLCHAIN]`

**Finding (P1, `NOVICE-ONLY CARRIES-TO-WS2`, deferred):**
- All 12 WS2 AgentCore runtime environment variables hardcode `BEDROCK_TEXT_MODEL_ID: "us.anthropic.claude-sonnet-4-6"`
- WS1 notebooks default all `boto3.client()` calls to `us-east-1`
- WS2 `cdk.json` and CDK stack assume `us-east-1`
- `us.anthropic.claude-sonnet-4-6` is the US cross-region pool only; non-US runners need `global.*`

Full portability refactor is deferred until both workshops are verified end-to-end in this account.
Must be completed before offering the workshop outside `us-east-1`.

---

### FD1 — Ontop mapping files: content gap, not account-prep gap `[CONTENT]`

**Finding:** WS2 Ontop ECS service is deployed with `desiredCount: 0` because `atlas.obda` and
`atlas.properties` do not yet exist. The container exits immediately at startup without them. This is
a content authoring gap (the R2RML/OBDA mappings must be written), not a missing account prerequisite.
The account is correctly configured; the WS0 package does not need to address this.

Tracked here to prevent confusion when the Ontop pass runs: the account is ready; the work is content.

---

### Cross-reference to `docs/ws0-foundation-spec.md`

The full specification for the WS0 Foundation package (what to build, how WS1/WS2 consume it, open
questions, export names) lives in `docs/ws0-foundation-spec.md`. This section is the findings log:
what was discovered during live deployment, in the order it was discovered. The spec is the design;
the findings are the evidence.

---

## WS1 Live SLGD Pipeline — completion record

**Branch:** `feature/agentcore-native` (HEAD `5b8faf9`)  
**Date completed:** 2026-05-31  
**Verified:** SLGD PIPELINE VERIFICATION: PASS

Final SLGD state after pipeline run:
- 428 `atlas:Account` nodes with `promotedBy` + `hasAccount` links ✓
- 105 `atlas:AdvisoryRelationship` + 9 `atlas:Advisor` nodes with `promotedBy` ✓
- End-to-end traversal `customer-{id}-resolved → account-{id}-resolved → txn-{id}-resolved` confirmed ✓
- 2 `atlas:WealthSignal` instances derived (LargeDepositPattern), SHACL-validated, `evidencedBy` → live Transaction ✓

**Bugs fixed during live run (all committed):**
- `pyarrow==14.0.2` pin in setup cell fallback removed from all 7 WS1 notebooks (`1caa8c9`)
- nb04 verify cell: account count `>= 380` floor (non-deterministic RNG), advisor `9` not `10` (`ddcbf03`)
- nb05 `cell-06b`: was regenerating customers/accounts from scratch (different RNG state → wrong customer_ids → broken hasAccount chain) — fixed to reuse cell-04 scope variables (`14433b0`)
- nb05 `cell-09f`: SPARQL brace conflict in CONSTRUCT query (`a5c5452`)
- nb05 `sparql_construct_slgd`: Neptune requires POST not GET for CONSTRUCT (`5b8faf9`)
- nb05 verify cell: account counts changed to `>= 400` (same non-determinism), advisor `9` not `10`

**Status:** WS2 pre-flight ready to run.

---

## WS2 UI live-data readiness — named protagonists + display labels

**Date:** 2026-06-07 · **Account:** 981814817046 · **Branch:** `feature/agentcore-native`

The two "true-UI" designs (warm-paper cards: signals, capabilities, rationale, audit,
coverage, possible-next) are meant to be powered by LIVE WS1/WS2 graph queries, logged in
as the named protagonists. Diagnosed + fixed three gaps so they are:

| # | Finding | Resolution | Tag |
|---|---------|-----------|-----|
| U1 | The "0 clients / 0 results" screen was a STALE DEMO-LOGIN artifact, not a broken data path. Authenticated as the real Cognito users against live AppSync: searchCustomers, askGraph, customer(), draftRationale, capabilities ALL return real data. | No code fix — confirmed healthy. The demo localStorage path (IS_LOCAL_DEV) is unreachable on CloudFront. | (diagnosis) |
| U2 | Promoted customers/advisors/households carry no `rdfs:label` (ER promotion wrote customerId but no name) → UIs showed raw UUIDs. | `scripts/load_display_labels.py` writes 273 `rdfs:label` triples from the synthetic fixtures (customer-master.json / advisors.json) via the sparql MCP `update` op (SigV4 + WriteDataViaQuery). Customer `c6b6e4ad…`→"Rachel Kim", first WEALTH advisor→"Marcus Webb"; all others keep their fixture names. | `LIVE-STATE` — labels live in SLGD only; a fresh SLGD rebuild must re-run this script (or fold label promotion into 05_entity_resolution.ipynb — recommended follow-up). |
| U3 | Login users were `banker-test`/`advisor-test` with an opaque password; the workshop teaches logging in AS Rachel Kim / Marcus Webb. | `scripts/setup_workshop_users.sh` creates `rachel.kim@…` (atlas-consumer-banker, name "Rachel Kim") + `marcus.webb@…` (atlas-wealth-advisor, name "Marcus Webb"), password `password123`, deletes all other users. Pool password policy relaxed (min 8, no class requirements) to allow `password123`. `exchangeCodeForToken` now reads the OIDC `name` claim from the ID token for the app-bar display name. | `LIVE-STATE` — users + relaxed policy are account-state, not in repo CFN. The two scripts are committed and idempotent; re-run after a pool rebuild. |

**Resolver enrichment (committed, in repo — `128d3c8`):** wealthSignals now returns a real
Provenance object (validatedBy=atlas:WealthSignalTypeShape, derivedFrom=the signal's real
evidencedBy txn, generatedBy=hasSignalType); `_display_label` prefers a real rdfs:label
and falls back to a readable handle off the real customerId; searchCustomers orders
signalled customers first (one row per customer via EXISTS).

**Verified live as Rachel Kim (password123):** dashboard shows real names + signals +
provenance; client-360 for c6b6e4ad = "Rachel Kim" in her household with named members;
capabilities (5, persona-scoped), askGraph (real rows), draftRationale (grounded Bedrock
narrative citing the real Large Deposit Pattern) all live.

**Follow-up (recommended):** promote `rdfs:label` inside `05_entity_resolution.ipynb` so a
clean SLGD build carries names natively (removes the U2 LIVE-STATE dependency); fold the
Cognito user creation + password policy into the WS0/CDK provisioning so U3 is declarative.

---

## WS2 UI — detail-page 403, N+1 latency, and the AgentCore invoke floor

**Date:** 2026-06-08 · **Account:** 981814817046

| # | Finding | Resolution | Tag |
|---|---------|-----------|-----|
| U4 | Clicking any customer/client/referral returned S3 **AccessDenied** (403). output:"export" ships only `<prefix>/_placeholder/index.html` for a dynamic route; `/customers/<enc-uri>/` resolved to a nonexistent object and OAC returned 403, so the SPA never loaded. | CloudFront SpaRewriteFn maps ANY `/customers//referrals//clients/` path to that route's `_placeholder/index.html`; new `useEntityUri()` hook reads the real URI from `window.location.pathname` (not useParams, which is the build-time placeholder). Committed in cloudfront.ts + published live to the function. | `FIXED` (live function updated AND in repo) |
| U5 | Dashboard latency ~24s. **N+1**: searchCustomers listed N customers, then a separate nested resolver call PER customer (signals; wealth also coverage) = N+1 AgentCore invocations. | searchCustomers batches signals AND coverage via GROUP_CONCAT with an INNER-LIMIT subquery (flat outer LIMIT times out >35s — materializes all 200 first); nested Customer.wealthSignals / advisoryRelationships short-circuit on the pre-fetched arrays. 51 calls → 1. Measured ~7s warm (was 23.7s). | `FIXED` (in repo) |
| U6 | Residual ~5–7s floor. A **trivial COUNT through the MCP is ~4.8s** — i.e. the cost is the AgentCore `invoke_agent_runtime` overhead (cold container spin per invoke), NOT Neptune (the SELECT is ~200ms) and NOT query shape. | NOT fixed — needs a transport change. Options, in order of effort: (a) move the atlas-sparql-mcp off AgentCore onto **ECS Fargate** with an always-warm task + ALB, so the resolver hits a hot HTTP endpoint (kills the per-invoke cold start — the user's call, and correct); (b) resolver → Neptune **direct** via SigV4 from inside the VPC (bypass the MCP for reads), keeping the MCP for governed writes; (c) provisioned concurrency / keep-warm ping. (a) or (b) should take the dashboard to sub-2s. | `OPEN` `PERF` |

**Route-referral (wired):** the customer-360 header now offers "Route referral" (when the
customer has no active coverage) → `/referrals/<householdUri>`. routeReferral itself was
already live (registry_resolver._resolve_route_referral starts the referral-orchestrator
Step Functions execution: select_advisor → validate[SHACL] → write_routing_decision →
notify → audit).

**Wealth coverage is real:** Marcus Webb covers real clients (Alexis Johnson, Casey Chen,
Taylor Brown, …); 14/30 dashboard clients show their advisor + active/ended state, batched.
Per-advisor scoping ("only MY clients") still needs an advisor-identity→advisor-URI mapping
(token has no advisor URI) — remains a roadmap item.
