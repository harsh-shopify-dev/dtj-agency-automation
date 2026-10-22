"""The store factory's worker on DTJ's VPS (Harsh, 22 Oct 2026: "everything will be automated ... i would suggest that the n8n
triggers it and same for the claude"). n8n leaves every AI step as a waiting run ("Request for Claude Code: <step>"); this service
takes each one within a minute, runs Claude Code on it with nobody at the computer, and the run is answered the way a laptop
session answered it. People still answer and approve in Telegram.

    python n8n/store-factory/worker.py              run as a service (tools/vps/dtj-worker.service)
    python n8n/store-factory/worker.py --once       one round: look at what waits for a person, start one new request, exit
    python n8n/store-factory/worker.py --status     every run it holds: running, waiting for a person, done, failed
    python n8n/store-factory/worker.py --retry 993  run a failed request again from the start (also lifts a stop)

How a request runs:
1. A run of a watched workflow waits at its "Wait for Claude Code" node; the worker reads the request (instructions, resume link).
2. Claude Code runs headless in this repo (`claude -p`) on DTJ's Claude API key: CLAUDE.md rule 9, an unattended AI step never
   uses a subscription login, so without ANTHROPIC_API_KEY nothing starts. Each request is capped at DTJ_CLAUDE_MAX_USD (Harsh's
   number; nothing starts without one). Claude may only run what .claude/vps-settings.json allows; anything else is refused.
3. When the job waits for a person in Telegram (store_job.py exits 3), Claude ends its turn with `DTJ_WAIT: <command>`. The worker
   runs that command itself every few minutes (no Claude, no cost) until the person has answered, then resumes the same Claude
   session with what the command printed. Only store_job.py commands are ever run this way, never through a shell.
4. Claude answers n8n itself (reply.py). A run Claude left unanswered is marked failed and the admin chat hears why; nothing is
   answered for it (a made-up result is worse than none). Three failures in a row stop new starts (CLAUDE.md self-healing) until
   --retry or a restart.
State: .work/worker/jobs.json; one log per run in .work/worker/<run>.log with resume links hidden. Secrets come from the
environment (the service's EnvironmentFile) and are never printed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import listen  # noqa: E402

STATE = ROOT / ".work" / "worker" / "jobs.json"
SETTINGS = ROOT / ".claude" / "vps-settings.json"
# the workflows taken; "Reel Factory: New Reel" ("Reel") joins once a person has watched its first live run (HANDOFF, 21 Oct 2026:
# it spends Flow credits)
STEPS = {listen.WORKFLOW: "Page Design", listen.ADD_SHOP: "Add Shop", listen.NEW_STORE: "New Store"}
POLL_SECONDS = 30          # how often n8n is asked for new requests
WAIT_EVERY = 300           # a command that waits for a person is run again every 5 minutes
WAIT_MINUTES = "4"         # ... and each run of it waits at most this long (store_job.py --minutes)
MAX_WAIT_DAYS = 7          # n8n's own Wait node gives up after 7 days too
CLAUDE_HOURS = 4           # one Claude turn may take this long (a whole store's pages), then it is stopped
FAILS_TO_STOP = 3
WAIT_LINE = re.compile(r"^DTJ_WAIT:\s*(.+?)\s*$", re.M)
WAIT_OK = re.compile(r"^python3? n8n/store-factory/store_job\.py (start|draft|copy|apps|installs|approve) ")
SHELL = re.compile(r"[;&|`$<>\\\n]")
RESUME_URL = re.compile(r"https?://\S*webhook-waiting/\S+")

HEADLESS = """You are running unattended on DTJ's VPS: n8n/store-factory/worker.py started you and nobody is at this computer.
Follow CLAUDE.md and the request below exactly, with these changes because you run alone:
- Every question, answer and yes happens in Telegram through the job's own commands (store_job.py and its Approve taps). Never
  ask anyone at this computer for anything and never wait for a login here.
- When a store_job.py command exits 3 (it waits for a person in Telegram), do not wait yourself and do not run it again: end your
  turn with this exact last line, the command exactly as you ran it:
  DTJ_WAIT: <the command>
  The worker runs it until the person answers, then resumes you with what it printed.
