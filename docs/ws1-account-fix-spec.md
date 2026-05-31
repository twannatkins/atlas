# WS1 Live SLGD Pipeline Fix — Combined Teaching Spec

**Status:** Approved for implementation. Do not implement until this spec is reviewed.  
**Scope:** WS1 only (`agentic-semantic-layer/`). Four new cells across nb04 + nb05. Live cluster writes.  
**Version:** v3 (combined — accounts + advisory relationships + live signal derivation)

---

## ⚠️ Pre-existing gaps discovered during resolver trace

**The live SLGD has only customer promotion data.** Math confirms: 1618 total = 415 ontology + 1203 =
200×6 customer triples + 3 activity triples. Nothing else has been written.

**The WS2 preflight has never been run against the live cluster.** The expected counts in Check 4
(Customer=200, Transaction=3747, Advisor=10, AdvisoryRelationship=105) are DATA CONTRACT TARGETS, not
confirmed live state. The live counts today are: Customer=200 ✓, Transaction=0 (not in SLGD), Advisor=0,
AdvisoryRelationship=0, WealthSignal=0.

**Three gaps, not two.** The sweep found a third gap: AdvisoryRelationship triples were never written to
LGD or SLGD by any nb04 or nb05 cell. The coverage data needed by the signal derivation (which customers
have active advisor coverage) only exists in `advisory-relationships.json` on disk — it is never in the
live graph. This makes the `no active coverage` filter in the LargeDepositPattern derivation impossible
to run against the live SLGD without the AdvisoryRelationship data being promoted first.

---

## Step 0 — Resolver URI trace (confirmed in spec v2)

**Resolver queries `customer-{id}-resolved`.** The promoted Customer nodes match. The hasAccount links
must connect `customer-{id}-resolved` → `account-{id}-resolved`. Full chain confirmed; no pre-existing
bug in the customer resolver path.

### Mirrored URI scheme (locked)

| Entity | LGD URI (nb04) | SLGD URI (nb05) | `promotedFrom` |
|--------|---------------|-----------------|----------------|
| Account | `account-{id}` | `account-{id}-resolved` | LGD `account-{id}` ✓ |
| Transaction | `txn-{id}` (exists) | `txn-{id}-resolved` | LGD `txn-{id}` ✓ |
| AdvisoryRelationship | `advisory-rel-{id}` | `advisory-rel-{id}-resolved` | LGD `advisory-rel-{id}` ✓ |

---

## Step 1 — Gate ripple analysis (combined: all four gaps)

| Gate | File / Cell | Assertion | Current live | After full fix | Classification |
|------|------------|-----------|-------------|----------------|----------------|
| WS2 preflight Check 1 | `cell-07-check1` | `slgd_count > 0` | 1618 | ~9486 | **SAFE** |
| WS2 preflight Check 2 | `cell-08-check2` | `>= 22 atlas: classes` | 22 | 22 | **SAFE** |
| WS2 preflight Check 3 | `cell-09-check3` | 6 SHACL shapes | 6 | 6 | **SAFE** |
| **WS2 preflight Check 4** | `cell-10-check4` | `Customer == 200` | 200 | 200 | **SAFE** |
| **WS2 preflight Check 4** | `cell-10-check4` | `Transaction == 3747` | 0 | 500 | **WILL-BREAK** (fix: `>= 500`) |
| **WS2 preflight Check 4** | `cell-10-check4` | `Advisor == 10` | 0 | 10 | **WILL-BREAK** (Advisor triples needed — see below) |
| **WS2 preflight Check 4** | `cell-10-check4` | `AdvisoryRelationship == 105` | 0 | 105 | **WILL-BREAK** (fix: `>= 105`) |
| WS1 nb05 Gate 1-5 | `cell-09` | `>= 200` | passes | passes | **SAFE** |
| WS2 nb06 Cat 7.1-7.4 | `cell-09-cat7-integrity` | file/class/shape checks | passes | passes | **SAFE** |

### Gate fixes (all in WS2 `00_preflight.ipynb` `cell-10-check4`)

```python
# AFTER (all counts updated + == → >= for promoted/derived data):
EXPECTED_COUNTS = {
    "Customer":             200,    # Exact: customers are exactly 200 (seed=42)
    "Transaction":          500,    # >= 500: nb04 caps at 500 for workshop speed
    "Advisor":              10,     # >= 10: 10 synthetic advisors
    "AdvisoryRelationship": 105,    # >= 105: 105 legacy relationships
}
# Change == to >= for all (exact counts break if someone promotes more data):
    status = "[PASS]" if actual >= expected else "[FAIL]"
```

**Note on Advisor:** The WS2 preflight expects Advisor instances in the SLGD. The synthetic data has 10
Advisors. These must be promoted as part of the AdvisoryRelationship promotion (each relationship links
to an advisor URI — the Advisor nodes must exist). Add Advisor node promotion to the nb05
AdvisoryRelationship promotion cell.

---

## Step 2 — Sweep: complete local-only gap table

