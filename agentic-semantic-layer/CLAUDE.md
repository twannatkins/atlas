# ATLAS Build Directives for Claude Code

## What this repo is
A public, open-source SageMaker notebook workshop demonstrating an
FSI-grounded, FIBO-bound semantic layer reference architecture on
AWS. The architecture is named ATLAS — Aligned Three-Layer
Architecture for Semantics. The lead use case is identifying wealth
signals from inside the bank. The audience is FSI architects and
ontologists.

## What this repo is not
- Not a productized platform. No vendor branding, no managed service.
- Not a clone of an existing AWS sample. ATLAS fills a specific gap:
  FIBO-bound, deterministic-vs-probabilistic-boundary-enforced,
  three-pattern data integration. Reference existing AWS samples
  where appropriate; do not copy them verbatim.
- Not bound to any specific institution. The fictional advisor
  persona is "Alex Morgan." No other named individuals appear.

## Architectural commitments that cannot be relaxed
1. Two-tier Neptune (LGD and SLGD). One cluster is not acceptable.
2. SHACL shapes enforce the deterministic-vs-probabilistic boundary
   mechanically. Module 6 must produce a runnable validator.
3. Bedrock LLMs are confined to NL<->SPARQL translation,
   reasoner-output explanation, and narrative drafting. Bedrock is
   NOT used for reasoning, scoring, or routing decisions.
4. Agents (Step Functions / AgentCore) execute routing decisions,
   but the decision logic is deterministic and the routes are
   enumerated. The LLM's role inside an agent runtime is interface,
   not reasoning.
5. SageMaker XGBoost + SHAP is the scoring path. Compliance-shaped
   outputs must be deterministic and explainable per record.
6. AWS Entity Resolution is the cross-source identity resolver.
7. Three connection patterns (Snowflake Horizon, Iceberg, real-time)
   are all demonstrated. Real-time depth is deferred to a follow-on
   lab; primitives must be in place.
8. Wealth signals in v1 are sourced from inside the bank only.
   External signals are an extension path documented in Section 7.

## Build order (serial, with approval gates)
- Build Module 1. Stop. Ask the human to validate.
- Build Module 2. Stop. Ask the human to validate.
- ... and so on through Module 8.

## Validation gates
Each module ends with an automated check. If the check fails, fix
and re-run. Do not proceed to the next module with a failing gate.

## Synthetic data requirements
- No real customer data, ever.
- Synthetic data must be reproducible: ship a generator script
  with a fixed random seed.
- Synthetic data must exercise the wealth-signal use case with a
  known number of detectable signals.

## Naming and branding
- The architecture is ATLAS. The repo is atlas-fsi-semantic-layer.
- Ontology IRI prefix: https://github.com/your-org/atlas/ontology#
- Code prefix in Python and notebooks: atlas_

## Private context
This repo was built with reference to private context that is NOT
included in the repo. Generated content must not include institution
names, internal program names, or named individuals beyond the
fictional persona "Alex Morgan."

If the build process draws on a private context file at
.claude-private/CLAUDE.local.md, that file is gitignored and not
part of the public release. Its contents must never appear in
committed output.

If you are uncertain whether a name belongs in committed output,
omit it and ask.

## Documentation tone
- Architect-readable, not marketing.
- No emoji. No exclamation marks in headings.
- Define every acronym on first use.
- Cite FIBO, PROV-O, DCAT, SKOS, GLEIF, ISO 20022, BIAN where used.

## Licensing
- MIT-0 license at repo root. Match AWS samples convention.
- FIBO is published under MIT; cite the version pinned.

## Tests
- Every notebook ends with a pytest-style validation cell.
- Run all validation cells in CI on a synthetic Neptune-mock harness
  before merge. The full workshop is run end-to-end weekly on AWS.
