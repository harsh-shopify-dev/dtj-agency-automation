"""The SEO report's way from GitHub to Telegram and back: the signer (notify_n8n.py), the n8n code nodes run in Node as n8n runs them
(../store-factory/node_harness.py), the workflow export and the bot's seo: buttons. Built and tested against the saved 14 Oct 2026
run in sample/ (no live n8n, GitHub or Telegram call).

    python -m unittest discover -s n8n/seo-engine -t n8n/seo-engine
"""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import re
import sys
import time
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "store-factory"))
import build_workflow  # noqa: E402
import notify_n8n  # noqa: E402
from node_harness import HAS_NODE, run_node  # noqa: E402

SCHEMA = Draft202012Validator(json.loads((HERE.parents[1] / "schemas" / "seo-weekly-report.schema.json").read_text(encoding="utf-8")))
KEY = "test-key-only-for-these-tests"
HARSH = {"telegram_user_id": "333", "name": "Harsh", "role": "admin", "active": True}
ANSHUL = {"telegram_user_id": "555", "name": "Anshul", "role": "admin", "active": True}
RIYA = {"telegram_user_id": "111", "name": "Riya", "role": "requester", "active": True}
OLD = {"telegram_user_id": "444", "name": "Old Admin", "role": "admin", "active": False}
TEAM = [HARSH, ANSHUL, RIYA, OLD]


def content(run_id: str = "9990001") -> dict:
    return notify_n8n.build_content(HERE / "sample" / "2026-10-14", run_id=run_id)


def webhook_item(c: dict, *, key: str = KEY, now: int | None = None, claims_in_node: bool = False, **over) -> dict:
    """What n8n's webhook node hands on after its JWT check: headers, body and (n8n's own field) jwtPayload."""
    text, body = notify_n8n.request_body(c)
    token = notify_n8n.sign(text, key, run_id=c.get("run_id", "x"), batch_id=(c.get("batch") or {}).get("id", "x"), now=now)
    item = {"headers": {"authorization": f"Bearer {token}"}, "body": json.loads(body), "params": {}, "query": {}}
    if claims_in_node:
        item["jwtPayload"] = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
    item.update(over)
    return item


def js(file: str, given, refs: dict | None = None) -> list[dict]:
    res = run_node(HERE / file, given, refs or {})
    if not res["ok"]:
        raise AssertionError(res["error"])
    return res["out"]


