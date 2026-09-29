# System Architecture — Agentic Customer 360

This diagram is Mermaid source. GitHub renders `.md` files with a
` ```mermaid ` fence natively — no extra tool needed once this file is in
your repo. It also pastes directly into https://mermaid.live or Draw.io
(Arrange > Insert > Advanced > Mermaid) if you want to export a PNG for
the solution document.

**How to read it:**
- **Solid arrows** = the daily batch loop (asynchronous — runs once per
  simulated day, regardless of which specific event triggered it).
- **Dashed arrows** = synchronous, event-triggered flows that fire the
  moment a specific event arrives, bypassing the daily loop. The
  guardrail is the only synchronous path in this system, matching the
  Production Bar's requirement that catastrophic actions be checked
  immediately, not on the next scheduled pass.
- **Cylinders** = persistent stores (memory / logs / output files).
- **Rectangles** = agents / active components.

```mermaid
flowchart TB

    subgraph DS["Data Sources"]
        HS["history_seed.jsonl<br/>(pre-loaded backstory)"]
        LS["live_stream.jsonl<br/>(async, out-of-order events)"]
    end

    subgraph ING["Ingestion Layer"]
        ES[["EventStore<br/>sorts by event_time per customer<br/>dedups by event_id<br/>detects late/out-of-order arrivals"]]
    end

    HS -->|"batch load, once"| ES
    LS -->|"fed in ingestion_time order"| ES

    subgraph SWARM["Swarm — signal-gathering agents (async, run every simulated day, no dependency on each other)"]
        TA["Transaction Agent<br/>tool: median/gap stats<br/>reads: core_banking_ledger"]
        SPA["Spend Agent<br/>tool: category baseline compare<br/>reads: card_payments"]
        UA["Usage Agent<br/>tool: login trend + keyword match<br/>reads: web_app_events"]
        SUA["Support Agent<br/>tool: keyword match, denial check<br/>reads: support_logs"]
        PA["Profile Agent<br/>tool: field-change detector<br/>reads: loan_kyc"]
        TRA["Transfer Agent<br/>tool: own-name match, balance-fraction calc<br/>reads: instant_payments, ach_wire, core_banking_ledger"]
    end

    ES -->|"customer's sorted events, up to as_of"| TA
    ES -->|"customer's sorted events, up to as_of"| SPA
    ES -->|"customer's sorted events, up to as_of"| UA
    ES -->|"customer's sorted events, up to as_of"| SUA
    ES -->|"customer's sorted events, up to as_of"| PA
    ES -->|"customer's sorted events, up to as_of"| TRA

    SB[("State Board<br/>shared per-customer findings<br/>(scoped to one customer_id)")]

    TA -->|"publish: structured findings only<br/>(signal, confidence, evidence ids)"| SB
    SPA -->|"publish findings"| SB
    UA -->|"publish findings"| SB
    SUA -->|"publish findings"| SB
    PA -->|"publish findings"| SB
    TRA -->|"publish findings"| SB

    subgraph SYNTH["Synthesis — handoff (sequential, one direction)"]
        LEA["Life-Event Agent<br/>tool: rule-weighted scoring,<br/>hard/soft evidence split"]
    end

    SB -->|"handoff: today's findings"| LEA

    LSM[("Life-State Memory<br/>persistent evidence per (customer, state, signal)<br/>exponential decay: 45-day half-life, 180-day forget")]

    LEA -->|"record new evidence"| LSM
    LSM -->|"decayed score per candidate state"| LEA

    subgraph GUARD["Guardrail Agent — synchronous, event-triggered, bypasses everything else"]
        GA["Guardrail Agent<br/>tool: deterministic keyword scan<br/>reads: support_logs (by ingestion_time)"]
    end

    ES -.->|"new support message arrives → scan immediately"| GA

    subgraph ACT["Action Decision"]
        AA["Action Agent<br/>tool: playbook lookup,<br/>ambiguity + confidence gating"]
    end

    LEA -->|"inference: state, band,<br/>agents agreeing, evidence"| AA
    GA -.->|"HARD OVERRIDE if matched<br/>(halts autonomous outreach)"| AA

    subgraph HITLBOX["Human-in-the-Loop"]
        HITL["HITL Console<br/>approve / reject / modify / 'why?'"]
    end

    AA -->|"if hitl_status = escalated"| HITL
    AA -->|"if auto_approved, skip straight through"| CP

    HITL -->|"final decision + full context shown"| APPLOG[("logs/approvals_*.jsonl<br/>audit-ready approval log")]
    HITL --> CP

    CP[("outputs/inferred_events_*.json<br/>graded checkpoint stream")]

    subgraph OBS["Observability (runs alongside every swarm call)"]
        TL["Trace Logger<br/>masks account_id, counterparty_name<br/>before writing"]
    end

    TA -.-> TL
    SPA -.-> TL
    UA -.-> TL
    SUA -.-> TL
    PA -.-> TL
    TRA -.-> TL
    TL --> TRACELOG[("logs/trace_*.jsonl<br/>one line per agent call")]

    classDef store fill:#e8f0fe,stroke:#4285f4,stroke-width:1px;
    classDef agent fill:#fff,stroke:#333,stroke-width:1px;
    classDef sync fill:#fdecea,stroke:#c0392b,stroke-width:1px;
    class SB,LSM,CP,APPLOG,TRACELOG store;
    class GA,AA sync;