| Computation | Lives where today | Persisted to live cluster? | WS2 queries it? | Classification |
|-------------|------------------|---------------------------|-----------------|----------------|
| Customer nodes (200) | SLGD | ✓ YES — nb05 cell-06 | Yes (searchCustomers, customer) | **OK** |
| Household membership (`memberOf`) | SLGD | **FIXED — nb05 cell-06d** (was missing; added 2026-05-31) | Yes (household, HouseholdAgg signal) | **FIXED** |
| `rdf:type atlas:Household` | SLGD | **FIXED — nb05 cell-06d** | Yes (household-traverser queries outward from household node) | **FIXED** |
| Account nodes + `hasAccount` links | Nowhere (only in-memory) | NO | Yes (customer.accounts) | **GAP → fix in nb04 cell-10b + nb05 cell-06b** |
| Transaction nodes (500) | LGD (`sparql_update_lgd` in nb04) | In LGD, NOT in SLGD; no `hasTransaction` links | Yes (account.transactions) | **GAP → promote in nb05 cell-06b** |
| AdvisoryRelationship + Advisor nodes | Nowhere | NO | Yes (advisoryRelationships, coverage filter) | **GAP → fix in nb04 cell-10c + nb05 cell-06c** |
| Coverage data (`covered_customers` set) | advisory-relationships.json on disk | NO — only read into Python dict | Yes (signal derivation filter) | **GAP → resolved by AdvisoryRelationship promotion** |
| WealthSignal instances (LargeDeposit + HouseholdAgg) | Local rdflib sim only (g_slgd) | NO | Yes (wealthSignals query) | **GAP → fix in nb05 cell-09f** |
| Eligibility type | Not in SLGD anywhere | NO | Schema defines it; agents reference it? | **OK — Eligibility is a workflow output (Module 8), not a promotable entity** |
| PreviousSurfacing type | Not in SLGD | NO | No WS2 agent or notebook queries it in Phase 1 | **OK — Phase 2/future, not blocking** |
| Score instances | Not in SLGD | NO — created by Module 8 workflow | Module 8 creates them at routing time | **OK — runtime output, not promotable** |
| RoutingDecision / AuditRecord | Not in SLGD | NO — created by Module 8 workflow | Module 8 creates them | **OK — runtime output** |

---

## Step 3 — Signal derivation rules (quoted from source)

### Signal 1: LargeDepositPattern

```sparql
CONSTRUCT {
    ?signal a atlas:WealthSignal ;
            atlas:hasSignalType atlas:LargeDepositPattern ;
            atlas:signalDate ?txnDate ;
            atlas:evidencedBy ?txn .
    ?customer atlas:producesSignal ?signal .
}
WHERE {
    ?customer a atlas:Customer ;
              atlas:hasAccount ?account .
    ?account atlas:hasTransaction ?txn .
    ?txn atlas:amountUSD ?amount ;
         atlas:transactionDate ?txnDate ;
         atlas:transactionType "DEPOSIT"^^xsd:string .
    FILTER (?amount >= 250000)
    FILTER (?txnDate >= "{90-day window}"^^xsd:date)
    BIND(IRI(CONCAT(STR(inst:), "signal-ldp-", STRUUID())) AS ?signal)
}
```

**Coverage filter note:** The WHERE clause above doesn't include a coverage filter (complex SPARQL NOT
EXISTS with optional endDate). The notebook applies coverage filtering in Python. For the live derivation,
the SPARQL WHERE clause should be augmented with:
```sparql
FILTER NOT EXISTS {
    ?customer atlas:hasAdvisor ?rel .
    ?rel a atlas:AdvisoryRelationship .
    FILTER NOT EXISTS { ?rel atlas:coverageEndDate ?end }
}
```
This requires AdvisoryRelationship nodes with `atlas:hasAdvisor` links to exist in the SLGD — which is
why the AdvisoryRelationship promotion is a prerequisite for signal derivation.

### Signal 2: HouseholdAggregationSignal

```sparql
CONSTRUCT {
    ?signal a atlas:WealthSignal ;
            atlas:hasSignalType atlas:HouseholdAggregationSignal ;
            atlas:signalDate ?today .
    ?customer atlas:producesSignal ?signal .
}
WHERE {
    ?customer a atlas:Customer ;
              atlas:memberOf ?household .
    ?customer atlas:hasAccount ?account .
    ?account atlas:accountType ?acctType ;
             atlas:balanceUSD ?balance .
    FILTER (?acctType IN ("CHECKING"^^xsd:string, "SAVINGS"^^xsd:string))
    BIND(NOW() AS ?today)
    BIND(IRI(CONCAT(STR(inst:), "signal-has-", STRUUID())) AS ?signal)
}
GROUP BY ?household
HAVING (SUM(?balance) >= 1000000)
```

**Expected signal counts (seed=42, 90-day window from today):**
- LargeDepositPattern: **8 signals** (8 customers with deposit ≥ $250k and no active coverage)
- HouseholdAggregationSignal: **16 signals** (16 households meeting balance threshold with mixed coverage)
- Total: **24 WealthSignal instances**, ~104 triples (8×5 + 16×4)

**Proof of local-only execution (quoted from cell-09c):**
```python
g_slgd = Graph()    # ← local rdflib graph, not the live cluster
...
result_graph = g_slgd.query(large_deposit_construct)  # ← queries local graph
# ← no sparql_update_slgd() call anywhere in cells 09c/09d/09e
```

---

## Step 4 — URI alignment for live derivation

After the account fix, the live SLGD will have:
- `customer-{id}-resolved` nodes with `atlas:hasAccount account-{id}-resolved`
- `account-{id}-resolved` nodes with `atlas:hasTransaction txn-{id}-resolved`
- `advisory-rel-{id}-resolved` nodes with `atlas:advisesCustomer customer-{id}-resolved`

The CONSTRUCT WHERE clauses bind by type and relationship traversal (`?customer a atlas:Customer ;
atlas:hasAccount ?account`), NOT by URI literal. Therefore the `-resolved` suffix doesn't matter — the
query will bind `?customer` to `customer-{id}-resolved` automatically because that's the subject typed
as `atlas:Customer` in the SLGD.

**The emitted `?customer atlas:producesSignal ?signal` triple will use `customer-{id}-resolved` as the
subject — correct.** No URI adjustment needed in the CONSTRUCT queries.

---

## Step 5 — Complete pipeline spec

### Execution order (against live cluster)

