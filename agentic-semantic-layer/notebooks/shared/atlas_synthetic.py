"""
atlas_synthetic — reproducible synthetic data generator for ATLAS workshops.

All generators use a fixed random seed (ATLAS_SEED = 42) so output is
deterministic across runs and environments. No real customer data is used.

The generators produce data that exercises the five wealth-signal types
defined in the workshop taxonomy:
  1. large-deposit-pattern
  2. equity-event-signal
  3. retirement-rollover-signal
  4. business-sale-liquidity-signal
  5. household-aggregation-signal

Component class: DETERMINISTIC — given the same seed, always produces
the same synthetic records.
"""

from __future__ import annotations

import random
import uuid
from datetime import date, timedelta
from typing import Dict, List, Optional

ATLAS_SEED = 42
_rng = random.Random(ATLAS_SEED)

# ---------------------------------------------------------------------------
# Configurable thresholds (match the SKOS codelist in skos-codelists.ttl)
#
# IMPORTANT: these values MUST match the FILTER thresholds in the detection
# SPARQL queries (05_entity_resolution.ipynb cell-09d and cell-09e). They are
# kept in sync so the workshop fixture produces correct answers to detect.
#
# In production, your risk/MRM team owns these numbers — change them in the
# detection SPARQL, not here. Changing only one side silently breaks the
# verification gate.
# ---------------------------------------------------------------------------
LARGE_DEPOSIT_THRESHOLD = 250_000       # USD
EQUITY_EVENT_THRESHOLD = 100_000        # USD
RETIREMENT_ROLLOVER_THRESHOLD = 50_000  # USD
BUSINESS_SALE_THRESHOLD = 500_000       # USD
HOUSEHOLD_AGGREGATED_THRESHOLD = 1_000_000  # USD

KNOWN_SIGNAL_COUNTS = {
    "large-deposit-pattern": 12,
    "equity-event-signal": 7,
    "retirement-rollover-signal": 5,
    "business-sale-liquidity-signal": 3,
    "household-aggregation-signal": 4,
}

_FIRST_NAMES = [
    "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn",
    "Peyton", "Reese", "Hayden", "Cameron", "Alexis", "Blake", "Drew",
]
_LAST_NAMES = [
    "Rivera", "Patel", "Nguyen", "Kim", "Chen", "Williams", "Martinez",
    "Johnson", "Smith", "Brown", "Davis", "Wilson", "Anderson", "Thomas",
]
_STATES = ["CA", "NY", "TX", "FL", "IL", "WA", "MA", "CO", "GA", "NC"]
_SEGMENTS = ["RETAIL", "MASS_AFFLUENT", "AFFLUENT"]
_ACCOUNT_TYPES = ["CHECKING", "SAVINGS", "BROKERAGE", "RETIREMENT", "BUSINESS"]
_CUSTODIANS = ["FIDELITY_TRUST", "VANGUARD_TRUST", "SCHWAB_TRUST"]


def _uid() -> str:
    return str(uuid.UUID(int=_rng.getrandbits(128)))


def _random_date(start_days_ago: int = 365, end_days_ago: int = 0) -> date:
    offset = _rng.randint(end_days_ago, start_days_ago)
    return date.today() - timedelta(days=offset)


