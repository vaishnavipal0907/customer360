from datetime import timedelta

from ingestion.reader import parse_time
from memory.state_board import Finding

AGENT_NAME = "profile_agent"
LOOKBACK_DAYS = 60
CHANGE_TYPES = {"address_change", "marital_status_change", "dependents_change",
                "kyc_update", "loan_application", "loan_disbursed"}


def run(customer_id, store, as_of):
    start = as_of - timedelta(days=LOOKBACK_DAYS)
    findings = []
    for e in store.events_for(customer_id, until=as_of):
        if e["source_system"] != "loan_kyc" or e["event_type"] not in CHANGE_TYPES:
            continue
        if parse_time(e["event_time"]) < start:
            continue
        p = e["payload"]
        findings.append(Finding(
            agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
            signal=f"profile_change:{e['event_type']}", value=1.0, confidence="high",
            evidence=[e["event_id"]],
            summary=f"{e['event_type']}: {p.get('old_value')} -> {p.get('new_value')} ({p.get('event_subtype')}).",
        ))
    return findings