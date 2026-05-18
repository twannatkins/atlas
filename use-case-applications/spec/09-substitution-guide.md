# 09 — Substitution Guide

This document explains how to substitute real institutional data for Workshop 1's synthetic data without changing the ontology, the SHACL shapes, the R2RML mapping logic, the registry records, or the agents.

This is the document that turns Workshop 2 from a workshop into a customer POC. If you are reading this with a Truist deployment in mind, this is your primary reference.

## The principle

ATLAS is designed so that *data is configuration, ontology is code*. Switching from synthetic data to real Gold-tier data is a configuration change — you point R2RML mappings at different sources, you update Lake Formation tag policies, you adjust the synthetic data seed scenarios in tests. None of these changes touches the ontology, the shapes, the GraphQL schema, the agents, or the UIs.

This separation is intentional. It is what makes Workshop 2 a *reference architecture* rather than a one-off demo. The same artifacts that work on synthetic data work on real data, with substitution at exactly one layer.

## What stays the same

The following do not change when you substitute real data:

- The 22 ontology classes in `agentic-semantic-layer/ontology/`
- The 6 SHACL shapes in `agentic-semantic-layer/ontology/atlas-shapes.ttl`
- The Workshop 2 ontology extensions in `use-case-applications/ontology-extensions/`
- The eight registered agents
- The five registered MCP servers
- The FIBO-shaped GraphQL schema
- The Wholesale UI and Wealth UI component code
- The CDK stack structure (though specific resource configurations may change)

If you find yourself wanting to modify any of these to accommodate real data, stop. The intent is almost certainly addressable as a configuration change in the substitution layer.

## What changes

Six things change when substituting real data. Each is a discrete, bounded change with its own substitution recipe.

### 1. R2RML mapping target sources

**What changes.** The R2RML mappings in `agentic-semantic-layer/mappings/pattern_a_iceberg/` and `pattern_b_snowflake_horizon/` reference logical source tables. The mappings themselves do not change; what changes is what those logical source names *resolve to*.

**For synthetic data.** The mappings resolve to Iceberg tables backed by the JSON files in `agentic-semantic-layer/data/synthetic/`. A small loader in `agentic-semantic-layer/notebooks/03_two_tier_neptune.ipynb` populates these from the JSON.

**For real data.** The mappings resolve to your institution's actual Gold-tier Iceberg tables in Lake Formation and your Snowflake Horizon shares. You update one configuration file (`use-case-applications/cdk/data-sources.config.ts`) with the actual table ARNs and Snowflake URLs.

**What you don't change.** The R2RML mapping TTL files. The logical table names. The triple maps. The class assignments. The property mappings. These are all defined in terms of the ontology, not the source.

### 2. Lake Formation tag policies

**What changes.** Workshop 2's CDK stack creates Lake Formation LF-Tags that scope data access by persona (Consumer Banker sees consumer accounts, Wealth Advisor sees their assigned book, BSA sees compliance-relevant subsets). For synthetic data, these tags are applied automatically by the workshop. For real data, your institution's existing LF-Tag taxonomy must be mapped to Workshop 2's persona expectations.

**For synthetic data.** The CDK stack applies LF-Tags named `atlas:lob=consumer`, `atlas:lob=wealth`, `atlas:scope=consumer-banker-book`, etc., to the synthetic Iceberg tables.

**For real data.** Your institution likely already has an LF-Tag taxonomy. Map your tags to Workshop 2's expected tag names in `use-case-applications/cdk/lake-formation-tag-mapping.config.ts`. The mapping is a one-time configuration; you do not modify the policies themselves.

**What you don't change.** The principle that Lake Formation enforces data-layer scoping. The list of personas. The relationship between persona and scope.

### 3. AWS Entity Resolution workflows

**What changes.** Workshop 2's `atlas-er-mcp` server calls an Entity Resolution workflow to resolve incoming records to canonical URIs. For synthetic data, this workflow uses simple matching rules against the synthetic JSON. For real data, the workflow uses your institution's actual matching configuration.

**For synthetic data.** The workshop deploys an ER workflow named `atlas-customer-resolution-synthetic` with simple matching rules (exact match on `customer_id`, fuzzy match on name + DOB).

**For real data.** Your institution has an existing entity resolution capability (often a vendor product or an internal MDM). One of two paths:

*Path A — Use AWS Entity Resolution as the workshop intends.* Configure an ER workflow against your real customer master and update `use-case-applications/cdk/entity-resolution.config.ts` to reference it.

*Path B — Adapter to existing MDM.* Replace the `atlas-er-mcp` Lambda implementation with an adapter that calls your existing MDM service and returns canonical URIs in the same format. The MCP server interface does not change; only the implementation behind it does.

**What you don't change.** The MCP server contract. The way agents consume ER results. The URI minting convention.

### 4. Synthetic data scenarios in demos

**What changes.** Workshop 2's notebooks reference specific synthetic data scenarios — the Rachel Kim referral scenario uses Anjali Patel as the canonical customer. These references appear in notebook narratives, in the UI demo data, and in verification cells.

**For synthetic data.** The scenarios use the seeded names from `agentic-semantic-layer/data/synthetic/customer-master.json`.

**For real data.** You cannot use real customer names in workshop materials (privacy, regulatory, and ethical reasons). Two options:

