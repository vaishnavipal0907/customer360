# Research Log — Agentic Customer 360

Each entry: what I read, what I took from it, and which decision it shaped.
Entries marked [TESTING] came from running the system against practice
scenarios rather than a specific external source, and are included because
they show deliberate, evidence-based design.

---

## 1. Memory architecture: snapshots vs. persistent evidence

**Decision:** Agent findings are transient snapshots recomputed each day.
A separate `LifeStateMemory` accumulates *evidence* per (customer, state,
signal), with exponential time-decay (45-day half-life, 180-day forget
window) instead of a fixed lookback window.

**Why:** [TESTING] Early versions had every agent look back a fixed number
of days. Real signals (a pharmacy purchase, a login drop) fell out of the
window and the inferred state reverted to "no significant event" even
though the underlying situation hadn't changed — exactly the failure the
problem statement describes ("infers new parent on day one but doesn't
carry that understanding forward").

**Source:** https://futurense.com/blog/ai-agent-memory-explained

---

## 2. Multi-agent coordination: swarm + handoff + synthesis

**Decision:** Signal-gathering agents (transaction, spend, usage, support,
profile, transfer) run as an independent **swarm**, writing structured
findings to a shared per-customer state board. A single **handoff** then
passes those findings to the Life-Event agent for **synthesis**. HITL acts
as a final gate, not a pipeline stage.

**Why:** the six signal agents genuinely don't depend on each other's
internals — each reads a different slice of the event stream — so
parallel/independent publication was a natural fit. Reconciling
conflicting reads (e.g. an income drop supporting both
`job_loss_or_income_disruption` and `new_child_life_event`
simultaneously) was deliberately NOT resolved inside the swarm; it was
pushed to the synthesis agent, matching the documented weakness of the
swarm pattern ("the swarm itself doesn't resolve conflicting reads").

**Source:** https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns

---

## 3. Hard evidence vs. soft evidence in confidence scoring

**Decision:** Signals are split into "hard" (concrete events: a transfer,
a KYC change, specific ticket text) and "soft" (behavioral proxies: login
drop, spend drop, a rejected ticket). Soft evidence alone is capped at
35% weight and can never reach medium/high confidence without at least
one corroborating hard signal.

**Why:** [TESTING] scenario_03 (a churn scenario) reached "high" confidence
after only three days, driven entirely by a login drop, a rejected support
ticket, and general dissatisfaction language — all soft, all correlated
with each other rather than independently corroborating. The practice
ground truth expected "low" confidence at that point. This showed that
agreement between weak, nonspecific proxies isn't the same kind of
evidence as agreement between independent hard signals, so the scoring
had to distinguish them explicitly rather than treating all agent
agreement as equally strong.

**Source:** https://www.sciencedirect.com/science/article/pii/S146708951630077X

---

## 4. Guardrails run on ingestion time, not event time

**Decision:** The guardrail agent scans support messages by
`ingestion_time`, not `event_time`, so a late-arriving legal or fraud
message is still caught on the day it actually reaches the system.

**Why:** the dataset schema explicitly separates `event_time` (when
something happened) from `ingestion_time` (when the system received it),
and states events may arrive late or out of order. A guardrail keyed to
`event_time` could silently skip a message that arrived late, which
directly contradicts the checklist's "correct handling of late or
out-of-order events."

**Source:** _(if you read anything about event-time vs. processing-time
in streaming systems — e.g. Kafka, streaming ingestion articles — cite it
here)_

---

## 5. Recurring-payment detection needs a proportional overdue margin

**Decision:** A standing instruction is flagged as "stopped" only when it
is overdue by `max(1.5x its usual gap, usual gap + 10 days)`, not a fixed
grace period.

**Why:** [TESTING] a fixed 3-day grace period on a ~30-day payment cycle
produced a false positive: a bill landing 11 days later than the previous
cycle (ordinary calendar-month drift, or a gap estimated from only 2-3
samples) was flagged as "stopped," which prematurely corroborated soft
churn evidence and pushed the system to high confidence too early. Scaling
the grace period to the payment's own typical spacing fixed this without
hardcoding anything scenario-specific.

**Source:** [TESTING-derived; no external source needed, but you could
cite something on outlier detection with small sample sizes if you want
an extra reference]

---

## 6. Explainability generated at decision time, not reconstructed after

**Decision:** `action_agent.explain()` builds its explanation directly
from the weighted evidence list that produced the score (which agents
fired, which signals, which weights), and this same text is shown to the
human in the HITL prompt and written into the checkpoint's `notes` field.

**Why:** the problem statement explicitly distinguishes real explainability
from "reconstructed after the fact by asking the model to explain what you
just did." Building the explanation from the same data structure used for
the decision (rather than a separate LLM call after the fact) guarantees
the explanation can't drift from the actual reasoning.

**Source:** _(search "explainable AI decision provenance" or similar)_

---

## 7. Known limitations (for the solution document)

- "Own name" transfer matching (`transfer_agent.is_own_name`) is a fragile
  string match on `counterparty_name`; production systems would use
  verified account linkage instead.
- Third-party payments (e.g. tuition) are never scored for fraud risk;
  only self-transfers are — a deliberate scope narrowing to avoid false
  positives on legitimate large payments (the tuition red herring).
- The income-baseline median can drift once enough reduced-pay periods
  accumulate; freezing the baseline from `history_seed` only would avoid
  this but wasn't implemented due to time.
- The action playbook (`action_agent.PLAYBOOK`) maps one state+band to one
  action; scenario_03's ground truth expected different actions
  (`relationship_manager_escalation` vs `proactive_retention_outreach`)
  for the same state and band at different points, likely based on
  severity/reversibility of the specific transfer rather than the state
  itself — not resolved in the current design, documented as a known gap.