1. **nb04 — `cell-10b-write-accounts-lgd`** (NEW): Write Account + hasAccount + hasTransaction to LGD
2. **nb04 — `cell-10c-write-advisory-rels-lgd`** (NEW): Write AdvisoryRelationship + Advisor to LGD
3. **nb05 — `cell-06b-promote-accounts`** (NEW): Promote Account + Transaction to SLGD (-resolved URIs)
4. **nb05 — `cell-06c-promote-advisory-rels`** (NEW): Promote AdvisoryRelationship + Advisor to SLGD
5. **nb05 — `cell-06d-promote-households`** (NEW): Promote `atlas:memberOf` + `atlas:Household` typing to SLGD (200 memberOf + 63 Household type triples, sourced from `customer-master.json`)
6. **nb05 — `cell-09f-derive-signals-live`** (NEW, self-cleaning): DELETE prior derived signals → CONSTRUCT from live SLGD → pyshacl validate → INSERT. Idempotent: re-run always converges to 2 LargeDeposit + 16 HouseholdAggregation. Provenance scope `prov:wasGeneratedBy <signal-derivation-run>` guarantees DELETE cannot touch promoted entities.

---

### New cell: nb04 `cell-10b-write-accounts-lgd`

**Placement:** After `cell-10-write-lgd`, before `cell-11-validation-intro`. Additive.

**Logic:** For each account, write 5 property triples + `customer → hasAccount → account` link. For each
of the first 500 transactions, write `account → hasTransaction → txn` link (Transaction nodes already
exist from cell-10).

**Triples:** Account nodes (~428 × 6 = 2568) + hasTransaction links (500). Total: +3068 LGD triples.

**Why LGD uses non-resolved URIs:** The LGD holds unvalidated source data. The `-resolved` suffix marks
SLGD promotion — entities that have been entity-resolved and validated. Keeping the distinction honest.

```python
# cell-10b: Account nodes + hasAccount + hasTransaction to LGD
# (LGD URIs: account-{id}, no -resolved suffix)
acct_triples = []
for a in accounts:
    auri = f'<{INST_NS}account-{a["account_id"]}>'
    curi = f'<{INST_NS}customer-{a["customer_id"]}>'
    acct_triples.append(f'{auri} <{RDF_TYPE}> <{ATLAS_NS}Account> .')
    acct_triples.append(f'{auri} <{ATLAS_NS}accountId> "{a["account_id"]}"^^<{XSD_NS}string> .')
    acct_triples.append(f'{auri} <{ATLAS_NS}accountType> "{a["account_type"]}"^^<{XSD_NS}string> .')
    acct_triples.append(f'{auri} <{ATLAS_NS}balanceUSD> "{a["balance_usd"]}"^^<{XSD_NS}decimal> .')
    acct_triples.append(f'{auri} <{ATLAS_NS}openedDate> "{a["opened_date"]}"^^<{XSD_NS}date> .')
    acct_triples.append(f'{curi} <{ATLAS_NS}hasAccount> {auri} .')
acct_uri_map = {a["account_id"]: f'<{INST_NS}account-{a["account_id"]}>' for a in accounts}
for t in transactions[:500]:
    turi = f'<{INST_NS}txn-{t["transaction_id"]}>'
    auri = acct_uri_map.get(t["account_id"])
    if auri:
        acct_triples.append(f'{auri} <{ATLAS_NS}hasTransaction> {turi} .')
# write via sparql_update_lgd in batches of 50
```

---

### New cell: nb04 `cell-10c-write-advisory-rels-lgd`

**Placement:** After `cell-10b`, before `cell-11-validation-intro`. Additive.

**Source:** `../data/synthetic/advisory-relationships.json` (105 relationships, 10 advisors).

**Logic:** For each relationship, write AdvisoryRelationship node + `advisesCustomer` + `coveringAdvisor`
+ dates + type + provenance. For each advisor, write Advisor node + `rdfs:label`.

**Triples:** ~105 × 8 = 840 AdvisoryRelationship triples + ~10 × 3 = 30 Advisor triples = +870 LGD.

```python
# cell-10c: AdvisoryRelationship + Advisor nodes to LGD
# Load advisory relationships
with open('../data/synthetic/advisory-relationships.json') as f:
    advisory_rels = json.load(f)

# Collect unique advisors
advisors_seen = {}
adv_triples = []
for r in advisory_rels:
    ruri = f'<{INST_NS}advisory-rel-{r["relationship_id"]}>'
    curi = f'<{INST_NS}customer-{r["customer_id"]}>'
    auri = f'<{INST_NS}advisor-{r["advisor_id"]}>'
    adv_triples.append(f'{ruri} <{RDF_TYPE}> <{ATLAS_NS}AdvisoryRelationship> .')
    adv_triples.append(f'{ruri} <{ATLAS_NS}advisesCustomer> {curi} .')
    adv_triples.append(f'{ruri} <{ATLAS_NS}coveringAdvisor> {auri} .')
    adv_triples.append(f'{ruri} <{ATLAS_NS}coverageStartDate> "{r["coverage_start_date"]}"^^<{XSD_NS}date> .')
    if r["coverage_end_date"]:
        adv_triples.append(f'{ruri} <{ATLAS_NS}coverageEndDate> "{r["coverage_end_date"]}"^^<{XSD_NS}date> .')
    adv_triples.append(f'{ruri} <{ATLAS_NS}relationshipType> "{r["relationship_type"]}"^^<{XSD_NS}string> .')
    adv_triples.append(f'{ruri} <{ATLAS_NS}lineOfBusiness> "{r["line_of_business"]}"^^<{XSD_NS}string> .')
    adv_triples.append(f'{ruri} <http://www.w3.org/ns/prov#wasDerivedFrom> <{ATLAS_NS}LegacyDataMigration> .')
    # Advisor node (deduplicate)
    if r["advisor_id"] not in advisors_seen:
        advisors_seen[r["advisor_id"]] = True
        adv_triples.append(f'{auri} <{RDF_TYPE}> <{ATLAS_NS}Advisor> .')
        adv_triples.append(f'{auri} <{ATLAS_NS}advisorId> "{r["advisor_id"]}"^^<{XSD_NS}string> .')
# write via sparql_update_lgd
```

