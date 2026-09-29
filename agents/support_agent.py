from datetime import timedelta

from agents.keywords import match_themes
from ingestion.reader import parse_time
from memory.state_board import Finding

AGENT_NAME = "support_agent"
LOOKBACK_DAYS = 30
TICKET_TYPES = {"ticket_created", "ticket_resolved", "call_transcript"}
DENIED_WORDS = ("reject", "denied", "declin")


def run(customer_id, store, as_of):
    start = as_of - timedelta(days=LOOKBACK_DAYS)
    events = store.events_for(customer_id, until=as_of)
    tickets = [e for e in events
               if e["source_system"] == "support_logs"
               and e["event_type"] in TICKET_TYPES
               and parse_time(e["event_time"]) >= start]

    hits = {}   # theme -> list of events
    for e in tickets:
        p = e["payload"]
        text = p.get("category", "").replace("_", " ") + " " + p.get("raw_text", "")
        for theme in match_themes(text):
            hits.setdefault(theme, []).append(e)

    findings = []
    for theme, evs in hits.items():
        open_count = sum(1 for e in evs if e["payload"].get("resolution_status") == "open")
        findings.append(Finding(
            agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
            signal=f"support_theme:{theme}", value=float(len(evs)),
            confidence="high" if open_count else "medium",
            evidence=[e["event_id"] for e in evs],
            summary=f"{len(evs)} support contact(s) mention '{theme}' ({open_count} still open) in the last {LOOKBACK_DAYS} days.",
        ))

    denied = [e for e in tickets
              if any(w in str(e["payload"].get("resolution_status", "")).lower() for w in DENIED_WORDS)]
    if denied:
        findings.append(Finding(
            agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
            signal="support_denied", value=float(len(denied)), confidence="medium",
            evidence=[e["event_id"] for e in denied],
            summary=f"{len(denied)} support request(s) were rejected by the bank in the last {LOOKBACK_DAYS} days.",
        ))
    return findings