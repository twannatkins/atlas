# WS1 Account-Gap Fix — Implementation Spec

**Status:** Approved for implementation. Do not implement until this spec is reviewed.  
**Scope:** WS1 only (`agentic-semantic-layer/`). Two notebooks modified. Live cluster writes required.  
**Decision basis:** Option A — write Accounts to LGD first (nb04), then promote to SLGD with real
`promotedFrom` provenance (nb05). No placeholder URIs.

---

## Step 1 — Gate ripple analysis

### Gates checked

| Gate | File / Cell | Assertion | Current value | After fix | Classification |
|------|------------|-----------|---------------|-----------|----------------|
| WS2 preflight Check 1 | `00_preflight.ipynb` / `cell-07-check1` | `slgd_count > 0` | ~1618 | ~8542 | **SAFE** (inequality, not exact) |
| WS2 preflight Check 2 | `cell-08-check2` | `len(found_classes) >= 22` | 22 | 22 (unchanged) | **SAFE** |
| WS2 preflight Check 2 | `cell-08-check2` | 15 named required classes present | passes | passes (Account already in ontology) | **SAFE** |
| WS2 preflight Check 3 | `cell-09-check3` | 6 SHACL shapes present | passes | passes (shapes unchanged) | **SAFE** |
| WS2 preflight Check 4 | `cell-10-check4` | `Customer == 200` | 200 | 200 (unchanged — customers not re-promoted) | **SAFE** |
| WS2 preflight Check 4 | `cell-10-check4` | `Transaction == 3747` | 0 (not in SLGD today) → after fix: 500 | 500 ≠ 3747 | **WILL-BREAK** |
| WS2 preflight Check 4 | `cell-10-check4` | `Advisor == 10` | 10 | 10 (unchanged) | **SAFE** |
| WS2 preflight Check 4 | `cell-10-check4` | `AdvisoryRelationship == 105` | 105 | 105 (unchanged) | **SAFE** |
| WS1 nb05 Gate 1 | `cell-09` | `entities_with_provenance >= 200` | ≥200 | ≥200+428 (still ≥200) | **SAFE** |
| WS1 nb05 Gate 2 | `cell-09` | `entities_with_activity >= 200` | ≥200 | ≥200+428 | **SAFE** |
| WS1 nb05 Gate 3 | `cell-09` | `entities_with_confidence >= 200` | ≥200 | accounts have no confidence score | **SAFE** — confidence check is on the `promotion_triples` in-memory list; Account triples live in a new cell's own list |
| WS1 nb05 Gate 5 | `cell-09` | `promoted_count >= 200` | 200 | 200 (customers only; new cell is separate) | **SAFE** |
| WS2 nb06 Cat 7.1 | `cell-09-cat7-integrity` | WS1 files exist | passes | passes (no file changes) | **SAFE** |
| WS2 nb06 Cat 7.2 | `cell-09-cat7-integrity` | `class_count == 22` | 22 | 22 (TTL files unchanged) | **SAFE** |
| WS2 nb06 Cat 7.3 | `cell-09-cat7-integrity` | `atlas-shapes.ttl` exists | passes | passes | **SAFE** |
| WS2 nb06 Cat 7.4 | `cell-09-cat7-integrity` | WS2 extensions use `atlas-part-2:` | passes | passes | **SAFE** |

### The one WILL-BREAK gate

**WS2 preflight `cell-10-check4` — Transaction count:**

```python
EXPECTED_COUNTS = {
    "Customer":             200,
    "Transaction":          3747,   # ← WILL-BREAK: SLGD currently has 0, fix adds 500
    "Advisor":              10,
    "AdvisoryRelationship": 105,
}
```

The preflight asserts `Transaction == 3747` (the full corpus count). But the fix promotes only
the first 500 transactions (the nb04 cap for workshop speed). This will fail with `found: 500`.

**Resolution options:**
- **Option A (recommended):** Update the assertion to `>= 500` and add a comment explaining that
  nb04 caps at 500 for workshop speed and nb05 promotes those 500.
- **Option B:** Promote all 3747 transactions (remove the 500 cap in nb04 and nb05). Higher SLGD
  write volume (~3000 more triples), longer run time. Correct but heavier.
