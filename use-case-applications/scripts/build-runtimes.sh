#!/usr/bin/env bash
#
# build-runtimes.sh — Option C: portable pre-built runtime dependency packaging.
#
# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS SCRIPT EXISTS (the teaching layer — read this first)
# ─────────────────────────────────────────────────────────────────────────────
# Every ATLAS runtime's main.py imports `bedrock_agentcore` — a ~600-line
# Starlette/uvicorn ASGI server that implements the AgentCore /invocations + /ping
# HTTP contract. That import is not optional; without it the runtime cannot start.
# So the deployed ZIP MUST contain bedrock-agentcore (and each runtime's other deps)
# alongside main.py. There are three ways to get the deps into the ZIP, and the CDK
# construct (cdk/lib/constructs/agentcore-runtimes.ts) supports all three:
#
#   PATH 3 — RAW SOURCE (the committed default, bundleRuntimeDeps unset):
#     fromCodeAsset ships main.py with NO deps. Runtimes provision green, then crash
#     on first invocation with ModuleNotFoundError: bedrock_agentcore. REJECTED as the
#     shippable path — a green deploy that crashes on first call is worse than a loud
#     failure, because it looks like success.
#
#   PATH 2 — DOCKER BUNDLING (bundleRuntimeDeps=true):
#     fromCodeAsset + CDK BundlingOptions runs `pip install` inside a Docker image at
#     `cdk synth`. Works on a laptop/CI with Docker. REJECTED as the published path:
#     the workshop runs inside SageMaker Studio / SageMaker Unified Studio notebook
#     kernels, which have NO Docker daemon. `cdk synth` with this flag fails instantly
#     in Studio — the exact environment the runner is in.
#
#   PATH 1 — OPTION C, THIS SCRIPT (runtimeArtifactsS3Prefix=<prefix>):
#     We pip-install each runtime's deps into a build dir, copy the source in, zip it,
#     and upload the ZIP to the runner's existing WS1 staging bucket. CDK then sources
#     the runtime via AgentRuntimeArtifact.fromS3 — it only references the S3 key, so
#     `cdk synth` needs NO Docker. The ZIP already has the deps, so the runtime STARTS.
#     This is the only path that is BOTH Studio-safe AND functional. It is the
#     publication fix tracked in docs/deployment-findings.md.
#
# WHAT A NOVICE SHOULD EXPECT TO SEE:
#   Running `build` prints one block per runtime: a pip-install line, a zip line, and
#   an "uploaded s3://…/<name>.zip" line — 12 runtimes total. Then it prints the exact
#   `cdk deploy -c runtimeArtifactsS3Prefix=<prefix>` command to run next. Nothing is
#   deployed by this script; it only prepares and uploads the ZIPs.
#
# ─────────────────────────────────────────────────────────────────────────────
# PREREQUISITES
#   - python3 + pip on PATH (no Docker required)
#   - awscli configured for the runner's account/region (us-east-1)
#   - The WS1 staging bucket name (preflight notebook persisted it as
#     `ontologyStagingBucket` in cdk/cdk.json). Pass it as $BUCKET or arg.
#
# AgentCore runtimes execute on Linux arm64. We pip-install with explicit
# --platform manylinux2014_aarch64 so wheels match the runtime, even when this
# script runs on macOS/x86. Pure-Python deps (rdflib, pyshacl) are unaffected;
# the flags only matter for any package with a native wheel.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
# Resolve repo paths relative to this script so it works from any CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USE_CASE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"      # use-case-applications/
BUILD_DIR="${USE_CASE_DIR}/.runtime-build"          # transient; gitignored

# S3 key prefix the ZIPs land under. MUST match the value you pass to CDK as
# -c runtimeArtifactsS3Prefix=<prefix>. The construct builds the key as
# "<prefix>/<runtime-name>.zip" (artifactBasename in agentcore-runtimes.ts).
S3_PREFIX="${S3_PREFIX:-runtimes}"

AWS_REGION="${AWS_REGION:-us-east-1}"

# Python interpreter used to drive pip. Defaults to python3 (correct on SageMaker
# Studio kernels, which ship pip). Override with PY=/path/to/python3 when the default
# python3 lacks pip — e.g. a uv-created venv. pip itself only needs to be >= 20.3 to
# honor the cross-platform wheel flags (--platform / --python-version / --only-binary).
PY="${PY:-python3}"

