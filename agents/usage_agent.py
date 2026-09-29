from datetime import timedelta

from agents.keywords import match_themes
from ingestion.reader import parse_time
from memory.state_board import Finding

AGENT_NAME = "usage_agent"
RECENT_DAYS = 14
BASELINE_DAYS = 90
MIN_BASELINE_LOGINS = 10
DROP_RATIO = 0.5
SPIKE_RATIO = 2.0
TEXT_LOOKBACK_DAYS = 30


def run(customer_id, store, as_of):
    events = store.events_for(customer_id, until=as_of)
    web = [e for e in events if e["source_system"] == "web_app_events"]
    return login_trend(customer_id, web, as_of) + text_themes(customer_id, web, as_of)


def login_trend(customer_id, web, as_of):
    recent_start = as_of - timedelta(days=RECENT_DAYS)
    baseline_start = recent_start - timedelta(days=BASELINE_DAYS)
    logins = [e for e in web if e["event_type"] == "login"]
    recent = [e for e in logins if parse_time(e["event_time"]) >= recent_start]
    baseline = [e for e in logins if baseline_start <= parse_time(e["event_time"]) < recent_start]
    if len(baseline) < MIN_BASELINE_LOGINS:
        return []

    expected = len(baseline) / BASELINE_DAYS * RECENT_DAYS
    ratio = len(recent) / expected
    summary = (f"{len(recent)} logins in the last {RECENT_DAYS} days vs about "
               f"{expected:.0f} expected ({ratio:.0%}).")
    if ratio <= DROP_RATIO:
        signal, confidence = "login_drop", ("high" if ratio <= 0.25 else "medium")
    elif ratio >= SPIKE_RATIO:
        signal, confidence = "login_spike", "medium"
    else:
        return []
    return [Finding(agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
                    signal=signal, value=round(ratio, 2), confidence=confidence,
                    evidence=[e["event_id"] for e in recent], summary=summary)]


def text_themes(customer_id, web, as_of):
    """Themes in search queries and in the features the customer used (e.g. a 'cancel' page)."""
    start = as_of - timedelta(days=TEXT_LOOKBACK_DAYS)
    hits = {}   # (kind, theme) -> list of (event_id, text)
    for e in web:
        if parse_time(e["event_time"]) < start:
            continue
        if e["event_type"] == "search_query":
            kind, text = "search_theme", e["payload"].get("search_text", "")
        elif e["event_type"] == "feature_used":
            kind, text = "feature_theme", e["payload"].get("feature_or_page", "").replace("_", " ")
        else:
            continue
        for theme in match_themes(text):
            hits.setdefault((kind, theme), []).append((e["event_id"], text))

    findings = []
    for (kind, theme), items in hits.items():
        findings.append(Finding(
            agent=AGENT_NAME, customer_id=customer_id, as_of_time=as_of.isoformat(),
            signal=f"{kind}:{theme}", value=float(len(items)),
            confidence="high" if len(items) >= 2 else "medium",
            evidence=[event_id for event_id, _ in items],
            summary=f"{len(items)} {kind.split('_')[0]} event(s) about '{theme}' in the last {TEXT_LOOKBACK_DAYS} days, e.g. '{items[-1][1]}'.",
        ))
    return findings