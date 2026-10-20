"""The content store: the git branch `smm-content` of this repository. It holds only data, never code, and is never merged:

    weeks/<YYYY-Www>/week.json, media/        the week's posts (written in the content session)
    weeks/<YYYY-Www>/approvals/<post>.json    named approvals (approve.py)
    weeks/<YYYY-Www>/published/<post>.<platform>.json   what code posted, with the live link
    weeks/<YYYY-Www>/handed/<post>.<platform>.json      what went to Telegram for a person to post by hand
    weeks/<YYYY-Www>/failures/<post>.<platform>.json    failed tries (3 = stop and alert)
    weeks/<YYYY-Www>/results/<post>.<platform>.<24h|7d>.json   numbers pulled from the platform
    notices/<key>.json                        alerts already sent (so each goes out once)
    reports/<YYYY-Www>.md                     the Monday results report
    log/actions.jsonl                         the action log (RUNBOOK 2.5)

Why a branch: GitHub Actions (the daily run) and every team laptop can read and write it with git, every change has a history,
and code reviews on the main branch are not flooded with weekly content. In Actions it is checked out at ./content.
Locally `python -m smm store` opens it as a git worktree in .work/smm-content.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BRANCH = "smm-content"
REPO = Path(__file__).resolve().parents[3]
LOCAL = REPO / ".work" / "smm-content"


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    @property
    def weeks(self) -> Path:
        return self.root / "weeks"

    def week_folder(self, week: str) -> Path:
        return self.weeks / week

    def week_names(self) -> list[str]:
        return sorted(p.name for p in self.weeks.iterdir() if (p / "week.json").exists()) if self.weeks.exists() else []

    def path(self, week: str, kind: str, post_id: str, platform: str | None = None, suffix: str | None = None) -> Path:
        name = ".".join(x for x in (post_id, platform, suffix) if x) + ".json"
        return self.week_folder(week) / kind / name

    def read(self, path: Path) -> dict | None:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def write(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def notice_once(self, key: str) -> bool:
        """True the first time a key is seen (then remembered), so an alert goes out once."""
        path = self.root / "notices" / f"{key}.json"
        if path.exists():
            return False
        self.write(path, {"sent_at": datetime.now(timezone.utc).isoformat()})
        return True

    # git
    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True, check=check)

    def save(self, message: str, push: bool = True) -> bool:
        """Commit everything in the store and push it. Returns False when there was nothing to save."""
        self.git("add", "-A")
        if not self.git("status", "--porcelain").stdout.strip():
            return False
        self.git("commit", "-q", "-m", message)
        if push:
            for _ in range(3):
                self.git("pull", "-q", "--rebase", "origin", BRANCH, check=False)
                if self.git("push", "-q", "origin", f"HEAD:refs/heads/{BRANCH}", check=False).returncode == 0:
                    return True
            raise RuntimeError(f"could not push {BRANCH}; run 'git -C {self.root} status' and push by hand")
        return True


def open_local(repo: Path = REPO, path: Path = LOCAL) -> Store:
    """The content branch as a worktree on this laptop (made the first time; a brand-new branch if origin has none)."""
    if (path / ".git").exists():
        store = Store(path)
        store.git("pull", "-q", "--rebase", "origin", BRANCH, check=False)
        return store
    run = lambda *a, check=True: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=check)
    run("fetch", "-q", "origin", BRANCH, check=False)
    if run("rev-parse", "--verify", "-q", f"origin/{BRANCH}", check=False).returncode == 0:
        run("worktree", "add", "-q", "-B", BRANCH, str(path), f"origin/{BRANCH}")
    else:
        run("worktree", "add", "-q", "--orphan", "-b", BRANCH, str(path))   # git 2.42+: an empty branch with no history
        store = Store(path)
        (path / "README.md").write_text("Data branch of DTJ's social media automation. See services/smm on the main branch.\n",
                                        encoding="utf-8")
        store.git("add", "README.md")
        store.git("commit", "-q", "-m", "SMM content store")
    return Store(path)
