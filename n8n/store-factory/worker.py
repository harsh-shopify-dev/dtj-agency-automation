"""The store factory's worker on DTJ's VPS (Harsh, 22 Oct 2026: "the n8n triggers it and same for the claude"; 23 Oct 2026: "there
will be a person watching it, its just because i dont have to tell you here to listen for the call"). n8n leaves every AI step as
a waiting run ("Request for Claude Code: <step>"); this service takes each one within a minute, asks in Telegram who is watching,
and once that person taps Start it runs Claude Code on it, answered the way a laptop session answered it. The person follows and
answers in Telegram (the job's questions, Approve taps and progress bar); nobody has to tell a laptop session to listen.

    python n8n/store-factory/worker.py              run as a service (tools/vps/dtj-worker.service)
    python n8n/store-factory/worker.py --once       one round: look at what waits for a person, start one new request, exit
    python n8n/store-factory/worker.py --status     every run it holds: running, waiting for a person, done, failed
    python n8n/store-factory/worker.py --retry 993  run a failed request again from the start (also lifts a stop)

How a request runs:
1. A run of a watched workflow waits at its "Wait for Claude Code" node; the worker reads the request (instructions, resume link).
2. Attended (the default, DTJ_WORKER_MODE=attended): the worker asks in Telegram "tap Start if you are watching"; nothing starts
   without that tap, whose name is recorded. Claude Code then runs in this repo (`claude -p`) on this machine's own Claude login,
   which CLAUDE.md rule 9 allows because a person is watching. Unattended (DTJ_WORKER_MODE=api, only if Harsh switches it on):
   no tap, Claude Code in --bare mode on ANTHROPIC_API_KEY only, capped at DTJ_CLAUDE_MAX_USD a request. Either way Claude may
   only run what .claude/vps-settings.json allows; anything else is refused.
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
import threading
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
MCP = ROOT / "tools" / "vps" / "mcp.json"  # n8n's MCP server (the repo's .mcp.json is not in git); the token from the environment
# the workflows taken; "Reel Factory: New Reel" ("Reel", Harsh 25 Oct 2026: "create the full n8n ai workflow and use claude on VPS")
# is watched only when the reel bot's token is set (DTJ_REEL_BOT_TOKEN): its Start tap and questions go through that bot
STEPS = {listen.WORKFLOW: "Page Design", listen.ADD_SHOP: "Add Shop", listen.NEW_STORE: "New Store", listen.REEL: "Reel"}
REEL_BOT = "DTJ_REEL_BOT_TOKEN"
POLL_SECONDS = 30          # how often n8n is asked for new requests
WAIT_EVERY = 300           # a command that waits for a person is run again every 5 minutes
WAIT_MINUTES = "0.2"       # ... and each run of it only looks (store_job.py --minutes): the loop never stops on one job
PARALLEL = 2               # Claude sessions at the same time (DTJ_WORKER_PARALLEL); more Start taps wait their turn, and say so
MAX_WAIT_DAYS = 7          # n8n's own Wait node gives up after 7 days too
CLAUDE_HOURS = 4           # one Claude turn may take this long (a whole store's pages), then it is stopped
FAILS_TO_STOP = 3
TIDY_ROUNDS = 10           # every 10 rounds (about 5 minutes) a Start question whose n8n run was answered elsewhere is closed
WAIT_LINE = re.compile(r"^DTJ_WAIT:\s*(.+?)\s*$", re.M)
WAIT_OK = re.compile(r"^python3? n8n/(store-factory/(store_job\.py (start|draft|copy|apps|installs|approve|pages|menus)|page_questions\.py)"
                     r"|reel-factory/reel_job\.py (plan|pictures|final|person)) ")
SHELL = re.compile(r"[;&|`$<>\\\n]")
RESUME_URL = re.compile(r"https?://\S*webhook-waiting/\S+")

HEADLESS = """You run on DTJ's VPS: n8n/store-factory/worker.py started you. {watch}
Follow CLAUDE.md and the request below exactly, with these changes because nobody is at this computer:
- Every question, answer and yes happens in Telegram through the job's own commands (store_job.py and its Approve taps). Never
  ask anyone at this computer for anything and never wait for a login here.
