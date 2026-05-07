# ATLAS Ontology

This directory contains the ATLAS ontology files. They are built in module order;
each module may extend or align the files from prior modules.

## File Inventory

| File | Introduced | Purpose |
|------|-----------|---------|
| `atlas-core.ttl` | Module 1 | 18-class starter ontology derived from competency questions |
| `atlas-fibo-alignment.ttl` | Module 2 | FIBO IRI bindings for every atlas-core class |
| `atlas-shapes.ttl` | Module 6 | SHACL shapes enforcing the deterministic-vs-probabilistic boundary |
| `extensions/prov-o-bindings.ttl` | Module 5 | PROV-O attribution patterns |
| `extensions/dcat-bindings.ttl` | Module 4 | DCAT dataset descriptors for source connection patterns |
| `extensions/skos-codelists.ttl` | Module 1 | SKOS concept scheme for WealthSignalType enumeration |
| `extensions/gleif-bindings.ttl` | Module 2 | GLEIF Legal Entity Identifier bindings for counterparty entities |

## FIBO Citation

This workshop aligns to FIBO (Financial Industry Business Ontology) published
by the Enterprise Data Management (EDM) Council under the MIT license.

FIBO version pinned: **FIBO 2024 Q3 Production Release**
FIBO IRI base: `https://spec.edmcouncil.org/fibo/ontology/`
FIBO GitHub: `https://github.com/edmcouncil/fibo`

The FIBO alignment bindings are in `atlas-fibo-alignment.ttl` and are introduced
in Module 2. This file (`atlas-core.ttl`) uses `rdfs:comment` annotations to
document the anticipated FIBO alignment; the normative bindings are in the
alignment file.

## Ontology IRI

All ATLAS ontology entities use the IRI prefix:

```
https://github.com/your-org/atlas/ontology#
```

Replace `your-org` with your GitHub username or organization when forking
this repository for production use.

## Class Summary (Module 1 baseline)

18 classes, each traceable to at least one competency question:

1. `atlas:Customer` — CQ1, CQ3, CQ6, CQ7
2. `atlas:Account` — CQ1, CQ2
3. `atlas:Holding` — CQ1, CQ2
4. `atlas:Transaction` — CQ1, CQ2, CQ7
5. `atlas:Household` — CQ3
6. `atlas:WealthSignal` — CQ1, CQ2, CQ4
7. `atlas:Eligibility` — CQ1, CQ4
8. `atlas:Score` — CQ2
9. `atlas:RoutingDecision` — CQ5, CQ6
10. `atlas:HumanReview` — CQ5, CQ6
11. `atlas:AuditRecord` — CQ6, CQ7
12. `atlas:Advisor` — CQ5, CQ6
13. `atlas:WorkflowStep` — CQ5
14. `atlas:WealthSignalType` — CQ1, CQ2
15. `atlas:HouseholdMembership` — CQ3
16. `atlas:DataSource` — CQ7
17. `atlas:ObservationWindow` — CQ1, CQ4
18. `atlas:PreviousSurfacing` — CQ4