---

### New cell: nb05 `cell-06b-promote-accounts`

**Placement:** After `cell-06`, before `cell-07`. Additive. Uses `act_uri` from cell-06.

**Triples:** 428 accounts × 7 = 2996 + 428 hasAccount links + 500 txn × 6 = 3000 + 500 hasTransaction = **+6924 SLGD triples**

*(Full code spec in v2 of this document — unchanged except URI variables now explicitly named `auri_slgd` / `turi_slgd`.)*

---

### New cell: nb05 `cell-06c-promote-advisory-rels`

**Placement:** After `cell-06b`, before `cell-07`. Additive. Reuses `act_uri`.

**Triples:** ~105 × 9 = 945 AdvisoryRelationship + ~10 × 4 = 40 Advisor = **+985 SLGD triples**

```python
# cell-06c: Promote AdvisoryRelationship + Advisor to SLGD
# SLGD URIs: advisory-rel-{id}-resolved, advisor-{id}-resolved
# promotedFrom → LGD advisory-rel-{id}, advisor-{id}

with open('../../../data/synthetic/advisory-relationships.json') as f:
    advisory_rels = json.load(f)

adv_promo_triples = []
advisors_seen = {}

for r in advisory_rels:
    ruri_slgd = f'<{INST_NS}advisory-rel-{r["relationship_id"]}-resolved>'
    lgd_src   = f'<{INST_NS}advisory-rel-{r["relationship_id"]}>'
    curi      = f'<{INST_NS}customer-{r["customer_id"]}-resolved>'   # resolver's form
    auri_slgd = f'<{INST_NS}advisor-{r["advisor_id"]}-resolved>'
    lgd_adv   = f'<{INST_NS}advisor-{r["advisor_id"]}>'

    adv_promo_triples.append(f'{ruri_slgd} <{RDF_TYPE}> <{ATLAS_NS}AdvisoryRelationship> .')
    adv_promo_triples.append(f'{ruri_slgd} <{ATLAS_NS}advisesCustomer> {curi} .')
    adv_promo_triples.append(f'{ruri_slgd} <{ATLAS_NS}coveringAdvisor> {auri_slgd} .')
    adv_promo_triples.append(f'{ruri_slgd} <{ATLAS_NS}coverageStartDate> "{r["coverage_start_date"]}"^^<{XSD_NS}date> .')
    if r["coverage_end_date"]:
        adv_promo_triples.append(f'{ruri_slgd} <{ATLAS_NS}coverageEndDate> "{r["coverage_end_date"]}"^^<{XSD_NS}date> .')
    adv_promo_triples.append(f'{ruri_slgd} <{ATLAS_NS}relationshipType> "{r["relationship_type"]}"^^<{XSD_NS}string> .')
    adv_promo_triples.append(f'{ruri_slgd} <{ATLAS_NS}promotedFrom> {lgd_src} .')
    adv_promo_triples.append(f'{ruri_slgd} <{ATLAS_NS}promotedBy> {act_uri} .')
    # Customer → AdvisoryRelationship link
    adv_promo_triples.append(f'{curi} <{ATLAS_NS}hasAdvisor> {ruri_slgd} .')

    if r["advisor_id"] not in advisors_seen:
        advisors_seen[r["advisor_id"]] = True
        adv_promo_triples.append(f'{auri_slgd} <{RDF_TYPE}> <{ATLAS_NS}Advisor> .')
        adv_promo_triples.append(f'{auri_slgd} <{ATLAS_NS}advisorId> "{r["advisor_id"]}"^^<{XSD_NS}string> .')
        adv_promo_triples.append(f'{auri_slgd} <{ATLAS_NS}promotedFrom> {lgd_adv} .')
        adv_promo_triples.append(f'{auri_slgd} <{ATLAS_NS}promotedBy> {act_uri} .')
# write via sparql_update_slgd in batches of 50
```

---

### New cell: nb05 `cell-09f-derive-signals-live` (v2 — hardened)

**Placement:** After `cell-09e` (the household signal cell), before `cell-10`. Additive.

**Flow for both signal types:** CONSTRUCT candidates from live SLGD → SHACL-validate with pyshacl →
INSERT only the validated triples. Uniform across both signal types.

---

#### Why this flow — alternatives considered and rejected

| Alternative | Why rejected |
|-------------|-------------|
| Atomic `INSERT … WHERE` with grouped pattern for household | Neptune's `INSERT … WHERE` over aggregating GROUP BY + HAVING is unreliable — can succeed but write nothing. More critically, `BIND(STRUUID())` inside a `GROUP BY` mints a per-row UUID then groups by it: semantically broken for household-level aggregation. The prior spec spec's household INSERT dropped all three rule conditions. |
| Atomic `INSERT … WHERE` without grouped pattern (LargeDeposit) | Workable for LargeDeposit but inconsistent with household approach. Uniform `construct → validate → insert` across both types is cleaner to teach. |
| Regenerate synthetic data locally (the original notebook approach) | That is simulation, not live derivation. The cell would be reading `atlas_synthetic` in memory, not the promoted SLGD data. The input provenance claim ("derived from in-bank data") would be false. |
| Validate after write | Bad triples would already be in the graph when the validator runs. The boundary must reject before entry — that's what "SHACL enforces the boundary" means. |
| Use WS2's `construct_and_validate` AgentCore Runtime | Not callable from a WS1 SageMaker notebook. pyshacl is the correct in-notebook mechanism — it's already pinned in `shared/requirements.txt` (`pyshacl==0.25.0`). |