- When a store_job.py, page_questions.py or reel_job.py command exits 3 (it waits for a person in Telegram), do not wait yourself and do not run it again: end your
  turn with this exact last line, the command exactly as you ran it:
  DTJ_WAIT: <the command>
  The worker runs it until the person answers, then resumes you with what it printed.
- A step that needs a person at a computer (a Shopify login, an install in the Dev Dashboard, a command the settings refuse): tell
  them in Telegram, leave that step, and say it in the n8n answer.
- At the end answer n8n yourself (reply.py, as the request says), also when the work stopped or is only partly done.
- A HANDOFF entry the request asks for goes to .work/handoff/<date>-run-<n8n run>.md (not docs/HANDOFF.md: the laptop merges these
  into git). Files you make go under /home/ai/dtj-agency-automation/.work/ (use that full path).

THE REQUEST
"""
# a person's message about a finished page (Harsh, 24 Oct 2026: "once we build the page i can also chat with you there"): it
# continues the page's own Claude session; a reply to any message that ends "(job page-<brief>, answer chat)" lands here
CHAT_JOB = re.compile(r"^page-(\d{1,9})$")
CHAT = """{name} wrote in Telegram about the page of brief {brief}: "{text}"
Do it now, on this page only, the way you built it (CLAUDE.md and the factory's rules still apply):
- Change the page's own files under /home/ai/dtj-agency-automation/.work/clients/n8n-{brief}-*/ (facts.json, brand.json,
  copy-answer.json, pictures with provision.gallery_photos / gallery_compose); never hand-edit template.json; every fact keeps its
  source, and samples stay marked SAMPLE.
- Rebuild and write the DRAFT with the same page_builder.ship_draft command as before (draft theme only), then look at the result.
- Before a long step (a rebuild, new pictures) tell {name}: python n8n/store-factory/page_chat.py --brief {brief} --chat {chat} --say
  "Working on it: <the step>, about <N> minutes". When done, the same command with what changed in plain words and the preview link.
- Anything beyond this page's draft (the product itself or its gallery, the store's settings or menus, the live theme, publishing,
  an app release) needs {name}'s clear yes in Telegram, by name: when this message is not that yes, ask with page_chat.py and stop.
- A question you need answered: ask with page_chat.py and end your turn; the answer comes back as the next message.
- A message about something else (another product, a whole store, a question): change nothing; answer it with page_chat.py in plain
  words: what you can do from here, and what starts it (a product link sent to the bot starts a page; a store's link starts a whole
  store, with its questions here).