- **Option C:** Remove Transaction from Check 4 entirely and re-classify it as a LGD-only count.

**Recommendation: Option A** — update expected to `>= 500`, add comment. This is honest (500 is
what the workshop loads) and keeps the gate meaningful.

**Required edit to `00_preflight.ipynb` `cell-10-check4`:**
```python
# BEFORE
EXPECTED_COUNTS = {
    "Customer":             200,
    "Transaction":          3747,
    ...
}

# AFTER
EXPECTED_COUNTS = {
    "Customer":             200,
    "Transaction":          500,   # nb04 caps at 500 for workshop speed; nb05 promotes these 500
    "Advisor":              10,
    "AdvisoryRelationship": 105,
}
# Change assertion from == to >=:
    status = "[PASS]" if actual >= expected else "[FAIL]"   # was: actual == expected
```

---

## Step 2 — Join-key confirmation

**All join keys are present and correct.** Confirmed from `atlas_synthetic`:

| Field | In `generate_accounts()` | In `generate_transactions()` | Join |
|-------|------------------------|------------------------------|------|
| `customer_id` | ✓ | ✓ | `account.customer_id == customer.customer_id` |
| `account_id` | ✓ (primary key) | ✓ | `transaction.account_id == account.account_id` |

Both `generate_accounts()` and `generate_transactions()` carry `account_id`. The full join is:
`customer_id → account.customer_id` (to build `atlas:hasAccount`) and
`account_id → transaction.account_id` (to build `atlas:hasTransaction`).

**Exact URI patterns confirmed from nb04 cell-10-write-lgd:**

```python
INST_NS = 'https://github.com/your-org/atlas/instance#'
ATLAS_NS = 'https://github.com/your-org/atlas/ontology#'

# Customer URI pattern (existing, from nb04 + nb05 promotion):
curi = f'<{INST_NS}customer-{c["customer_id"]}>'
# Promoted customer URI (from nb05 cell-06):
entity_uri = f'<{INST_NS}customer-{cid}-resolved>'

# Transaction URI pattern (existing, from nb04):
turi = f'<{INST_NS}txn-{t["transaction_id"]}>'
```

**Account URI to author (new, following the same pattern):**
```python
auri = f'<{INST_NS}account-{a["account_id"]}>'
```

**Nb05 promotion reuses `act_uri` from cell-06:**
```python
act_uri = f'<{INST_NS}{promotion_run_id}>'   # defined in cell-06
```

The new Account promotion cell (cell-06b) **must run after cell-06** so `act_uri`,
`promotion_run_id`, `promotion_timestamp`, and the `sparql_update_slgd()` helper are in scope.

**Count arithmetic:**
- Accounts for 200 customers: **428** (verified from `atlas_synthetic` with seed=42)
- Transactions (nb04 cap): **500** (first 500 of 3747)
- Current SLGD total: **1618** triples
- New SLGD total after fix: **8542** triples (+6924)
- New LGD triples from nb04 Account cell: **+3068**

---

## Step 3 — Complete implementation spec

### File 1: `agentic-semantic-layer/notebooks/04_three_connection_patterns.ipynb`

**New cell: `cell-10b-write-accounts-lgd`**
**Placement:** New code cell immediately after `cell-10-write-lgd` (before `cell-11-validation-intro`).
**Why additive:** `cell-10-write-lgd` is the existing Pattern A/B/C write; this adds Account nodes
and links to what was already written, staying in the same notebook's responsibility scope.

