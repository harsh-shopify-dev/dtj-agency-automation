"""listen.py against a fake n8n (no network, no real waiting): which request is offered, when it stops and what it prints.

    python -m unittest discover -s n8n/store-factory -p "test_*.py"
"""
import io
import json
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import listen

PD = "WF-PD"
TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkdGotbWNwIn0.c2VjcmV0LXNpZ25hdHVyZQ"


def run_(execution_id, started):
    return {"id": execution_id, "workflowId": PD, "status": "waiting", "mode": "integrated", "startedAt": started, "stoppedAt": None,
            "waitTill": "2026-10-15T05:49:11.596Z"}


class FakeN8n:
    """search_workflows + search_workflow_executions from memory; `fail` = how many calls fail before it answers again."""

    def __init__(self, runs=(), fail=0, error=None):
        self.runs, self.fail, self.calls = list(runs), fail, []
        self.error = error or urllib.error.URLError("timed out")

    def __call__(self, tool, args):
        self.calls.append((tool, args))
        if self.fail:
            self.fail -= 1
            raise self.error
        if tool == "search_workflows":
            return {"data": [{"id": PD, "name": "Store Factory: Page Design"}, {"id": "WF-X", "name": "Store Factory: Page Design (old copy)"}]}
        if tool == "search_workflow_executions":
            assert args["workflowId"] == PD and args["status"] == ["waiting"], args
            return {"data": [r for r in self.runs if r["status"] == "waiting"], "nextCursor": None}
        raise AssertionError(f"listen.py must only read: {tool}")


class Clock:
    """A fake clock: sleeping moves it forward instantly."""

    def __init__(self):
        self.now, self.sleeps = 0.0, []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def __call__(self):
        return self.now


