import json
import sys

from ingestion.reader import parse_time


def main(name):
    with open(f"data/{name}/ground_truth.json", encoding="utf-8") as f:
        truth = json.load(f)
    checks = truth.get("false_positive_checks", [])
    if not checks:
        print(f"{name}: no false_positive_checks defined.")
        return

    with open(f"data/{name}/live_stream.jsonl", encoding="utf-8") as f:
        events = {json.loads(line)["event_id"]: json.loads(line) for line in f if line.strip()}
    with open(f"outputs/inferred_events_{name}.json", encoding="utf-8") as f:
        checkpoints = json.load(f)

    print(f"=== {name} ===")
    for check in checks:
        event = events.get(check["event_id"])
        if not event:
            print(f"  {check['event_id']}: not found in live_stream, skipping")
            continue
        t = parse_time(event["event_time"])
        window_end = t.timestamp() + check["window_hours"] * 3600
        forbidden = set(check["must_not_trigger_action"])

        violations = [cp for cp in checkpoints
                      if t.timestamp() <= parse_time(cp["as_of_time"]).timestamp() <= window_end
                      and cp["action"] in forbidden]

        status = "FAIL" if violations else "OK"
        print(f"  [{status}] {check['event_id']} ({check['notes'][:60]}...)")
        for v in violations:
            print(f"      -> at {v['as_of_time'][:10]}, action={v['action']} (forbidden)")


if __name__ == "__main__":
    main(sys.argv[1])