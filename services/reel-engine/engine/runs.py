"""One reel run: <root>/runs/<brand>/<run>/ with state.json (every stage's last answer) and the run's files.
Nothing in a run folder is ever deleted; a redo writes a new version next to the old one."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .brands import slug


class Run:
    def __init__(self, root: Path, brand: str, run: str):
        self.brand, self.run = slug(brand, "brand"), slug(run, "run")
        self.dir = Path(root) / "runs" / self.brand / self.run
        self.dir.mkdir(parents=True, exist_ok=True)
        self._path = self.dir / "state.json"
        self.state = json.loads(self._path.read_text(encoding="utf-8")) if self._path.is_file() else {"stages": {}}

    def save(self) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self._path)

    def done(self, stage: str) -> dict | None:
        return self.state["stages"].get(stage)

    def record(self, stage: str, result: dict) -> None:
        self.state["stages"][stage] = {**result, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        self.save()
