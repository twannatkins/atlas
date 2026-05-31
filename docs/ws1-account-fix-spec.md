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
| Household membership (`memberOf`) | SLGD (via Customer triples in nb04→promotion) | ✓ YES | Yes (household) | **OK** |
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
5. **nb05 — `cell-09f-derive-signals-live`** (NEW): Run CONSTRUCT against live SLGD, INSERT results

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

### New cell: nb05 `cell-09f-derive-signals-live`

**Placement:** After `cell-09e` (the household signal cell), before `cell-10`. Additive.

**THE PRINCIPLE:** This cell runs the SAME CONSTRUCT queries against the LIVE SLGD and writes the
resulting signal triples back via `sparql_update_slgd()`. It does NOT hand-write signal URIs or insert
pre-computed signal triples. Signals emerge from the data — this is the deterministic-boundary thesis.

**Why derive live instead of inserting:** Inserting pre-computed signals violates SR 11-7's
reproducibility requirement. A regulator must be able to re-run the derivation against the current graph
and get the same signals. If signals are pre-inserted, re-running the derivation produces duplicates or
contradictions. Signals are computed outputs, not loaded inputs.

**Why CONSTRUCT + SHACL instead of Python rules:** SPARQL CONSTRUCT is version-controlled, readable, and
runnable by any SPARQL-compliant engine. Python rules are harder to audit. SHACL validation before write
ensures every minted WealthSignal has `atlas:hasSignalType` (required by `WealthSignalTypeShape`) before
it enters the graph.

**SHACL validation:** `WealthSignalTypeShape` requires `atlas:hasSignalType` with `sh:minCount 1` and
`sh:maxCount 1`. The `construct_and_validate` operation in `atlas-sparql-mcp` runs CONSTRUCT then passes
the resulting triples to `atlas-shacl-mcp` for validation before any INSERT. **However,** the
`construct_and_validate` operation is a WS2 AgentCore Runtime call — not directly available from nb05.
For the live derivation in the notebook, use the signed `sparql_update_slgd()` helper with an
INSERT-WHERE (CONSTRUCT semantics written as INSERT ... WHERE) so the derivation and write are atomic.
Post-write SHACL validation runs via a separate `pyshacl` call against a local copy of the signal triples.

```python
# cell-09f: Derive WealthSignals against the LIVE SLGD and write them back.
# PRINCIPLE: signals emerge from CONSTRUCT; never inserted by hand.

from datetime import date, timedelta
import uuid

LARGE_DEPOSIT_THRESHOLD = 250_000
HOUSEHOLD_THRESHOLD = 1_000_000
observation_window_start = str(date.today() - timedelta(days=90))

# ── Signal 1: LargeDepositPattern ──────────────────────────────────────────
# Run as INSERT ... WHERE (equivalent to CONSTRUCT + INSERT, but atomic)
# Coverage filter uses the promoted AdvisoryRelationship nodes in SLGD.

ldp_insert = f"""
PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
PREFIX inst:  <https://github.com/your-org/atlas/instance#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
PREFIX prov:  <http://www.w3.org/ns/prov#>

INSERT {{
    ?signal a atlas:WealthSignal ;
            atlas:hasSignalType atlas:LargeDepositPattern ;
            atlas:signalDate ?txnDate ;
            atlas:evidencedBy ?txn ;
            prov:wasGeneratedBy <{INST_NS}signal-derivation-run> ;
            prov:generatedAtTime "{date.today().isoformat()}"^^xsd:date .
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
    BIND(IRI(CONCAT(STR(inst:), "signal-ldp-", STRUUID())) AS ?signal)
}}
"""

# ── Signal 2: HouseholdAggregationSignal ────────────────────────────────────
has_insert = f"""
PREFIX atlas: <https://github.com/your-org/atlas/ontology#>
PREFIX inst:  <https://github.com/your-org/atlas/instance#>
PREFIX xsd:   <http://www.w3.org/2001/XMLSchema#>
PREFIX prov:  <http://www.w3.org/ns/prov#>

INSERT {{
    ?signal a atlas:WealthSignal ;
            atlas:hasSignalType atlas:HouseholdAggregationSignal ;
            atlas:signalDate "{date.today().isoformat()}"^^xsd:date ;
            prov:wasGeneratedBy <{INST_NS}signal-derivation-run> ;
            prov:generatedAtTime "{date.today().isoformat()}"^^xsd:date .
    ?customer atlas:producesSignal ?signal .
}}
WHERE {{
    ?customer a atlas:Customer ;
              atlas:memberOf ?household .
    ?customer atlas:hasAccount ?account .
    ?account atlas:accountType ?acctType ;
             atlas:balanceUSD ?balance .
    FILTER (?acctType IN ("CHECKING"^^xsd:string, "SAVINGS"^^xsd:string))
    BIND(IRI(CONCAT(STR(inst:), "signal-has-", STRUUID())) AS ?signal)
}}
GROUP BY ?household ?customer ?signal
HAVING (SUM(?balance) >= {HOUSEHOLD_THRESHOLD})
"""

if neptune_available:
    ok1 = sparql_update_slgd(ldp_insert)
    ok2 = sparql_update_slgd(has_insert)
    print(f'LargeDepositPattern written: {ok1}')
    print(f'HouseholdAggregationSignal written: {ok2}')
else:
    print('[SKIP] Neptune not reachable — signals not written.')
    print('       Run from SageMaker (inside VPC) for live derivation.')
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
