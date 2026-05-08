# ATLAS Ontology — FIBO Alignment Gaps

Every class in `atlas-core.ttl` either has a FIBO binding in `atlas-fibo-alignment.ttl`
or appears in this document with a justification for why FIBO does not cover it and
the chosen extension standard.

This document is a Module 2 deliverable. It is intended for an architect or ontologist
who needs to understand where ATLAS extends beyond FIBO and why.

## Why Gaps Exist

FIBO (Financial Industry Business Ontology) is a reference vocabulary for the financial
services industry. It covers parties, accounts, instruments, legal entities, and
regulatory structures. It does not cover:

- **Operational workflow concepts** — how a bank routes, reviews, and approves internal
  decisions. FIBO models what things *are*, not what a bank *does with them*.
- **Machine learning scoring** — FIBO predates the widespread use of ML in FSI
  decision-making. Concepts like "explainable score" and "model version" are not in scope.
- **Bank-specific groupings** — concepts like "Household" that are institution-defined
  rather than industry-standard. FIBO models what the industry agrees on; households
  are defined differently at every bank.
- **Temporal observation patterns** — FIBO models entities at a point in time, not
  the observation windows and change-detection patterns that wealth-signal detection requires.

These gaps are not deficiencies in FIBO. They are the boundary between what an industry
standard should cover and what an institution must model for itself.

## Gap Inventory

| ATLAS Class | Why FIBO Does Not Cover It | Extension Standard | Rationale |
|---|---|---|---|
| `atlas:Household` | FIBO models legal and natural persons, not institution-defined groupings of persons. Every bank defines "household" differently (shared address, shared tax ID, beneficiary relationship). | None (bank-specific) | No W3C or industry standard covers household grouping. This is intentionally institution-specific. The class carries its own evidence via `atlas:HouseholdMembership`. |
| `atlas:WealthSignal` | FIBO does not model internal bank signals or lead-generation concepts. A wealth signal is an operational concept — it exists only within the bank's detection system. | None (bank-specific, with SKOS typing) | The signal taxonomy uses SKOS for the type enumeration, but the signal class itself is bank-specific. |
| `atlas:Eligibility` | FIBO does not model internal eligibility determinations. Eligibility is a bank-specific decision with institution-defined criteria. | PROV-O (for provenance of the determination) | The Eligibility instance carries `prov:wasGeneratedBy` to record which process produced it, but the class itself is bank-specific. |
| `atlas:Score` | FIBO does not model ML scoring outputs. Scores are a product of the bank's analytical infrastructure, not an industry-standard concept. | None (bank-specific, with SHAP explainability as structural requirement) | The Score class is defined by its explainability contract: it must carry `atlas:modelVersion`, `atlas:explainability`, and SHAP attributions. No standard covers this pattern. |
| `atlas:RoutingDecision` | FIBO does not model workflow routing. Routing is an operational concept — it describes what the bank does with a signal, not what the signal is. | None (bank-specific, with PROV-O provenance) | The routing decision carries `prov:wasGeneratedBy` linking to the Step Functions execution. The closed route set is enforced by SHACL, not by FIBO. |
| `atlas:WorkflowStep` | FIBO does not model state machines or workflow steps. These are operational infrastructure concepts. | None (bank-specific) | WorkflowStep enumerates the bounded agent's state transitions. It exists so SPARQL can answer CQ5 ("which steps require human review"). |
| `atlas:HouseholdMembership` | FIBO does not model reified relationships with evidence. The concept of "membership with a confidence score and a basis" is an entity-resolution output, not an industry-standard relationship. | PROV-O (for provenance when probabilistic) | When membership is inferred by AWS Entity Resolution (probabilistic), the HouseholdMembership node carries `prov:wasGeneratedBy` and `atlas:confidence`. |
| `atlas:ObservationWindow` | FIBO models entities, not temporal observation patterns. The concept of "evaluate transactions within this date range" is an analytical pattern, not a financial concept. | None (bank-specific) | ObservationWindow is a simple [startDate, endDate] interval. OWL-Time was considered but rejected as over-engineering for a two-property class. |
| `atlas:PreviousSurfacing` | FIBO does not model internal lead-management history. Whether a customer was previously surfaced is an operational record, not a financial concept. | PROV-O (for provenance chain) | PreviousSurfacing links to the prior Eligibility determination via PROV-O, enabling CQ4's "what has changed since" query. |
| `atlas:ScoreExplanation` | FIBO does not model SHAP attributions or feature-level explanations. This is an ML-specific concept that postdates FIBO's design. | None (bank-specific) | ScoreExplanation carries per-feature SHAP values. No standard covers this; it is defined by the XGBoost + SHAP contract. |

## Extension Ring Summary

The "extension ring" is the set of W3C and industry standards that real banks layer
around FIBO to cover the gaps above. In ATLAS v1.0, the ring members are:

| Standard | What It Covers in ATLAS | Where Used |
|---|---|---|
| **PROV-O** (W3C Provenance Ontology) | Provenance of every promoted edge in the SLGD. Who did what, when, and from what source. | Modules 5, 6, 8. Every entity promoted from LGD to SLGD carries `prov:wasDerivedFrom` and `prov:wasGeneratedBy`. |
| **DCAT v3** (W3C Data Catalog Vocabulary) | Catalog of federated data sources. Lets a data steward see what is connected without reading R2RML mappings. | Module 4. Each connection pattern (Iceberg, Snowflake Horizon, stream) is a `dcat:Dataset` instance. |
| **SKOS** (W3C Simple Knowledge Organization System) | Code lists, taxonomies, controlled vocabularies. The wealth-signal taxonomy, customer segments, and routing routes. | Modules 1, 2, 6, 8. The `WealthSignalTypeScheme` and `RoutingRouteScheme` are SKOS concept schemes. |
| **GLEIF / LEI** (Global Legal Entity Identifier Foundation) | Legal entity identifiers for institutional counterparties. | Module 2 (demonstration). A single LEI lookup and binding to `fibo-be-le-lei:LegalPerson`. |
| **ISO 20022** | Transaction and payment message structure for stream-derived events. | Module 4 Pattern C. Event payloads on the Kafka/Kinesis stream use ISO 20022 message structure. |
| **BIAN** (Banking Industry Architecture Network) | Service domain labels for crosswalking the ontology to bank operating-model terminology. | Module 2 (labelling only). ATLAS classes carry `rdfs:seeAlso` links to BIAN service domains where applicable. |

## The Decision Framework for Future Gaps

When you encounter a concept in your own domain that FIBO does not cover, apply this
decision tree:

1. **Is there a W3C standard that covers it?** (PROV-O for provenance, DCAT for data
   sources, SKOS for taxonomies, OWL-Time for temporal concepts) → Use the standard.
2. **Is there an industry standard that covers it?** (GLEIF for legal entities,
   ISO 20022 for payment messages, BIAN for service domains) → Use the standard.
3. **Is it institution-specific?** (Household definitions, internal scoring models,
   workflow routing) → Model it as a bank-specific class with clear documentation
   of why no standard covers it.

The worst outcome is inventing a bank-specific class when a standard exists. The
second-worst outcome is forcing a standard binding that does not fit. Both are
caught by the validation gate: every class must either have a binding in
`atlas-fibo-alignment.ttl` or an entry in this document.
