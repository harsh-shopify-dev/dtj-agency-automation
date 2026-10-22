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
ENV = {"ANTHROPIC_API_KEY": "sk-ant-test", "DTJ_CLAUDE_MAX_USD": "5"}


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
                "claude_code_stage": "new_store", "resume_url": RESUME,
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

    def worker(self, runs, environ=ENV):
        return worker.Worker(call=self.n8n, run=runs, tell=self.told.append, environ=dict(environ), state=self.tmp / "w" / "jobs.json",
                             clock=lambda: self.now[0], sleep=lambda s: None, out=self.printed.append, settings=self.settings)


class Ready(Base):
    def test_nothing_starts_without_the_api_key_or_the_spend_cap(self):
        runs = Runs()
        self.assertIn("rule 9", self.worker(runs, {"DTJ_CLAUDE_MAX_USD": "5"}).ready())
        self.assertIn("DTJ_CLAUDE_MAX_USD", self.worker(runs, {"ANTHROPIC_API_KEY": "k"}).ready())
        self.assertIn("DTJ_CLAUDE_MAX_USD", self.worker(runs, {"ANTHROPIC_API_KEY": "k", "DTJ_CLAUDE_MAX_USD": "0"}).ready())
        self.assertEqual(self.worker(runs).ready(), "")
        self.assertEqual(self.worker(runs, {}).serve(), 2)
        self.assertEqual(runs.calls, [])


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
        self.assertEqual(argv[:8], ["claude", "-p", "--output-format", "json", "--permission-mode", "dontAsk", "--settings",
                                    str(self.settings)])
        self.assertEqual(argv[8:10], ["--max-budget-usd", "5"])
        self.assertIn("unattended on DTJ's VPS", kw["input"])
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
        runs = Runs(claude=[result("budget", error=True)])
        w = self.worker(runs)
        w.round()
        self.assertIn("Claude Code stopped: error_during_execution", w.s["jobs"]["993"]["why"])
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
