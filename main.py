import json
import sys
from datetime import timedelta

from ingestion.reader import parse_time
from ingestion.scenario import load_scenario
from memory.state_board import StateBoard
from memory.life_state import LifeStateMemory
from agents import guardrail_agent, action_agent
from agents.action_agent import explain
from pipeline import analyse_day
from hitl.console import review
from logs.trace import TraceLogger


def run_scenario(name, interactive=False):
    store, pending, customer_id, start, end = load_scenario(name)
    board, memory = StateBoard(), LifeStateMemory()
    tracer = TraceLogger(f"logs/trace_{name}.jsonl")

    checkpoints, approvals, last_key, i, day = [], [], None, 0, start
    while day <= end:
        while i < len(pending) and parse_time(pending[i]["ingestion_time"]) <= day:
            store.add(pending[i])
            i += 1

        inference = analyse_day(day, customer_id, store, board, memory, tracer=tracer)
        hits = guardrail_agent.scan(store, customer_id, day - timedelta(days=1), day)
        cp = action_agent.decide(inference, hits, day)

        key = (cp["inferred_state"], cp["confidence_band"], cp["action"])
        if key != last_key:
            cp, record = review(cp, explain(inference), auto_mode=not interactive)
            if record:
                approvals.append(record)
            print(f"{cp['as_of_time'][:10]}  {cp['inferred_state']:32s} {cp['confidence_band']:7s} "
                  f"{cp['action']:32s} {cp['hitl_status']}")
            last_key = key
        checkpoints.append(cp)
        day += timedelta(days=1)

    with open(f"outputs/inferred_events_{name}.json", "w", encoding="utf-8") as f:
        json.dump(checkpoints, f, indent=2)
    with open(f"logs/approvals_{name}.jsonl", "w", encoding="utf-8") as f:
        for r in approvals:
            f.write(json.dumps(r) + "\n")
    print(f"\nWrote {len(checkpoints)} checkpoints and {len(approvals)} HITL decisions.")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "scenario_01"
    interactive = "--interactive" in sys.argv
    run_scenario(name, interactive=interactive)