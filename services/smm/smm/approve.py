"""Record a named yes for posts (Tier 2: posting publicly). One approval record per post, holding the post's fingerprint, so a
post that changes afterwards needs a new yes.

Who may approve (CLAUDE.md rule 2): Harsh; or, when Harsh is not reachable, any active DTJ teammate, recorded as
"<name> (Harsh not reachable)". The person gives the yes themselves; whoever runs this command types their name exactly.

    python -m smm approve --week 2026-W43 --posts p1,p2,p5 --by "Harsh"
    python -m smm approve --week 2026-W43 --posts p1-p7 --by "Riya" --harsh-unreachable
    python -m smm approve --week 2026-W43 --posts p3 --revoke --by "Harsh"      (before it is posted)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .config import IST
from .gate import check_week, history_of
from .store import Store
from .week import load


class ApprovalError(Exception):
    pass


def expand(week: str, spec: str) -> list[str]:
    """'p1,p3-p5' -> ['2026-W43-p1', '2026-W43-p3', '2026-W43-p4', '2026-W43-p5']. 'all' is not accepted: name the posts."""
    out = []
    for part in [p.strip() for p in spec.split(",") if p.strip()]:
        m = re.fullmatch(r"p(\d{1,2})(?:-p?(\d{1,2}))?", part.removeprefix(f"{week}-"))
        if not m:
            raise ApprovalError(f"'{part}' is not a post number like p3 or p1-p7")
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        out += [f"{week}-p{i}" for i in range(lo, hi + 1)]
    if not out:
        raise ApprovalError("name the posts, e.g. --posts p1,p2")
    return out


def approve(store: Store, week_name: str, posts: str, by: str, harsh_unreachable: bool = False, revoke: bool = False,
            now: datetime | None = None) -> list[str]:
    name = (by or "").strip()
    if not name or name.lower() in {"claude", "bot", "system", "auto"}:
        raise ApprovalError("an approval needs the name of the person who said yes")
    approved_by = f"{name} (Harsh not reachable)" if harsh_unreachable and name.lower() != "harsh" else name
    wk = load(store.week_folder(week_name))
    ids = expand(week_name, posts)
    now = now or datetime.now(IST)
    report = check_week(wk, history_of(store.weeks, week_name), now=None if revoke else now)
    lines = []
    for pid in ids:
        post = wk.post(pid)
        path = store.path(week_name, "approvals", pid)
        if revoke:
            if any(store.path(week_name, "published", pid, pl).exists() for pl in post["platforms"]):
                lines.append(f"{pid}: already posted on a platform; a live post is taken down by a person, not by code")
            store.write(path, {"post_id": pid, "revoked": True, "revoked_by": approved_by,
                               "revoked_at": datetime.now(timezone.utc).isoformat()})
            lines.append(f"{pid}: approval withdrawn by {approved_by}")
            continue
        if report[pid]:
            raise ApprovalError(f"{pid} does not pass the gate, so it cannot be approved:\n  - " + "\n  - ".join(report[pid]))
        store.write(path, {"post_id": pid, "fingerprint": wk.fingerprint(post), "approved_by": approved_by,
                           "approved_at": datetime.now(timezone.utc).isoformat(), "publish_at": post["publish_at"],
                           "platforms": sorted(post["platforms"])})
        lines.append(f"{pid}: approved by {approved_by} for {post['publish_at'][:16].replace('T', ' ')} IST on "
                     f"{', '.join(sorted(post['platforms']))}")
    return lines
