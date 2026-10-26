"""The watcher's short card for Telegram, shown above every Approve (no heavy imports: the worker's Python sends it)."""
from __future__ import annotations

MARK = {"pass": "PASS", "fix": "FIX FIRST", "block": "BLOCKED"}


def card(v: dict) -> str:
    score = f", {v['score']}/100" if isinstance(v.get("score"), (int, float)) else ""
    lines = [f"Watcher ({str(v.get('gate', '')).upper()}, round {v.get('round')}): {MARK.get(v.get('verdict'), '?')}{score}"]
    for b in (v.get("blocking") or [])[:5]:
        lines.append(f"BLOCK {b.get('item', '')}: {b.get('issue', '')} -> {b.get('fix', '')}")
    for i in (v.get("issues") or [])[:5]:
        lines.append(f"- {i.get('item', '')}: {i.get('issue', '')}")
    for idea in (v.get("ideas") or [])[:3]:
        lines.append(f"Idea: {idea.get('idea', '')} ({idea.get('gain', '')}, {idea.get('effort', '')})")
    if v.get("for_person"):
        lines.append(str(v["for_person"]))
    if v.get("missing_judges"):
        lines.append("Not judged by: " + ", ".join(v["missing_judges"]))
    return "\n".join(lines)[:3800]
