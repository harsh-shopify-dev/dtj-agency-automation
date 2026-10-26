"""The watcher's short card for Telegram, shown above every Approve (no heavy imports: the worker's Python sends it)."""
from __future__ import annotations

MARK = {"pass": "✅ Good to go", "fix": "🟡 Fix first", "block": "⛔ Blocked"}
GATE = {"g0": "references", "g1": "plan", "g2": "pictures", "g3": "clips", "g4": "final reel", "g5": "process"}


def card(v: dict) -> str:
    gate = str(v.get("gate", "")).lower()
    score = f" · {v['score']}/100" if isinstance(v.get("score"), (int, float)) else ""
    lines = [f"<b>🔍 Quality check: {GATE.get(gate, gate)}</b>", f"{MARK.get(v.get('verdict'), '?')}{score}"]
    block = (v.get("blocking") or [])[:3]
    if block:
        lines += ["", "<b>Must fix</b>"] + [f"• {_esc(b.get('issue', ''))}" for b in block]
    issues = (v.get("issues") or [])[:3]
    if issues:
        lines += ["", "<b>Worth fixing</b>"] + [f"• {_esc(i.get('issue', ''))}" for i in issues]
    ideas = (v.get("ideas") or [])[:2]
    if ideas:
        lines += ["", "<b>Ideas</b>"] + [f"💡 {_esc(i.get('idea', ''))}" for i in ideas]
    if v.get("for_person"):
        lines += ["", _esc(v["for_person"])]
    return "\n".join(lines)[:3800]


def _esc(text) -> str:
    s = str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").strip()
    return s if len(s) <= 180 else s[:177].rsplit(" ", 1)[0] + "…"
