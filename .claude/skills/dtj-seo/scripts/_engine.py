"""Shared by the dtj-seo skill scripts: find the repo and import the SEO engine (services/seo-engine/seo_engine)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
ENGINE = REPO / "services" / "seo-engine"
WORK = REPO / ".work" / "seo"

if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))
try:  # the Windows console is cp1252; rupee signs and dashes would crash a print
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def latest_run(name: str) -> Path | None:
    """The newest .work/seo/<date>/<name>, or None."""
    found = sorted(WORK.glob(f"*/{name}"))
    return found[-1] if found else None


def read_json(path: str | Path) -> dict | list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, data) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
