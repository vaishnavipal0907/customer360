import json
import re

_ACCOUNT_RE = re.compile(r"\bACC_[A-Z0-9_]+\b")
_NAME_HINT_KEYS = {"counterparty_name", "merchant_name"}


def mask(value):
    """Recursively mask account IDs and known name fields in any JSON-safe structure."""
    if isinstance(value, str):
        return _ACCOUNT_RE.sub(lambda m: m.group(0)[:8] + "***", value)
    if isinstance(value, list):
        return [mask(v) for v in value]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in _NAME_HINT_KEYS and isinstance(v, str):
                out[k] = v[:2] + "***"          # keep first letters only, e.g. "Da***"
            elif k == "account_id" and isinstance(v, str):
                out[k] = v[:8] + "***"
            else:
                out[k] = mask(v)
        return out
    return value


class TraceLogger:
    def __init__(self, path):
        self.path = path
        open(self.path, "w", encoding="utf-8").close()   # fresh file per run

    def log(self, as_of, agent_name, customer_id, finding_count, findings_summary):
        record = {
            "as_of_time": as_of.isoformat(),
            "agent": agent_name,
            "customer_id": customer_id[:8] + "***",       # masked even though it's an ID, not a name
            "finding_count": finding_count,
            "findings": mask(findings_summary),
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")