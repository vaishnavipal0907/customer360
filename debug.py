import sys
from datetime import timedelta

from ingestion.reader import parse_time
from ingestion.scenario import load_scenario
from memory.state_board import StateBoard
from memory.life_state import LifeStateMemory
from pipeline import analyse_day


def main(name, date):
    store, pending, customer_id, start, _ = load_scenario(name)
    target = parse_time(f"{date}T00:00:00Z")
    board, memory = StateBoard(), LifeStateMemory()

    i, day = 0, start
    while True:
        while i < len(pending) and parse_time(pending[i]["ingestion_time"]) <= day:
            store.add(pending[i])
            i += 1
        analyse_day(day, customer_id, store, board, memory)
        if day >= target:
            break
        day += timedelta(days=1)

    print(f"\n=== {name} as of {date} ===")
    print("\nFindings from the agents today:")
    for f in board.findings_for(customer_id):
        print(f"  [{f.confidence}] {f.agent}: {f.signal} -> {f.summary}")

    print("\nState scores (top 3):")
    scores = memory.score(customer_id, day)
    for state, s in sorted(scores.items(), key=lambda kv: -kv[1]["score"])[:3]:
        print(f"  {state}: score {s['score']:.2f}, agents {sorted(s['agents'])}")
        for signal, weight, ids in sorted(s["items"], key=lambda x: -x[1]):
            print(f"       {signal}  weight={weight}  events={ids[:3]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])