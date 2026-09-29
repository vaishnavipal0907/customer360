import re

from ingestion.reader import parse_time

AGENT_NAME = "guardrail_agent"

RULES = [
    {"name": "legal_threat",
     "patterns": [r"\blawsuit\b", r"\blegal action\b", r"\battorney\b", r"\blawyer\b", r"\bsue\b", r"\bsuing\b"],
     "action": "relationship_manager_escalation", "subtype": "legal_escalation_queue", "state": None},
    {"name": "fraud_claim",
     "patterns": [r"\bunauthori[sz]ed\b", r"\bfraud\b", r"\bscam\b", r"\bhacked\b", r"\bstolen\b", r"didn'?t make"],
     "action": "compliance_fraud_hold", "subtype": "customer_reported_fraud",
     "state": "potential_fraud_or_takeover"},
    {"name": "self_harm_mention",
     "patterns": [r"\bsuicid", r"kill myself", r"end my life", r"hurt myself"],
     "action": "relationship_manager_escalation", "subtype": "urgent_human_wellbeing_review", "state": None},
]


def scan(store, customer_id, since, until):
    """Check support messages that ARRIVED in (since, until] against the hard rules."""
    hits = []
    for e in store.events_for(customer_id, until=until):
        if e["source_system"] != "support_logs":
            continue
        if not (since < parse_time(e["ingestion_time"]) <= until):
            continue
        text = (e["payload"].get("raw_text") or "").lower().replace("\u2019", "'")
        for rule in RULES:
            if any(re.search(p, text) for p in rule["patterns"]):
                hits.append({"rule": rule["name"], "event_id": e["event_id"], "action": rule["action"],
                             "subtype": rule["subtype"], "state": rule["state"]})
    return hits