# The 12 runtime source dirs, relative to use-case-applications/. The ZIP basename
# is the dir's last path segment — kept in lockstep with artifactBasename() in
# cdk/lib/constructs/agentcore-runtimes.ts. If you add/rename a runtime, update both.
RUNTIMES=(
  "mcp-servers/atlas-shacl-mcp"
  "mcp-servers/atlas-sparql-mcp"
  "mcp-servers/atlas-er-mcp"
  "mcp-servers/atlas-fibo-mcp"
  "mcp-servers/atlas-registry-mcp"
  "agents/nl-to-sparql-agent"
  "agents/wealth-signal-detector"
  "agents/household-traverser"
  "agents/referral-rationale-drafter"
  "agents/behavioral-signal-agent"
  "agents/theme-summarizer"
  "agents/conversational-context-manager"
)

# ── Helpers ──────────────────────────────────────────────────────────────────
# log() writes to stderr so functions like package() can `echo` a clean return value
# (the produced zip path) on stdout without log lines polluting the captured output.
log() { echo "[build-runtimes] $*" >&2; }

resolve_bucket() {
  # Bucket precedence: $BUCKET env → $1 arg → cdk.json ontologyStagingBucket.
  local bucket="${BUCKET:-${1:-}}"
  if [[ -z "${bucket}" ]]; then
    local cdk_json="${USE_CASE_DIR}/cdk/cdk.json"
    if [[ -f "${cdk_json}" ]]; then
      bucket="$(python3 -c "import json,sys; print(json.load(open('${cdk_json}'))['context'].get('ontologyStagingBucket',''))" 2>/dev/null || true)"
    fi
  fi
  if [[ -z "${bucket}" ]]; then
    echo "ERROR: staging bucket not provided. Set \$BUCKET, pass it as arg 2, or" >&2
    echo "       populate ontologyStagingBucket in cdk/cdk.json (preflight bridge does this)." >&2
    exit 1
  fi
  echo "${bucket}"
}

# ─────────────────────────────────────────────────────────────────────────────
# TEARDOWN — defined BEFORE create, per the teardown-first rule.
# Removes the uploaded ZIPs from the staging bucket and the local build dir, so the
# deployment reverts to the committed default path (flag unset → raw source ZIPs).
#
# AFTER running this, redeploy WITHOUT -c runtimeArtifactsS3Prefix to return CDK to
# the fromCodeAsset path. (Leaving the flag set while the ZIPs are gone would make
# the runtimes fail to create — fromS3 would point at a missing key.)
#
#   Usage:  ./scripts/build-runtimes.sh teardown [bucket]
# ─────────────────────────────────────────────────────────────────────────────
teardown() {
  local bucket; bucket="$(resolve_bucket "${1:-}")"
  log "TEARDOWN — removing pre-built runtime ZIPs from s3://${bucket}/${S3_PREFIX}/"
  for rel in "${RUNTIMES[@]}"; do
    local name; name="$(basename "${rel}")"
    local key="${S3_PREFIX}/${name}.zip"
    log "  delete s3://${bucket}/${key}"
    aws s3 rm "s3://${bucket}/${key}" --region "${AWS_REGION}" || true
  done
  if [[ -d "${BUILD_DIR}" ]]; then
    log "  removing local build dir ${BUILD_DIR}"
    rm -rf "${BUILD_DIR}"
  fi
  log "TEARDOWN complete. Now redeploy WITHOUT -c runtimeArtifactsS3Prefix to revert"
  log "to the default fromCodeAsset path:  (cd cdk && npx cdk deploy)"
}