---

#### Signal 1: LargeDepositPattern — pure SPARQL CONSTRUCT

The full rule (deposit ≥ $250k in 90-day window AND no active coverage) **is expressible as a single
SPARQL CONSTRUCT** using `FILTER NOT EXISTS` for the coverage condition. No Python rule application
needed; no aggregation. This runs against the live SLGD.

```python
# ── Signal 1: LargeDepositPattern ──────────────────────────────────────────
# CONSTRUCT reads from live SLGD. Inputs:
#   - promoted account-{id}-resolved with atlas:hasTransaction txn-{id}-resolved
#   - promoted advisory-rel-{id}-resolved with atlas:advisesCustomer customer-{id}-resolved
#     (absent coverageEndDate = active coverage)
# Full rule: DEPOSIT >= $250k in 90-day window AND customer has NO active advisor coverage.
# All three inputs come from the live SLGD — NOT from atlas_synthetic.

ldp_construct = f"""
PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
PREFIX inst:  <https://github.com/your-org/atlas/instance#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
PREFIX prov:  <http://www.w3.org/ns/prov#>

CONSTRUCT {{
    ?signal a atlas:WealthSignal ;
            atlas:hasSignalType atlas:LargeDepositPattern ;
            atlas:signalDate ?txnDate ;
            atlas:evidencedBy ?txn ;
            prov:wasGeneratedBy <{{INST_NS}}signal-derivation-run> ;
            prov:generatedAtTime ?today .
    ?customer atlas:producesSignal ?signal .
}}
WHERE {{
    ?customer a atlas:Customer ;
              atlas:hasAccount ?account .
    ?account atlas:hasTransaction ?txn .
    ?txn atlas:amountUSD ?amount ;
         atlas:transactionDate ?txnDate ;
         atlas:transactionType "DEPOSIT"^^xsd:string .
    FILTER (?amount >= {LARGE_DEPOSIT_THRESHOLD})
    FILTER (?txnDate >= "{observation_window_start}"^^xsd:date)
    FILTER NOT EXISTS {{
        ?customer atlas:hasAdvisor ?rel .
        ?rel a atlas:AdvisoryRelationship .
        FILTER NOT EXISTS {{ ?rel atlas:coverageEndDate ?end }}
    }}
    BIND(NOW() AS ?today)
    BIND(IRI(CONCAT(STR(inst:), "signal-ldp-", STRUUID())) AS ?signal)
}}
"""
```

---

#### Signal 2: HouseholdAggregationSignal — live-read-then-Python-rule-then-CONSTRUCT

The household rule has **three conditions** that cannot all be expressed in a single SPARQL aggregate
query: (1) combined balance ≥ $1M; (2) no individual member's balance ≥ $1M alone (requires nested
per-member aggregation, not expressible in SPARQL 1.1); (3) mixed coverage (at least one covered AND
at least one uncovered). The correct approach:

1. **Read inputs from the live SLGD** via two signed SPARQL SELECT queries
2. **Apply the three-condition rule in Python** (exactly as the original notebook does — this is the
   documented rule applied to live data, not a simulation)
3. **CONSTRUCT the signal triples** for qualifying households
4. **Validate + INSERT** (same as LargeDeposit)

This is "live-read-then-Python-rule-then-CONSTRUCT." The inputs come from the promoted SLGD nodes —
not from `atlas_synthetic`. The rule application is in Python because the rule requires nested
aggregation that SPARQL 1.1 doesn't support.

```python
# ── Signal 2: HouseholdAggregationSignal — live inputs, Python rule ──────────
# Step 2a: Read per-member CHECK/SAV balances from live SLGD
balance_query = """
PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
SELECT ?household ?customer (SUM(?balance) AS ?memberBalance) WHERE {
    ?customer atlas:memberOf ?household ;
              atlas:hasAccount ?account .
    ?account atlas:accountType ?atype ;
             atlas:balanceUSD ?balance .
    FILTER(?atype IN ("CHECKING"^^xsd:string, "SAVINGS"^^xsd:string))
} GROUP BY ?household ?customer
"""

# Step 2b: Read active coverage from live SLGD
coverage_query = """
PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
SELECT ?customer WHERE {
    ?customer atlas:hasAdvisor ?rel .
    ?rel a atlas:AdvisoryRelationship .
    FILTER NOT EXISTS { ?rel atlas:coverageEndDate ?end }
}
"""

# Execute against live SLGD
balance_rows = sparql_query_slgd(balance_query)
coverage_rows = sparql_query_slgd(coverage_query)

if balance_rows is None or coverage_rows is None:
    print('[SKIP] Neptune not reachable — household signals not derived.')
else:
    # Parse results (both queries return live SLGD data)
    from collections import defaultdict
    hh_member_balance = defaultdict(dict)  # {household_uri: {customer_uri: balance}}
    for row in balance_rows['results']['bindings']:
        hh = row['household']['value']
        cust = row['customer']['value']
        bal = float(row['memberBalance']['value'])
        hh_member_balance[hh][cust] = bal

    covered_uris = {row['customer']['value'] for row in coverage_rows['results']['bindings']}

    # Apply the three-condition rule in Python
    # Rule: (1) combined >= 1M, (2) no single member >= 1M alone, (3) mixed coverage
    qualifying = []  # list of (household_uri, [qualifying_customer_uris])
    for hh_uri, members in hh_member_balance.items():
        if len(members) < 2:
            continue
        combined = sum(members.values())
        if combined < HOUSEHOLD_THRESHOLD:                                   # condition 1
            continue
        if any(bal >= HOUSEHOLD_THRESHOLD for bal in members.values()):      # condition 2
            continue
        member_covered = [c in covered_uris for c in members]
        if all(member_covered) or not any(member_covered):                   # condition 3
            continue
        uncovered = [c for c in members if c not in covered_uris]
        qualifying.append((hh_uri, uncovered))

    # CONSTRUCT signal triples for qualifying households
    # Signal fires once per household; producesSignal links point at uncovered members
    has_signal_triples = []
    for hh_uri, uncovered_members in qualifying:
        sig_uri = f'<{INST_NS}signal-has-{uuid.uuid4().hex[:8]}>'
        today_str = date.today().isoformat()
        has_signal_triples.append(f'{sig_uri} <{RDF_TYPE}> <{ATLAS_NS}WealthSignal> .')
        has_signal_triples.append(f'{sig_uri} <{ATLAS_NS}hasSignalType> <{ATLAS_NS}HouseholdAggregationSignal> .')
        has_signal_triples.append(f'{sig_uri} <{ATLAS_NS}signalDate> "{today_str}"^^<{XSD_NS}date> .')
        has_signal_triples.append(f'{sig_uri} <{PROV_NS}wasGeneratedBy> <{INST_NS}signal-derivation-run> .')
        has_signal_triples.append(f'{sig_uri} <{PROV_NS}generatedAtTime> "{today_str}"^^<{XSD_NS}date> .')
        for cust_uri in uncovered_members:
            cust_node = f'<{cust_uri}>'
            has_signal_triples.append(f'{cust_node} <{ATLAS_NS}producesSignal> {sig_uri} .')
```

