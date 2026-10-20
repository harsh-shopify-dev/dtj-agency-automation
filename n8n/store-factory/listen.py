"""Listen for the Telegram call: wait until a NEW page request is waiting for Claude Code, print it as one JSON line and exit.

A designer's Claude Code session starts this in the background. When it exits with a request, Claude handles it (CLAUDE.md,
"n8n hand-offs": read the run, do its instructions, answer through reply.py) and then starts listening again.

    python n8n/store-factory/listen.py                     check "Store Factory: Page Design" every 30 s, for up to 8 hours
    python n8n/store-factory/listen.py --interval 60 --hours 4
    python n8n/store-factory/listen.py --once              check once: exit 0 = printed one, 3 = nothing new is waiting
    python n8n/store-factory/listen.py --status            how many requests are waiting, and how many of those were offered already
    python n8n/store-factory/listen.py --forget 345        offer run 345 again (for a request that failed)
    python n8n/store-factory/listen.py --workflow "Reel Factory: New Reel"   listen for reel requests instead (on the reel VPS)

On a hit, stdout is ONE line: {"execution_id": "...", "workflow_id": "...", "started_at": "...", "waiting": <new ones still waiting>}.
The oldest request is offered first and each run only once: offered ids are kept in .work/listen/offered.json (not in git).
Exit codes: 0 found (or --status / --forget done), 1 bad arguments, 2 n8n failed 3 times in a row or the workflow is missing,
3 nothing came in.
Only one laptop should listen at a time: each laptop keeps its own list, so two listeners would both take the same request.
Read only against n8n (search_workflows, search_workflow_executions); the n8n token is never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_n8n import ERRORS, find_workflows, redact  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]  # the repo root (this file is <root>/n8n/store-factory/listen.py)
OFFERED = ROOT / ".work" / "listen" / "offered.json"
WORKFLOW = "Store Factory: Page Design"
KEEP = 500                # offered ids remembered (oldest dropped first)
RETRY_DELAYS = (5, 15)    # seconds before the 2nd and the 3rd try; a 3rd failure in a row stops the listener


class Failed(Exception):
    """n8n failed (unreachable or refused) 3 times in a row."""


class NotFound(Exception):
    """The workflow is not on n8n."""


def load_offered(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return []
    return [str(i) for i in data.get("offered", [])] if isinstance(data, dict) else []


def save_offered(path: Path, ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"offered": ids[-KEEP:]}, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def forget(path: Path, execution_id: str) -> bool:
    ids = load_offered(path)
    if str(execution_id) not in ids:
        return False
    save_offered(path, [i for i in ids if i != str(execution_id)])
    return True


def with_retry(fn, sleep, delays=RETRY_DELAYS):
    """fn(), tried up to len(delays) + 1 times with a pause between tries; raises Failed after the last failure."""
    last = None
    for attempt in range(len(delays) + 1):
        try:
            return fn()
        except ERRORS as exc:
            last = exc
            if attempt < len(delays):
                sleep(delays[attempt])
    raise Failed(last)


def find_workflow(call, name: str = WORKFLOW) -> str:
    found = find_workflows(call, name)
    if not found:
        raise NotFound(f'no workflow named "{name}" on n8n (python n8n/store-factory/setup_n8n.py shows what is missing)')
    return found[0]["id"]


def waiting(call, workflow_id: str) -> list[dict]:
    """The runs of the workflow that wait now, oldest first."""
    runs, cursor = [], None
    for _ in range(20):  # 20 pages of 100 is far more than will ever wait
        args = {"workflowId": workflow_id, "status": ["waiting"], "limit": 100}
        if cursor:
            args["cursor"] = cursor
        answer = call("search_workflow_executions", args)
        runs += answer.get("data", [])
        cursor = answer.get("nextCursor")
        if not cursor:
            break
    runs = [r for r in runs if r.get("status", "waiting") == "waiting" and r.get("id") is not None]
    return sorted(runs, key=lambda r: (r.get("startedAt") or "", len(str(r["id"])), str(r["id"])))


def pick(runs: list[dict], offered: list[str]) -> tuple[dict | None, int]:
    """The oldest run not offered before, and how many new ones are left after it."""
    seen = set(offered)
    fresh = [r for r in runs if str(r["id"]) not in seen]
    return (fresh[0], len(fresh) - 1) if fresh else (None, 0)


def offer_next(call, workflow_id: str, path: Path, sleep=time.sleep) -> dict | None:
    runs = with_retry(lambda: waiting(call, workflow_id), sleep)
    offered = load_offered(path)
    hit, left = pick(runs, offered)
    if hit is None:
        return None
    save_offered(path, offered + [str(hit["id"])])  # recorded before it is printed: never offered twice
    return {"execution_id": str(hit["id"]), "workflow_id": workflow_id, "started_at": hit.get("startedAt"), "waiting": left}


def listen(call, workflow_id: str, path: Path, interval: int, hours: float, sleep=time.sleep, clock=time.monotonic) -> dict | None:
    """Check every `interval` seconds until a new request waits (returned) or `hours` have passed (None)."""
    end = clock() + hours * 3600
    while True:
        hit = offer_next(call, workflow_id, path, sleep)
        if hit:
            return hit
        if clock() + interval > end:
            return None
        sleep(interval)


def kind(name: str) -> str:
    return "page requests" if name == WORKFLOW else "requests"


def status(call, workflow_id: str, path: Path, sleep=time.sleep, name: str = WORKFLOW) -> str:
    runs = with_retry(lambda: waiting(call, workflow_id), sleep)
    offered = set(load_offered(path))
    ids = [str(r["id"]) for r in runs]
    done = [i for i in ids if i in offered]
    listing = ", ".join(f"{i} (offered)" if i in offered else i for i in ids)
    return (f"{name}: {len(ids)} {kind(name)[:-1]}(s) waiting for Claude Code, {len(done)} of them already offered on this laptop."
            + (f" Oldest first: {listing}." if ids else ""))


def main(argv=None, *, call=None, sleep=time.sleep, clock=time.monotonic, offered_path: Path = OFFERED, secrets=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--interval", type=int, default=30, help="seconds between checks (at least 10; default 30)")
    ap.add_argument("--hours", type=float, default=8, help="stop after this many hours (at most 12; default 8)")
    ap.add_argument("--workflow", default=WORKFLOW, help=f'the n8n workflow to watch (default "{WORKFLOW}"; reels: "Reel Factory: New Reel")')
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="check once: exit 0 = printed one, 3 = nothing waiting")
    mode.add_argument("--status", action="store_true", help="how many are waiting and how many of those were offered")
    mode.add_argument("--forget", metavar="EXECUTION_ID", help="remove an id from the offered list so it is offered again")

    def bad_arguments(message):  # exit 1, so exit 2 always means "n8n failed"
        ap.print_usage(sys.stderr)
        sys.exit(f"listen.py: error: {message}")
    ap.error = bad_arguments
    args = ap.parse_args(argv)
    if args.interval < 10:
        ap.error("--interval must be at least 10 seconds")
    if not 0 < args.hours <= 12:
        ap.error("--hours must be more than 0 and at most 12")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    if args.forget:
        if forget(offered_path, args.forget):
            print(f"Forgot {args.forget}: it will be offered again while it is still waiting.")
        else:
            print(f"{args.forget} was not in the offered list; nothing changed.")
        return 0

    if call is None:
        from n8n_mcp import call  # the real server (the token is read inside, never printed)
        if secrets is None:
            from setup_n8n import _live_secrets as secrets
    try:
        workflow_id = with_retry(lambda: find_workflow(call, args.workflow), sleep)
        if args.status:
            print(status(call, workflow_id, offered_path, sleep, args.workflow))
            return 0
        if args.once:
            hit = offer_next(call, workflow_id, offered_path, sleep)
        else:
            print(f"Listening for {kind(args.workflow)} ({args.workflow}) every {args.interval} s, up to {args.hours:g} h. "
                  "Only one laptop should listen at a time.", file=sys.stderr, flush=True)
            hit = listen(call, workflow_id, offered_path, args.interval, args.hours, sleep, clock)
    except NotFound as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 2
    except Failed as exc:
        cause = exc.args[0] if exc.args else exc
        hidden = secrets() if callable(secrets) else (secrets or ())
        print(f"Stopped: n8n failed 3 times in a row ({type(cause).__name__}): {redact(cause, hidden)[:500]}", file=sys.stderr)
        return 2
    if hit:
        print(json.dumps(hit), flush=True)
        return 0
    if args.once:
        print("No new page request is waiting.")
    else:
        print(f"Stopped listening after {args.hours:g} hours: no page request came in.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
