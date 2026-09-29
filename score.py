import json
import sys

from ingestion.reader import parse_time


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def score(name):
    truth = load(f"data/{name}/ground_truth.json")["checkpoints"]
    ours = sorted(load(f"outputs/inferred_events_{name}.json"),
                  key=lambda c: parse_time(c["as_of_time"]))

    def latest_at(ts):
        t, best = parse_time(ts), None
        for c in ours:
            if parse_time(c["as_of_time"]) <= t:
                best = c
        return best

    hits = {"state": 0, "band": 0, "action": 0}
    print(f"\n=== {name} ===")
    for gt in truth:
        got = latest_at(gt["as_of_time"])
        checks = {
            "state": (gt["expected_inferred_state"], got["inferred_state"]),
            "band": (gt["expected_confidence_band"], got["confidence_band"]),
            "action": (gt["expected_action"], got["action"]),
        }
        print(gt["as_of_time"][:10])
        for field, (want, have) in checks.items():
            ok = want == have
            hits[field] += ok
            print(f"   {field:7s} {'OK  ' if ok else 'MISS'} expected={want}  got={have}")

    n = len(truth)
    print(f"\nScore: state {hits['state']}/{n}, band {hits['band']}/{n}, action {hits['action']}/{n}")


if __name__ == "__main__":
    score(sys.argv[1] if len(sys.argv) > 1 else "scenario_01")