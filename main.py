from ingestion.reader import load_jsonl, arrival_order
from memory.event_store import EventStore

SCENARIO = "data/scenario_01"


def main():
    store = EventStore()

    history = load_jsonl(f"{SCENARIO}/history_seed.jsonl")
    for event in history:
        store.add(event)
    print(f"Loaded {len(history)} history events")

    live = arrival_order(load_jsonl(f"{SCENARIO}/live_stream.jsonl"))
    counts = {"on_time": 0, "late": 0, "duplicate": 0}
    for event in live:
        counts[store.add(event)] += 1
    print(f"Live stream: {len(live)} events -> {counts}")

    for customer_id, events in store.by_customer.items():
        print(customer_id, "has", len(events), "events in total")
if __name__ == "__main__":
    main()