```

## Component summary (for cross-checking against the Production Bar checklist)

| Component | Type | Data source(s) | Output |
|---|---|---|---|
| EventStore | Ingestion | `history_seed.jsonl`, `live_stream.jsonl` | Per-customer sorted event list |
| Transaction Agent | Swarm (async) | `core_banking_ledger` | `income_drop`, `income_stopped`, `recurring_started:*`, `recurring_stopped:*` |
| Spend Agent | Swarm (async) | `card_payments` | `spend_spike:*`, `spend_drop:*`, `card_activity_drop` |
| Usage Agent | Swarm (async) | `web_app_events` | `login_drop`, `login_spike`, `search_theme:*`, `feature_theme:*` |
| Support Agent | Swarm (async) | `support_logs` | `support_theme:*`, `support_denied` |
| Profile Agent | Swarm (async) | `loan_kyc` | `profile_change:*` |
| Transfer Agent | Swarm (async) | `instant_payments`, `ach_wire`, `core_banking_ledger` | `external_self_transfer`, `income_swept_out` |
| State Board | Shared memory | Swarm agent outputs | Today's findings, per customer |
| Life-Event Agent | Synthesis (handoff) | State Board | Inferred state, confidence band, evidence |
| Life-State Memory | Persistent memory | Life-Event Agent | Decayed, accumulated evidence scores |
| Guardrail Agent | Synchronous, event-triggered | `support_logs` (by `ingestion_time`) | Hard override (bypasses inference) |
| Action Agent | Decision | Life-Event inference + Guardrail hits | Proposed action, subtype, `hitl_status` |
| HITL Console | Human checkpoint | Action Agent's proposal | Final decision + approval log entry |
| Trace Logger | Observability | Every swarm agent call | Masked, timestamped trace log |

## Why this topology (brief justification, for the solution document)

- **Swarm** for the six signal agents: they read disjoint slices of the
  event stream and have no dependency on each other's output, which is
  exactly where the swarm pattern's parallelism wins and its main
  weakness (unresolved disagreement) is deferred, on purpose, to synthesis.
- **Handoff** from the swarm into the Life-Event Agent: a single,
  one-directional pass with a clearly scoped package (structured
  findings, not raw reasoning traces).
- **Guardrail kept fully outside the daily batch loop**, checked
  synchronously against `ingestion_time` the moment a message arrives.
  This is the one place the system needs to react in real time rather
  than wait for the next scheduled pass — matching the Production Bar's
  distinction between synchronous flows (authorization-time checks) and
  asynchronous ones (everything else).
- **HITL as a gate, not a pipeline stage:** it only activates when the
  Action Agent's `hitl_status` is `escalated`, so low-stakes `no_action`
  and `auto_approved` decisions flow straight through without blocking on
  a human every single day.
