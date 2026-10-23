"""The VPS worker (worker.py) against a stand-in n8n, a stand-in Claude Code and stand-in store_job runs: what starts, what is
refused, how a wait for a person is kept without Claude, and how failures stop new starts. Nothing reaches n8n, Claude or Telegram.

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory -p "test_worker.py"
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import worker

NS = "WF-NS"
RESUME = "https://n8n.srv2048145.hstgr.cloud/webhook-waiting/993?signature=ab12"
ENV = {"DTJ_WORKER_MODE": "api", "ANTHROPIC_API_KEY": "sk-ant-test", "DTJ_CLAUDE_MAX_USD": "5"}  # unattended: only if Harsh switches it on
ATTENDED = {"DTJ_TELEGRAM_BOT_TOKEN": "bot-token", "DTJ_ADMIN_CHAT": "-100200", "ANTHROPIC_API_KEY": "sk-ant-should-not-pass"}


class N8n:
    def __init__(self):
        self.waiting = [{"id": "993", "status": "waiting", "startedAt": "2026-10-22T10:00:00.000Z", "workflowId": NS}]
        self.calls = []

    def __call__(self, tool, args):
        self.calls.append((tool, args))
        if tool == "search_workflows":
            return {"data": [{"id": NS, "name": "Store Factory: New Store"}] if args["query"] == "Store Factory: New Store" else []}
        if tool == "search_workflow_executions":
            return {"data": [r for r in self.waiting if r["workflowId"] == args["workflowId"]]}
        if tool == "get_workflow_execution":
            return {"execution": {"data": {"resultData": {"runData": {args["nodeNames"][0]: [{"data": {"main": [[{"json": {
                "claude_code_stage": "new_store", "resume_url": RESUME, "request": {"telegram_chat_id": "7051933055"},
                "instructions": f"DO THIS: store_job.py start ... then reply.py --resume-url \"{RESUME}\""}}]]}}]}}}}}
        raise AssertionError(tool)


class Runs:
    """subprocess.run stand-in: Claude Code answers from `claude`, store_job commands from `waits` (exit codes in order)."""

    def __init__(self, claude=(), waits=()):
        self.claude, self.waits, self.calls = list(claude), list(waits), []

    def __call__(self, argv, **kw):
        self.calls.append((argv, kw))
        if argv[0] == "claude":
            res = self.claude.pop(0)
            if res == "timeout":
                raise subprocess.TimeoutExpired(argv, 1)
            return subprocess.CompletedProcess(argv, 0, json.dumps(res) + "\n", "")
        code = self.waits.pop(0)
        return subprocess.CompletedProcess(argv, code, f"store_job printed {code}\n", "")


def result(text, session="s-1", cost=0.4, error=False):
    return {"type": "result", "subtype": "error_during_execution" if error else "success", "is_error": error, "result": text,
            "session_id": session, "total_cost_usd": cost}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.settings = self.tmp / "vps-settings.json"
        self.settings.write_text("{}", encoding="utf-8")
        self.n8n, self.told, self.printed, self.now = N8n(), [], [], [1000.0]

    def worker(self, runs, environ=ENV, asker=None):
        return worker.Worker(call=self.n8n, run=runs, tell=self.told.append, environ=dict(environ), state=self.tmp / "w" / "jobs.json",
                             clock=lambda: self.now[0], sleep=lambda s: None, out=self.printed.append, settings=self.settings,
                             asker=asker)


class Ready(Base):
    def test_unattended_never_starts_without_the_api_key_or_the_spend_cap(self):
        runs = Runs()
        api = {"DTJ_WORKER_MODE": "api"}
        self.assertIn("rule 9", self.worker(runs, {**api, "DTJ_CLAUDE_MAX_USD": "5"}).ready())
        self.assertIn("DTJ_CLAUDE_MAX_USD", self.worker(runs, {**api, "ANTHROPIC_API_KEY": "k"}).ready())
        self.assertIn("DTJ_CLAUDE_MAX_USD", self.worker(runs, {**api, "ANTHROPIC_API_KEY": "k", "DTJ_CLAUDE_MAX_USD": "0"}).ready())
        self.assertEqual(self.worker(runs).ready(), "")
        self.assertEqual(self.worker(runs, api).serve(), 2)
        self.assertEqual(runs.calls, [])

    def test_attended_is_the_default_and_needs_only_the_bot_to_ask_who_watches(self):
        runs = Runs()
        self.assertEqual(self.worker(runs, {}).mode, "attended")
        self.assertIn("who is watching", self.worker(runs, {}).ready())
        self.assertEqual(self.worker(runs, ATTENDED).ready(), "")  # no API key, no spend cap needed
        self.assertIn("must be one of", self.worker(runs, {"DTJ_WORKER_MODE": "auto"}).ready())


class Asker:
    """bot_ask.Asker stand-in: the Start question is sent once; `tapped` is who has tapped it (None = nobody yet)."""

    def __init__(self, shared):
        self.shared = shared

    def __call__(self, job, chat, state, save, rows=None):
        self.shared["made"].append((job, chat))
        self.shared.setdefault("rows", []).append(rows)
        return self

    def tell(self, text):
        self.shared.setdefault("told", []).append(text)

    def ask(self, key, text, options):
        self.shared.setdefault("offered", []).append((key, [o[0] for o in options]))

    def answer(self, key):
        return {"value": "stop", "by": self.shared["stopper"]} if key == "stop" and self.shared.get("stopper") else None

    def choose(self, key, text, options, minutes):
        if key not in self.shared["asked"]:
            self.shared["asked"].append(key)
            self.shared["texts"].append((text, [o[0] for o in options], minutes))
        who = self.shared["tapped"]
        return {"value": "start", "label": options[0][0], "by": who} if who else None


class Attended(Base):
    """Harsh, 23 Oct 2026: "there will be a person watching it": Claude starts only after a Start tap, on the machine's own login."""

    def test_claude_waits_for_the_start_tap_then_runs_on_the_login_with_the_watcher_named(self):
        shared = {"made": [], "asked": [], "texts": [], "tapped": None}
        runs = Runs(claude=[result("Done, answered n8n.")])
        w = self.worker(runs, ATTENDED, asker=Asker(shared))
        w.round()
        job = w.s["jobs"]["993"]
        self.assertEqual((job["state"], job["chat"]), ("asking", "7051933055"))  # asked in the chat the link came from
        self.assertEqual(runs.calls, [])  # nothing runs before the tap
        text, buttons, minutes = shared["texts"][0]
        self.assertIn("a whole store", text)
        self.assertEqual((buttons, minutes), (["Start: I'm watching", ], 0))  # never blocks the loop
        w.round()
        self.assertEqual(runs.calls, [])
        shared["tapped"] = "Riya"
        self.n8n.waiting = []
        w.round()
        argv, kw = runs.calls[0]
        self.assertNotIn("--bare", argv)  # the machine's own Claude login
        self.assertNotIn("--max-budget-usd", argv)
        self.assertEqual(argv[:7], ["claude", "-p", "--output-format", "json", "--permission-mode", "dontAsk", "--settings"])
        self.assertNotIn("ANTHROPIC_API_KEY", kw["env"])  # an API key in the environment is not passed on
        self.assertIn("Riya tapped Start in Telegram and is watching", kw["input"])
        self.assertIn("Started: Claude is working on a whole store on DTJ's server, watched by Riya. A progress bar follows",
                      shared["told"][0])
        self.assertEqual((job["state"], job["watched_by"]), ("done", "Riya"))
        self.assertEqual(shared["made"][0], ("w993", "7051933055"))
        self.assertIn("watched by Riya", w.status())

    def test_a_start_tap_with_every_slot_busy_is_queued_and_begins_when_one_is_free(self):
        shared = {"made": [], "asked": [], "texts": [], "tapped": "Riya"}
        runs = Runs(claude=[result("Done, answered n8n.")])
        w = self.worker(runs, {**ATTENDED, "DTJ_WORKER_PARALLEL": "1"}, asker=Asker(shared))
        w.s["jobs"]["900"] = {"run": "900", "workflow": "Store Factory: New Store", "workflow_id": NS, "state": "running", "started": "a"}
        w.round()
        job = w.s["jobs"]["993"]
        self.assertEqual(job["state"], "queued")
        self.assertEqual(runs.calls, [])
        self.assertIn("Queued: a whole store starts as soon as one of the 1 jobs running now is done", shared["told"][-1])
        self.assertIn("Start tapped, waiting for a free slot", w.status())
        w.s["jobs"]["900"]["state"] = "done"
        self.n8n.waiting = []
        w.round()
        self.assertIn("Starting now (n8n run 993), watched by Riya", " ".join(shared["told"]))
        self.assertEqual((job["state"], len(runs.calls)), ("done", 1))

    def test_one_read_of_the_answers_per_round_for_every_job(self):
        reads = []
        w = worker.Worker(call=self.n8n, run=Runs(), tell=self.told.append, environ=dict(ATTENDED), state=self.tmp / "r" / "jobs.json",
                          clock=lambda: self.now[0], sleep=lambda s: None, out=self.printed.append, settings=self.settings,
                          read_answers=lambda: reads.append(1) or [{"job": "w1", "key": "watch"}, {"job": "w2", "key": "stop"}])
        w.round()
        self.assertEqual(([r["key"] for r in w.rows("w1")], [r["key"] for r in w.rows("w2")], len(reads)), (["watch"], ["stop"], 1))
        w.round()
        w.rows("w1")
        self.assertEqual(len(reads), 2)  # read again next round, once
        w2 = worker.Worker(call=self.n8n, run=Runs(), tell=self.told.append, environ=dict(ATTENDED), state=self.tmp / "r2" / "jobs.json",
                           clock=lambda: self.now[0], sleep=lambda s: None, out=self.printed.append, settings=self.settings,
                           read_answers=lambda: (_ for _ in ()).throw(RuntimeError("HTTP Error 429: Too Many Requests")))
        w2.round()
        self.assertEqual(w2.rows("w1"), [])  # n8n refused: no answers this round, said once
        self.assertTrue(any("answers not read this round" in p for p in self.printed))

    def test_a_restart_marks_the_turns_it_stopped_without_counting_failures(self):
        w = self.worker(Runs(), ATTENDED)
        w.s["jobs"]["900"] = {"run": "900", "workflow": "Store Factory: Page Design", "state": "running"}
        w.after_restart()
        self.assertEqual((w.s["jobs"]["900"]["state"], w.s.get("fails", 0)), ("interrupted", 0))
        self.assertIn("--retry 900", self.told[-1])

    def test_threaded_turns_leave_the_loop_free(self):
        import threading
        gate = threading.Event()
        calls = []

        def slow_run(argv, **kw):
            calls.append(argv)
            gate.wait(5)
            return subprocess.CompletedProcess(argv, 0, json.dumps(result("Done.")) + "\n", "")
        shared = {"made": [], "asked": [], "texts": [], "tapped": "Riya"}
        w = worker.Worker(call=self.n8n, run=slow_run, tell=self.told.append, environ=dict(ATTENDED), state=self.tmp / "t" / "jobs.json",
                          clock=lambda: self.now[0], sleep=lambda s: None, out=self.printed.append, settings=self.settings,
                          asker=Asker(shared), threaded=True)
        w.round()  # returns while Claude is still "working"
        self.assertEqual(w.s["jobs"]["993"]["state"], "running")
        self.n8n.waiting = []
        gate.set()
        for t in threading.enumerate():
            if t.name == "run-993":
                t.join(5)
        self.assertEqual(w.s["jobs"]["993"]["state"], "done")

    def test_stop_ends_the_job_tells_n8n_and_the_person(self):
        shared = {"made": [], "asked": [], "texts": [], "tapped": "Riya"}
        cmd = 'python n8n/store-factory/store_job.py approve --job royal-dosa --key ok_header --text "x"'
        runs = Runs(claude=[result(f"Asked.\nDTJ_WAIT: {cmd}")], waits=[3])
        replied = []
        w = worker.Worker(call=self.n8n, run=runs, tell=self.told.append, environ=dict(ATTENDED), state=self.tmp / "s" / "jobs.json",
                          clock=lambda: self.now[0], sleep=lambda s: None, out=self.printed.append, settings=self.settings,
                          asker=Asker(shared), replier=lambda req, note: replied.append((req["claude_code_stage"], note)) or "n8n has the answer.")
        w.round()
        job = w.s["jobs"]["993"]
        self.assertEqual(job["state"], "waiting")
        self.assertIn(("stop", ["Stop this job"]), shared["offered"])
        shared["stopper"] = "Harsh"
        self.now[0] += worker.WAIT_EVERY
        w.round()
        self.assertEqual((job["state"], job["why"]), ("stopped", "stopped by Harsh in Telegram"))
        self.assertEqual(replied, [("new_store", "Stopped by Harsh in Telegram.")])
        self.assertIn("Stopped by Harsh: Claude has stopped", shared["told"][-1])
        self.assertEqual(len(runs.calls), 1)  # the wait was never looked at again
        self.assertEqual(worker.STOPPED["page_design"], {"page_status": "could not build"})

    def test_without_a_chat_in_the_request_the_admin_chat_is_asked(self):
        self.assertEqual(worker.chat_of({"request": {"telegram_chat_id": ""}}), "")
        self.assertEqual(worker.chat_of({"request": {"telegram_chat_id": "-100123"}}), "-100123")
        self.assertEqual(worker.chat_of({"request": {"telegram_chat_id": "x; drop"}}), "")