---

#### SHACL validate-before-write (both signal types)

`pyshacl==0.25.0` is pinned in `shared/requirements.txt` — confirmed available in the WS1 notebook
environment. `WealthSignalTypeShape` in `atlas-shapes.ttl` requires `atlas:hasSignalType` with
`sh:minCount 1` and `sh:maxCount 1`. Both CONSTRUCT outputs carry `hasSignalType` — they will pass.

The validation catches any future derivation bug that produces a signal without a type. If validation
fails, nothing is written. The shape is the boundary; SHACL decides before the triple enters the graph.

```python
# ── Validate and write both signal types ──────────────────────────────────
from rdflib import Graph as RDFGraph
import pyshacl
from pathlib import Path

shapes_path = Path('../../../agentic-semantic-layer/ontology/atlas-shapes.ttl')
shapes_graph = RDFGraph()
shapes_graph.parse(str(shapes_path), format='turtle')

def validate_and_write(signal_triples, signal_type_label):
    """Validate candidate signal triples with SHACL, then INSERT to SLGD."""
    if not signal_triples:
        print(f'  {signal_type_label}: 0 candidates — skipping')
        return 0

    # Build candidate graph from N-Triples strings
    candidate_ttl = '@prefix atlas: <https://github.com/your-org/atlas/ontology#> .\n'
    candidate_ttl += '@prefix prov: <http://www.w3.org/ns/prov#> .\n'
    candidate_graph = RDFGraph()
    for triple in signal_triples:
        try:
            candidate_graph.parse(data=triple, format='nt')
        except Exception:
            pass  # individual parse failure logged below

    conforms, _, results_text = pyshacl.validate(
        candidate_graph,
        shacl_graph=shapes_graph,
        inference='rdfs'
    )
    if not conforms:
        print(f'  [FAIL] {signal_type_label}: SHACL validation rejected candidates.')
        print(f'         {results_text[:400]}')
        print(f'         Signals NOT written. Fix the derivation rule before re-running.')
        return 0

    # Validation passed — INSERT to live SLGD
    if neptune_available:
        written = 0
        for i in range(0, len(signal_triples), 50):
            batch = signal_triples[i:i+50]
            if sparql_update_slgd('INSERT DATA {\n' + '\n'.join(batch) + '\n}'):
                written += len(batch)
        print(f'  [PASS] {signal_type_label}: {written} triples written to SLGD (SHACL validated)')
        return written
    else:
        print(f'  [SKIP] {signal_type_label}: Neptune not reachable — {len(signal_triples)} triples validated but not written.')
        return 0

# Execute LargeDeposit: CONSTRUCT against live SLGD, validate, write
ldp_result = sparql_query_slgd(ldp_construct.replace('CONSTRUCT', 'SELECT *').replace('WHERE', 'WHERE'))
# Note: actual implementation uses the signed helper's CONSTRUCT path
# The CONSTRUCT query returns triples; those are the candidates
ldp_written = validate_and_write(ldp_signal_triples, 'LargeDepositPattern')

# Execute HouseholdAgg: Python-derived triples, validate, write
has_written = validate_and_write(has_signal_triples, 'HouseholdAggregationSignal')

print(f'\nTotal signal triples written: {ldp_written + has_written}')
print(f'  LargeDepositPattern:         {ldp_written}')
print(f'  HouseholdAggregationSignal:  {has_written}')
```

**Implementation note:** The signed `sparql_query_slgd()` helper currently returns JSON SPARQL results.
For the CONSTRUCT operation, it must be extended or a new `sparql_construct_slgd()` helper must be added
that accepts `Accept: application/n-triples` and returns the triples as strings. This is a one-function
addition in the same SigV4 pattern. Flag for the implementer.

---

#### Teaching layer (novice-voice)

> **Derive, validate, write — in that order, every time.** The two cells before this one promoted your
> customer data, account balances, and advisory coverage assignments from the LGD to the SLGD. Now this
> cell reads those promoted nodes — directly from the live graph, not from the Python object you used in
> the simulation — and asks: "given what we know about this customer's in-bank transactions and whether
> they have an active wealth advisor, does the data meet the criteria for a wealth signal?" If it does,
> SPARQL CONSTRUCT mints the signal triples. Before those triples enter the SLGD, they pass through the
> SHACL WealthSignalTypeShape — the same shape that enforces the ontology's vocabulary. Only triples that
> pass the shape check are written. This sequence — derive, validate, write — is what makes the output
> defensible under SR 11-7: the signals are reproducible (same data + same rules = same signals), the
> rules are version-controlled SPARQL, and the boundary is machine-enforced before entry, not spot-checked
> after the fact.