class Listen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.offered = Path(self.tmp.name) / ".work" / "listen" / "offered.json"
        self.clock = Clock()

    def tearDown(self):
        self.tmp.cleanup()

    def main(self, argv, fake, secrets=()):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = listen.main(argv, call=fake, sleep=self.clock.sleep, clock=self.clock, offered_path=self.offered, secrets=secrets)
        return code, out.getvalue(), err.getvalue()

    def test_the_oldest_unoffered_request_comes_first_as_one_json_line(self):
        fake = FakeN8n([run_("351", "2026-10-12T07:10:00.000Z"), run_("99", "2026-10-12T06:00:00.000Z"), run_("350", "2026-10-12T07:00:00.000Z")])
        code, out, err = self.main(["--once"], fake)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertEqual(json.loads(out), {"execution_id": "99", "workflow_id": PD, "started_at": "2026-10-12T06:00:00.000Z", "waiting": 2})
        self.assertEqual(json.loads(self.offered.read_text(encoding="utf-8")), {"offered": ["99"]})  # folders made as needed

    def test_offered_requests_are_not_offered_again_and_forget_brings_one_back(self):
        fake = FakeN8n([run_("350", "2026-10-12T07:00:00.000Z"), run_("351", "2026-10-12T07:10:00.000Z")])
        got = [self.main(["--once"], fake) for _ in range(3)]
        self.assertEqual([c for c, _, _ in got], [0, 0, 3])
        self.assertEqual([json.loads(o)["execution_id"] for _, o, _ in got[:2]], ["350", "351"])
        self.assertEqual([json.loads(o)["waiting"] for _, o, _ in got[:2]], [1, 0])
        self.assertIn("No new page request is waiting.", got[2][1])

        code, out, _ = self.main(["--forget", "350"], FakeN8n())
        self.assertEqual(code, 0)
        self.assertIn("Forgot 350", out)
        code, out, _ = self.main(["--once"], fake)
        self.assertEqual((code, json.loads(out)["execution_id"]), (0, "350"))
        code, out, _ = self.main(["--forget", "777"], FakeN8n())
        self.assertEqual(code, 0)
        self.assertIn("777 was not in the offered list", out)

    def test_once_exit_codes(self):
        self.assertEqual(self.main(["--once"], FakeN8n())[0], 3)
        self.assertEqual(self.main(["--once"], FakeN8n([run_("400", "2026-10-12T08:00:00.000Z")]))[0], 0)
        self.assertEqual(self.main(["--once"], FakeN8n([run_("400", "2026-10-12T08:00:00.000Z")]))[0], 3)  # already offered

    def test_listening_waits_until_a_request_comes_in(self):
        fake = FakeN8n()
        real_call = fake.__call__
        polls = []

        def call(tool, args):
            if tool == "search_workflow_executions":
                polls.append(self.clock.now)
                if len(polls) == 4:
                    fake.runs.append(run_("402", "2026-10-12T08:01:30.000Z"))
            return real_call(tool, args)

        code, out, err = self.main(["--interval", "30"], call)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["execution_id"], "402")
        self.assertEqual(polls, [0, 30, 60, 90])
        self.assertIn("Listening for page requests (Store Factory: Page Design) every 30 s, up to 8 h. "
                      "Only one laptop should listen at a time.", err)

    def test_nothing_coming_in_stops_with_exit_3_after_the_hours(self):
        code, out, err = self.main(["--interval", "600", "--hours", "1"], FakeN8n())
        self.assertEqual(code, 3)
        self.assertEqual(out.strip(), "Stopped listening after 1 hours: no page request came in.")
        self.assertLessEqual(self.clock.now, 3600)
        self.assertEqual(len(self.clock.sleeps), 6)  # checks at 0, 10, ..., 60 minutes: 7 checks, 6 pauses

    def test_three_failures_in_a_row_exit_2_without_the_token(self):
        error = RuntimeError(f"search_workflow_executions: 401 Unauthorized (Authorization: Bearer {TOKEN}; token={TOKEN})")
        fake = FakeN8n([run_("500", "2026-10-12T09:00:00.000Z")], fail=3, error=error)
        code, out, err = self.main(["--once"], fake, secrets=[TOKEN])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("n8n failed 3 times in a row", err)
        self.assertIn("401 Unauthorized", err)
        self.assertNotIn(TOKEN, err)
        self.assertNotIn("c2VjcmV0", err)
        self.assertEqual(self.clock.sleeps, list(listen.RETRY_DELAYS))
        self.assertFalse(self.offered.exists())

    def test_two_failures_then_an_answer_still_finds_the_request(self):
        fake = FakeN8n([run_("501", "2026-10-12T09:00:00.000Z")], fail=2)
        code, out, err = self.main(["--once"], fake)
        self.assertEqual((code, json.loads(out)["execution_id"]), (0, "501"))

    def test_a_missing_workflow_exits_2(self):
        def call(tool, args):
            return {"data": []}
        code, out, err = self.main(["--once"], call)
        self.assertEqual(code, 2)
        self.assertIn('no workflow named "Store Factory: Page Design"', err)

    def test_page_and_add_shop_requests_are_watched_together_oldest_first(self):
        add = "WF-AS"
        shop_run = dict(run_("700", "2026-10-21T06:00:00.000Z"), workflowId=add)
        page_run = run_("701", "2026-10-21T07:00:00.000Z")

        def call(tool, args):
            if tool == "search_workflows":
                return {"data": [{"id": PD, "name": "Store Factory: Page Design"}, {"id": add, "name": "Store Factory: Add Shop"}]}
            if tool == "search_workflow_executions":
                return {"data": [r for r in (shop_run, page_run) if r["workflowId"] == args["workflowId"]]}
            raise AssertionError(tool)
        code, out, err = self.main(["--once"], call)
        self.assertEqual(json.loads(out), {"execution_id": "700", "workflow_id": add, "started_at": "2026-10-21T06:00:00.000Z",
                                           "waiting": 1, "workflow": "Store Factory: Add Shop"})
        code, out, err = self.main(["--once"], call)
        self.assertEqual((json.loads(out)["execution_id"], json.loads(out)["workflow"]), ("701", "Store Factory: Page Design"))
        code, out, _ = self.main(["--status"], call)
        self.assertIn("add-shop request(s) waiting", out)
        # one workflow named by hand (the reel VPS): only that one, and missing means exit 2
        code, out, err = self.main(["--once", "--workflow", "Reel Factory: New Reel"], call)
        self.assertEqual(code, 2)

    def test_status_counts_waiting_and_offered(self):
        fake = FakeN8n([run_("350", "2026-10-12T07:00:00.000Z"), run_("351", "2026-10-12T07:10:00.000Z")])
        self.main(["--once"], fake)
        code, out, _ = self.main(["--status"], fake)
        self.assertEqual(code, 0)
        self.assertIn("2 page request(s) waiting for Claude Code, 1 of them already offered", out)
        self.assertIn("350 (offered), 351", out)

    def test_limits_on_interval_and_hours(self):
        for argv in (["--interval", "5"], ["--hours", "13"], ["--hours", "0"], ["--once", "--status"]):
            with self.assertRaises(SystemExit) as stop:
                self.main(argv, FakeN8n())
            self.assertNotIn(stop.exception.code, (0, 2, 3), argv)  # 2 is kept for "n8n failed"

    def test_the_offered_file_lives_in_the_repo_work_folder(self):
        self.assertEqual(listen.OFFERED.parent.parent.parent, listen.HERE.parent.parent)
        self.assertEqual(listen.OFFERED.relative_to(listen.ROOT).as_posix(), ".work/listen/offered.json")
        self.assertTrue((listen.ROOT / "CLAUDE.md").exists())


class Pieces(unittest.TestCase):
    def test_pick_sorts_by_start_time_then_id(self):
        runs = listen.waiting(FakeN8n([run_("10", "2026-10-12T07:00:00.000Z"), run_("9", "2026-10-12T07:00:00.000Z"),
                                       run_("2", "2026-10-12T08:00:00.000Z")]), PD)
        self.assertEqual([r["id"] for r in runs], ["9", "10", "2"])
        hit, left = listen.pick(runs, ["9"])
        self.assertEqual((hit["id"], left), ("10", 1))

    def test_waiting_follows_pages(self):
        pages = [{"data": [run_("1", "2026-10-12T07:00:00.000Z")], "nextCursor": "abc"}, {"data": [run_("2", "2026-10-12T06:00:00.000Z")]}]
        seen = []

        def call(tool, args):
            seen.append(args.get("cursor"))
            return pages[len(seen) - 1]
        self.assertEqual([r["id"] for r in listen.waiting(call, PD)], ["2", "1"])
        self.assertEqual(seen, [None, "abc"])


if __name__ == "__main__":
    unittest.main()
