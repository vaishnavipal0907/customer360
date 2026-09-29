from dataclasses import dataclass, field


@dataclass
class Finding:
    agent: str            # which agent produced this
    customer_id: str
    as_of_time: str       # the moment this finding describes
    signal: str           # short name, e.g. "income_drop"
    value: float          # the measured number
    confidence: str       # "low" | "medium" | "high" (confidence in the measurement)
    evidence: list = field(default_factory=list)   # event_ids that support it
    summary: str = ""     # one plain-English sentence


class StateBoard:
    """Shared per-customer whiteboard. Agents publish structured findings here."""

    def __init__(self):
        self.board = {}   # customer_id -> {agent_name: [Finding, ...]}

    def publish(self, customer_id, agent_name, findings):
        # Replaces this agent's previous findings with the fresh ones
        self.board.setdefault(customer_id, {})[agent_name] = findings

    def findings_for(self, customer_id):
        all_findings = []
        for agent_findings in self.board.get(customer_id, {}).values():
            all_findings.extend(agent_findings)
        return all_findings