class Signer(unittest.TestCase):
    def test_the_sample_run_makes_a_report_that_fits_the_schema(self):
        c = content()
        self.assertEqual(list(SCHEMA.iter_errors(c)), [])
        self.assertEqual((c["batch"]["id"], c["batch"]["counts"]), ("fix-2026-10-14", {"auto": 4, "blocked": 0, "manual": 6}))
        self.assertEqual([x["cid"] for x in c["batch"]["changes"]], ["c001", "c002", "c003", "c004"])
        self.assertEqual(len(c["batch"]["manual"]), 6)
        self.assertTrue(c["report_md"].startswith("# DTJ search report, 2026-10-14"))
        self.assertEqual(c["run_url"], "https://github.com/harsh-shopify-dev/dtj-agency-automation/actions/runs/9990001")

    def test_business_details_are_shown_in_words_not_raw_data(self):
        c4 = content()["batch"]["changes"][3]
        self.assertEqual(c4["kind"], "site_jsonld")
        self.assertTrue(c4["after"].startswith("business details for Google and AI"), c4["after"])
        self.assertNotIn("@context", c4["after"])

    def test_the_signature_covers_the_exact_content_and_expires(self):
        text, _ = notify_n8n.request_body(content())
        token = notify_n8n.sign(text, KEY, run_id="9990001", batch_id="fix-2026-10-14", now=1_000_000)
        head, body, mac = token.split(".")
        want = base64.urlsafe_b64encode(hmac.new(KEY.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
        self.assertEqual(mac, want)
        claims = json.loads(base64.urlsafe_b64decode(body + "=="))
        self.assertEqual(claims["sha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual((claims["iss"], claims["aud"], claims["exp"] - claims["iat"]), ("dtj-seo-weekly", "dtj-n8n", 600))
        self.assertEqual(json.loads(base64.urlsafe_b64decode(head + "==")), {"alg": "HS256", "typ": "JWT"})

    def test_an_incomplete_check_is_marked_with_its_reason(self):
        cov = {"complete": False, "unreadable_sitemaps": [{"url": "x"}], "fewer_than_before": True, "pages_read": 10, "previous_pages": 24}
        self.assertIn("1 sitemap(s) could not be read", notify_n8n.coverage_text(cov))
        self.assertIn("only 10 pages were read; the last complete check read 24", notify_n8n.coverage_text(cov))
        self.assertIsNone(notify_n8n.coverage_text({"complete": True}))

    def test_without_the_secret_nothing_is_sent_and_the_run_still_passes(self):
        self.assertEqual(notify_n8n.main(["--run-id", "1", "--out", str(HERE / "sample")], env={}), 0)

    def test_sending_retries_429_and_5xx_three_times_but_not_a_refusal(self):
        calls = []

        def opener(statuses):
            def go(req, timeout):
                calls.append(req)
                code = statuses.pop(0)
                if code >= 400:
                    raise urllib.error.HTTPError(req.full_url, code, "x", {}, None)

                class R:
                    status = code
                    def __enter__(self): return self
                    def __exit__(self, *a): return False
                return R()
            return go
        self.assertEqual(notify_n8n.post("https://x", b"{}", "t", opener=opener([503, 429, 200]), wait=0), 200)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0].headers["Authorization"], "Bearer t")
        calls.clear()
        self.assertEqual(notify_n8n.post("https://x", b"{}", "t", opener=opener([403]), wait=0), 403)
        self.assertEqual(len(calls), 1)
        calls.clear()
        self.assertEqual(notify_n8n.post("https://x", b"{}", "t", opener=opener([502, 502, 502]), wait=0), 502)
        self.assertEqual(len(calls), 3)


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class CheckTheReport(unittest.TestCase):
    def check(self, item) -> dict:
        return js("check_report.js", item)[0]["json"]

    def test_a_signed_report_passes_with_the_claims_from_the_header_or_from_n8n(self):
        for in_node in (False, True):
            got = self.check(webhook_item(content(), claims_in_node=in_node))
            self.assertTrue(got["ok"], got)
            self.assertEqual(got["report"]["batch"]["id"], "fix-2026-10-14")

    def test_the_sha256_in_javascript_equals_python_for_non_ascii_text(self):
        c = content()
        c["report_md"] += "\n₹70Cr+ — नमस्ते 😀 \"quotes\" \\ back"
        self.assertTrue(self.check(webhook_item(c))["ok"])

    def test_a_changed_body_an_old_or_foreign_signature_goes_to_the_dead_letter(self):
        item = webhook_item(content())
        item["body"]["content"] = item["body"]["content"].replace("fix-2026-10-14", "fix-2026-10-15")
        self.assertIn("does not match its signature", self.check(item)["reason"])
        old = webhook_item(content(), now=int(time.time()) - 3600)
        self.assertIn("expired", self.check(old)["reason"])
        c = content()
        text, body = notify_n8n.request_body(c)
        tok = notify_n8n.sign(text, KEY, run_id="9990001", batch_id="fix-2026-10-14")
        head, claims, mac = tok.split(".")
        forged = json.loads(base64.urlsafe_b64decode(claims + "=="))
        forged["iss"] = "someone-else"
        bad = {"headers": {"authorization": "Bearer " + head + "." + base64.urlsafe_b64encode(json.dumps(forged).encode()).rstrip(b"=").decode()
                           + "." + mac}, "body": json.loads(body)}
        self.assertIn("issuer", self.check(bad)["reason"])
        self.assertIn("no signed claims", self.check({"headers": {}, "body": json.loads(body)})["reason"])
        extra = webhook_item(content())
        extra["body"]["also"] = 1
        self.assertIn("other than", self.check(extra)["reason"])

    def test_the_signed_run_and_batch_must_be_the_ones_inside(self):
        c = content()
        text, body = notify_n8n.request_body(c)
        tok = notify_n8n.sign(text, KEY, run_id="1234", batch_id="fix-2026-10-14")
        got = self.check({"headers": {"authorization": f"Bearer {tok}"}, "body": json.loads(body)})
        self.assertIn("signed run or batch", got["reason"])
        other = content()
        other["repo"] = "someone/else"
        other["run_url"] = "https://github.com/someone/else/actions/runs/9990001"
        self.assertIn("another repository", self.check(webhook_item(other))["reason"])

    def test_javascript_and_the_json_schema_give_the_same_verdict(self):
        def drop(path):
            def f(c):
                *p, last = path
                t = c
                for k in p:
                    t = t[k]
                del t[last]
            return f

        def put(path, value):
            def f(c):
                *p, last = path
                t = c
                for k in p:
                    t = t[k]
                t[last] = value
            return f
        cases = {
            "fine": lambda c: None,
            "mode approve": put(["mode"], "approve"),
            "mode unknown": put(["mode"], "live"),
            "no batch": drop(["batch"]),
            "unknown top field": put(["extra"], 1),
            "schema version": put(["schema"], "dtj-seo-weekly/2"),
            "run id not digits": put(["run_id"], "12a"),
            "run url elsewhere": put(["run_url"], "https://evil.example/actions/runs/1"),
            "site http": put(["site"], "http://digitaltusharjoshi.com"),
            "made_at not a date": put(["made_at"], "monday"),
            "pages negative": put(["scan", "pages"], -1),
            "complete as text": put(["scan", "complete"], "yes"),
            "scan unknown": put(["scan", "x"], 1),
            "warning ok": put(["scan", "warning"], "1 sitemap(s) could not be read"),
            "batch id": put(["batch", "id"], "fix-oct"),
            "counts float": put(["batch", "counts", "auto"], 4.5),
            "change unknown field": put(["batch", "changes", 0, "x"], 1),
            "change how manual": put(["batch", "changes", 0, "how"], "manual"),
            "change cid": put(["batch", "changes", 0, "cid"], "1"),
            "change after long": put(["batch", "changes", 0, "after"], "a" * 601),
            "change before null": put(["batch", "changes", 0, "before"], None),
            "manual not text": put(["batch", "manual"], [1]),
            "empty report": put(["report_md"], ""),
        }  # (a 60,001-character report is refused by both too, but is longer than Windows lets the test hand to Node)
        for name, change in cases.items():
            c = copy.deepcopy(content())
            change(c)
            schema_ok = not list(SCHEMA.iter_errors(c))
            got = self.check(webhook_item(c))
            self.assertEqual(got["ok"], schema_ok, f"{name}: JS {got.get('reason')!r}, schema ok {schema_ok}")
        # one rule the schema alone cannot say: the auto count must match the list
        c = content()
        c["batch"]["counts"]["auto"] = 5
        self.assertIn("auto count", self.check(webhook_item(c))["reason"])


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class PlanAndMessages(unittest.TestCase):
    def plan(self, checked, batches=(), users=TEAM):
        # as in n8n: this node's input is what "Load Batches" gave; the check result is read from "Check the Report"
        return js("plan_report.js", list(batches) or [{}], {"Check the Report": checked, "Load Bot Users": list(users) or [{}],
                                                            "Load Batches": list(batches) or [{}]})

    def report(self, **change):
        r = content()
        for k, v in change.items():
            r[k] = v
        return {"ok": True, "report": r}

    def test_a_good_report_is_saved_for_the_active_admins_and_logged(self):
        out = self.plan(self.report())
        self.assertEqual(len(out), 1)
        p = out[0]["json"]
        self.assertEqual(p["action"], "save")
        self.assertEqual(p["admins"], ["333", "555"])
        row = p["row"]
        self.assertEqual((row["batch_id"], row["run_id"], row["status"], row["can_approve"], row["auto_changes"], row["sent_to"]),
                         ("fix-2026-10-14", "9990001", "waiting", True, 4, 2))
        self.assertEqual(set(row), {c["name"] for c in build_workflow.tables()["dtj_seo_batches"]["columns"]})
        self.assertEqual(set(p["log"]), {c["name"] for c in build_workflow.tables()["dtj_action_log"]["columns"]})
        self.assertEqual((p["log"]["tier"], p["log"]["result"]), (0, "recommended"))

    def test_the_same_run_twice_is_sent_once(self):
        self.assertEqual(self.plan(self.report(), batches=[{"id": 3, "batch_id": "fix-2026-10-14", "run_id": "9990001"}]), [])
        self.assertEqual(len(self.plan(self.report(), batches=[{"id": 3, "batch_id": "fix-2026-10-14", "run_id": "5"}])), 1)

    def test_no_yes_when_the_check_is_incomplete_or_nothing_is_ready(self):
        r = content()
        r["scan"]["complete"] = False
        self.assertEqual(self.plan({"ok": True, "report": r})[0]["json"]["row"]["status"], "not asked")
        r = content()
        r["batch"]["counts"]["auto"] = 0
        r["batch"]["changes"] = []
        row = self.plan({"ok": True, "report": r})[0]["json"]["row"]
        self.assertEqual((row["status"], row["can_approve"]), ("not asked", False))

    def test_a_failed_check_goes_to_the_dead_letter_with_the_reason(self):
        p = self.plan({"ok": False, "reason": "the content does not match its signature (SHA-256)", "raw": "{...}"})[0]["json"]
        self.assertEqual(p["action"], "dead_letter")
        self.assertEqual(set(p["dead"]), {c["name"] for c in build_workflow.tables()["dtj_dead_letter"]["columns"]})
        self.assertEqual((p["log"]["result"], p["dead"]["raw"]), ("blocked", "{...}"))
        alert = js("dead_letter_alert.js", {"id": 9}, {"Plan the Report": p})
        self.assertEqual([i["json"]["chat_id"] for i in alert], ["333", "555"])
        self.assertIn("did not pass its checks", alert[0]["json"]["text"])
        self.assertIn("SHA-256", alert[0]["json"]["text"])

    def messages(self, report=None):
        p = self.plan(report or self.report())[0]["json"]
        return p, js("report_messages.js", {"id": 42}, {"Plan the Report": p})

    def test_each_admin_gets_the_file_and_the_question_with_the_row_on_the_buttons(self):
        p, out = self.messages()
        kinds = [(i["json"]["kind"], i["json"]["chat_id"]) for i in out]
        self.assertEqual(kinds, [("file", "333"), ("ask", "333"), ("file", "555"), ("ask", "555")])
        f = out[0]
        self.assertEqual(base64.b64decode(f["binary"]["data"]["data"]).decode("utf-8"), p["report"]["report_md"])
        self.assertEqual(f["binary"]["data"]["fileName"], "dtj-seo-report-2026-10-14.md")
        ask = out[1]["json"]
        self.assertEqual((ask["yes_data"], ask["no_data"]), ("seo:yes:42", "seo:no:42"))
        self.assertLessEqual(len(ask["yes_data"].encode()), 64)
        self.assertLessEqual(len(ask["text"]), 4096)
        for want in ("fix-2026-10-14", "4 ready to apply", "c001 Hide from Google, /elementor-hf/footer/", "c004 Business details for Google and AI, /: offices in Rajkot, Ahmedabad",
                     "One yes covers this batch only", "test mode", "GitHub run 9990001"):
            self.assertIn(want, ask["text"])

    def test_text_is_escaped_and_kept_under_telegrams_limit(self):
        r = content()
        many = [{"cid": f"c{i:03d}", "kind": "meta_description", "url": f"https://digitaltusharjoshi.com/p{i}/", "before": "old",
                 "after": "<b>x</b> & " + "y" * 300, "how": "auto"} for i in range(1, 41)]
        r["batch"]["changes"], r["batch"]["counts"]["auto"] = many, len(many)
        _, out = self.messages({"ok": True, "report": r})
        text = out[1]["json"]["text"]
        self.assertLessEqual(len(text), 4096)
        self.assertNotIn("<b>x</b>", text)
        self.assertIn("&lt;b&gt;x&lt;/b&gt; &amp;", text)
        self.assertRegex(text, r"and \d+ more in the file")

    def test_without_a_yes_button_the_message_says_why(self):
        r = content()
        r["scan"]["complete"], r["scan"]["warning"] = False, "1 sitemap(s) could not be read"
        _, out = self.messages({"ok": True, "report": r})
        self.assertEqual(out[1]["json"]["kind"], "text")
        self.assertIn("No Yes button this week", out[1]["json"]["text"])
        self.assertIn("This check is incomplete", out[1]["json"]["text"])

    def test_the_apply_switch_is_off_and_the_same_in_both_nodes(self):
        flags = [re.search(r"^const APPLY_ON = (true|false);", (HERE / f).read_text(encoding="utf-8"), re.M).group(1)
                 for f in ("report_messages.js", "answer_plan.js")]
        self.assertEqual(flags, ["false", "false"], "shadow first: only Harsh's yes turns the apply on, in both files together")


def batch_row(**over) -> dict:
    row = {"id": 42, "batch_id": "fix-2026-10-14", "run_id": "9990001", "run_url": "https://github.com/x/y/actions/runs/9990001",
           "site": "https://digitaltusharjoshi.com", "status": "waiting", "can_approve": True, "auto_changes": 4,
           "made_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(), "answered_by": "", "answered_at": ""}
    row.update(over)
    return row


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Answers(unittest.TestCase):
    def decide(self, answer, user=HARSH, rows=None, row_id=42):
        tap = {"row_id": row_id, "answer": answer, "by": user["name"], "user_id": user["telegram_user_id"], "chat_id": user["telegram_user_id"]}
        out = js("answer_plan.js", TEAM, {"Answer from the Bot": tap, "Load the Team": TEAM,
                                          "Find the Batch": rows if rows is not None else [batch_row()]})
        self.assertEqual(len(out), 1)
        return out[0]["json"]

    def test_harshs_yes_is_recorded_with_his_name_and_nothing_is_started_in_shadow(self):
        d = self.decide("yes")
        self.assertEqual((d["action"], d["status"], d["approved_by"], d["answered_by"]), ("record", "yes", "Harsh", "Harsh"))
        self.assertFalse(d["dispatch"])
        self.assertEqual(d["apply_status"], "shadow: recorded, not applied")
        self.assertEqual(d["body"], {"ref": "chore/initial-import",
                                     "inputs": {"run_id": "9990001", "approved_by": "Harsh", "only": "", "batch_id": "fix-2026-10-14"}})
        self.assertEqual(d["others"], ["555"])

    def test_a_teammate_confirms_harsh_cannot_be_reached_before_their_yes_counts(self):
        ask = self.decide("yes", user=ANSHUL)
        self.assertEqual(ask["action"], "confirm")
        self.assertEqual((ask["yes_data"], ask["no_data"]), ("seo:yesnr:42", "seo:cancel:42"))
        self.assertIn("needs Harsh's yes", ask["text"])
        d = self.decide("yesnr", user=ANSHUL)
        self.assertEqual((d["action"], d["approved_by"], d["answered_by"]), ("record", "Anshul (Harsh not reachable)", "Anshul"))
        self.assertEqual(d["body"]["inputs"]["approved_by"], "Anshul (Harsh not reachable)")
        self.assertEqual(self.decide("cancel", user=ANSHUL)["action"], "reply")

    def test_a_no_is_recorded_without_an_approver(self):
        d = self.decide("no", user=ANSHUL)
        self.assertEqual((d["action"], d["status"], d["approved_by"], d["dispatch"]), ("record", "no", "", False))

    def test_one_answer_per_batch_and_only_the_newest_fresh_batch(self):
        done = self.decide("yes", rows=[batch_row(status="yes", answered_by="Harsh", answered_at="2026-10-19T05:00:00Z")])
        self.assertEqual(done["action"], "reply")
        self.assertIn("already answered: yes by Harsh", done["text"])
        newer = self.decide("yes", rows=[batch_row(), batch_row(id=43, batch_id="fix-2026-10-20", run_id="9990002")])
        self.assertIn("replaced by a newer report", newer["text"])
        old = self.decide("yes", rows=[batch_row(made_at="2026-01-01T00:00:00+00:00")])
        self.assertIn("more than 7 days old", old["text"])
        self.assertIn("nothing to approve", self.decide("yes", rows=[batch_row(can_approve=False)])["text"])
        self.assertIn("nothing to approve", self.decide("yes", rows=[batch_row(status="not asked", can_approve=False)])["text"])
        self.assertIn("cannot find", self.decide("yes", row_id=7)["text"])

    def test_people_outside_the_team_or_inactive_cannot_answer(self):
        self.assertIn("Only the DTJ team", self.decide("yes", user=OLD)["text"])
        self.assertIn("Only the DTJ team", self.decide("yes", user={"telegram_user_id": "999", "name": "X"})["text"])
        self.assertIn("not valid", self.decide("maybe")["text"])

    def say(self, d, saved=None, got=None):
        return js("answer_messages.js", got or {}, {"Decide the Answer": d, "Save the Answer": saved if saved is not None else {"id": 42}})

    def test_after_saving_the_person_and_the_other_admins_hear_it_once_logged(self):
        out = self.say(self.decide("yes"))
        self.assertEqual([i["json"]["chat_id"] for i in out], ["333", "555"])
        self.assertIn("Test mode (shadow): nothing was changed on the site", out[0]["json"]["text"])
        self.assertIn("run number 9990001", out[0]["json"]["text"])
        log = out[0]["json"]["log"]
        self.assertEqual((log["tier"], log["mode"], log["result"], log["approved_by"]), (2, "shadow", "recommended", "Harsh"))
        self.assertEqual(set(log), {c["name"] for c in build_workflow.tables()["dtj_action_log"]["columns"]})
        self.assertNotIn("log", out[1]["json"])
        no = self.say(self.decide("no"))
        self.assertEqual(no[0]["json"]["log"]["result"], "blocked")

    def test_a_second_quick_tap_is_not_counted(self):
        out = self.say(self.decide("no", user=ANSHUL), saved={})
        self.assertEqual(len(out), 1)
        self.assertIn("was not counted", out[0]["json"]["text"])
        self.assertEqual(out[0]["json"]["log"]["after"], "not changed")

    def test_when_the_apply_is_on_githubs_answer_is_reported(self):
        d = self.decide("yes")
        d["dispatch"] = True
        started = self.say(d, got={"statusCode": 204, "body": ""})
        self.assertIn("has started on GitHub", started[0]["json"]["text"])
        self.assertEqual(started[0]["json"]["log"]["result"], "success")
        failed = self.say(d, got={"statusCode": 422, "body": {"message": "Workflow does not have 'workflow_dispatch' trigger"}})
        self.assertIn("did not start", failed[0]["json"]["text"])
        self.assertEqual((failed[0]["json"]["log"]["result"], failed[0]["json"]["log"]["error"]),
                         ("failed", "Workflow does not have 'workflow_dispatch' trigger"))


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Bot(unittest.TestCase):
    def tap(self, data, user="333"):
        msg = {"chat_id": user, "chat_type": "private", "user_id": user, "name": "Harsh", "text": "", "callback_id": "c1",
               "kind": "button", "data": data}
        res = run_node(HERE.parent / "store-factory" / "bot_route.js", [{}], {"Read the Message": msg,
                                                                               "Load Bot Users": [HARSH, ANSHUL, RIYA]})
        self.assertTrue(res["ok"], res)
        return [i["json"] for i in res["out"]]

    def test_seo_buttons_go_to_the_seo_workflow_for_anyone_on_the_team(self):
        self.assertEqual(self.tap("seo:yes:42"), [{"action": "seo", "chat_id": "333", "row_id": 42, "answer": "yes", "by": "Harsh",
                                                   "user_id": "333"}])
        self.assertEqual(self.tap("seo:yesnr:42", user="111")[0]["answer"], "yesnr")  # not admin-only: the SEO lane checks the person
        self.assertEqual(self.tap("seo:delete:42")[0]["action"], "reply")
        self.assertEqual(self.tap("seo:yes:42", user="999")[0]["action"], "reply")  # not on the team

    def test_the_bot_export_routes_seo_to_the_seo_answer_and_keeps_the_reply_fallback(self):
        bot = json.loads((HERE.parent / "store-factory" / "telegram_bot.workflow.json").read_text(encoding="utf-8"))
        nodes = {n["name"]: n for n in bot["nodes"]}
        rules = [r["outputKey"] for r in nodes["What to Do"]["parameters"]["rules"]["values"]]
        self.assertEqual(rules, ["design", "switch", "intake", "stop", "brief", "site", "seo"])
        outs = bot["connections"]["What to Do"]["main"]
        self.assertEqual([t["node"] for t in outs[6]], ["SEO Answer"])
        self.assertEqual([t["node"] for t in outs[7]], ["Send"])
        seo = nodes["SEO Answer"]["parameters"]
        self.assertEqual(seo["workflowId"]["cachedResultName"], build_workflow.NAME)
        self.assertEqual(set(seo["workflowInputs"]["value"]), {n for n, _ in build_workflow.INPUTS})
        self.assertEqual(nodes["Who Is It"]["parameters"]["jsCode"],
                         (HERE.parent / "store-factory" / "bot_route.js").read_text(encoding="utf-8"))


class Export(unittest.TestCase):
    def setUp(self):
        self.wf = json.loads(build_workflow.EXPORT.read_text(encoding="utf-8"))

    def test_the_export_is_made_from_the_code_files(self):
        self.assertEqual(build_workflow.main(["--check"]), 0)

    def test_every_wire_meets_a_node_and_the_trigger_inputs_match_the_bot(self):
        names = {n["name"] for n in self.wf["nodes"]}
        for src, kinds in self.wf["connections"].items():
            self.assertIn(src, names)
            for outs in kinds["main"]:
                for t in outs:
                    self.assertIn(t["node"], names)
        trig = next(n for n in self.wf["nodes"] if n["name"] == "Answer from the Bot")
        self.assertEqual([(v["name"], v["type"]) for v in trig["parameters"]["workflowInputs"]["values"]], build_workflow.INPUTS)

    def test_the_webhook_needs_the_signature_and_no_secret_is_in_the_files(self):
        hook = next(n for n in self.wf["nodes"] if n["type"] == "n8n-nodes-base.webhook")
        self.assertEqual((hook["parameters"]["authentication"], hook["parameters"]["path"]), ("jwtAuth", "dtj-seo-weekly"))
        self.assertEqual(hook["credentials"], {"jwtAuth": {"name": "DTJ SEO Report Key"}})
        for n in self.wf["nodes"]:
            for c in (n.get("credentials") or {}).values():
                self.assertEqual(set(c), {"name"}, n["name"])
        blob = build_workflow.EXPORT.read_text(encoding="utf-8") + (HERE / "sample" / "request.json").read_text(encoding="utf-8")
        for pat in (r"\b[0-9]{8,10}:[A-Za-z0-9_-]{30,}\b", r"gh[pousr]_[A-Za-z0-9]{20,}", r"github_pat_", r"sk-ant-", r"eyJ[A-Za-z0-9_-]{20,}\."):
            self.assertIsNone(re.search(pat, blob), pat)

    def test_the_answer_is_saved_only_while_the_batch_still_waits(self):
        save = next(n for n in self.wf["nodes"] if n["name"] == "Save the Answer")
        conds = save["parameters"]["filters"]["conditions"]
        self.assertEqual(save["parameters"]["matchType"], "allConditions")
        self.assertIn({"keyName": "status", "condition": "eq", "keyValue": "waiting"}, conds)
        self.assertIn({"keyName": "id", "condition": "eq", "keyValue": "={{ $json.row_id }}"}, conds)


if __name__ == "__main__":
    unittest.main()
