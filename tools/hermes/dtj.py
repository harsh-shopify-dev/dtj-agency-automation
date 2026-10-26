"""dtj: the one command Hermes Agent may run on DTJ's VPS (Harsh, 26 Oct 2026: "set up hermes for reels").

Hermes (Docker, profile ugc_generation_automation) is the team's front door in Telegram; it runs `dtj` over ssh with a key that can
run nothing else (authorized_keys forced command -> this file with --ssh). The reel work itself does not change: `dtj` feeds the
request through the reel bot's OWN code nodes ("Read the Message", "Who Is It", read live from n8n so the checks, the daily limit and
every refusal are exactly the bot's), and a new reel starts "Reel Factory: New Reel" the way the bot does. Then, as today, the
worker asks "tap Start if you are watching" in @dtj_reels_bot, Claude Code makes the reel, and the person approves the plan, the
pictures and the final reel there (phase 1; the buttons move into the Hermes bot in phase 2, see the Hermes migration spec).

    dtj.py --ssh                                  ssh forced command: the request comes on stdin (tools/hermes/hermes_dtj.sh)
    dtj.py --user <telegram id> --name <name> <remake|reel|refs|audience|status|help> [text ...]   by hand, on the VPS

`photo` (Hermes only): a photo the person sent to the Hermes bot, base64 on stdin line 5; saved in ~/dtj/hermes/photos/<user>/ and
used as a product picture by that person's next remake / reel within 30 minutes, exactly like photos sent to the reel bot.

stdin for --ssh: line 1 the sender's Telegram user id, line 2 their name, line 3 the platform (Hermes's own HERMES_SESSION_* values,
not typed by the model), line 4 the sub-command, the rest the request text. Output: one JSON line {"ok", "say", ...} for Hermes to
relay word for word. Every call is logged to ~/dtj/hermes/dtj.log (who, what, the result); never a token.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "n8n" / "store-factory"))
from node_harness import run_node  # noqa: E402

BOT = ROOT / "n8n" / "reel-factory"
BOT_WORKFLOW = "DRHXIhjKpwYjPjJO"        # Reel Factory: Telegram Bot (its live code nodes are the rules)
NEW_REEL = "dS36LVeRXLuIuajm"            # Reel Factory: New Reel
PROJECT = "NuKdhPFWwCCbm1K3"
SUBS = ("remake", "reel", "refs", "audience", "status", "help", "photo")
ENV_FILE = Path.home() / ".config" / "dtj" / "worker.env"
LOG = Path.home() / "dtj" / "hermes" / "dtj.log"
PHOTOS = Path.home() / "dtj" / "hermes" / "photos"
PHOTO_MINUTES = 30                       # the reel bot's own window for "photos sent just before"
MAGIC = {bytes([0xFF, 0xD8, 0xFF]): ".jpg", bytes([0x89]) + b"PNG": ".png", b"RIFF": ".webp"}
IST = timezone(timedelta(hours=5, minutes=30))
REEL_BOT = "@dtj_reels_bot"


def load_env(path: Path = ENV_FILE) -> None:
    """The worker's settings file (N8N_MCP_TOKEN): an ssh forced command starts with an empty environment."""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*([A-Z][A-Z0-9_]*)=(.*)$", line)
            if m and m.group(1) not in os.environ:
                os.environ[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    except OSError:
        pass


def mcp_call(tool: str, args: dict) -> dict:
    import n8n_mcp  # noqa: PLC0415  (reads N8N_MCP_TOKEN at call time)
    return n8n_mcp.call(tool, args)


def plain(text: str) -> str:
    """The bot's replies are Telegram HTML; Hermes relays plain text."""
    return html.unescape(re.sub(r"</?b>", "", str(text or "")))


def live_code(call, names: tuple[str, ...]) -> dict[str, str]:
    """The reel bot's code nodes as they run in n8n now (so REFS_READY and any later fix count), else the files in this repo."""
    out: dict[str, str] = {}
    try:
        wf = call("get_workflow_details", {"workflowId": BOT_WORKFLOW}).get("workflow", {})
        for node in wf.get("nodes", []):
            if node.get("name") in names and node.get("parameters", {}).get("jsCode"):
                out[node["name"]] = node["parameters"]["jsCode"]
    except Exception:  # noqa: BLE001  n8n unreachable: the repo copy is the same code as deployed
        pass
    files = {"Read the Message": "reel_bot_read.js", "Who Is It": "reel_bot_route.js"}
    for n in names:
        out.setdefault(n, (BOT / files[n]).read_text(encoding="utf-8"))
    return out


def tables(call) -> dict[str, str]:
    found = call("search_data_tables", {"query": "dtj_", "limit": 100}).get("data", [])
    return {t.get("name"): t.get("id") for t in found}


def rows(call, table_id: str, filters: list[dict]) -> list[dict]:
    out: list[dict] = []
    for _ in range(20):
        args = {"dataTableId": table_id, "projectId": PROJECT, "limit": 100, "skip": len(out), "filter": {"type": "and", "filters": filters}}
        page = call("get_data_table_rows", args)
        got = (page.get("rows") if "rows" in page else page.get("data")) or []
        out += got
        if len(got) < 100:
            break
    return out


def recent_photos(user: str, now: datetime, root: Path | None = None) -> list[dict]:
    """Photos this person sent to the Hermes bot in the last 30 minutes, as rows the bot's "Load Recent Photos" gives: the value
    carries an HP: mark so the picture is a VPS path, not a Telegram file id (handle() takes the tg: off again)."""
    folder = (root or PHOTOS) / user
    if not folder.is_dir():
        return []
    cutoff = now.timestamp() - PHOTO_MINUTES * 60
    out = []
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.stat().st_mtime >= cutoff:
            at = datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat()
            out.append({"job": "reelpics-" + user, "value": "HP:" + str(f), "at": at})
    return out


def save_photo(user: str, b64: str, now: datetime, root: Path | None = None) -> dict:
    import base64  # noqa: PLC0415
    try:
        raw = base64.b64decode(b64, validate=True)
    except ValueError:
        raw = b""
    ext = next((e for m, e in MAGIC.items() if raw.startswith(m)), None)
    if not ext or len(raw) > 10_000_000:
        return {"ok": False, "say": "That does not look like a photo (JPG, PNG or WEBP under 10 MB). Please send it again."}
    folder = (root or PHOTOS) / user
    folder.mkdir(parents=True, exist_ok=True)
    f = folder / (now.strftime("%Y%m%d-%H%M%S-%f") + ext)
    f.write_bytes(raw)
    n = len(recent_photos(user, now, root))
    return {"ok": True, "action": "photo", "path": str(f),
            "say": f"Photo saved ({n} in the last {PHOTO_MINUTES} minutes). Now send the ad you want to copy (a reel or Meta ad link), "
                   "or send more product photos."}


def refs_for(call, chat: str, now: datetime) -> dict:
    """What the bot's Load ... nodes give "Who Is It", with the same filters (deploy_reel_bot.py)."""
    t = tables(call)
    today = now.astimezone(IST).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
    return {
        "Load Bot Users": rows(call, t["dtj_bot_users"], [{"columnName": "telegram_user_id", "condition": "isNotEmpty", "value": None}]),
        "Load Open Questions": rows(call, t["dtj_bot_answers"], [{"columnName": "chat_id", "condition": "eq", "value": chat},
                                                                 {"columnName": "value", "condition": "isEmpty", "value": None}]),
        "Load Recent Photos": rows(call, t["dtj_bot_answers"], [{"columnName": "job", "condition": "eq", "value": "reelpics-" + chat}])
                              + recent_photos(chat, now, PHOTOS_ROOT[0]),
        "Load Today's Reels": rows(call, t["dtj_reel_jobs"], [{"columnName": "createdAt", "condition": "gte", "value": today}]),
        "Load Settings": rows(call, t["dtj_reel_settings"], [{"columnName": "key", "condition": "isNotEmpty", "value": None}]),
    }


PHOTOS_ROOT = [None]                     # tests point this at a temporary folder


def is_member(call, user: str) -> bool:
    team = rows(call, tables(call)["dtj_bot_users"], [{"columnName": "telegram_user_id", "condition": "eq", "value": user}])
    return any(str(r.get("active")).lower() != "false" for r in team)


def handle(user: str, name: str, sub: str, text: str, call=mcp_call, now: datetime | None = None, code_dir: Path | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if not re.fullmatch(r"\d{4,15}", user or ""):
        return {"ok": False, "say": "Reels start from Telegram (your Telegram account says who you are). Please send this from the Hermes bot."}
    if sub not in SUBS:
        return {"ok": False, "say": "Unknown request. Use: remake, reel, refs, audience, status or help."}
    if sub == "photo":
        if not is_member(call, user):
            return {"ok": False, "say": "This bot is only for the DTJ team. To get access, send Harsh this number: " + user}
        return save_photo(user, (text or "").strip(), now, PHOTOS_ROOT[0])
    name = re.sub(r"[\x00-\x1f]", " ", name or "").strip()[:60] or "there"
    message = {"message": {"chat": {"id": int(user), "type": "private"}, "from": {"id": int(user), "first_name": name, "is_bot": False},
                           "text": ("/" + sub + " " + (text or "")).strip()[:1600]}}
    code = live_code(call, ("Read the Message", "Who Is It"))
    tmp = code_dir or (Path.home() / "dtj" / "hermes")
    tmp.mkdir(parents=True, exist_ok=True)
    files = {}
    for n, js in code.items():
        f = tmp / ("node_" + n.lower().replace(" ", "_") + ".js")
        f.write_text(js, encoding="utf-8")
        files[n] = f
    read = run_node(files["Read the Message"], message)
    if not read.get("ok"):
        return {"ok": False, "say": "That did not go through (reading the request). Please try again in a minute."}
    msg = read["out"][0]["json"]
    refs = {"Read the Message": msg, **refs_for(call, str(user), now)}
    routed = run_node(files["Who Is It"], {}, refs)
    if not routed.get("ok"):
        return {"ok": False, "say": "That did not go through (checking the request). Please try again in a minute."}
    out = (routed.get("out") or [{}])[0].get("json", {})
    action = out.get("action")
    if action == "reply":
        return {"ok": True, "action": "reply", "say": plain(out.get("text"))}
    if action == "reel":
        inputs = dict(out.get("inputs") or {})
        inputs["product_images"] = str(inputs.get("product_images", "")).replace("tg:HP:", "")   # Hermes photos: VPS paths
        res = call("execute_workflow", {"workflowId": NEW_REEL, "triggerNodeName": "New UGC Reel", "executionMode": "production",
                                        "inputs": {"formData": inputs}})
        kind = "a remake" if inputs.get("reel_type") == "remake" else "a UGC reel"
        return {"ok": True, "action": "reel", "run": res.get("executionId"),
                "say": (f"Saved: {kind} for {inputs.get('product_name')}. In a minute {REEL_BOT} asks \"tap Start if you are watching\"; "
                        f"nothing starts before someone taps it. Then you approve the plan, the pictures and the reel in {REEL_BOT}. "
                        "(Open that bot once and press Start if you never have.)")}
    if action == "refs":
        return {"ok": True, "action": "refs", "say": f"Reference searches are not connected through Hermes yet: send the same /refs or /audience to {REEL_BOT}."}
    return {"ok": True, "action": action or "none", "say": f"Do that in {REEL_BOT} (taps, answers, photos and /reels N stay there for now)."}


def log(entry: dict) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **entry}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ssh", action="store_true", help="read the request from stdin (the ssh forced command)")
    ap.add_argument("--user", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("sub", nargs="?", default="help")
    ap.add_argument("text", nargs="*")
    a = ap.parse_args(argv)
    load_env()
    if a.ssh:
        lines = sys.stdin.read(14_000_000).split("\n")
        user, name, platform, sub = (lines + ["", "", "", ""])[:4]
        text = " ".join(x.strip() for x in lines[4:] if x.strip())
    else:
        user, name, platform, sub, text = a.user, a.name, "cli", a.sub, " ".join(a.text)
    sub = sub.strip().lower().lstrip("/")
    try:
        res = handle(user.strip(), name, sub, text)
    except Exception as e:  # noqa: BLE001  one plain line for the person; the reason is in the log
        res = {"ok": False, "say": "That did not go through. Please try again in a minute.", "error": str(e)[:300]}
    shown = f"<photo, {len(text) * 3 // 4} bytes>" if sub == "photo" else text[:300]
    log({"user": user.strip(), "name": name.strip()[:60], "platform": platform.strip()[:20], "sub": sub, "text": shown,
         "action": res.get("action"), "ok": res.get("ok"), "run": res.get("run"), "error": res.get("error")})
    res.pop("error", None)
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