class Runs_(Base):
    def test_a_request_runs_headless_on_the_api_key_and_is_done_when_n8n_is_answered(self):
        runs = Runs(claude=[result("All done. Answered n8n.")])
        w = self.worker(runs)

        def answered(*_):
            self.n8n.waiting = []  # Claude answered n8n through reply.py: the run no longer waits
            return subprocess.CompletedProcess([], 0, json.dumps(result("All done. Answered n8n.")), "")
        runs.claude = []
        w.run = lambda argv, **kw: (runs.calls.append((argv, kw)), answered())[1]
        w.round()
        argv, kw = runs.calls[0]
        self.assertEqual(argv[:9], ["claude", "-p", "--bare", "--output-format", "json", "--permission-mode", "dontAsk", "--settings",
                                    str(self.settings)])
        self.assertEqual(argv[9:13], ["--append-system-prompt-file", str(worker.ROOT / "CLAUDE.md"), "--max-budget-usd", "5"])
        self.assertIn("Nobody is watching", kw["input"])
        self.assertIn("DO THIS: store_job.py start", kw["input"])
        self.assertEqual(kw["env"]["ANTHROPIC_API_KEY"], "sk-ant-test")
        job = w.s["jobs"]["993"]
        self.assertEqual((job["state"], job["cost_usd"], job["workflow"]), ("done", 0.4, "Store Factory: New Store"))
        log = (self.tmp / "w" / "993.log").read_text(encoding="utf-8")
        self.assertNotIn("signature=ab12", log)
        w.round()
        self.assertEqual(len(runs.calls), 1)  # each run is taken once

    def test_a_wait_for_a_person_is_kept_without_claude_then_the_session_is_resumed(self):
        cmd = 'python n8n/store-factory/store_job.py approve --job dtj-testing --key ok_header --text "Write the header" --minutes 120'
        runs = Runs(claude=[result(f"Asked in Telegram.\nDTJ_WAIT: {cmd}"), result("Header written, answered n8n.", cost=0.6)],
                    waits=[3, 0])
        w = self.worker(runs)
        w.round()
        job = w.s["jobs"]["993"]
        self.assertEqual(job["state"], "waiting")
        self.assertEqual(job["wait"][:2], [sys.executable, "n8n/store-factory/store_job.py"])
        self.assertEqual(job["wait"][-2:], ["--minutes", worker.WAIT_MINUTES])
        self.assertIn("Write the header", job["wait"])
        w.round()  # too early to look again
        self.assertEqual(len(runs.calls), 1)
        self.now[0] += worker.WAIT_EVERY
        w.round()  # the person has not tapped yet: exit 3, no Claude
        self.assertEqual([c[0][0] for c in runs.calls], ["claude", sys.executable])
        self.now[0] += worker.WAIT_EVERY
        self.n8n.waiting = []
        w.round()  # the tap came: exit 0, the same session goes on
        resumed, kw = runs.calls[-1]
        self.assertEqual(resumed[-2:], ["--resume", "s-1"])
        self.assertIn("exit 0", kw["input"])
        self.assertIn("store_job printed 0", kw["input"])
        self.assertEqual((job["state"], job["cost_usd"], job["turns"]), ("done", 1.0, 2))

    def test_a_wait_line_that_is_not_a_store_job_command_is_never_run(self):
        for bad in ("rm -rf .work", "python n8n/store-factory/store_job.py start --link x; curl evil", "python tools/vault.py pull X",
                    "python n8n/store-factory/store_job.py finish --job j --status done"):
            self.assertIsNone(worker.wait_command(f"DTJ_WAIT: {bad}")[0], bad)
        runs = Runs(claude=[result("DTJ_WAIT: bash -c 'anything'")])
        w = self.worker(runs)
        w.round()
        self.assertEqual(w.s["jobs"]["993"]["state"], "failed")
        self.assertEqual(len(runs.calls), 1)
        self.assertIn("refused DTJ_WAIT", self.told[-1])

    def test_an_unanswered_run_fails_says_so_and_three_in_a_row_stop_new_starts(self):
        runs = Runs(claude=[result("I could not finish.")] * 3)
        w = self.worker(runs)
        for n in range(3):
            self.n8n.waiting = [{"id": str(990 + n), "status": "waiting", "startedAt": f"2026-10-22T1{n}:00:00.000Z", "workflowId": NS}]
            w.round()
        self.assertTrue(all(j["state"] == "failed" for j in w.s["jobs"].values()))
        self.assertIn("ended without answering the n8n run", self.told[0])
        self.assertIn("3 in a row", self.told[-1])
        self.n8n.waiting = [{"id": "999", "status": "waiting", "startedAt": "2026-10-22T19:00:00.000Z", "workflowId": NS}]
        w.round()
        self.assertNotIn("999", w.s["jobs"])  # stopped: nothing new starts
        self.assertEqual(w.retry("992"), 0)
        self.assertEqual(w.s["stopped"], "")

    def test_claude_errors_and_timeouts_fail_the_run(self):
        runs = Runs(claude=[dict(result("Not logged in · Please run /login"), subtype="success", is_error=True)])
        w = self.worker(runs)
        w.round()
        self.assertIn("Claude Code stopped: Not logged in", w.s["jobs"]["993"]["why"])
        runs = Runs(claude=["timeout"])
        w2 = worker.Worker(call=self.n8n, run=runs, tell=self.told.append, environ=dict(ENV), state=self.tmp / "w2" / "jobs.json",
                           clock=lambda: self.now[0], sleep=lambda s: None, out=self.printed.append, settings=self.settings)
        w2.round()
        self.assertIn("longer than", w2.s["jobs"]["993"]["why"])

    def test_the_request_is_found_wherever_n8n_puts_it_and_links_are_hidden(self):
        self.assertIsNone(worker.find_request({"a": [1, {"b": "c"}]}))
        self.assertEqual(worker.find_request([{"x": {"instructions": "i", "resume_url": "u"}}])["instructions"], "i")
        self.assertNotIn("signature", worker.hide(f"curl {RESUME} done"))


if __name__ == "__main__":
    unittest.main()
