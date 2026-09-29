# Agentic Customer 360 — Proactive Intervention Desk
### Solution Document

---

## 1. The problem being solved

A bank's "Customer 360" view is only useful if something acts on it.
Dashboards are passive; a human has to log in, notice a pattern, and
decide. At scale, subtle multi-week shifts — a client's income quietly
dropping, a customer withdrawing from the relationship, a new baby
changing spending — go unnoticed until they've already become a churn
event or a missed opportunity.

This system replaces passive monitoring with **ambient agents**: background
processes that continuously read an asynchronous, out-of-order stream of
banking events (transactions, logins, support tickets, KYC updates) and,
for each customer, must commit to one of six concrete actions — or
explicitly decide **no action** — rather than simply surfacing a flag. It
must also maintain a standing, continuously-updated belief about *what
life event the customer is currently going through*, so that belief
survives across weeks rather than being re-derived (or forgotten) every
time a new event arrives.

---

## 2. Architecture, and why it was designed this way

Full component-level diagram: `architecture_diagram.md`. Summary below.

**Ingestion.** An `EventStore` holds each customer's events, sorted by
`event_time`, deduplicated by `event_id`. Events are fed in
`ingestion_time` order to simulate real arrival, and a late event is
inserted at its correct historical position rather than appended, so it
can never double-count or corrupt a rolling window.

**Signal-gathering: a swarm of six specialist agents.** Transaction,
Spend, Usage, Support, Profile, and Transfer agents each read one
disjoint slice of the event stream and independently publish structured
**findings** (a signal name, a confidence level, and supporting event
IDs) to a shared, per-customer **State Board**. Swarm was chosen here
because these six data sources genuinely don't depend on each other —
the classic case where parallel, independent processing wins on latency.
Its documented weakness (a swarm doesn't resolve disagreement between its
own members) was accepted deliberately, because resolving it is exactly
the synthesis agent's job, one stage later. Agents never see each other's
reasoning, only the structured conclusion published to the board — this
is the "no raw access to another agent's chain-of-thought" pattern from
the problem statement, and it's what keeps memory leakage between
customers structurally impossible (the board and all memory stores are
keyed by `customer_id`).

**Synthesis: a handoff into persistent memory.** The Life-Event Agent
receives the swarm's findings via a single, one-directional handoff. It
does not decide anything on today's findings alone; instead, every
finding becomes a piece of **evidence** recorded in `LifeStateMemory`,
scored per (customer, candidate state, signal), with **exponential time
decay** (45-day half-life, forgotten after 180 days) rather than a fixed
lookback window. This was the single most important design decision in
the system, discovered through testing rather than assumed upfront: a
version with only a rolling-window agent memory correctly identified a
medical hardship on day one, then "forgot" it three weeks later once the
triggering events aged out of the window — precisely the failure mode the
problem statement warns against. Persistent, decaying evidence lets the
system's belief about a customer accumulate and fade gracefully instead
of resetting.

**Confidence calibration: hard evidence vs. soft evidence.** Signals are
split into **hard** (a concrete event: a transfer, a KYC change, a new or
cancelled recurring payment, explicit ticket text) and **soft**
(behavioral proxies: a login drop, a spend drop, a rejected ticket,
general dissatisfaction language). Soft evidence alone is capped at 35%
weight, and medium/high confidence is unreachable without at least one
corroborating hard signal. This exists because testing showed that
several soft, mutually-correlated proxies (an unhappy customer both logs
in less *and* complains more) can agree strongly with each other without
constituting independent corroboration of anything — the system reached
"high confidence" on a churn scenario in three days from soft signals
alone, when the practice ground truth expected "low" at that point.

**Guardrails: the one synchronous flow.** A deterministic keyword scanner
checks every support message the moment it is ingested (by
`ingestion_time`, so a late-arriving message is still caught), completely
outside the daily batch loop. A match (legal threat, fraud claim,
self-harm mention) hard-overrides whatever the Life-Event Agent concludes
and halts autonomous outreach immediately. This is the only part of the
system that cannot wait for the next scheduled pass, matching the
Production Bar's distinction between synchronous, authorization-time
checks and asynchronous, background ones.

