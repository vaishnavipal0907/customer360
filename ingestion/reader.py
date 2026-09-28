import json
from datetime import datetime


def parse_time(ts: str) -> datetime:
    # Turns "2026-02-01T08:02:00Z" into a datetime object
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def load_jsonl(path):
    """Read a .jsonl file: one JSON object per line."""
    events = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"Skipping bad line {line_no} in {path}")
    return events


def arrival_order(events):
    """Order events by when the system RECEIVED them (simulates a live stream)."""
    return sorted(events, key=lambda e: parse_time(e["ingestion_time"]))
