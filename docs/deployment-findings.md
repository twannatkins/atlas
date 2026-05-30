# ATLAS Deployment Findings

## Module completion log

| Module | Status | Notes |
|--------|--------|-------|
| WS1 Module 3 — Two-Tier Neptune | COMPLETE | All 4 validation gates pass. 22 atlas: classes, 415 triples in SLGD. LGD empty. |
| WS1 Module 4 — Three Connection Patterns | COMPLETE | No errors. All 3 patterns generated triples; LGD populated. SigV4 signing fix applied pre-run. |

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
| L5 | `atlas-neptune-iam-auth` v3 uses `neptune-db:*` on `*` | Set during debugging; not the intended scoped policy | `LIVE-STATE` `SELF-BITING` | Restore to scoped `neptune-db:Read/WriteDataViaQuery` on the two cluster resource ARNs. The v2 policy was correct; the diagnostic v3 was left as default. |

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
