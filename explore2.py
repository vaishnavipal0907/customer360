from collections import defaultdict
from ingestion.reader import load_jsonl

SCENARIO = "data/scenario_01"
events = load_jsonl(f"{SCENARIO}/history_seed.jsonl") + load_jsonl(f"{SCENARIO}/live_stream.jsonl")

totals = defaultdict(lambda: [0, 0])   # (month, category) -> [count, total amount]
for e in events:
    if e["source_system"] == "card_payments" and e["event_type"] == "purchase":
        key = (e["event_time"][:7], e["payload"]["mcc_category"])
        totals[key][0] += 1
        totals[key][1] += e["payload"]["amount"]

for (month, cat), (n, amt) in sorted(totals.items()):
    print(month, f"{cat:15s} count={n:3d} total={amt}")