"""
WATCHED = "{name} tapped Start in Telegram and is watching the job there (its questions, Approve taps and progress bar)."
ALONE = "Nobody is watching: every yes still comes only through the job's Approve taps in Telegram."
MODES = ("attended", "api")


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
        return None, (f"refused DTJ_WAIT command (only store_job.py start/draft/copy/apps/installs/approve/pages/menus, page_questions.py or "
                      f"reel_job.py plan/pictures/final/person, "
                      f"no shell): {line[:200]}")
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
                 claude: str = "claude", asker: Callable | None = None, threaded: bool = False, replier: Callable | None = None,
                 read_answers: Callable | None = None, read_chats: Callable | None = None, say: Callable | None = None):
        self.call, self.run, self.tell, self.environ, self.path = call, run, tell, environ, state
        # each Claude session in its own thread, so the loop keeps asking Start for new requests and looking at waits (Harsh,
        # 23 Oct 2026: brief 10 showed nothing while brief 9 was being designed); False = one after another (tests)
        self.threaded, self.lock = threaded, threading.RLock()
        self.procs: dict[str, subprocess.Popen] = {}  # the Claude session of each running job, so Stop can end it
        # every Start question and Stop button of a round reads ONE copy of the recent answers (23 Oct 2026: a read per question
        # made n8n answer 429 Too Many Requests, and a Start tap went unseen)
        self._answers: list | None = None
        self.read_answers = read_answers or _read_answers
        self.replier = replier or _reply
        self.read_chats, self.say = read_chats or _read_chats, say or _say
        try:
            self.parallel = max(1, int(environ.get("DTJ_WORKER_PARALLEL") or PARALLEL))
        except ValueError:
            self.parallel = PARALLEL
        self.mode = str(environ.get("DTJ_WORKER_MODE") or "attended").strip().lower()
        self.asker = asker or _asker
        self.clock, self.sleep, self.out, self.settings, self.claude = clock, sleep, out, settings, claude
        self.s = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {"jobs": {}, "fails": 0, "stopped": ""}
        self.ids: dict[str, str] = {}

    def save(self) -> None:
        with self.lock:
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
        """Why nothing may start ("" = ready). Attended: the bot and a chat to ask who watches. Unattended (api): the API key and the
        spend cap, both Harsh's to give."""
        if self.mode not in MODES:
            return f"DTJ_WORKER_MODE must be one of {', '.join(MODES)}"
        if not self.settings.exists():
            return f"{self.settings.name} is missing: what Claude may run on the VPS"
        if self.mode == "attended":
            if not (self.environ.get("DTJ_TELEGRAM_BOT_TOKEN") and self.environ.get("DTJ_ADMIN_CHAT")):
                return "DTJ_TELEGRAM_BOT_TOKEN and DTJ_ADMIN_CHAT are needed: the worker asks in Telegram who is watching"
            return ""
        if not self.environ.get("ANTHROPIC_API_KEY"):
            return ("ANTHROPIC_API_KEY is not set: an unattended Claude step runs on DTJ's Claude API key only, never on a "
                    "subscription login (CLAUDE.md rule 9)")
        try:
            if float(self.environ.get("DTJ_CLAUDE_MAX_USD", "")) <= 0:
                raise ValueError
        except ValueError:
            return "DTJ_CLAUDE_MAX_USD is not set: the most one request may spend on the Claude API (Harsh's number)"
        return ""

    # ---- n8n
    def workflow_ids(self) -> dict[str, str]:
        if not self.ids:
            for name in STEPS:
                if name == listen.REEL and not self.environ.get(REEL_BOT):
                    continue  # no reel bot yet: reel requests stay waiting in n8n until it is set
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
        """One Claude turn: in its own thread when the worker runs as the service (the loop goes on meanwhile)."""
        with self.lock:
            job.update(state="running", turn_started=now_iso())
            self.save()
        if self.threaded:
            threading.Thread(target=self._turn, args=(job, prompt), name=f"run-{job['run']}", daemon=True).start()
        else:
            self._turn(job, prompt)

    def _turn(self, job: dict, prompt: str) -> None:
        env = dict(self.environ)
        if self.mode == "api":
            # --bare: Anthropic auth is strictly ANTHROPIC_API_KEY, the subscription login on this machine is never read (rule 9,
            # made sure by Claude Code itself); --bare skips CLAUDE.md discovery, so the rulebook is handed in explicitly
            argv = [self.claude, "-p", "--bare", "--output-format", "json", "--permission-mode", "dontAsk", "--settings",
                    str(self.settings), "--append-system-prompt-file", str(ROOT / "CLAUDE.md"),
                    "--max-budget-usd", str(self.environ["DTJ_CLAUDE_MAX_USD"]), "--mcp-config", str(MCP)]
        else:
            # attended: this machine's own Claude login (a person tapped Start and watches); an API key in the environment is not
            # passed on, so the login is what runs (Harsh, 23 Oct 2026: no API key for this)
            env.pop("ANTHROPIC_API_KEY", None)
            argv = [self.claude, "-p", "--output-format", "json", "--permission-mode", "dontAsk", "--settings", str(self.settings),
                    "--mcp-config", str(MCP)]
        if job.get("session"):
            argv += ["--resume", job["session"]]
        self.log(job["run"], f"claude turn {job.get('turns', 0) + 1} started")
        done = None
        try:
            done = self._claude(job, argv, prompt, env)
            if job.get("state") == "stopped":  # a person tapped Stop while it ran: already answered and said
                return None
            res = json.loads((done.stdout or "").strip().splitlines()[-1]) if (done.stdout or "").strip() else {}
        except subprocess.TimeoutExpired:
            with self.lock:
                return self.failed(job, f"Claude ran longer than {CLAUDE_HOURS} hours and was stopped")
        except ValueError:
            res = {}
        with self.lock:
            return self._after(job, res, done)

    def _claude(self, job: dict, argv: list, prompt: str, env: dict):
        """Claude Code as a process the Stop button can end (the service); an injected `run` in tests."""
        if self.run is not subprocess.run:
            return self.run(argv, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT),
                            env=env, timeout=CLAUDE_HOURS * 3600)
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace", cwd=str(ROOT), env=env)
        self.procs[job["run"]] = proc
        try:
            out, err = proc.communicate(prompt, timeout=CLAUDE_HOURS * 3600)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise
        finally:
            self.procs.pop(job["run"], None)
        return subprocess.CompletedProcess(argv, proc.returncode, out, err)

    def _after(self, job: dict, res: dict, done) -> None:
        """What a finished turn means: a wait for a person, done (n8n answered), or failed."""
        job["turns"] = job.get("turns", 0) + 1
        job["session"] = res.get("session_id") or job.get("session")
        if isinstance(res.get("total_cost_usd"), (int, float)):  # Claude Code's own figure for this turn
            job["cost_usd"] = round(job.get("cost_usd", 0) + res["total_cost_usd"], 4)
        text = str(res.get("result") or "")
        self.log(job["run"], f"claude turn ended ({res.get('subtype') or 'no result'}): {text[-1500:]}")
        chat = job.pop("chat_turn", None)
        if chat:  # a page chat turn: the session answered in Telegram itself; its n8n run was answered long ago
            if not res or res.get("is_error"):
                why = str(res.get("result") or res.get("subtype") or "no answer from Claude Code")[:300]
                self.say(chat["chat"], chat["brief"], f"I could not finish that change: {why}")
            job["state"] = "done"
            self.save()
            return None
        if not res or res.get("is_error"):
            # Claude Code's own words first (22 Oct 2026, a test run: is_error with subtype "success" and the result "Not logged in")
            why = str(res.get("result") or res.get("subtype") or ((done.stderr or "")[-300:] if done else "") or "no answer from Claude Code")
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
        job["chat"] = chat_of(req) or str(self.environ.get("DTJ_ADMIN_CHAT") or "")
        job["brief"] = brief_of(req)  # a page's chat finds its session by the brief number
        if self.mode == "api":
            self.begin(job, req, "")
            return True
        job["state"] = "asking"
        self.save()
        self.watch(job, req)
        return True

    def watch(self, job: dict, req: dict | None = None) -> None:
        """The attended gate: "tap Start if you are watching", asked once in the request's chat (else the admin chat); Claude starts
        when someone taps it, never before. Looked at once a round, so nothing else waits for it."""
        ask = self._ask(job)
        what = {"New Store": "a whole store", "Add Shop": "a new shop", "Page Design": "a product page", "Reel": "a reel"}.get(STEPS[job["workflow"]],
                                                                                                          "a request")
        got = ask.choose("watch", f"New request for {what} (n8n run {job['run']}). Claude starts on DTJ's VPS as soon as the person "
                                  "who will watch it taps Start. You follow it here: its questions, the Approve taps and the "
                                  "progress bar.", [("Start: I'm watching", "start")], 0)
        if not got:
            return
        job["watched_by"] = got.get("by") or "a teammate"
        self.log(job["run"], f"Start tapped by {job['watched_by']}")
        busy = [j for j in self.s["jobs"].values() if j.get("state") == "running"]
        if self.full(job):
            job["state"] = "queued"
            self.save()
            ask.tell(f"Queued: {what} starts as soon as one of the {len(busy)} jobs running now is done. I tell you here when it starts.")
            return
        # say it started and what comes, not only "Noted" (Harsh, 23 Oct 2026: "i should get a progress bar or some updates in between
        # as i will not understand whats happening")
        ask.tell(f"Started: Claude is working on {what} on DTJ's server, watched by {job['watched_by']}. A progress bar follows here "
                 "and moves at every step; questions and Approve buttons come here too. Nothing to do for you until then.")
        # a way out at any time (Harsh, 23 Oct 2026: "i sent this command but it should have stopped i guess", after /stop)
        ask.ask("stop", "To stop this job at any time, tap Stop. Claude stops at once and n8n is told who stopped it.",
                [("Stop this job", "stop")])
        self.begin(job, req or self.request(job["run"], job["workflow_id"], job["workflow"]), job["watched_by"])

    def begin(self, job: dict, req: dict, watcher: str) -> None:
        self.out(f"run {job['run']} ({job['workflow']}): started" + (f", watched by {watcher}" if watcher else ""))
        watch = WATCHED.format(name=watcher) if watcher else ALONE
        self.claude_turn(job, HEADLESS.format(watch=watch) + req["instructions"])

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
                                env=dict(self.environ), timeout=float(WAIT_MINUTES) * 60 + 120)
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

    def look_at_chats(self) -> None:
        """A person's messages about a finished page: each continues that page's Claude session, one turn at a time per page."""
        try:
            rows = self.read_chats()
        except Exception as exc:  # noqa: BLE001 - n8n did not answer: the next round reads again
            self.out(f"page chat: could not read the messages ({exc})")
            rows = []
        seen = self.s.setdefault("chat_seen", [])
        new = False
        for row in sorted(rows, key=lambda r: int(r.get("id") or 0)):
            rid, m = str(row.get("id")), CHAT_JOB.match(str(row.get("job") or ""))
            text = str(row.get("value") or "").strip()
            if rid in seen or not m or row.get("key") != "chat" or not text:
                continue
            seen.append(rid)
            new = True
            msg = {"brief": m.group(1), "text": text[:1500], "by": str(row.get("by") or "someone"), "chat": str(row.get("chat_id") or "")}
            job = self.page_job(msg["brief"])
            if not job:
                self.say(msg["chat"], msg["brief"], f"I have no page session for brief {msg['brief']} on DTJ's server, so I cannot "
                                                    "change it from here. Ask Harsh.")
                continue
            job.setdefault("chat_queue", []).append(msg)
            self.log(job["run"], f"page chat from {msg['by']}: {msg['text'][:200]}")
        if new:
            del seen[:-500]
            self.save()
        for job in [j for j in self.s["jobs"].values() if j.get("chat_queue")]:
            if job.get("state") in ("running", "waiting", "asking", "queued"):
                continue  # one turn at a time per page: the next message waits for this one
            if len([j for j in self.s["jobs"].values() if j.get("state") == "running"]) >= self.parallel:
                return
            msg = job["chat_queue"].pop(0)
            job["chat_turn"] = msg
            self.say(msg["chat"], msg["brief"], f"Got it, {msg['by']}: working on it now. I answer here when the page is updated.")
            self.claude_turn(job, CHAT.format(name=msg["by"], brief=msg["brief"], text=msg["text"].replace('"', "'"), chat=msg["chat"]))

    def page_job(self, brief: str) -> dict | None:
        """The newest job of that brief with a Claude session to continue."""
        jobs = [j for j in self.s["jobs"].values() if str(j.get("brief") or "") == str(brief) and j.get("session")]
        return max(jobs, key=lambda j: j.get("started", ""), default=None)

    def look_at_queue(self) -> None:
        """A queued job (Start tapped, every slot busy) begins when a slot is free, the oldest first."""
        queued = sorted((j for j in self.s["jobs"].values() if j.get("state") == "queued"), key=lambda j: j.get("started", ""))
        for job in queued:
            if self.full(job):
                continue
            try:
                ask = self._ask(job)
                ask.tell(f"Starting now (n8n run {job['run']}), watched by {job.get('watched_by') or 'a teammate'}.")
                self.begin(job, self.request(job["run"], job["workflow_id"], job["workflow"]), job.get("watched_by") or "")
            except Exception as exc:  # noqa: BLE001 - n8n or Telegram did not answer: the next round tries again
                self.log(job["run"], f"could not start from the queue: {exc}")

    def look_at_starts(self) -> None:
        for job in [j for j in self.s["jobs"].values() if j.get("state") == "asking"]:
            try:
                self.watch(job)
            except Exception as exc:  # noqa: BLE001 - n8n or Telegram did not answer: the next round asks again
                self.log(job["run"], f"could not look at the Start tap: {exc}")

    def rows(self, job: str) -> list:
        """This round's answers for one job (the bot's dtj_bot_answers rows), read once per round for every job."""
        if self._answers is None:
            try:
                self._answers = self.read_answers()
            except Exception as exc:  # noqa: BLE001 - n8n did not answer: no answers this round, the next one reads again
                self.out(hide(f"answers not read this round: {exc}"))
                self._answers = []
        return [r for r in self._answers if r.get("job") == job]

    def is_reel(self, job: dict) -> bool:
        return STEPS.get(job.get("workflow", "")) == "Reel"

    def full(self, job: dict) -> bool:
        """No free slot for this job: every slot busy, or (a reel) another reel runs (one Flow browser on the VPS)."""
        running = [j for j in self.s["jobs"].values() if j.get("state") == "running"]
        return len(running) >= self.parallel or (self.is_reel(job) and any(self.is_reel(j) for j in running))

    def _ask(self, job: dict):
        # a reel's Start / Stop taps go through the reel bot (job ids "wr<run>"; _asker picks the bot by that prefix)
        return self.asker(f"{'wr' if self.is_reel(job) else 'w'}{job['run']}"[:24], job["chat"], job.setdefault("ask", {"asked": {}, "answers": {}}), self.save,
                          rows=self.rows)

    def look_at_stops(self) -> None:
        for job in [j for j in self.s["jobs"].values() if j.get("state") in ("running", "waiting", "queued") and j.get("ask")]:
            try:
                ask = self._ask(job)
                got = ask.answer("stop")
            except Exception:  # noqa: BLE001 - n8n did not answer: the next round looks again
                continue
            if got:
                self.stop(job, got.get("by") or "a teammate", ask)

    def stop(self, job: dict, by: str, ask=None) -> None:
        """A person tapped Stop: Claude ends, n8n hears the run was stopped (nothing more is done), the person hears it."""
        with self.lock:
            job.update(state="stopped", why=f"stopped by {by} in Telegram", stopped_at=now_iso())
            job.pop("wait", None)
            self.save()
        proc = self.procs.get(job["run"])
        if proc and proc.poll() is None:
            proc.kill()
        self.log(job["run"], f"stopped by {by}")
        try:
            sent = self.replier(self.request(job["run"], job["workflow_id"], job["workflow"]), f"Stopped by {by} in Telegram.")
        except Exception as exc:  # noqa: BLE001 - n8n did not take the answer: its own Wait node ends the run later
            sent = f"n8n was not told ({str(exc)[:120]})"
        if ask:
            ask.tell(f"Stopped by {by}: Claude has stopped and nothing more is done for this job. {sent}")

    def round(self) -> None:
        self._answers = None  # a fresh read of the answers, at most once this round
        self.read_inbox()
        self.rounds = getattr(self, "rounds", 0) + 1
        if self.rounds % TIDY_ROUNDS == 1:
            self.tidy()
        self.look_at_stops()
        self.look_at_queue()
        self.look_at_starts()
        self.look_at_waits()
        self.look_at_chats()
        self.start_next()

    def after_restart(self) -> None:
        """Jobs a restart stopped mid-turn (the service's Claude sessions stop with it): said, never counted as failures."""
        for job in [j for j in self.s["jobs"].values() if j.get("state") == "running"]:
            job.update(state="interrupted", why="the worker restarted while Claude was working on it")
            self.tell(f"Store factory worker: {job['workflow']} run {job['run']} was stopped by a restart of the worker. "
                      f"python n8n/store-factory/worker.py --retry {job['run']} runs it again.")
        self.save()

    def serve(self) -> int:
        why = self.ready()
        if why:
            self.out(f"not started: {why}")
            return 2
        self.after_restart()
        while True:
            try:
                self.round()
            except listen.Failed as exc:
                self.out(hide(f"n8n did not answer 3 times: {exc}; trying again in {POLL_SECONDS * 4} s"))
                self.sleep(POLL_SECONDS * 3)
            self.sleep(POLL_SECONDS)

    def status(self) -> str:
        jobs = sorted(self.s["jobs"].values(), key=lambda j: j.get("started", ""))
        lines = [(f"stopped: {self.s['stopped']}" if self.s.get("stopped") else "running") + f" ({self.mode})"]
        for j in jobs[-30:]:
            extra = {"waiting": f"for a person since {j.get('wait_since')}", "failed": j.get("why", ""), "asking": "for a Start tap",
                     "queued": "Start tapped, waiting for a free slot", "interrupted": j.get("why", ""), "stopped": j.get("why", ""),
                     "closed": j.get("why", ""),
                     "done": f"watched by {j['watched_by']}" if j.get("watched_by") else f"{j.get('cost_usd', 0)} USD"}.get(j.get("state"), "")
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

    @property
    def inbox(self) -> Path:
        return self.path.parent / "inbox.jsonl"

    def send(self, command: dict) -> int:
        """A command for the running service (23 Oct 2026: --retry edited jobs.json under the service, whose own copy wrote the old
        jobs back): it is applied at the start of the service's next round, within about 30 seconds."""
        self.inbox.parent.mkdir(parents=True, exist_ok=True)
        with self.inbox.open("a", encoding="utf-8") as f:
            f.write(json.dumps(command) + "\n")
        self.out(f"sent to the worker service: {json.dumps(command)} (applied within about {POLL_SECONDS} s)")
        return 0

    def read_inbox(self) -> None:
        if not self.inbox.exists():
            return
        lines = self.inbox.read_text(encoding="utf-8").splitlines()
        self.inbox.unlink()
        for line in lines:
            try:
                cmd = json.loads(line)
            except ValueError:
                continue
            if cmd.get("retry"):
                self.retry(str(cmd["retry"]))
            page = cmd.get("page") or {}
            if page.get("run") and str(page["run"]) in self.s["jobs"]:  # a run from before jobs kept their brief (brief 12, run 1421)
                self.s["jobs"][str(page["run"])]["brief"] = str(page.get("brief") or "")
                self.save()

    def tidy(self) -> None:
        """Start questions and queued jobs whose n8n run no longer waits (answered elsewhere) are closed: nothing more is asked."""
        for job in [j for j in self.s["jobs"].values() if j.get("state") in ("asking", "queued")]:
            try:
                if not self.still_waiting(job):
                    job.update(state="closed", why="its n8n run was answered elsewhere")
                    self.log(job["run"], "closed: the n8n run no longer waits")
            except Exception:  # noqa: BLE001 - n8n did not answer: the next tidy looks again
                continue
        self.save()


