"""Tests for the Claude API copy step (page_builder/copy_step.py). No real API call is made: a stand-in client returns prepared answers,
so these run offline, cost nothing and need no key."""
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from page_builder import copy_contract, copy_step
from page_builder.assemble import build_pdp
from page_builder.examples import fixtures


class Block:
    def __init__(self, type_, text=""):
        self.type, self.text = type_, text


class Usage:
    def __init__(self, i=1200, o=150, cache_read=0, cache_write=0):
        self.input_tokens, self.output_tokens = i, o
        self.cache_read_input_tokens, self.cache_creation_input_tokens = cache_read, cache_write


class Resp:
    def __init__(self, content, stop="end_turn", model="claude-opus-5-5", usage=None):
        self.content, self.stop_reason, self.model = content, stop, model
        self.usage = usage or Usage()
        self._request_id = "req_test_1"


def answer(slots: dict, *, thinking_first=True, **kw) -> Resp:
    content = ([Block("thinking", "")] if thinking_first else []) + [Block("text", json.dumps({"slots": slots}))]
    return Resp(content, **kw)


class FakeClient:
    """Records every call; returns `resp`, or raises `exc`."""

    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.calls = resp, exc, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: self._call("beta", kw)))
        self.messages = SimpleNamespace(create=lambda **kw: self._call("plain", kw))

    def _call(self, kind, kw):
        self.calls.append((kind, kw))
        if self.exc:
            raise self.exc
        return self.resp


def toilova():
    return fixtures.toilova()


def current_slots(brand, facts) -> dict:
    return {s["slot"]: s["current"] for s in copy_contract.list_slots(build_pdp(brand, facts))}


def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


class DryRunTests(unittest.TestCase):
    def test_dry_run_calls_nothing_and_keeps_the_page(self):
        b, f = toilova()
        out = copy_step.run_copy_step(b, f)
        self.assertEqual((out.mode, out.status), ("dry-run", "not-run"))
        self.assertEqual(out.result.template, build_pdp(b, f).template)
        self.assertEqual(out.slots_sent, len(current_slots(b, f)))
        self.assertIsNone(out.cost_usd)

    def test_request_uses_the_current_api_shape(self):
        b, f = toilova()
        p = copy_step.run_copy_step(b, f).params
        self.assertEqual(p["model"], "claude-opus-5-5")
        self.assertNotIn("thinking", p)  # thinking cannot be switched off on this model; effort is the control
        self.assertNotIn("temperature", p)
        self.assertEqual(p["output_config"]["effort"], copy_step.EFFORT)
        fmt = p["output_config"]["format"]
        self.assertEqual(fmt["type"], "json_schema")
        objects = [n for n in walk(fmt["schema"]) if n.get("type") == "object"]
        self.assertTrue(objects)
        for o in objects:  # structured outputs accept only closed objects
            self.assertIs(o.get("additionalProperties"), False)
        text = json.dumps(fmt["schema"])
        for unsupported in ("maxLength", "minLength", "minimum", "maximum"):
            self.assertNotIn(unsupported, text)
        self.assertEqual(sorted(fmt["schema"]["properties"]["slots"]["required"]), sorted(current_slots(b, f)))
        self.assertEqual((p["betas"], p["fallbacks"]), (["server-side-fallback-2026-07-01"], "default"))

    def test_only_signposts_are_sent_never_fact_text(self):
        b, f = toilova()
        sent = copy_step.run_copy_step(b, f).params["messages"][0]["content"]
        self.assertIn("Why choose TOILOVA?", sent)
        for fact in ("Foam that reaches every corner.", "No toxic fumes.", "Sprinkle the sachet, wait, and flush. No brush."):
            self.assertNotIn(fact, sent)

    def test_without_fallbacks_the_plain_endpoint_is_used(self):
        b, f = toilova()
        client = FakeClient(answer({}))
        copy_step.run_copy_step(b, f, client=client, fallbacks=False)
        kind, kw = client.calls[0]
        self.assertEqual(kind, "plain")
        self.assertNotIn("betas", kw)
        self.assertNotIn("fallbacks", kw)

    def test_prompt_version_is_a_stable_short_fingerprint(self):
        self.assertRegex(copy_step.prompt_version(), r"^[0-9a-f]{12}$")
        self.assertEqual(copy_step.prompt_version(), copy_step.prompt_version())


class LiveAnswerTests(unittest.TestCase):
    def test_good_lines_are_applied_and_recorded_as_validated_copy(self):
        b, f = toilova()
        slots = current_slots(b, f)
        slots["dtj_why.heading"] = "Why people pick TOILOVA"
        client = FakeClient(answer(slots))
        out = copy_step.run_copy_step(b, f, client=client)
        self.assertEqual(out.status, "applied")
        self.assertEqual(out.accepted, {"dtj_why.heading": "Why people pick TOILOVA"})
        self.assertTrue(out.result.ok)
        rec = out.result.model.prov[("dtj_why", "heading")]
        self.assertEqual((rec["kind"], rec["text"]), ("copy", "Why people pick TOILOVA"))
        self.assertEqual(client.calls[0][0], "beta")

    def test_rule_breaking_lines_keep_the_template_wording(self):
        b, f = toilova()
        slots = current_slots(b, f)
        slots["dtj_faq.heading"] = "Best answers, guaranteed"
        slots["dtj_why.heading"] = "77 reasons for TOILOVA"
        slots["dtj_inside.heading"] = "<b>What's in the box</b>"
        out = copy_step.run_copy_step(b, f, client=FakeClient(answer(slots)))
        self.assertEqual(out.status, "no-changes")
        self.assertEqual(set(out.rejected), {"dtj_faq.heading", "dtj_why.heading", "dtj_inside.heading"})
        self.assertIn("claim", out.rejected["dtj_faq.heading"])
        self.assertIn("77", out.rejected["dtj_why.heading"])
        self.assertEqual(out.result.template, build_pdp(b, f).template)

    def test_unchanged_lines_are_not_counted_as_rewrites(self):
        b, f = toilova()
        out = copy_step.run_copy_step(b, f, client=FakeClient(answer(current_slots(b, f))))
        self.assertEqual(out.status, "no-changes")
        self.assertFalse([v for v in out.result.model.prov.values() if v["kind"] == "copy"])

    def test_the_answer_may_start_with_a_thinking_block(self):
        b, f = toilova()
        slots = current_slots(b, f)
        slots["dtj_faq.heading"] = "Your questions"
        self.assertEqual(copy_step.run_copy_step(b, f, client=FakeClient(answer(slots, thinking_first=True))).status, "applied")
        self.assertEqual(copy_step.run_copy_step(b, f, client=FakeClient(answer(slots, thinking_first=False))).status, "applied")