**Cell content (logic):**
```python
# Write Account nodes and links to the LGD.
# Accounts are the financial accounts held by each customer.
# This cell runs after cell-10-write-lgd so the customer nodes already exist.
#
# For each customer we write:
#   - An atlas:Account node with account_id, account_type, balance_usd, opened_date
#   - An atlas:hasAccount triple linking the Customer to the Account
#
# For each of the first 500 transactions (matching nb04's existing cap):
#   - An atlas:hasTransaction triple linking the Account to the Transaction
#     (the Transaction nodes were written by cell-10-write-lgd / Pattern B)

print('\nAccount nodes and links — writing to LGD...')

acct_triples = []
for a in accounts:                     # accounts was generated in cell-10-write-lgd scope
    auri  = f'<{INST_NS}account-{a["account_id"]}>'
    curi  = f'<{INST_NS}customer-{a["customer_id"]}>'
    acct_triples.append(f'{auri} <{RDF_TYPE}> <{ATLAS_NS}Account> .')
    acct_triples.append(f'{auri} <{ATLAS_NS}accountId> "{a["account_id"]}"^^<{XSD_NS}string> .')
    acct_triples.append(f'{auri} <{ATLAS_NS}accountType> "{a["account_type"]}"^^<{XSD_NS}string> .')
    acct_triples.append(f'{auri} <{ATLAS_NS}balanceUSD> "{a["balance_usd"]}"^^<{XSD_NS}decimal> .')
    acct_triples.append(f'{auri} <{ATLAS_NS}openedDate> "{a["opened_date"]}"^^<{XSD_NS}date> .')
    acct_triples.append(f'{curi} <{ATLAS_NS}hasAccount> {auri} .')

# Build account_id→URI lookup for the transaction linking step
acct_uri_map = {a["account_id"]: f'<{INST_NS}account-{a["account_id"]}>' for a in accounts}

# Add atlas:hasTransaction links for the 500 transactions already written
for t in transactions[:500]:
    turi = f'<{INST_NS}txn-{t["transaction_id"]}>'
    auri  = acct_uri_map.get(t["account_id"])
    if auri:
        acct_triples.append(f'{auri} <{ATLAS_NS}hasTransaction> {turi} .')

print(f'  Account nodes: {len(accounts)} ({len(accounts)*6} triples with links)')
print(f'  hasTransaction links: {min(500, len(transactions))}')
print(f'  Total account triples: {len(acct_triples)}')

if neptune_available:
    written = 0
    for i in range(0, len(acct_triples), 50):
        batch = acct_triples[i:i+50]
        if sparql_update_lgd('INSERT DATA {\n' + '\n'.join(batch) + '\n}'):
            written += len(batch)
    print(f'  Written to LGD: {written} triples')
else:
    print('  [SKIP] Neptune not reachable — account triples generated but not written.')
    print(f'         When run inside VPC, {len(acct_triples)} triples will be written.')
```

**LGD triple count after this cell:**
- Before: existing Pattern A/B/C triples (Customer, Transaction, BehavioralEvent nodes)
- After: +3068 new triples (428 accounts × 6 triples + 500 hasTransaction links)

---

### File 2: `agentic-semantic-layer/notebooks/05_entity_resolution.ipynb`

**New cell: `cell-06b-promote-accounts`**
**Placement:** Immediately after `cell-06` (the Customer promotion cell), before `cell-07` (the
promotion log). **Must run after cell-06** to inherit `act_uri`, `promotion_run_id`,
`sparql_update_slgd()`, `INST_NS`, `ATLAS_NS`, `XSD_NS`, `PROV_NS`, `RDF_TYPE`, and `neptune_available`.