*Option A — Keep the synthetic scenarios for teaching, run real data in production.* The workshop notebooks teach using Anjali Patel. The deployed application runs against real data with real (uncomment-anonymized) customers. The teaching narrative is fictional; the deployment is real.

*Option B — Anonymized real scenarios.* Pick three to five real-but-anonymized scenarios that match the workshop's narrative arcs. Replace the references in notebook narratives and UI demo data. This is more work but produces more relatable teaching for the institution's engineers.

**What you don't change.** The structure of the scenarios. The verification cells (which check counts and shapes, not specific names). The notebook teaching arc.

### 5. Bedrock model IDs and regions

**What changes.** Workshop 2 uses specific Bedrock model IDs (Claude on Bedrock). For synthetic data, these are the default workshop model IDs. For real data, your institution may have specific models approved through MRM, or specific regional deployments.

**For synthetic data.** Defaults defined in each agent's descriptor JSON.

**For real data.** Update `use-case-applications/cdk/bedrock-models.config.ts` with your institution's approved model IDs and regions. Each agent descriptor references this config rather than hardcoding model IDs.

**What you don't change.** The fact that LLMs are at the edges of the architecture. The agents that use them. The posture of each agent.

### 6. IDC group names and assignments

**What changes.** The IAM Identity Center groups (`atlas-consumer-banker`, `atlas-wealth-advisor`, etc.) are workshop conventions. Your institution likely has existing groups (`truist-cnsmr-banker-l3`, or whatever your naming convention is). Cognito federation needs to know how to map.

**For synthetic data.** The workshop creates the `atlas-*` groups in IDC and assigns the workshop attendee to all of them.

**For real data.** Your institution has its own group taxonomy. Map your groups to Workshop 2's persona expectations in `use-case-applications/cdk/idc-group-mapping.config.ts`. Authentication continues to work against your real groups; the mapping translates them to the Workshop 2 persona names that the registry and SHACL graphs reference.

**What you don't change.** The principle that personas are identity-claim-driven. The five persona definitions. The four-layer permission model.

## The substitution sequence

When moving from a workshop deployment to a customer POC, work through these six substitutions in this order:

1. **Configuration files first.** Update the six `*.config.ts` files in `use-case-applications/cdk/` with your institution's actual values. Do not deploy yet — review the configs against your security and compliance teams.

2. **Validate the ontology against your data.** Run the ontology alignment exercise from `agentic-semantic-layer/notebooks/02_fibo_alignment.ipynb` against a sample of your real data. Where your data has concepts not in the ontology, add them to `use-case-applications/ontology-extensions/` (not to Workshop 1's ontology). This is the most important step — it is where you discover whether your data actually fits the ATLAS model or whether you need extensions.

3. **Run a parallel ER workflow.** Before pointing the workshop at real data, run AWS Entity Resolution against a sample. Verify the canonical URIs make sense. Adjust matching rules if needed. This is where most real-data deployments find their first surprise.

4. **Deploy to a non-production environment first.** Truist's pilot environment (the CDK-deployed sandbox referenced in your AWS Lab Account) is the right target. Run the full Phase 1 acceptance criteria against real data in this environment before considering production.

5. **Run the Rachel Kim scenario with anonymized real data.** Pick one real wealth-eligible household, anonymize the names for the demo, and walk through the full Phase 1 flow. This is your end-to-end smoke test.

6. **Document the deviations.** Anywhere your deployment differs from the workshop default (different IDC groups, different ER configuration, different Bedrock models), document the deviation in your institution's deployment notes. This is what makes the next institution's substitution easier.

## What the substitution does not address

Three things are out of scope for the substitution guide and require additional work:

**Production hardening.** The workshop deployment is workshop-fidelity. It works for one workshop attendee and synthetic data volumes. Production hardening for thousands of concurrent users, cross-region replication, disaster recovery, full SOC 2 readiness, and load testing is your institution's deployment engineering — not the workshop's.

**Real-time data ingest at scale.** Pattern C (the real-time event pattern) works at workshop scale. Scaling it to actual transaction volumes is a separate engineering exercise involving Kinesis throughput, Lambda concurrency, and Neptune write rate planning.

**Cross-line-of-business data sharing agreements.** Workshop 2 assumes the personas have authorized access to the data their roles imply. In reality, cross-LOB data sharing (Consumer Banking sharing customer data with Wealth) is governed by data sharing agreements, customer consent records, and regulatory considerations. ATLAS does not bypass these — the ontology models them via `atlas:DataSource` and PROV-O attribution — but the operational work of establishing the agreements is your institution's.

## The teaching purpose of this guide

This document is also part of Workshop 2's teaching. A novice who reads it should leave understanding *why* the ATLAS architecture separates ontology from data: not as an aesthetic preference, but as the property that makes the workshop's artifacts portable across institutions, across data volumes, and across deployment environments.

When a Truist engineer reads this guide, they should see clearly which six things will change for their deployment and which everything-else will stay the same. The brevity of the substitution list is the proof that the architecture works.

If a future revision of ATLAS makes substitution harder — if more than six things change, or if substitution requires modifying the ontology — that is a signal that the architecture has drifted from its founding principle. The substitution guide is the canary.
