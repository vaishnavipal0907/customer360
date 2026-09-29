import json
import sys
from collections import Counter, defaultdict
from ingestion.reader import load_jsonl

name = sys.argv[1]
base = f"data/{name}"
live = load_jsonl(f"{base}/live_stream.jsonl")
history = load_jsonl(f"{base}/history_seed.jsonl")

with open(f"{base}/ground_truth.json", encoding="utf-8") as f:
    truth = json.load(f)
signals = set(truth["signal_events"])
herrings = set(truth["red_herring_events"])
print("scenario_id:", truth["scenario_id"])

print("\n=== Non-routine or tagged events in the live stream ===")
for e in live:
    tagged = e["event_id"] in signals or e["event_id"] in herrings
    routine = (e["source_system"] == "card_payments" and e["event_type"] == "purchase") or \
              (e["source_system"] == "web_app_events" and e["event_type"] == "login")
    if routine and not tagged:
        continue
    tag = "SIGNAL" if e["event_id"] in signals else "RED-HERRING" if e["event_id"] in herrings else ""
    print(e["event_time"][:10], e["event_id"], tag, e["source_system"], e["event_type"], e["payload"])

print("\n=== Card spend by month and category (history + live) ===")
totals = defaultdict(lambda: [0, 0])
for e in history + live:
    if e["source_system"] == "card_payments" and e["event_type"] == "purchase":
        key = (e["event_time"][:7], e["payload"]["mcc_category"])
        totals[key][0] += 1
        totals[key][1] += e["payload"]["amount"]
for (month, cat), (n, amt) in sorted(totals.items()):
    print(month, f"{cat:18s} count={n:3d} total={amt}")

print("\n=== Logins per month ===")
logins = Counter(e["event_time"][:7] for e in history + live
                 if e["source_system"] == "web_app_events" and e["event_type"] == "login")
for month, n in sorted(logins.items()):
    print(month, n)