**Cell content (logic):**
```python
# Promote Account and Transaction entities from LGD to SLGD.
# This cell runs after cell-06 so it shares the same promotion activity (act_uri),
# giving accounts and transactions the same provenance as the 200 promoted customers.
#
# promotedFrom points at the LGD nodes that cell-10b-write-accounts-lgd created in nb04.
# This is honest provenance: the LGD nodes are the authoritative source.

print('Account + Transaction promotion to SLGD...')

acct_promo_triples = []

# Re-generate accounts (deterministic — same seed produces same accounts every run)
import atlas_synthetic
customers_promo = atlas_synthetic.generate_customers(n=200)
accounts_promo  = atlas_synthetic.generate_accounts(customers_promo)
transactions_promo = atlas_synthetic.generate_transactions(accounts_promo, lookback_days=90)

for a in accounts_promo:
    auri     = f'<{INST_NS}account-{a["account_id"]}>'
    lgd_src  = f'<{INST_NS}account-{a["account_id"]}>'  # same URI — LGD is the source
    curi     = f'<{INST_NS}customer-{a["customer_id"]}-resolved>'  # promoted customer URI

    acct_promo_triples.append(f'{auri} <{RDF_TYPE}> <{ATLAS_NS}Account> .')
    acct_promo_triples.append(f'{auri} <{ATLAS_NS}accountId> "{a["account_id"]}"^^<{XSD_NS}string> .')
    acct_promo_triples.append(f'{auri} <{ATLAS_NS}accountType> "{a["account_type"]}"^^<{XSD_NS}string> .')
    acct_promo_triples.append(f'{auri} <{ATLAS_NS}balanceUSD> "{a["balance_usd"]}"^^<{XSD_NS}decimal> .')
    acct_promo_triples.append(f'{auri} <{ATLAS_NS}openedDate> "{a["opened_date"]}"^^<{XSD_NS}date> .')
    acct_promo_triples.append(f'{auri} <{ATLAS_NS}promotedFrom> {lgd_src} .')
    acct_promo_triples.append(f'{auri} <{ATLAS_NS}promotedBy> {act_uri} .')
    # Customer→Account link in SLGD
    acct_promo_triples.append(f'{curi} <{ATLAS_NS}hasAccount> {auri} .')

# Promote first 500 transactions with account linkage
acct_uri_map_promo = {a["account_id"]: f'<{INST_NS}account-{a["account_id"]}>' for a in accounts_promo}

for t in transactions_promo[:500]:
    turi    = f'<{INST_NS}txn-{t["transaction_id"]}>'
    lgd_src = f'<{INST_NS}txn-{t["transaction_id"]}>'
    auri    = acct_uri_map_promo.get(t["account_id"])

    acct_promo_triples.append(f'{turi} <{RDF_TYPE}> <{ATLAS_NS}Transaction> .')
    acct_promo_triples.append(f'{turi} <{ATLAS_NS}amountUSD> "{t["amount_usd"]}"^^<{XSD_NS}decimal> .')
    acct_promo_triples.append(f'{turi} <{ATLAS_NS}transactionDate> "{t["transaction_date"]}"^^<{XSD_NS}date> .')
    acct_promo_triples.append(f'{turi} <{ATLAS_NS}transactionType> "{t["transaction_type"]}"^^<{XSD_NS}string> .')
    acct_promo_triples.append(f'{turi} <{ATLAS_NS}promotedFrom> {lgd_src} .')
    acct_promo_triples.append(f'{turi} <{ATLAS_NS}promotedBy> {act_uri} .')
    if auri:
        acct_promo_triples.append(f'{auri} <{ATLAS_NS}hasTransaction> {turi} .')

print(f'  Account triples: {len([t for t in acct_promo_triples if "Account" in t or "account" in t])}')
print(f'  Transaction triples: {len([t for t in acct_promo_triples if "Transaction" in t or "transact" in t])}')
print(f'  Total: {len(acct_promo_triples)}')

if neptune_available:
    written = 0
    for i in range(0, len(acct_promo_triples), 50):
        batch = acct_promo_triples[i:i+50]
        if sparql_update_slgd('INSERT DATA {\n' + '\n'.join(batch) + '\n}'):
            written += len(batch)
    print(f'  Written to SLGD: {written} triples')
else:
    print(f'  [SKIP] Neptune not reachable — {len(acct_promo_triples)} triples not written.')
```

**SLGD count after this cell:** ~8542 (1618 existing + 6924 new)

---

### File 3: `use-case-applications/notebooks/phase-1-referral/00_preflight.ipynb`

**Edit cell `cell-10-check4`** — Transaction count update:

```python
# BEFORE (WILL-BREAK):
EXPECTED_COUNTS = {
    "Customer":             200,
    "Transaction":          3747,
    "Advisor":              10,
    "AdvisoryRelationship": 105,
}
# with: status = "[PASS]" if actual == expected else "[FAIL]"

# AFTER:
EXPECTED_COUNTS = {
    "Customer":             200,
    # nb04 caps transaction writes at 500 for workshop speed; nb05 promotes those 500.
    # The full synthetic corpus has 3747 transactions; only the promoted 500 land in SLGD.
    "Transaction":          500,
    "Advisor":              10,
    "AdvisoryRelationship": 105,
}
# Change == to >= so a re-run with all 3747 also passes:
    status = "[PASS]" if actual >= expected else "[FAIL]"
```

