from fnmatch import fnmatch

from agents.life_event_rules import RULES, CONFIDENCE_FACTOR, SOFT_SIGNALS

AGENT_NAME = "life_event_agent"
MIN_SCORE = 0.5            # below this: no significant event
MEDIUM = (1.5, 2)          # (min score, min distinct agents)
HIGH = (3.0, 3)
HARD_GATE = 0.5            # hard evidence needed before soft signals count fully
SOFT_ALONE_FACTOR = 0.35   # how much soft evidence counts when there is no hard evidence
AMBIGUITY_MARGIN = 0.15    # top two states within 15% of each other = ambiguous


def is_soft(signal):
    return any(fnmatch(signal, p) for p in SOFT_SIGNALS)


def weight_for(rules, signal):
    return max([w for pattern, w in rules.items() if fnmatch(signal, pattern)], default=0.0)


def update_memory(customer_id, findings, memory, as_of):
    """Turn fresh findings into evidence for every state they support."""
    for f in findings:
        for state, rules in RULES.items():
            w = weight_for(rules, f.signal)
            if w > 0:
                memory.record(customer_id, state, f.signal, f.agent,
                              w * CONFIDENCE_FACTOR[f.confidence], as_of, f.evidence)


def band_for(score, n_agents, corroborated):
    # No medium or high without at least one hard (concrete) signal.
    if not corroborated:
        return "low"
    if score >= HIGH[0] and n_agents >= HIGH[1]:
        return "high"
    if score >= MEDIUM[0] and n_agents >= MEDIUM[1]:
        return "medium"
    return "low"


def infer(customer_id, memory, as_of):
    scores = memory.score(customer_id, as_of)

    candidates = []
    for state, s in scores.items():
        hard = sum(w for sig, w, _ in s["items"] if not is_soft(sig))
        soft = sum(w for sig, w, _ in s["items"] if is_soft(sig))
        corroborated = hard >= HARD_GATE
        effective = hard + soft * (1.0 if corroborated else SOFT_ALONE_FACTOR)
        candidates.append((state, effective, corroborated, s))
    candidates.sort(key=lambda c: c[1], reverse=True)

    if not candidates or candidates[0][1] < MIN_SCORE:
        return {"state": "no_significant_event", "band": "low", "score": 0.0,
                "agents": set(), "ambiguous": False, "runner_up": None,
                "evidence": [], "corroborated": False}

    state, score, corroborated, top = candidates[0]
    band = band_for(score, len(top["agents"]), corroborated)
    runner_up, ambiguous = None, False
    if len(candidates) > 1:
        r_state, r_score = candidates[1][0], candidates[1][1]
        runner_up = (r_state, round(r_score, 2))
        ambiguous = band != "low" and (score - r_score) / score < AMBIGUITY_MARGIN
    return {"state": state, "band": band, "score": score, "agents": top["agents"],
            "ambiguous": ambiguous, "runner_up": runner_up, "evidence": top["items"],
            "corroborated": corroborated}