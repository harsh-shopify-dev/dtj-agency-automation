"""Action log: one JSON line per action (RUNBOOK 2.5), checked against schemas/action.schema.json.
Same format as services/seo-engine/seo_engine/actionlog.py; this one lives in the content store (log/actions.jsonl)."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "action.schema.json"
_SECRET_KEY = re.compile(r"token|password|secret|authorization|api[_-]?key", re.I)


def scrub(value):
    if isinstance(value, dict):
        return {k: "[redacted]" if _SECRET_KEY.search(str(k)) else scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


class ActionLog:
    def __init__(self, path: str | Path, run_id: str | None = None):
        self.path = Path(path)
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self._validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))

    def record(self, *, tier: int, mode: str, target: str, action: str, reason: str, result: str, **extra) -> dict:
        row = {"ts": datetime.now(timezone.utc).isoformat(), "run_id": self.run_id, "client_id": "dtj", "automation": "smm",
               "tier": tier, "mode": mode, "target": target, "action": action, "reason": reason, "result": result, **scrub(extra)}
        self._validator.validate(row)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row
