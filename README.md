# Agentic Customer 360 — Proactive Intervention Desk

Inter IIT Tech Meet 15.0 — Prepathon PS submission (NLP track).

A multi-agent system that reads an asynchronous, out-of-order stream of
banking events for one customer at a time, infers what life event they
are likely going through, and decides on one of six bounded actions (or
explicitly no action), with human review, hard-coded safety guardrails,
and full trace logging.

## Where things are

| What | Where |
|---|---|
| Solution document (problem, architecture, decisions, limitations) | `solution_document.md` |
| Research log (sources read and what was taken from them) | `research_log.md` |
| Architecture diagram (Mermaid — renders natively on GitHub) | `architecture_diagram.md` |
| Agent code, one file per agent | `agents/` |
| Memory: event store, state board, persistent decayed evidence | `memory/` |
| Event loading and per-scenario setup | `ingestion/` |
| Human-in-the-loop console | `hitl/` |
| Trace logging with PII masking | `logs/trace.py` |
| Main pipeline (shared by the runner and the debugger) | `pipeline.py` |
| Practice datasets (not modified) | `data/scenario_01`, `data/scenario_02`, `data/scenario_03` |
| Graded output (generated when you run it) | `outputs/inferred_events_<scenario>.json` |
| Approval log, trace log (generated when you run it) | `logs/approvals_<scenario>.jsonl`, `logs/trace_<scenario>.jsonl` |

## Setup

Requires Python 3.10+. No third-party packages are used — everything
runs on the standard library (`json`, `datetime`, `statistics`, `re`,
`fnmatch`, `dataclasses`), so there is nothing to install beyond Python
itself. `requirements.txt` is present but intentionally empty for this
reason.

```bash
python -m venv venv
# Windows:
venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate
```

## Running a scenario

```bash
python main.py scenario_01
```

This replays the scenario one simulated day at a time (per
`replay_config.json`), runs all six swarm agents, updates persistent
memory, applies guardrails, decides an action, auto-approves any HITL
escalation, and writes:

- `outputs/inferred_events_scenario_01.json` — the full 74-checkpoint
  output in the required schema (`as_of_time`, `inferred_state`,
  `confidence_band`, `action`, `action_subtype`, `hitl_status`, `notes`)
- `logs/approvals_scenario_01.jsonl` — one record per HITL decision
- `logs/trace_scenario_01.jsonl` — one line per agent call per day,
  with account IDs and counterparty names masked

The console only prints a line when the decision actually changes, so
you see the story unfold rather than 74 identical rows.

### Running with a real human-in-the-loop prompt

```bash
python main.py scenario_01 --interactive
```

Every time the proposed decision escalates to a human, this stops and
shows the inferred state, confidence, proposed action, and the exact
reasoning behind it, then asks: **Approve (a) / Reject (r) / Modify (m) /
Why? (w)**. `w` reprints the reasoning without consuming your decision.
Without `--interactive`, escalations are auto-approved so batch runs
(scoring, CI) don't block on input.

## Scoring against the practice ground truth

```bash
python score.py scenario_01
```

Compares your output's `inferred_state`, `confidence_band`, and `action`
against `data/scenario_01/ground_truth.json` at each of its checkpoints,
and prints a per-field score. Run `main.py` for that scenario first.

## Checking for false positives on red herrings

```bash
python check_false_positives.py scenario_01
```

Verifies that no forbidden action fires within the specified time window
of a red-herring event (per `ground_truth.json`'s
`false_positive_checks`), independent of whatever state/band/action the
system otherwise settles on.

## Debugging a specific date

```bash
python debug.py scenario_01 2026-03-12
```

Replays a scenario up to (and including) the given date and prints
every finding each agent produced that day, plus the top three
candidate life-event states with their decayed scores and the specific
evidence behind each — this is also a working prototype of the
explainability output the system produces at decision time.

## Design notes

The short version: six independent signal agents (swarm) publish
findings to a shared per-customer state board; a Life-Event agent
(handoff) turns those findings into persistent, time-decayed evidence
and infers a state and confidence band; a deterministic guardrail runs
synchronously on every incoming support message; an action agent maps
state+confidence to one of six bounded actions, gated by a hard/soft
evidence split and an ambiguity check; HITL reviews anything escalated.
Full reasoning for every one of these choices, including what testing
against the practice scenarios revealed and fixed, is in
`solution_document.md` and `research_log.md`.