- A step that needs a person at a computer (a Shopify login, an install in the Dev Dashboard, a command the settings refuse): tell
  them in Telegram, leave that step, and say it in the n8n answer.
- At the end answer n8n yourself (reply.py, as the request says), also when the work stopped or is only partly done.

THE REQUEST
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def hide(text: str) -> str:
    """Resume links (they resume the n8n run) and token-like values out of every log line and message."""
    from setup_n8n import redact  # noqa: PLC0415
    return redact(RESUME_URL.sub("[resume link hidden]", str(text)))


def find_request(data) -> dict | None:
    """The "Request for Claude Code" node's output inside an execution, wherever n8n's answer puts it."""
    if isinstance(data, dict):
        if isinstance(data.get("instructions"), str) and isinstance(data.get("resume_url"), str):
            return data
        items = data.values()
    elif isinstance(data, list):
        items = data
    else:
        return None
    for v in items:
        hit = find_request(v)
        if hit:
            return hit
    return None


def wait_command(result: str) -> tuple[list[str] | None, str]:
    """The command Claude left with DTJ_WAIT, as an argv for this Python (never a shell), or (None, why it is refused)."""
    found = WAIT_LINE.findall(result or "")
    if not found:
        return None, ""
    line = found[-1].strip().strip("`")
    if SHELL.search(line) or not WAIT_OK.match(line):
        return None, f"refused DTJ_WAIT command (only store_job.py start/draft/copy/apps/installs/approve, no shell): {line[:200]}"
    argv = shlex.split(line)
    argv[0] = sys.executable
    if "--minutes" in argv:  # each look waits briefly; the worker comes back every WAIT_EVERY seconds
        i = argv.index("--minutes")
        argv[i + 1:i + 2] = [WAIT_MINUTES]
    else:
        argv += ["--minutes", WAIT_MINUTES]
    return argv, ""


