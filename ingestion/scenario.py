import json

from ingestion.reader import load_jsonl, arrival_order, parse_time
from memory.event_store import EventStore


def load_scenario(name):
    base = f"data/{name}"
    with open(f"{base}/replay_config.json", encoding="utf-8") as f:
        config = json.load(f)
    with open(f"{base}/entities.json", encoding="utf-8") as f:
        entities = json.load(f)

    store = EventStore()
    customer_id = entities["customer_id"]
    store.profiles[customer_id] = entities.get("profile", {})
    for e in load_jsonl(f"{base}/history_seed.jsonl"):
        store.add(e)
    pending = arrival_order(load_jsonl(f"{base}/live_stream.jsonl"))
    return (store, pending, customer_id,
            parse_time(config["simulated_start"]), parse_time(config["simulated_end"]))