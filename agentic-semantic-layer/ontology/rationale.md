# ATLAS Ontology — Class Rationale

Every class in `atlas-core.ttl` traces to at least one competency question.
This document is the Module 1 deliverable that makes the ontology defensible
in front of a committee or a model risk management reviewer.

| Class | Competency Questions | One-Sentence Justification |
|-------|---------------------|---------------------------|
| `atlas:Customer` | CQ1, CQ3, CQ4, CQ6, CQ7 | The primary subject of wealth-signal detection; every competency question begins or ends with a Customer. |
| `atlas:Account` | CQ1, CQ2 | Accounts hold the transactions and holdings that are the raw evidence for wealth signals. |
| `atlas:Holding` | CQ1, CQ2 | A Customer's investment position, required to model equity-event and retirement-rollover signals. |
| `atlas:Transaction` | CQ1, CQ2, CQ7 | The atomic dated financial event that constitutes the evidence for large-deposit and business-sale signals; CQ7 requires specific dated observations. |
| `atlas:Household` | CQ3 | CQ3 asks about household relationships; household-aggregation signals require a class that groups Customers and supports aggregate-balance queries. |
| `atlas:WealthSignal` | CQ1, CQ2, CQ4 | The core domain concept: a typed, dated in-bank observation that indicates wealth-management eligibility. |
| `atlas:Eligibility` | CQ1, CQ4 | Modelled as a class (not a boolean) because CQ4 asks for the outcome and what has changed since — both require independent identity, dates, and history. |
| `atlas:Score` | CQ2 | CQ2 asks for the deterministic vs probabilistic decomposition; a single decimal property cannot carry the SHAP attributions, model version, and explainability flag required. |
| `atlas:RoutingDecision` | CQ5, CQ6 | CQ5 asks which steps require human review; RoutingDecision is the node that triggers HumanReview and holds the selected route from the enumerated set. |
| `atlas:HumanReview` | CQ5, CQ6 | CQ5 requires evidence of human review in the graph; HumanReview carries the outcome, the date, and the task token. |
| `atlas:AuditRecord` | CQ6, CQ7 | CQ6 requires a full audit trail from signal detection to advisor approval; AuditRecord is the PROV-O node that makes that trail queryable. |
| `atlas:Advisor` | CQ5, CQ6 | CQ6 asks 'contacted by a Wealth advisor' — the advisor is a named participant in the audit trail and must be a queryable entity. |
| `atlas:WorkflowStep` | CQ5 | CQ5 asks 'which steps require human review' — WorkflowStep enumerates the bounded agent's state transitions so the graph can answer this. |
| `atlas:WealthSignalType` | CQ1, CQ2 | CQ1 and CQ2 implicitly require typing signals (large-deposit vs equity-event differ in evidence and threshold); SKOS concept scheme enables closed-set SHACL enforcement. |
| `atlas:HouseholdMembership` | CQ3 | CQ3 asks for the evidence of household membership; reified as a class (rather than plain atlas:memberOf) when the basis and confidence score must be stored. |
| `atlas:DataSource` | CQ7 | CQ7 asks what data was used; DataSource is the DCAT dataset descriptor that PROV-O attribution points to, enabling source lineage queries. |
| `atlas:ObservationWindow` | CQ1, CQ4 | CQ1 says 'in the last 90 days'; CQ4 asks 'what has changed since'; both require a queryable time interval with a start and end date. |
| `atlas:PreviousSurfacing` | CQ4 | CQ4 is entirely about whether a customer was previously surfaced and what changed; PreviousSurfacing is the node that stores the outcome and the date of the prior determination. |

## Competency Question Coverage

| CQ | Classes derived |
|----|----------------|
| CQ1 | `atlas:Customer`, `atlas:Account`, `atlas:Holding`, `atlas:Transaction`, `atlas:WealthSignal`, `atlas:Eligibility`, `atlas:WealthSignalType`, `atlas:ObservationWindow` |
| CQ2 | `atlas:Account`, `atlas:Holding`, `atlas:Transaction`, `atlas:WealthSignal`, `atlas:Score`, `atlas:WealthSignalType` |
| CQ3 | `atlas:Customer`, `atlas:Household`, `atlas:HouseholdMembership` |
| CQ4 | `atlas:Customer`, `atlas:WealthSignal`, `atlas:Eligibility`, `atlas:ObservationWindow`, `atlas:PreviousSurfacing` |
| CQ5 | `atlas:RoutingDecision`, `atlas:HumanReview`, `atlas:Advisor`, `atlas:WorkflowStep` |
| CQ6 | `atlas:Customer`, `atlas:RoutingDecision`, `atlas:HumanReview`, `atlas:AuditRecord`, `atlas:Advisor` |
| CQ7 | `atlas:Customer`, `atlas:Transaction`, `atlas:AuditRecord`, `atlas:DataSource` |

## Coverage Competency Questions (Added in Finishing Pass)

These three competency questions exercise the `atlas:AdvisoryRelationship` class
and are the canonical Phase 1 questions for Part 2 of the workshop.

| CQ | Question | Satisfying SPARQL | Why It Is a Valid FSI CQ |
|----|----------|-------------------|------------------------|
| CQ-Coverage-1 | For any customer, identify their currently active wealth advisor, if any. | `SELECT ?customer ?advisor WHERE { ?customer atlas:hasAdvisor ?rel . ?rel atlas:coveringAdvisor ?advisor . FILTER NOT EXISTS { ?rel atlas:coverageEndDate ?end } }` | Every regulated institution must be able to identify the responsible advisor for any customer at any point in time. This is a basic accountability question. |
| CQ-Coverage-2 | For any household, identify which members have active wealth coverage and which do not. | `SELECT ?household ?covered ?uncovered WHERE { ?covered atlas:memberOf ?household ; atlas:hasAdvisor ?rel . FILTER NOT EXISTS { ?rel atlas:coverageEndDate ?end } . ?uncovered atlas:memberOf ?household . FILTER NOT EXISTS { ?uncovered atlas:hasAdvisor ?rel2 . FILTER NOT EXISTS { ?rel2 atlas:coverageEndDate ?end2 } } FILTER (?covered != ?uncovered) }` | Household-level coverage gaps are the primary source of wealth-management referral opportunities. A household with one engaged member and three unengaged members represents three potential referrals. |
| CQ-Coverage-3 | For any historical date, identify the wealth advisor covering a customer at that date. | `SELECT ?customer ?advisor ?start ?end WHERE { ?customer atlas:hasAdvisor ?rel . ?rel atlas:coveringAdvisor ?advisor ; atlas:coverageStartDate ?start . OPTIONAL { ?rel atlas:coverageEndDate ?end } FILTER (?start <= "2024-11-01"^^xsd:date) FILTER (!BOUND(?end) \|\| ?end >= "2024-11-01"^^xsd:date) }` | Regulatory inquiries often ask about historical state: "who was responsible for this customer when this event occurred?" Without temporal coverage, this question is unanswerable. |

### Class Derivation from Coverage CQs

| CQ | Classes Derived or Exercised |
|----|------------------------------|
| CQ-Coverage-1 | `atlas:Customer`, `atlas:AdvisoryRelationship`, `atlas:Advisor` |
| CQ-Coverage-2 | `atlas:Customer`, `atlas:Household`, `atlas:AdvisoryRelationship` |
| CQ-Coverage-3 | `atlas:Customer`, `atlas:AdvisoryRelationship`, `atlas:Advisor` |
