from datetime import timedelta
from statistics import median

from ingestion.reader import parse_time
from memory.state_board import Finding

AGENT_NAME = "transfer_agent"
LOOKBACK_DAYS = 45
BALANCE_WINDOW_DAYS = 60
MIN_FRACTION = 0.10       # ignore moves smaller than 10% of the typical balance
SWEEP_WINDOW_DAYS = 1     # "swept" = moved out within a day of an income credit
INCOME_TYPES = {"salary_credit", "benefits_credit"}


def name_tokens(name):
    return [t for t in name.lower().replace("-", " ").split() if len(t) > 1]


def is_own_name(counterparty, tokens):
    text = (counterparty or "").lower()
    return bool(tokens) and all(t in text for t in tokens)


def typical_balance(ledger, when):
    start = when - timedelta(days=BALANCE_WINDOW_DAYS)
    balances = [e["payload"]["balance_after"] for e in ledger
                if start <= parse_time(e["event_time"]) < when and "balance_after" in e["payload"]]
    return median(balances) if balances else None


def run(customer_id, store, as_of):
    events = store.events_for(customer_id, until=as_of)
    ledger = [e for e in events if e["source_system"] == "core_banking_ledger"]
    tokens = name_tokens(store.profiles.get(customer_id, {}).get("name", ""))
    start = as_of - timedelta(days=LOOKBACK_DAYS)

    # Outbound transfers to an account in the customer's OWN name (e.g. at another bank).
    # Payments to third parties (tuition, rent, ...) are deliberately not flagged here.
    own_out = [e for e in events
               if e["source_system"] in ("instant_payments", "ach_wire")
               and e["payload"].get("direction") == "outbound"
               and e["payload"].get("status", "completed") == "completed"
               and parse_time(e["event_time"]) >= start
               and is_own_name(e["payload"].get("counterparty_name"), tokens)]
    if not own_out:
        return []

    income = [e for e in ledger if e["payload"].get("transaction_type") in INCOME_TYPES]
    moved_fraction, swept = 0.0, []
    for t in own_out:
        when, amount = parse_time(t["event_time"]), t["payload"]["amount"]
        balance = typical_balance(ledger, when)
        if balance:
            moved_fraction += amount / balance
        for inc in income:
            days_apart = abs((when - parse_time(inc["event_time"])).total_seconds()) / 86400
            pay = inc["payload"]["amount"]
            if days_apart <= SWEEP_WINDOW_DAYS and 0.8 * pay <= amount <= 1.5 * pay:
                swept.append(t)
                break

    findings = []
    if moved_fraction >= MIN_FRACTION:
        findings.append(Finding(
            agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
            signal="external_self_transfer", value=round(moved_fraction, 2),
            confidence="high" if (moved_fraction >= 0.3 or len(own_out) >= 2) else "medium",
            evidence=[e["event_id"] for e in own_out],
            summary=(f"{len(own_out)} outbound transfer(s) to accounts in the customer's own name, "
                     f"about {moved_fraction:.0%} of the typical balance, in the last {LOOKBACK_DAYS} days."),
        ))
    if swept:
        findings.append(Finding(
            agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
            signal="income_swept_out", value=float(len(swept)),
            confidence="high" if len(swept) >= 2 else "medium",
            evidence=[e["event_id"] for e in swept],
            summary=f"Income was moved out to the customer's own external account within a day of arriving, {len(swept)} time(s).",
        ))
    return findings