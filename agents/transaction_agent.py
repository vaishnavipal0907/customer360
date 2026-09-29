from statistics import mean, median

from agents.keywords import match_themes
from ingestion.reader import parse_time
from memory.state_board import Finding

AGENT_NAME = "transaction_agent"
INCOME_TYPES = {"salary_credit", "benefits_credit"}
RECENT_N = 2             # how many of the latest income credits we compare
LOW_FRACTION = 0.75      # a credit below 75% of normal counts as "reduced"
GAP_FACTOR = 2.5         # income counts as "missing" after 2.5x the usual gap
RECURRING_MIN_OCCURRENCES = 3
RECURRING_OVERDUE_FACTOR = 1.5   # must be at least 50% later than usual to count as "stopped"
RECURRING_OVERDUE_MIN_DAYS = 10  # ...or at least this many days late, whichever is bigger
RECURRING_STALE_FACTOR = 4.0     # beyond this, memory decay (not this agent) handles staleness
RECURRING_NEW_WITHIN_DAYS = 45
RECURRING_MIN_HISTORY_DAYS = 60
RECURRING_GRACE_DAYS = 3


def run(customer_id, store, as_of):
    events = store.events_for(customer_id, until=as_of)
    ledger = [e for e in events if e["source_system"] == "core_banking_ledger"]
    return income_findings(customer_id, ledger, as_of) + recurring_findings(customer_id, ledger, as_of)


def income_findings(customer_id, ledger, as_of):
    income = [e for e in ledger if e["payload"].get("transaction_type") in INCOME_TYPES]
    if len(income) < RECENT_N + 3:
        return []

    recent = income[-RECENT_N:]
    baseline = income[:-RECENT_N]
    normal = median(e["payload"]["amount"] for e in baseline)
    findings = []

    low = [e for e in recent if e["payload"]["amount"] < LOW_FRACTION * normal]
    if low:
        recent_avg = mean(e["payload"]["amount"] for e in recent)
        ratio = recent_avg / normal
        findings.append(Finding(
            agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
            signal="income_drop", value=round(ratio, 2),
            confidence="high" if len(low) == RECENT_N else "low",
            evidence=[e["event_id"] for e in recent],
            summary=(f"Last {RECENT_N} income credits average {recent_avg:.0f} vs a normal of "
                     f"{normal:.0f} ({ratio:.0%}); {len(low)} of {RECENT_N} are clearly reduced."),
        ))

    times = [parse_time(e["event_time"]) for e in income]
    baseline_times = times[:-RECENT_N]
    gaps = [(b - a).days for a, b in zip(baseline_times[:-1], baseline_times[1:])]
    typical_gap = median(gaps) if gaps else 0
    days_since = (as_of - times[-1]).days
    if typical_gap > 0 and days_since > GAP_FACTOR * typical_gap:
        findings.append(Finding(
            agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
            signal="income_stopped", value=float(days_since), confidence="medium",
            evidence=[income[-1]["event_id"]],
            summary=f"No income credit for {days_since} days; usual gap is about {typical_gap:.0f} days.",
        ))
    return findings


def recurring_findings(customer_id, ledger, as_of):
    """Standing instructions that newly appeared, or that stopped arriving on schedule."""
    if not ledger:
        return []
    first_ledger_time = parse_time(ledger[0]["event_time"])
    by_type = {}
    for e in ledger:
        if e["event_type"] == "standing_instruction":
            by_type.setdefault(e["payload"].get("transaction_type", "unknown"), []).append(e)

    findings = []
    for ttype, evs in by_type.items():
        times = [parse_time(e["event_time"]) for e in evs]
        first, last = times[0], times[-1]
        ids = [e["event_id"] for e in evs]

        if ((as_of - first).days <= RECURRING_NEW_WITHIN_DAYS
                and (first - first_ledger_time).days >= RECURRING_MIN_HISTORY_DAYS):
            themes = list(match_themes(ttype.replace("_", " "))) or ["other"]
            for theme in themes:
                findings.append(Finding(
                    agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
                    signal=f"recurring_started:{theme}", value=float(evs[0]["payload"]["amount"]),
                    confidence="high", evidence=ids,
                    summary=f"New recurring payment '{ttype}' of {evs[0]['payload']['amount']} appeared.",
                ))

        if len(times) >= RECURRING_MIN_OCCURRENCES:
            gap = median([(b - a).days for a, b in zip(times[:-1], times[1:])])
            since = (as_of - last).days
            overdue_threshold = max(gap * RECURRING_OVERDUE_FACTOR, gap + RECURRING_OVERDUE_MIN_DAYS)
            if gap > 0 and overdue_threshold < since <= gap * RECURRING_STALE_FACTOR:
                findings.append(Finding(
                    agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
                    signal=f"recurring_stopped:{ttype}", value=float(since), confidence="medium",
                    evidence=ids[-2:],
                    summary=f"Recurring '{ttype}' is overdue: last seen {since} days ago, usual gap {gap:.0f} days.",
                ))
    return findings