**Action decision and HITL as a gate, not a stage.** The Action Agent maps
a (state, band) pair to one of the six bounded actions via a playbook, but
only when confidence is high and the top two candidate states are not too
close to each other (an "ambiguous" case, within a 15% margin, is routed
to `relationship_manager_escalation` instead of guessed at — the system's
concrete answer to "coordination under disagreement"). HITL then only
activates when the proposed `hitl_status` is `escalated`; low-stakes
`no_action` decisions flow straight through, so the human isn't
interrupted on every one of 74 simulated days, only on the handful where
the decision actually changes. Every escalation records what was shown,
the decision made, and the final result to an audit-ready log.

**Observability.** Every swarm agent call is written to a trace log as one
JSON line (agent, findings, timestamp), with account IDs and counterparty
names masked before anything is written to disk — masking happens at the
log boundary, not on the underlying event store, since agents still need
real values to compute correctly.

---

## 3. Key decisions and the reasoning behind them

| Decision | Reasoning | Source |
|---|---|---|
| Two-layer memory: transient findings + decayed persistent evidence | Fixed-window agent memory forgot resolved-but-still-relevant signals within weeks | Testing; corroborated by Redis's long-term-memory architecture writeup and the LLM-agent survey's working/long-term memory split |
| Swarm → handoff → synthesis, not one topology everywhere | Signal sources are independent (swarm fits); disagreement resolution needs a dedicated later stage (handoff) | Multi-agent orchestration literature on swarm's parallelism vs. its unresolved-disagreement weakness |
| Hard/soft evidence split with a corroboration gate | Soft, correlated proxies produced false high-confidence before real evidence existed | Testing; corroborated by fraud-detection "layered evidence" and weak/strong anomaly-weighting practice |
| Proportional overdue margin for recurring payments (`max(1.5x gap, gap+10 days)`) | A fixed 3-day grace period flagged normal calendar-month drift as "stopped," feeding a false hard signal into the confidence gate above | Testing (scenario_03) |
| Guardrail scans by `ingestion_time`, fully outside the daily loop | A guardrail keyed to `event_time` could silently miss a late-arriving legal/fraud message | Dataset schema documentation |
| Explanations built from the same weighted-evidence structure used to decide, not a separate summarization step | Prevents the explanation shown to a human from ever drifting from the actual reasoning | Problem statement's distinction between real explainability and post-hoc reconstruction |

Full detail, with direct source links and what was taken from each, is in
`research_log.md`.

---

## 4. Known limitations and tradeoffs

- **"Own name" transfer matching is a fragile string match** on
  `counterparty_name` rather than verified account linkage; a production
  system would resolve this against a real identity graph.
- **Third-party payments are never scored for fraud risk** — only
  self-transfers are. This was a deliberate narrowing to avoid false
  positives on legitimate large payments (a tuition transfer in
  scenario_01), but it means the system would miss a genuine third-party
  fraud pattern.
- **The income baseline can drift** once enough reduced-pay periods
  accumulate into the comparison window, since the baseline is computed
  from the ledger directly rather than frozen at `history_seed`. Not
  fixed due to time constraints; documented rather than silently left.
- **The action playbook is one action per (state, band) pair.** Testing
  against scenario_03 showed the practice ground truth expecting
  different actions (`relationship_manager_escalation`, then later
  `proactive_retention_outreach`) for the *same* state and confidence
  band, most likely driven by the severity of the specific transfer
  involved rather than the state itself. This was identified but not
  resolved — a genuine open design question left as future work rather
  than patched with a rule fitted to one scenario.
- **Rule thresholds (decay half-life, corroboration weights, spike/drop
  ratios) are hand-tuned against three practice scenarios** and would
  benefit from calibration against a larger, more diverse set before any
  production use.
- **No LLM is used anywhere in the pipeline.** Sentiment and theme
  detection are keyword-based. This keeps the system fully explainable
  and deterministic, at the cost of missing paraphrased or indirect
  language a real NLP model would catch.