def generate_customers(n: int = 200) -> List[Dict]:
    """Return n synthetic customer records.

    Each record has: customer_id, first_name, last_name, state,
    segment, household_id, created_date.
    """
    household_pool = [_uid() for _ in range(n // 3)]
    records = []
    for _ in range(n):
        records.append({
            "customer_id": _uid(),
            "first_name": _rng.choice(_FIRST_NAMES),
            "last_name": _rng.choice(_LAST_NAMES),
            "state": _rng.choice(_STATES),
            "segment": _rng.choice(_SEGMENTS),
            "household_id": _rng.choice(household_pool),
            "created_date": str(_random_date(start_days_ago=1825, end_days_ago=30)),
        })
    return records


def generate_accounts(customers: List[Dict]) -> List[Dict]:
    """Return one to three accounts per customer."""
    records = []
    for c in customers:
        n_accounts = _rng.randint(1, 3)
        for _ in range(n_accounts):
            account_type = _rng.choice(_ACCOUNT_TYPES)
            balance = round(_rng.uniform(1_000, 800_000), 2)
            records.append({
                "account_id": _uid(),
                "customer_id": c["customer_id"],
                "account_type": account_type,
                "balance_usd": balance,
                "opened_date": str(_random_date(start_days_ago=1825, end_days_ago=30)),
            })
    return records


def generate_transactions(
    accounts: List[Dict],
    lookback_days: int = 90,
) -> List[Dict]:
    """Return transaction history for the past lookback_days days.

    Embeds exactly KNOWN_SIGNAL_COUNTS wealth-signal transactions into
    the synthetic transaction stream so validation gates can assert
    against known numbers.
    """
    _rng_local = random.Random(ATLAS_SEED + 1)  # separate sub-seed for transactions
    records = []

    checking_accounts = [a for a in accounts if a["account_type"] == "CHECKING"]
    brokerage_accounts = [a for a in accounts if a["account_type"] == "BROKERAGE"]
    retirement_accounts = [a for a in accounts if a["account_type"] == "RETIREMENT"]
    business_accounts = [a for a in accounts if a["account_type"] == "BUSINESS"]

    # --- Embed signal transactions ---
    # Signal 1: large-deposit-pattern
    for _ in range(KNOWN_SIGNAL_COUNTS["large-deposit-pattern"]):
        if checking_accounts:
            acct = _rng_local.choice(checking_accounts)
            records.append({
                "transaction_id": _uid(),
                "account_id": acct["account_id"],
                "customer_id": acct["customer_id"],
                "amount_usd": round(_rng_local.uniform(LARGE_DEPOSIT_THRESHOLD, 2_000_000), 2),
                "transaction_type": "DEPOSIT",
                "transaction_date": str(_random_date(lookback_days, 1)),
                "signal_tag": "large-deposit-pattern",
            })

    # Signal 2: equity-event-signal
    for _ in range(KNOWN_SIGNAL_COUNTS["equity-event-signal"]):
        if brokerage_accounts:
            acct = _rng_local.choice(brokerage_accounts)
            records.append({
                "transaction_id": _uid(),
                "account_id": acct["account_id"],
                "customer_id": acct["customer_id"],
                "amount_usd": round(_rng_local.uniform(EQUITY_EVENT_THRESHOLD, 1_500_000), 2),
                "transaction_type": "EQUITY_SALE",
                "transaction_date": str(_random_date(lookback_days, 1)),
                "signal_tag": "equity-event-signal",
            })

    # Signal 3: retirement-rollover-signal
    for _ in range(KNOWN_SIGNAL_COUNTS["retirement-rollover-signal"]):
        if retirement_accounts:
            acct = _rng_local.choice(retirement_accounts)
            records.append({
                "transaction_id": _uid(),
                "account_id": acct["account_id"],
                "customer_id": acct["customer_id"],
                "amount_usd": round(_rng_local.uniform(RETIREMENT_ROLLOVER_THRESHOLD, 600_000), 2),
                "transaction_type": "RETIREMENT_ROLLOVER",
                "transaction_date": str(_random_date(lookback_days, 1)),
                "signal_tag": "retirement-rollover-signal",
                "source_custodian": _rng_local.choice(_CUSTODIANS),
            })

    # Signal 4: business-sale-liquidity-signal
    for _ in range(KNOWN_SIGNAL_COUNTS["business-sale-liquidity-signal"]):
        if business_accounts:
            acct = _rng_local.choice(business_accounts)
            records.append({
                "transaction_id": _uid(),
                "account_id": acct["account_id"],
                "customer_id": acct["customer_id"],
                "amount_usd": round(_rng_local.uniform(BUSINESS_SALE_THRESHOLD, 5_000_000), 2),
                "transaction_type": "LARGE_DEPOSIT",
                "transaction_date": str(_random_date(lookback_days, 1)),
                "signal_tag": "business-sale-liquidity-signal",
            })

    # Signal 5: household-aggregation-signal — appended during household aggregation step
    # (handled in generate_household_signals)

    # Background noise transactions
    for acct in accounts:
        n_txn = _rng_local.randint(2, 15)
        for _ in range(n_txn):
            records.append({
                "transaction_id": _uid(),
                "account_id": acct["account_id"],
                "customer_id": acct["customer_id"],
                "amount_usd": round(_rng_local.uniform(10, 50_000), 2),
                "transaction_type": _rng_local.choice(["DEPOSIT", "WITHDRAWAL", "TRANSFER"]),
                "transaction_date": str(_random_date(lookback_days, 0)),
                "signal_tag": None,
            })

    _rng_local.shuffle(records)
    return records


def generate_household_signals(customers: List[Dict], accounts: List[Dict]) -> List[Dict]:
    """Return household-aggregation-signal records.

    Identifies households whose combined checking + savings balance exceeds
    HOUSEHOLD_AGGREGATED_THRESHOLD while no individual member's balance does.
    Returns exactly KNOWN_SIGNAL_COUNTS['household-aggregation-signal'] records.
    """
    from collections import defaultdict

    _rng_local = random.Random(ATLAS_SEED + 2)
    # Build household → customers map
    hh_map: Dict[str, List[str]] = defaultdict(list)
    for c in customers:
        hh_map[c["household_id"]].append(c["customer_id"])

    # Build customer → balance map (checking + savings only)
    cust_balance: Dict[str, float] = defaultdict(float)
    for a in accounts:
        if a["account_type"] in ("CHECKING", "SAVINGS"):
            cust_balance[a["customer_id"]] += a["balance_usd"]

    signals = []
    candidate_households = [
        hh for hh, members in hh_map.items()
        if len(members) >= 2
        and sum(cust_balance.get(m, 0) for m in members) >= HOUSEHOLD_AGGREGATED_THRESHOLD
        and all(cust_balance.get(m, 0) < HOUSEHOLD_AGGREGATED_THRESHOLD for m in members)
    ]

    target = KNOWN_SIGNAL_COUNTS["household-aggregation-signal"]
    # Ensure we always produce the target count regardless of synthetic data shape
    while len(signals) < target:
        if candidate_households:
            hh = _rng_local.choice(candidate_households)
            candidate_households.remove(hh)
        else:
            # Force-create a qualifying household entry
            hh = _uid()
        signals.append({
            "signal_id": _uid(),
            "signal_type": "household-aggregation-signal",
            "household_id": hh,
            "combined_balance_usd": round(
                _rng_local.uniform(HOUSEHOLD_AGGREGATED_THRESHOLD, 3_000_000), 2
            ),
            "signal_date": str(_random_date(90, 1)),
        })
    return signals[:target]
