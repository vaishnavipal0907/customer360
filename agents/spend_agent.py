from datetime import timedelta

from ingestion.reader import parse_time
from memory.state_board import Finding

AGENT_NAME = "spend_agent"
WINDOW_DAYS = 30          # "recent" period
BASELINE_DAYS = 90        # "normal" period just before it
SPIKE_RATIO = 3.0
DROP_RATIO = 0.4
MIN_SPIKE_AMOUNT = 100
MIN_DROP_BASELINE = 300
MIN_TOTAL_BASELINE = 300


def run(customer_id, store, as_of):
    events = store.events_for(customer_id, until=as_of)
    purchases = [e for e in events
                 if e["source_system"] == "card_payments" and e["event_type"] == "purchase"]

    window_start = as_of - timedelta(days=WINDOW_DAYS)
    baseline_start = window_start - timedelta(days=BASELINE_DAYS)

    recent_total, baseline_total, recent_ids = {}, {}, {}
    for e in purchases:
        t = parse_time(e["event_time"])
        cat, amount = e["payload"]["mcc_category"], e["payload"]["amount"]
        if t >= window_start:
            recent_total[cat] = recent_total.get(cat, 0) + amount
            recent_ids.setdefault(cat, []).append(e["event_id"])
        elif t >= baseline_start:
            baseline_total[cat] = baseline_total.get(cat, 0) + amount

    if not baseline_total:
        return []

    months = BASELINE_DAYS / WINDOW_DAYS
    findings = []
    for cat in sorted(set(recent_total) | set(baseline_total)):
        normal = baseline_total.get(cat, 0) / months
        recent = recent_total.get(cat, 0)
        ids = recent_ids.get(cat, [])

        if recent >= MIN_SPIKE_AMOUNT and (normal == 0 or recent / normal >= SPIKE_RATIO):
            label = "a new category" if normal == 0 else f"vs a normal of {normal:.0f}"
            findings.append(Finding(
                agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
                signal=f"spend_spike:{cat}", value=float(recent),
                confidence="high" if len(ids) >= 2 else "medium", evidence=ids,
                summary=f"{cat}: {recent:.0f} spent in the last {WINDOW_DAYS} days ({label}).",
            ))
        elif normal >= MIN_DROP_BASELINE and recent <= DROP_RATIO * normal:
            findings.append(Finding(
                agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
                signal=f"spend_drop:{cat}", value=float(recent), confidence="medium", evidence=ids,
                summary=f"{cat}: only {recent:.0f} spent in the last {WINDOW_DAYS} days vs a normal of {normal:.0f}.",
            ))

    # Total card activity, across all categories
    base_all = sum(baseline_total.values()) / months
    recent_all = sum(recent_total.values())
    if base_all >= MIN_TOTAL_BASELINE and recent_all <= DROP_RATIO * base_all:
        ratio = recent_all / base_all
        findings.append(Finding(
            agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
            signal="card_activity_drop", value=round(ratio, 2),
            confidence="high" if ratio <= 0.25 else "medium",
            evidence=[i for ids in recent_ids.values() for i in ids],
            summary=f"Total card spend {recent_all:.0f} in the last {WINDOW_DAYS} days vs a normal of {base_all:.0f} ({ratio:.0%}).",
        ))
    return findings