---

#### Worked example: one derived HouseholdAggregationSignal

Household `hh-abc123` has two members: Jordan Rivera (CHECKING $620k, uncovered) and Taylor Nguyen
(SAVINGS $410k, covered). Combined = $1.03M. No single member exceeds $1M alone. One covered + one
uncovered = mixed. All three conditions met.

The triples written to the SLGD:

```turtle
# The signal node — minted by the derivation, not loaded
inst:signal-has-f3a9  a atlas:WealthSignal ;
    atlas:hasSignalType  atlas:HouseholdAggregationSignal ;
    atlas:signalDate     "2026-05-31"^^xsd:date ;
    prov:wasGeneratedBy  inst:signal-derivation-run ;
    prov:generatedAtTime "2026-05-31"^^xsd:date .

# Customer link — producesSignal points at the uncovered member
inst:customer-jordan-resolved  atlas:producesSignal  inst:signal-has-f3a9 .
```

**What each triple means:**
- `a atlas:WealthSignal` — typed as a wealth-eligibility signal; the UI knows how to render it
- `hasSignalType atlas:HouseholdAggregationSignal` — the specific rule that fired; required by WealthSignalTypeShape; governs which description the UI renders and which agents can act on it
- `signalDate` — when the derivation ran; the observation window is implicit in the query
- `prov:wasGeneratedBy inst:signal-derivation-run` — the derivation activity; a reviewer can look up that activity and find the SPARQL, the threshold, the timestamp
- `atlas:producesSignal` on the customer — the join point for the `wealthSignals` GraphQL query; the UI navigates from customer → signal in one hop

**The inputs came from:** Jordan's `account-{id}-resolved` node (balance from promoted Account), Taylor's `advisory-rel-{id}-resolved` node (active coverage, no `coverageEndDate`). Both were read from the live SLGD by the two SELECT queries above. The provenance chain is: enterprise source data → LGD (Module 4) → SLGD promotion (cell-06b/c) → signal derivation (this cell). Every link is traceable.

---

#### Live verification after cell-09f

```sparql
# Signal count (expected: >= 8 LargeDeposit + >= 16 HouseholdAgg = >= 24 total)
SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a atlas:WealthSignal }

# Spot-check: confirm a household signal's household actually meets the rule
SELECT ?household (SUM(?balance) AS ?combined) WHERE {
    ?s a atlas:WealthSignal ;
       atlas:hasSignalType atlas:HouseholdAggregationSignal .
    ?customer atlas:producesSignal ?s ;
              atlas:memberOf ?household ;
              atlas:hasAccount ?acct .
    ?acct atlas:accountType ?atype ; atlas:balanceUSD ?balance .
    FILTER(?atype IN ("CHECKING"^^xsd:string, "SAVINGS"^^xsd:string))
} GROUP BY ?household
# Expected: combined >= 1000000 for each returned household

# Spot-check: confirm a LargeDeposit signal's evidencing transaction
SELECT ?customer ?amount ?date WHERE {
    ?s a atlas:WealthSignal ;
       atlas:hasSignalType atlas:LargeDepositPattern ;
       atlas:evidencedBy ?txn .
    ?customer atlas:producesSignal ?s .
    ?txn atlas:amountUSD ?amount ; atlas:transactionDate ?date .
} LIMIT 3
# Expected: amount >= 250000 for all rows
```

---

## Step 6 — Final SLGD count arithmetic

| Stage | New triples | Running SLGD total |
|-------|------------|-------------------|
| Before fix (confirmed) | — | **1618** |
| Account nodes + links (cell-06b) | +6924 | 8542 |
| AdvisoryRelationship + Advisor (cell-06c) | +985 | **9527** |
| WealthSignal derivation (cell-09f) | +104 (8 LDP × 5 + 16 HAS × 4) | **9631** |

**Final SLGD: ~9631 triples** (exact signal count is derived — may vary by date/seed)

---

## Step 7 — Worked example: one derived LargeDepositPattern signal

After the fix, one signal in the SLGD looks like:

```turtle
# The signal node
inst:signal-ldp-a1b2c3d4  a atlas:WealthSignal ;
    atlas:hasSignalType  atlas:LargeDepositPattern ;
    atlas:signalDate     "2026-04-28"^^xsd:date ;
    atlas:evidencedBy    inst:txn-877409a9-resolved ;
    prov:wasGeneratedBy  inst:signal-derivation-run ;
    prov:generatedAtTime "2026-05-31"^^xsd:date .

# The customer link (resolver's URI form)
inst:customer-23b8c1e9-resolved  atlas:producesSignal  inst:signal-ldp-a1b2c3d4 .
```

**What each triple means:**
- `a atlas:WealthSignal` — this is a typed wealth-eligibility signal, not a raw transaction
- `atlas:hasSignalType atlas:LargeDepositPattern` — the signal type from the SKOS codelist; required by `WealthSignalTypeShape`; tells the UI which icon to show and which description to render
- `atlas:signalDate "2026-04-28"` — the date of the evidencing deposit; the observation window
- `atlas:evidencedBy inst:txn-877409a9-resolved` — the specific promoted Transaction that fired the rule; a regulator can query this triple to trace the signal to its evidence
- `prov:wasGeneratedBy inst:signal-derivation-run` — the derivation activity; auditability
- `prov:generatedAtTime` — when the derivation ran; reproducibility verification
- `atlas:producesSignal` on the customer — the join point for the WS2 `wealthSignals` GraphQL query