Also update the remediation message to mention the 500-transaction cap:
```python
    print("  Remediation: Re-run Workshop 1 modules 4 and 5 to reload the synthetic data.")
    print("  Transaction count reflects the first 500 transactions (workshop cap).")
```

---

### Run order (against live cluster)

1. **Pull latest code in Studio:**
   ```bash
   cd ~/atlas && git pull
   ```
2. **Open `04_three_connection_patterns.ipynb`** — Restart kernel, run all cells.
   - `cell-10-write-lgd` runs first (writes Customer/Transaction/BehavioralEvent nodes to LGD as before)
   - `cell-10b-write-accounts-lgd` runs next (writes Account nodes + hasAccount + hasTransaction to LGD)
   - `cell-12-validation-gate` — should still pass (adds a count assertion check for Account nodes)
3. **Open `05_entity_resolution.ipynb`** — Restart kernel, run all cells.
   - `cell-04` and `cell-06` run as before (Customer promotion)
   - `cell-06b-promote-accounts` runs next (Account + Transaction promotion to SLGD)
   - `cell-09` (existing gate) — SAFE, still passes
4. **Run WS2 preflight `00_preflight.ipynb`** — confirm new counts pass:
   - Check 4: Customer=200 ✓, Transaction≥500 ✓, Advisor=10 ✓, AdvisoryRelationship=105 ✓

---

### Live SLGD verification queries (run after promotion)

```sparql
# Account count (expected: 428)
SELECT (COUNT(DISTINCT ?a) AS ?n) WHERE { ?a a atlas:Account ; atlas:promotedBy ?act }

# hasAccount link count (expected: 428)
SELECT (COUNT(*) AS ?n) WHERE { ?c atlas:hasAccount ?a }

# Transaction count in SLGD (expected: 500)
SELECT (COUNT(DISTINCT ?t) AS ?n) WHERE { ?t a atlas:Transaction ; atlas:promotedBy ?act }

# Sample traversal: customer → accounts → transactions
SELECT ?c ?a ?accountType ?t ?amount WHERE {
    ?c a atlas:Customer ; atlas:hasAccount ?a .
    ?a atlas:accountType ?accountType ; atlas:hasTransaction ?t .
    ?t atlas:amountUSD ?amount .
} LIMIT 5

# New SLGD total (expected: ~8542)
SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }
```

---

### Novice explanation (teaching voice)

> **Why Account and Transaction data needs its own promotion step.** When Workshop 1 runs Entity
> Resolution, it promotes 200 Customer entities from the LGD to the SLGD — the curated, validated
> graph that Workshop 2 agents query. But customers don't exist in isolation: each holds financial
> accounts, and those accounts record transactions. Workshop 2's Wholesale UI renders account balances
> and recent transactions alongside each customer's wealth signals, forming the "Entity 360" view a
> Consumer Banker needs before routing a referral. For that view to work, Account and Transaction
> nodes must be promoted to the SLGD with the same PROV-O provenance as the customer entities —
> each account carries `atlas:promotedFrom` pointing at the LGD source and `atlas:promotedBy`
> linking to the same promotion activity. This cell extends the promotion path established in
> cell-06 to cover the full customer graph: Customer, Account, and Transaction.

---

### Honest ripple summary (full blast radius)

| What changes | Where | Live cluster write? |
|-------------|-------|---------------------|
| New cell `cell-10b-write-accounts-lgd` | WS1 nb04 (additive) | Yes — +3068 LGD triples |
| New cell `cell-06b-promote-accounts` | WS1 nb05 (additive) | Yes — +6924 SLGD triples |
| Edit `cell-10-check4` Transaction count | WS2 nb00 preflight | No (notebook edit only) |
| SLGD total after fix | live cluster | ~8542 (was 1618) |
| LGD total after fix | live cluster | existing + 3068 new |
| Gates broken | WS2 nb00 Check 4 Transaction | Fixed by spec |
| Gates safe (no change) | All others | No edit needed |
| Ontology | No change | No |
| CDK / resolver | No change | No |
| WS2 notebooks (nb03–nb06) | No change | No |

---

*Spec written 2026-05-31. Join keys confirmed from `atlas_synthetic` — all present.
Transaction count arithmetic: 428 accounts, 500 transactions promoted, SLGD +6924 = 8542 total.*