# ─────────────────────────────────────────────────────────────────────────────
# PACKAGE — pip-install deps + source into a per-runtime build dir, then zip.
# Pure packaging; no AWS calls. Used by `build` and by the local dry-run.
#   package <relpath>  →  echoes the absolute path to the produced .zip
# ─────────────────────────────────────────────────────────────────────────────
package() {
  local rel="$1"
  local name; name="$(basename "${rel}")"
  local src="${USE_CASE_DIR}/${rel}"
  local out="${BUILD_DIR}/${name}"
  local zip_path="${BUILD_DIR}/${name}.zip"

  if [[ ! -f "${src}/main.py" ]]; then
    echo "ERROR: ${src}/main.py not found — is the runtime path correct?" >&2
    exit 1
  fi
  if [[ ! -f "${src}/requirements.txt" ]]; then
    echo "ERROR: ${src}/requirements.txt not found — cannot bundle deps for ${name}." >&2
    exit 1
  fi

  log "package ${name}"
  rm -rf "${out}" "${zip_path}"
  mkdir -p "${out}"

  # Install deps for Linux arm64 (the AgentCore runtime arch). --only-binary=:all:
  # forces wheels so we never compile native code on the wrong host. If a dep has no
  # arm64 wheel this fails loudly rather than shipping an x86 build that crashes.
  log "  pip install -r ${rel}/requirements.txt  (target: linux/aarch64, via ${PY})"
  # Explicit failure check: inside a command-substitution caller (package "$x"),
  # bash relaxes `set -e`, so guard the install so a missing arm64 wheel aborts the
  # whole build loudly instead of silently shipping a ZIP without bedrock-agentcore.
  if ! "${PY}" -m pip install \
      --quiet --disable-pip-version-check \
      --platform manylinux2014_aarch64 \
      --implementation cp \
      --python-version 3.12 \
      --only-binary=:all: \
      --target "${out}" \
      -r "${src}/requirements.txt"; then
    echo "ERROR: pip install failed for ${name}. Need a Python >=3.10 with pip >=20.3" >&2
    echo "       (bedrock-agentcore requires-python >=3.10). Set PY=/path/to/python3.12." >&2
    exit 1
  fi

  # Copy the runtime source (main.py + any sibling .py such as neptune_client.py,
  # atlas_sparql.py) in alongside the installed deps.
  log "  copy source *.py into bundle"
  cp "${src}"/*.py "${out}/"

  # Zip from inside the build dir so paths are flat (main.py at the ZIP root, which
  # is what the AgentCore entrypoint ["main.py"] expects).
  log "  zip → ${zip_path}"
  ( cd "${out}" && zip -qr "${zip_path}" . )

  echo "${zip_path}"
}

# ─────────────────────────────────────────────────────────────────────────────
# BUILD — package all 12 runtimes and upload each ZIP to the staging bucket.
#   Usage:  ./scripts/build-runtimes.sh build [bucket]
# Idempotent: re-running overwrites the same keys (aws s3 cp replaces).
# ─────────────────────────────────────────────────────────────────────────────
build() {
  local bucket; bucket="$(resolve_bucket "${1:-}")"
  log "BUILD — packaging ${#RUNTIMES[@]} runtimes → s3://${bucket}/${S3_PREFIX}/"
  mkdir -p "${BUILD_DIR}"
  for rel in "${RUNTIMES[@]}"; do
    local name; name="$(basename "${rel}")"
    local zip_path; zip_path="$(package "${rel}")"
    local key="${S3_PREFIX}/${name}.zip"
    log "  upload ${zip_path} → s3://${bucket}/${key}"
    aws s3 cp "${zip_path}" "s3://${bucket}/${key}" --region "${AWS_REGION}"
  done
  log "BUILD complete. Deploy with the S3-sourced runtimes (no Docker required):"
  log "  (cd cdk && npx cdk deploy -c runtimeArtifactsS3Prefix=${S3_PREFIX})"
}

# ─────────────────────────────────────────────────────────────────────────────
# DRY-RUN-ONE — package a single runtime locally and list the ZIP contents.
# No AWS calls. Proves bedrock_agentcore + deps land next to main.py.
#   Usage:  ./scripts/build-runtimes.sh dry-run-one [relpath]
# ─────────────────────────────────────────────────────────────────────────────
dry_run_one() {
  local rel="${1:-mcp-servers/atlas-sparql-mcp}"
  local name; name="$(basename "${rel}")"
  log "DRY-RUN (local only, no AWS) — packaging ${rel}"
  local zip_path; zip_path="$(package "${rel}")"
  log "ZIP produced: ${zip_path}"
  log "Top-level entries (expect main.py + bedrock_agentcore/ + deps):"
  unzip -l "${zip_path}" | awk 'NR>3 {print $4}' | sed 's#/.*##' | sort -u | sed '/^$/d'
}

# ── Dispatch ─────────────────────────────────────────────────────────────────
cmd="${1:-help}"
shift || true
case "${cmd}" in
  build)        build "$@" ;;
  teardown)     teardown "$@" ;;
  dry-run-one)  dry_run_one "$@" ;;
  *)
    cat <<EOF
build-runtimes.sh — Option C portable runtime packaging (no Docker)

Commands:
  build [bucket]         Package all 12 runtimes and upload ZIPs to the staging bucket.
                         Then: (cd cdk && npx cdk deploy -c runtimeArtifactsS3Prefix=${S3_PREFIX})
  teardown [bucket]      Remove the uploaded ZIPs + local build dir, reverting to the
                         default fromCodeAsset path. Then redeploy WITHOUT the flag.
  dry-run-one [relpath]  Package ONE runtime locally and list ZIP contents (no AWS).
                         Default relpath: mcp-servers/atlas-sparql-mcp

Bucket resolution: \$BUCKET env → arg → cdk/cdk.json ontologyStagingBucket.
S3 prefix:         \$S3_PREFIX env (default "runtimes"). Must match -c runtimeArtifactsS3Prefix.
EOF
    ;;
esac