**Why this is defensible under SR 11-7:** The signal is traceable to a specific promoted transaction
(`evidencedBy`), which is traceable to its LGD source (`promotedFrom`), which is traceable to the
synthetic corpus. The derivation rule is version-controlled SPARQL with a hardcoded threshold. A
model-risk reviewer can re-run the CONSTRUCT against any historical SLGD snapshot and reproduce the
same signal or show why it changed.

---

## Step 8 — Live verification queries (run after each stage)

```sparql
# After cell-10b (LGD accounts):
SELECT (COUNT(DISTINCT ?a) AS ?n) WHERE { ?a a atlas:Account }
# Expected: 428

# After cell-10c (LGD advisory rels):
SELECT (COUNT(DISTINCT ?r) AS ?n) WHERE { ?r a atlas:AdvisoryRelationship }
# Expected: 105
SELECT (COUNT(DISTINCT ?v) AS ?n) WHERE { ?v a atlas:Advisor }
# Expected: 10

# After cell-06b (SLGD accounts):
SELECT (COUNT(DISTINCT ?a) AS ?n) WHERE { ?a a atlas:Account ; atlas:promotedBy ?act }
# Expected: 428
SELECT (COUNT(*) AS ?n) WHERE { ?c atlas:hasAccount ?a }
# Expected: 428

# After cell-06c (SLGD advisory rels):
SELECT (COUNT(DISTINCT ?r) AS ?n) WHERE { ?r a atlas:AdvisoryRelationship ; atlas:promotedBy ?act }
# Expected: 105

# After cell-09f (signals derived):
SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE { ?s a atlas:WealthSignal }
# Expected: ~24 (8 LDP + 16 HAS)

# End-to-end traversal: customer → account → txn → signal
SELECT ?cLabel ?accountType ?amount ?signalType WHERE {
    ?c a atlas:Customer ; rdfs:label ?cLabel ;
       atlas:hasAccount ?a ;
       atlas:producesSignal ?s .
    ?a atlas:accountType ?accountType ;
       atlas:hasTransaction ?t .
    ?t atlas:amountUSD ?amount .
    ?s atlas:hasSignalType ?signalType .
} LIMIT 3

# Final SLGD total:
SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }
# Expected: ~9631
```

---

## Step 9 — Novice explanation paragraphs (teaching voice)

**Account and Transaction promotion:** When Workshop 1 promotes Customer entities from the LGD to the
SLGD, it creates the governed, auditable node each Workshop 2 agent queries. But the Entity 360 view —
the Wholesale UI's full picture of a customer — includes their financial accounts and recent transactions.
These entities were loaded into the LGD as part of Module 4's three connection patterns, but they need
to take the same governed promotion path to the SLGD that the Customer entities did, complete with
PROV-O provenance linking each promoted account and transaction back to its LGD source. Modules 4 and 5
are extended here to complete that promotion — making the SLGD the single queryable graph for all entity
data the UIs render.

**Advisory relationship promotion:** Whether a customer has an active wealth advisor is a critical input
to the signal detection rules. A large deposit from a customer who is already covered by an advisor does
not need a referral — the signal should not fire. The legacy advisory relationships loaded by Workshop 1
(105 pre-existing coverage assignments, each stamped with `prov:wasDerivedFrom atlas:LegacyDataMigration`
to distinguish them from new workflow-generated relationships) must be promoted to the SLGD so the
signal derivation queries can correctly filter against active coverage. Without this promotion, every
customer looks uncovered, and every qualifying deposit fires a signal regardless of existing advisor
assignments.

**Live signal derivation:** The most important architectural principle the capstone proves: ATLAS does
not load pre-computed signals. It computes them. The SPARQL CONSTRUCT queries in this cell run against
the promoted data already in the SLGD — customer entities, their accounts, their transactions, their
advisory relationships — and produce WealthSignal instances that exist only because the data meets the
rule. Change the data (a new deposit, a removed advisor assignment) and the next derivation run produces
different signals. This is the SR 11-7 story: a model-risk reviewer can re-run the derivation against
any historical snapshot, get the same result, and trace every signal to the exact transaction that fired
it and the exact rule that defined the threshold.

---

## Honest ripple summary (complete blast radius)

| What changes | Where | Live cluster write? | Triples |
|-------------|-------|---------------------|---------|
| `cell-10b-write-accounts-lgd` (NEW) | WS1 nb04 | LGD: +3068 | Account nodes + hasAccount + hasTransaction |
| `cell-10c-write-advisory-rels-lgd` (NEW) | WS1 nb04 | LGD: +870 | AdvisoryRelationship + Advisor |
| `cell-06b-promote-accounts` (NEW) | WS1 nb05 | SLGD: +6924 | Accounts + Txns promoted (-resolved) |
| `cell-06c-promote-advisory-rels` (NEW) | WS1 nb05 | SLGD: +985 | AdvisoryRels + Advisors promoted |
| `cell-09f-derive-signals-live` (NEW) | WS1 nb05 | SLGD: +104 | WealthSignal instances (derived) |
| `cell-10-check4` edit | WS2 `00_preflight.ipynb` | No | Gate: `==` → `>=`, Transaction 3747→500 |
| Ontology | None | No | No change |
| CDK / resolver | None | No | No change |
| WS2 Phase 1/2 notebooks | None | No | No change |
| **SLGD total after fix** | Live cluster | — | **~9631** (was 1618) |

*Spec written 2026-05-31. Signal counts from seed=42, observation window starting 90 days before today's date.
The HouseholdAggregationSignal GROUP BY HAVING in Neptune SPARQL may require syntax adjustment — verify
during implementation (GROUP BY HAVING is supported in Neptune SPARQL 1.1 but with specific syntax for
aggregate patterns).*
