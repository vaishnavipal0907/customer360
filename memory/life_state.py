from dataclasses import dataclass, field

HALF_LIFE_DAYS = 45       # evidence loses half its weight every 45 days
FORGET_AFTER_DAYS = 180   # ...and is dropped completely after this


@dataclass
class Evidence:
    state: str
    signal: str
    agent: str
    weight: float
    last_seen: object          # datetime
    event_ids: list = field(default_factory=list)


class LifeStateMemory:
    """Per-customer memory of evidence for each possible life state."""

    def __init__(self):
        self.evidence = {}     # customer_id -> {(state, signal): Evidence}

    def record(self, customer_id, state, signal, agent, weight, as_of, event_ids):
        items = self.evidence.setdefault(customer_id, {})
        key = (state, signal)
        old = items.get(key)
        if old:
            old.weight = max(old.weight, weight)     # keep the strongest reading
            old.last_seen = as_of                    # ...and refresh its age
            old.event_ids = sorted(set(old.event_ids) | set(event_ids))
        else:
            items[key] = Evidence(state, signal, agent, weight, as_of, list(event_ids))

    def score(self, customer_id, as_of):
        """Return {state: {"score", "agents", "items"}} with time decay applied."""
        result = {}
        items = self.evidence.get(customer_id, {})
        for key, ev in list(items.items()):
            age = (as_of - ev.last_seen).days
            if age > FORGET_AFTER_DAYS:
                del items[key]
                continue
            w = ev.weight * 0.5 ** (age / HALF_LIFE_DAYS)
            entry = result.setdefault(ev.state, {"score": 0.0, "agents": set(), "items": []})
            entry["score"] += w
            if w >= 0.15:
                entry["agents"].add(ev.agent)
            entry["items"].append((ev.signal, round(w, 2), ev.event_ids))
        return result