def brief_of(req: dict) -> str:
    """The brief (dtj_client_intake row) a page request is for, when the request names one."""
    inner = req.get("request") if isinstance(req.get("request"), dict) else {}
    v = str(inner.get("row_id") or "")
    return v if re.fullmatch(r"\d{1,9}", v) else ""


def chat_of(req: dict) -> str:
    """The Telegram chat the request came from (the person who sent the link), when the request names one."""
    inner = req.get("request") if isinstance(req.get("request"), dict) else {}
    for v in (inner.get("telegram_chat_id"), inner.get("chat_id"), req.get("telegram_chat_id")):
        if re.fullmatch(r"-?\d{3,20}", str(v or "")):
            return str(v)
    return ""


STOPPED = {"page_design": {"page_status": "could not build"}, "new_store": {"store_status": "partly done"},
           "add_shop": {"shop_status": "could not add"}, "reel": {"reel_status": "could not make"}}


def _reply(req: dict, note: str) -> str:
    """Answer a stopped job's n8n run with reply.py (the resume link only on its command line, never in a file)."""
    import tempfile  # noqa: PLC0415
    body = dict(STOPPED.get(str(req.get("claude_code_stage") or ""), {}), note=note)
    if len(body) < 2:
        return "n8n was not told (unknown step)"
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "stopped.json"
        f.write_text(json.dumps(body), encoding="utf-8")
        done = subprocess.run([sys.executable, str(HERE / "reply.py"), "--resume-url", req["resume_url"], "--body", str(f)],
                              capture_output=True, text=True, timeout=120, cwd=str(ROOT))
    return "n8n has the answer." if done.returncode == 0 else "n8n was not told (reply.py failed)."