class Worker:
    def __init__(self, *, call, run: Callable = subprocess.run, tell: Callable[[str], None] = lambda text: None,
                 environ=os.environ, state: Path = STATE, clock=time.time, sleep=time.sleep, out=print, settings: Path = SETTINGS,
                 claude: str = "claude"):
        self.call, self.run, self.tell, self.environ, self.path = call, run, tell, environ, state
        self.clock, self.sleep, self.out, self.settings, self.claude = clock, sleep, out, settings, claude
        self.s = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {"jobs": {}, "fails": 0, "stopped": ""}
        self.ids: dict[str, str] = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def log(self, run_id: str, text: str) -> None:
        f = self.path.parent / f"{run_id}.log"
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a", encoding="utf-8") as h:
            h.write(f"[{now_iso()}] {hide(text)}\n")

    def ready(self) -> str:
        """Why nothing may start ("" = ready): the API key and the spend cap are Harsh's to give."""
        if not self.environ.get("ANTHROPIC_API_KEY"):
            return ("ANTHROPIC_API_KEY is not set: an unattended Claude step runs on DTJ's Claude API key only, never on a "
                    "subscription login (CLAUDE.md rule 9)")
        try:
            if float(self.environ.get("DTJ_CLAUDE_MAX_USD", "")) <= 0:
                raise ValueError
        except ValueError:
            return "DTJ_CLAUDE_MAX_USD is not set: the most one request may spend on the Claude API (Harsh's number)"
        if not self.settings.exists():
            return f"{self.settings.name} is missing: what Claude may run on the VPS"
        return ""

    # ---- n8n
    def workflow_ids(self) -> dict[str, str]:
        if not self.ids:
            for name in STEPS:
                try:
                    self.ids[listen.find_workflow(self.call, name)] = name
                except listen.NotFound:
                    continue  # a workflow not on this n8n is simply not watched
        return self.ids

    def still_waiting(self, job: dict) -> bool:
        runs = listen.with_retry(lambda: listen.waiting(self.call, job["workflow_id"]), self.sleep)
        return any(str(r["id"]) == job["run"] for r in runs)

    def request(self, run_id: str, workflow_id: str, name: str) -> dict:
        got = self.call("get_workflow_execution", {"workflowId": workflow_id, "executionId": run_id, "includeData": True,
                                                   "nodeNames": [f"Request for Claude Code: {STEPS[name]}"]})
        req = find_request(got)
        if not req:
            raise RuntimeError(f"run {run_id} has no Request for Claude Code: {STEPS[name]} output")
        return req

    # ---- Claude
    def claude_turn(self, job: dict, prompt: str) -> None:
        argv = [self.claude, "-p", "--output-format", "json", "--permission-mode", "dontAsk", "--settings", str(self.settings),
                "--max-budget-usd", str(self.environ["DTJ_CLAUDE_MAX_USD"])]
        if job.get("session"):
            argv += ["--resume", job["session"]]
        job.update(state="running", turn_started=now_iso())
        self.save()
        self.log(job["run"], f"claude turn {job.get('turns', 0) + 1} started")
        try:
            done = self.run(argv, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT),
                            env=dict(self.environ), timeout=CLAUDE_HOURS * 3600)
            res = json.loads((done.stdout or "").strip().splitlines()[-1]) if (done.stdout or "").strip() else {}
        except subprocess.TimeoutExpired:
            return self.failed(job, f"Claude ran longer than {CLAUDE_HOURS} hours and was stopped")
        except ValueError:
            res = {}
        job["turns"] = job.get("turns", 0) + 1
        job["session"] = res.get("session_id") or job.get("session")
        if isinstance(res.get("total_cost_usd"), (int, float)):  # Claude Code's own figure for this turn
            job["cost_usd"] = round(job.get("cost_usd", 0) + res["total_cost_usd"], 4)
        text = str(res.get("result") or "")
        self.log(job["run"], f"claude turn ended ({res.get('subtype') or 'no result'}): {text[-1500:]}")
        if not res or res.get("is_error"):
            why = str(res.get("subtype") or (done.stderr or "")[-300:] or "no answer from Claude Code")
            return self.failed(job, f"Claude Code stopped: {why}")
        argv_wait, refused = wait_command(text)
        if refused:
            return self.failed(job, refused)
        if argv_wait:
            job.update(state="waiting", wait=argv_wait, wait_since=job.get("wait_since") or now_iso(), next_look=self.clock() + WAIT_EVERY)
            self.save()
            return None
        if self.still_waiting(job):
            return self.failed(job, "Claude Code ended without answering the n8n run")
        job.update(state="done", done_at=now_iso())
        job.pop("wait", None)
        self.s["fails"] = 0
        self.save()
        self.out(f"run {job['run']}: done ({job.get('cost_usd', 0)} USD by Claude Code's own count)")
        return None

    def failed(self, job: dict, why: str) -> None:
        job.update(state="failed", why=hide(why)[:500], failed_at=now_iso())
        self.s["fails"] = self.s.get("fails", 0) + 1
        msg = f"Store factory worker: {job['workflow']} run {job['run']} failed: {hide(why)[:300]}"
        if self.s["fails"] >= FAILS_TO_STOP:
            self.s["stopped"] = f"{self.s['fails']} failures in a row (last: run {job['run']})"
            msg += f"\nThat is {self.s['fails']} in a row: no new request starts until someone runs worker.py --retry or restarts it."
        self.save()
        self.log(job["run"], f"failed: {why}")
        self.tell(msg)
        self.out(msg)

    # ---- one round
    def start_next(self) -> bool:
        if self.s.get("stopped"):
            return False
        ids = self.workflow_ids()
        if not ids:
            return False
        hit = listen.offer_next(self.call, list(ids), self.path.parent / "offered.json", self.sleep, names=dict(ids))
        if not hit:
            return False
        name = ids[hit["workflow_id"]]
        job = {"run": hit["execution_id"], "workflow_id": hit["workflow_id"], "workflow": name, "started": now_iso(), "state": "new"}
        self.s["jobs"][job["run"]] = job
        self.save()
        try:
            req = self.request(job["run"], job["workflow_id"], name)
        except Exception as exc:  # noqa: BLE001 - n8n's answer had no request: said, the run stays for a person
            self.failed(job, f"could not read the request: {exc}")
            return True
        self.out(f"run {job['run']} ({name}): started")
        self.claude_turn(job, HEADLESS + req["instructions"])
        return True

    def look_at_waits(self) -> None:
        for job in [j for j in self.s["jobs"].values() if j.get("state") == "waiting"]:
            if self.clock() < job.get("next_look", 0):
                continue
            since = datetime.strptime(job["wait_since"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - since).days >= MAX_WAIT_DAYS:
                self.failed(job, f"nobody answered in Telegram for {MAX_WAIT_DAYS} days")
                continue
            try:
                done = self.run(job["wait"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT),
                                env=dict(self.environ), timeout=int(WAIT_MINUTES) * 60 + 120)
                code, printed = done.returncode, (done.stdout or "") + (done.stderr or "")
            except subprocess.TimeoutExpired:
                code, printed = 3, ""
            if code == 3:  # still waiting for the person
                job["next_look"] = self.clock() + WAIT_EVERY
                self.save()
                continue
            shown = " ".join(shlex.quote(a) for a in ["python", *job["wait"][1:]])
            self.log(job["run"], f"the person answered: {shown} exited {code}")
            job.pop("wait_since", None)
            self.claude_turn(job, f"The command you were waiting on has finished.\n$ {shown}\nexit {code}\n{printed[-4000:]}\n"
                                  "Continue the request from here, under the same rules.")

    def round(self) -> None:
        self.look_at_waits()
        self.start_next()

    def serve(self) -> int:
        why = self.ready()
        if why:
            self.out(f"not started: {why}")
            return 2
        while True:
            try:
                self.round()
            except listen.Failed as exc:
                self.out(hide(f"n8n did not answer 3 times: {exc}; trying again in {POLL_SECONDS * 4} s"))
                self.sleep(POLL_SECONDS * 3)
            self.sleep(POLL_SECONDS)

    def status(self) -> str:
        jobs = sorted(self.s["jobs"].values(), key=lambda j: j.get("started", ""))
        lines = [f"stopped: {self.s['stopped']}" if self.s.get("stopped") else "running"]
        for j in jobs[-30:]:
            extra = {"waiting": f"for a person since {j.get('wait_since')}", "failed": j.get("why", ""),
                     "done": f"{j.get('cost_usd', 0)} USD"}.get(j.get("state"), "")
            lines.append(f"run {j['run']} {j['workflow']}: {j.get('state')} {extra}".rstrip())
        return "\n".join(lines)

    def retry(self, run_id: str) -> int:
        job = self.s["jobs"].get(str(run_id))
        if not job:
            self.out(f"no run {run_id} in the worker's list")
            return 1
        listen.forget(self.path.parent / "offered.json", str(run_id))
        del self.s["jobs"][str(run_id)]
        self.s.update(fails=0, stopped="")
        self.save()
        self.out(f"run {run_id} will be taken again on the next round")
        return 0


def _tell(text: str) -> None:
    """The admin chat in Telegram (DTJ_ADMIN_CHAT), through the DTJ bot."""
    token, chat = os.environ.get("DTJ_TELEGRAM_BOT_TOKEN", ""), os.environ.get("DTJ_ADMIN_CHAT", "")
    if not (token and chat):
        return
    sys.path.insert(0, str(ROOT / "services" / "store-builder"))
    from page_builder.progress import _post  # noqa: PLC0415
    _post(f"https://api.telegram.org/bot{token}/sendMessage", {"chat_id": chat, "text": text[:3900]})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--retry", metavar="RUN")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from n8n_mcp import call  # noqa: PLC0415
    w = Worker(call=call, tell=_tell)
    if a.status:
        print(w.status())
        return 0
    if a.retry:
        return w.retry(a.retry)
    if a.once:
        why = w.ready()
        if why:
            print(f"not started: {why}")
            return 2
        w.round()
        return 0
    return w.serve()


if __name__ == "__main__":
    raise SystemExit(main())