class ClaudeCodeAnswerTests(unittest.TestCase):
    """The copy written by a Claude Code session instead of the API: same request, same gate."""

    def test_request_file_carries_the_same_prompt_and_slots(self):
        b, f = toilova()
        req = copy_step.copy_request(build_pdp(b, f))
        self.assertEqual(req["system"], copy_step.system_prompt())
        self.assertEqual(set(req["answer_schema"]["properties"]["slots"]["required"]), set(current_slots(b, f)))
        self.assertNotIn("response_schema", req["request"])

    def test_answer_goes_through_the_same_gate(self):
        b, f = toilova()
        slots = current_slots(b, f)
        slots["dtj_why.heading"] = "Why people pick TOILOVA"
        slots["dtj_faq.heading"] = "Best answers, guaranteed"
        out = copy_step.apply_copy_answer(b, f, {"slots": slots})
        self.assertEqual((out.mode, out.status), ("claude-code", "applied"))
        self.assertEqual(out.accepted, {"dtj_why.heading": "Why people pick TOILOVA"})
        self.assertIn("claim", out.rejected["dtj_faq.heading"])
        self.assertEqual(copy_step.apply_copy_answer(b, f, None).status, "bad-json")
        self.assertEqual(copy_step.apply_copy_answer(b, f, "text").result.template, build_pdp(b, f).template)


class FailureTests(unittest.TestCase):
    def assert_template_kept(self, out, status):
        b, f = toilova()
        self.assertEqual(out.status, status)
        self.assertEqual(out.accepted, {})
        self.assertEqual(out.result.template, build_pdp(b, f).template)

    def test_a_refusal_keeps_the_template_wording(self):
        b, f = toilova()
        self.assert_template_kept(copy_step.run_copy_step(b, f, client=FakeClient(Resp([], stop="refusal"))), "refusal")

    def test_a_cut_off_answer_keeps_the_template_wording(self):
        b, f = toilova()
        out = copy_step.run_copy_step(b, f, client=FakeClient(Resp([Block("text", '{"slots": {"dtj_why.he')], stop="max_tokens")))
        self.assert_template_kept(out, "cut-off")

    def test_an_api_error_is_recorded_not_raised(self):
        b, f = toilova()
        out = copy_step.run_copy_step(b, f, client=FakeClient(exc=TimeoutError("timed out")))
        self.assert_template_kept(out, "api-error")
        self.assertIn("TimeoutError", out.error)
        self.assertEqual(out.usage, {})

    def test_bad_json_keeps_the_template_wording(self):
        b, f = toilova()
        self.assert_template_kept(copy_step.run_copy_step(b, f, client=FakeClient(Resp([Block("text", "not json")]))), "bad-json")

    def test_a_rewritten_page_that_fails_lint_falls_back(self):
        b, f = toilova()
        slots = current_slots(b, f)
        slots["dtj_why.heading"] = "Why people pick TOILOVA"
        real = copy_step.build_pdp
        calls = []

        def fake_build(brand, facts, **kw):
            res = real(brand, facts, **kw)
            calls.append(kw)
            if kw.get("copy_overrides"):
                res.report["lint"].append({"rule": "L01", "severity": "error", "message": "forced for the test"})
            return res

        with mock.patch.object(copy_step, "build_pdp", fake_build):
            out = copy_step.run_copy_step(b, f, client=FakeClient(answer(slots)))
        self.assertEqual(out.status, "lint-fallback")
        self.assertTrue(out.lint_errors)
        self.assertNotIn(("dtj_why", "heading"), [k for k, v in out.result.model.prov.items() if v["kind"] == "copy"])


class CostTests(unittest.TestCase):
    def test_cost_comes_from_reported_usage_and_listed_prices(self):
        b, f = toilova()
        out = copy_step.run_copy_step(b, f, client=FakeClient(answer({}, usage=Usage(i=1000, o=200))))
        self.assertEqual(out.cost_usd, round((1000 * 4.00 + 200 * 20.00) / 1_000_000, 6))
        self.assertEqual(out.usage["input_tokens"], 1000)
        self.assertEqual(out.request_id, "req_test_1")

    def test_a_run_served_by_another_model_reports_tokens_but_no_cost(self):
        b, f = toilova()
        out = copy_step.run_copy_step(b, f, client=FakeClient(answer({}, model="claude-opus-4-8")))
        self.assertIsNone(out.cost_usd)
        self.assertEqual(out.served_by, "claude-opus-4-8")

    def test_the_report_never_contains_a_key(self):
        b, f = toilova()
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test-not-a-real-key"}):
            out = copy_step.run_copy_step(b, f, client=FakeClient(answer({})))
            self.assertNotIn("sk-ant", json.dumps(out.as_report()) + json.dumps(out.params))


if __name__ == "__main__":
    unittest.main()