def _asker(job: str, chat: str, state: dict, save: Callable[[], None], rows: Callable | None = None):
    """The store job's own Telegram questions (bot_ask.Asker: the bot's buttons, answers through n8n's dtj_bot_answers)."""
    import store_job  # noqa: PLC0415
    from bot_ask import Asker  # noqa: PLC0415
    token = os.environ.get(REEL_BOT, "") if job.startswith("wr") else store_job._token()
    return Asker(job, chat, send=store_job._sender(token), rows=rows or store_job._rows, state=state, save=save,
                 add_row=store_job._add_row)


def _read_answers() -> list:
    """The worker's own answers of the last 8 days (Start and Stop taps: jobs w<run>), in one read."""
    from datetime import timedelta  # noqa: PLC0415
    import store_job  # noqa: PLC0415
    from n8n_mcp import call  # noqa: PLC0415
    from setup_n8n import table_rows  # noqa: PLC0415
    table = store_job.answers_table()
    if not table:
        return []
    since = (datetime.now(timezone.utc) - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return table_rows(call, table, [{"columnName": "job", "condition": "like", "value": "w%"},
                                    {"columnName": "createdAt", "condition": "gte", "value": since}])


def _read_chats() -> list:
    """People's messages about finished pages (dtj_bot_answers rows "page-<brief>" / "chat") of the last 2 days, in one read."""
    from datetime import timedelta  # noqa: PLC0415
    import store_job  # noqa: PLC0415
    from n8n_mcp import call  # noqa: PLC0415
    from setup_n8n import table_rows  # noqa: PLC0415
    table = store_job.answers_table()
    if not table:
        return []
    since = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return table_rows(call, table, [{"columnName": "job", "condition": "like", "value": "page-%"},
                                    {"columnName": "createdAt", "condition": "gte", "value": since}])


def _say(chat: str, brief: str, text: str) -> None:
    """One message about a page in its chat (page_chat.py), ending with the reply line."""
    import page_chat  # noqa: PLC0415
    page_chat.send(chat, brief, text)


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
    ap.add_argument("--page", nargs=2, metavar=("RUN", "BRIEF"), help="link an older page run to its brief, for the page chat")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from n8n_mcp import call  # noqa: PLC0415
    w = Worker(call=call, tell=_tell, threaded=not a.once)
    if a.status:
        print(w.status())
        return 0
    if a.retry:
        return w.send({"retry": a.retry})
    if a.page:
        return w.send({"page": {"run": a.page[0], "brief": a.page[1]}})
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
