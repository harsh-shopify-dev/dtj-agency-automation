"""Tests for DTJ's social media automation. Run: cd services/smm && python -m unittest discover -s tests"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smm import approve as approve_mod  # noqa: E402
from smm.config import IST, load as load_config  # noqa: E402
from smm.daily import Daily  # noqa: E402
from smm.gate import check_week, numbers_in  # noqa: E402
from smm.http import Http, PublishError, clean  # noqa: E402
from smm.publishers import Job, linkedin, meta, x  # noqa: E402
from smm.results import pull, report  # noqa: E402
from smm.store import Store  # noqa: E402
from smm.week import final_text, load  # noqa: E402

WEEK = "2026-W44"


def good_post(n: int = 1, **over) -> dict:
    post = {
        "id": f"{WEEK}-p{n}", "publish_at": f"2026-10-{25 + n:02d}T19:00:00+05:30", "theme": "client-result", "format": "image",
        "proof_ids": ["sales-royal-dosa-paper"], "media": [{"file": f"media/p{n}.jpg", "alt": "The Royal Dosa Paper's Shopify sales chart"}],
        "overlay_text": ["Real Shopify sales report", "The Royal Dosa Paper", "₹5.28Cr in sales"],
        "platforms": {
            "instagram": {"caption": f"Post {n}. ₹5.28Cr in sales and 75,000 orders.\nLink in bio for your free growth audit.", "hashtags": ["#D2C", "#Shopify"]},
            "facebook": {"caption": f"Post {n}. ₹5.28Cr in sales. Get your free growth audit: {{link}}"},
            "x": {"text": f"Post {n}. ₹5.28Cr in sales from their own Shopify report. Free growth audit: {{link}}"},
        },
    }
    post.update(over)
    return post


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = Store(self.tmp)
        self.folder = self.store.week_folder(WEEK)
        (self.folder / "media").mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_week(self, posts: list[dict]):
        for i, p in enumerate(posts):
            for m in p["media"]:
                path = self.folder / m["file"]
                if not path.exists():
                    Image.new("RGB", (1080, 1350), (i * 40 % 255, 90, 120)).save(path, "JPEG")
        (self.folder / "week.json").write_text(json.dumps({"week": WEEK, "posts": posts}, ensure_ascii=False), encoding="utf-8")
        return load(self.folder)


class GateTests(Base):
    def test_good_post_passes(self):
        wk = self.write_week([good_post()])
        self.assertEqual(check_week(wk), {f"{WEEK}-p1": []})

    def test_number_not_in_cited_proof_is_blocked(self):
        p = good_post()
        p["platforms"]["instagram"]["caption"] = "₹6Cr in sales. Link in bio."
        problems = check_week(self.write_week([p]))[p["id"]]
        self.assertTrue(any("'₹6Cr' is not a figure" in x for x in problems), problems)

    def test_blocked_figures_and_small_counts(self):
        p = good_post(proof_ids=["sales-zebein"], overlay_text=["Up 746%", "3 things we fixed"])
        p["platforms"] = {"facebook": {"caption": "₹3.56Cr in sales {link}"}}
        problems = check_week(self.write_week([p]))[p["id"]]
        self.assertTrue(any("746%" in x and "audit F4" in x for x in problems), problems)
        self.assertFalse(any("'3'" in x for x in problems))
        self.assertTrue(numbers_in("We hit #1 on Google") == ["#1"])
        self.assertEqual(numbers_in("D2C brands"), [])

    def test_blocked_everywhere(self):
        p = good_post(overlay_text=["Trusted by 90+ brands"])
        self.assertTrue(any("90+" in x for x in check_week(self.write_week([p]))[p["id"]]))

    def test_never_say_and_jargon(self):
        p = good_post()
        p["platforms"]["facebook"]["caption"] = "Our automation doubled ROAS, guaranteed. {link}"
        problems = " ".join(check_week(self.write_week([p]))[p["id"]])
        for word in ("automation", "roas", "guaranteed"):
            self.assertIn(word, problems.lower())
        p["explains_jargon"] = True
        problems = " ".join(check_week(self.write_week([p]))[p["id"]])
        self.assertNotIn("'roas'", problems.lower())
        self.assertIn("both of us", "both of us")  # 'bot' must not match inside words
        p2 = good_post()
        p2["platforms"]["facebook"]["caption"] = "Both founders said yes. {link}"
        self.assertEqual(check_week(self.write_week([p2]))[p2["id"]], [])

    def test_platform_rules(self):
        p = good_post()
        p["platforms"]["instagram"]["caption"] = "See {link}"
        p["platforms"]["x"]["text"] = "₹5.28Cr {link} " + "a" * 255
        p["platforms"]["facebook"]["caption"] = "₹5.28Cr https://example.com"
        problems = " ".join(check_week(self.write_week([p]))[p["id"]])
        self.assertIn("link in bio", problems)
        self.assertIn("x text", problems)
        self.assertIn("instead of a typed link", problems)

    def test_picture_shape_and_one_post_per_day(self):
        p1, p2 = good_post(1), good_post(2, publish_at="2026-10-26T21:00:00+05:30")
        wk = self.write_week([p1, p2])
        Image.new("RGB", (1080, 400)).save(self.folder / "media" / "p1.jpg", "JPEG")
        report_ = check_week(wk)
        self.assertTrue(any("shape" in x for x in report_[p1["id"]]))
        self.assertTrue(any("one post a day" in x for x in report_[p2["id"]]))

    def test_ai_person_needs_label(self):
        p = good_post(theme="founder-pain", ai_media={"used": True, "realistic_person": True, "label_on": False})
        self.assertTrue(any("label" in x for x in check_week(self.write_week([p]))[p["id"]]))


class ApproveTests(Base):
    def test_expand(self):
        self.assertEqual(approve_mod.expand(WEEK, "p1,p3-p4"), [f"{WEEK}-p1", f"{WEEK}-p3", f"{WEEK}-p4"])
        with self.assertRaises(approve_mod.ApprovalError):
            approve_mod.expand(WEEK, "all")

    def test_named_yes_records_fingerprint(self):
        self.write_week([good_post()])
        now = datetime(2026, 10, 20, 10, 0, tzinfo=IST)
        with self.assertRaises(approve_mod.ApprovalError):
            approve_mod.approve(self.store, WEEK, "p1", "", now=now)
        lines = approve_mod.approve(self.store, WEEK, "p1", "Riya", harsh_unreachable=True, now=now)
        self.assertIn("Riya (Harsh not reachable)", lines[0])
        rec = self.store.read(self.store.path(WEEK, "approvals", f"{WEEK}-p1"))
        self.assertEqual(rec["fingerprint"], load(self.folder).fingerprint(good_post()))

    def test_failing_post_cannot_be_approved(self):
        p = good_post()
        p["platforms"]["facebook"]["caption"] = "Guaranteed. {link}"
        self.write_week([p])
        with self.assertRaises(approve_mod.ApprovalError):
            approve_mod.approve(self.store, WEEK, "p1", "Harsh", now=datetime(2026, 10, 20, tzinfo=IST))


class FakeTelegram:
    def __init__(self):
        self.sent = []

    def text(self, message):
        self.sent.append(("text", message))

    def files(self, paths, caption=""):
        self.sent.append(("files", [p.name for p in paths], caption))


ENV_LIVE = {"AUTOMATION_ENABLED": "true", "SMM_ENABLED": "true", "SMM_DRY_RUN": "false", "SMM_MODE": "approve",
            "SMM_LIVE_PLATFORMS": "instagram,facebook", "META_PAGE_TOKEN": "t", "META_IG_USER_ID": "1", "META_PAGE_ID": "2",
            "WP_USER": "u", "WP_APP_PASSWORD": "p"}
DUE = datetime(2026, 10, 26, 19, 5, tzinfo=IST)


class DailyTests(Base):
    def run_daily(self, env, publish=None, now=DUE):
        tg = FakeTelegram()
        calls = []

        def fake_publish(platform, job):
            calls.append((platform, job.texts))
            job.public_urls()
            return {"id": f"{platform}-1", "url": f"https://example/{platform}"}
        d = Daily(load_config(env), self.store, env, tg=tg, out=lambda *_: None, publish=publish or fake_publish,
                  host=lambda path, name, alt: f"https://cdn/{name}")
        d.run(now)
        return tg, calls

    def approve(self):
        approve_mod.approve(self.store, WEEK, "p1", "Harsh", now=datetime(2026, 10, 20, tzinfo=IST))

    def test_unapproved_post_is_not_posted_or_handed(self):
        self.write_week([good_post()])
        tg, calls = self.run_daily(ENV_LIVE)
        self.assertEqual(calls, [])
        self.assertIn("nobody has approved it", tg.sent[-1][1])
        self.assertFalse((self.folder / "handed").exists())

    def test_live_platforms_post_others_go_to_a_person(self):
        self.write_week([good_post()])
        self.approve()
        tg, calls = self.run_daily(ENV_LIVE)
        self.assertEqual(sorted(c[0] for c in calls), ["facebook", "instagram"])
        fb = dict(calls)["facebook"]["caption"]
        self.assertIn("utm_source=facebook", fb)
        self.assertIn("utm_content=2026-W44-p1", fb)
        self.assertTrue(self.store.path(WEEK, "published", f"{WEEK}-p1", "instagram").exists())
        self.assertEqual(sum(1 for s in tg.sent if s[0] == "files"), 1)
        handed = self.store.read(self.store.path(WEEK, "handed", f"{WEEK}-p1", "x"))
        self.assertIn("SMM_LIVE_PLATFORMS", handed["reason"])
        log = [json.loads(line) for line in (self.tmp / "log" / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sorted(r["result"] for r in log), ["recommended", "success", "success"])
        # second run: nothing again
        tg2, calls2 = self.run_daily(ENV_LIVE, now=DUE + timedelta(hours=1))
        self.assertEqual(calls2, [])

    def test_kill_switch_and_dry_run_post_nothing(self):
        self.write_week([good_post()])
        self.approve()
        for env in ({**ENV_LIVE, "AUTOMATION_ENABLED": "false"}, {**ENV_LIVE, "SMM_DRY_RUN": "true"}, {**ENV_LIVE, "SMM_MODE": "shadow"}):
            shutil.rmtree(self.folder / "handed", ignore_errors=True)
            tg, calls = self.run_daily(env)
            self.assertEqual(calls, [])
            self.assertTrue(any(s[0] == "files" for s in tg.sent))

    def test_changed_after_approval_is_blocked(self):
        self.write_week([good_post()])
        self.approve()
        Image.new("RGB", (1080, 1350), (1, 2, 3)).save(self.folder / "media" / "p1.jpg", "JPEG")
        tg, calls = self.run_daily(ENV_LIVE)
        self.assertEqual(calls, [])
        self.assertIn("changed after Harsh approved it", tg.sent[-1][1])

    def test_three_failures_stop(self):
        self.write_week([good_post()])
        self.approve()

        def boom(platform, job):
            raise PublishError("HTTP 400: bad")
        for i in range(4):
            tg, _ = self.run_daily({**ENV_LIVE, "SMM_LIVE_PLATFORMS": "instagram"}, publish=boom, now=DUE + timedelta(hours=i))
        rec = self.store.read(self.store.path(WEEK, "failures", f"{WEEK}-p1", "instagram"))
        self.assertEqual(rec["count"], 3)

    def test_late_posts_are_not_posted(self):
        self.write_week([good_post()])
        self.approve()
        tg, calls = self.run_daily(ENV_LIVE, now=DUE + timedelta(days=2))
        self.assertEqual(calls, [])
        self.assertTrue(any("MISSED" in s[1] for s in tg.sent if s[0] == "text"))

    def test_runway_warning(self):
        self.write_week([good_post()])
        tg, _ = self.run_daily(ENV_LIVE, now=datetime(2026, 10, 24, 9, 0, tzinfo=IST))
        self.assertIn("No approved post yet", tg.sent[-1][1])


class FakeResponse:
    def __init__(self, body=None, status=200, headers=None):
        self.body, self.status_code, self.headers = body or {}, status, headers or {}
        self.text = json.dumps(self.body)
        self.content = self.text.encode()

    def json(self):
        return self.body


class FakeSession:
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        for key, answer in self.answers:
            if key in url:
                return answer(kw) if callable(answer) else answer
        return FakeResponse({})


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.pic = self.tmp / "p.jpg"
        Image.new("RGB", (1080, 1350)).save(self.pic, "JPEG")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def job(self, fmt="image", texts=None):
        post = good_post(format=fmt)
        return Job(post=post, texts=texts or {"caption": "hi (test) #D2C", "text": "hi"}, files=[self.pic], alts=["alt"],
                   public_urls=lambda: ["https://cdn/p.jpg"])

    def test_instagram_image_flow(self):
        s = FakeSession([("/media_publish", FakeResponse({"id": "M1"})), ("/1/media", FakeResponse({"id": "C1"})),
                         ("/C1", FakeResponse({"status_code": "FINISHED"})), ("/M1", FakeResponse({"permalink": "https://ig/p/1"}))])
        out = meta.instagram(self.job(), Http(s, sleep=lambda _: None), ENV_LIVE, sleep=lambda _: None)
        self.assertEqual(out, {"id": "M1", "url": "https://ig/p/1"})
        self.assertIn("v26.0", s.calls[0][1])
        self.assertEqual(s.calls[0][2]["data"]["image_url"], "https://cdn/p.jpg")

    def test_instagram_error_status(self):
        s = FakeSession([("/1/media", FakeResponse({"id": "C1"})), ("/C1", FakeResponse({"status_code": "ERROR"}))])
        with self.assertRaises(PublishError):
            meta.instagram(self.job(), Http(s, sleep=lambda _: None), ENV_LIVE, sleep=lambda _: None)

    def test_retry_then_give_up_and_no_token_in_errors(self):
        s = FakeSession([("graph", FakeResponse({"error": "x"}, status=500))])
        with self.assertRaises(PublishError) as ctx:
            Http(s, sleep=lambda _: None).call("GET", "https://graph.facebook.com/v26.0/1?access_token=SECRET")
        self.assertEqual(len(s.calls), 3)
        self.assertNotIn("SECRET", str(ctx.exception))
        self.assertNotIn("123:ABC", clean("https://api.telegram.org/bot123:ABC/sendMessage"))

    def test_linkedin_escapes_and_reads_urn(self):
        self.assertEqual(linkedin.little_text("a (b) #c"), r"a \(b\) \#c")
        s = FakeSession([("/rest/posts", FakeResponse({}, status=201, headers={"x-restli-id": "urn:li:share:9"})),
                         ("initializeUpload", FakeResponse({"value": {"uploadUrl": "https://up/1", "image": "urn:li:image:1"}}))])
        env = {"LINKEDIN_TOKEN": "t", "LINKEDIN_ORG_ID": "42"}
        out = linkedin.publish(self.job(), Http(s, sleep=lambda _: None), env)
        self.assertEqual(out["id"], "urn:li:share:9")
        body = [c for c in s.calls if c[1].endswith("/rest/posts")][0][2]["json"]
        self.assertEqual(body["author"], "urn:li:organization:42")
        self.assertEqual(body["content"]["media"]["id"], "urn:li:image:1")

    def test_x_oauth_signature_is_stable(self):
        env = {"X_API_KEY": "k", "X_API_SECRET": "s", "X_ACCESS_TOKEN": "t", "X_ACCESS_SECRET": "ts"}
        h1 = x.oauth1_header("POST", "https://api.x.com/2/tweets", env, nonce="n", timestamp="1")
        h2 = x.oauth1_header("POST", "https://api.x.com/2/tweets", env, nonce="n", timestamp="1")
        self.assertEqual(h1, h2)
        self.assertIn('oauth_signature="', h1)
        s = FakeSession([("/2/media/upload", FakeResponse({"data": {"id": "77"}})), ("/2/tweets", FakeResponse({"data": {"id": "99"}}, 201))])
        out = x.publish(self.job(texts={"text": "hello"}), Http(s, sleep=lambda _: None), env)
        self.assertEqual(out["id"], "99")
        self.assertEqual(s.calls[-1][2]["json"]["media"]["media_ids"], ["77"])


class TextAndResultsTests(Base):
    def test_final_text_adds_link_and_hashtags(self):
        p = good_post()
        ig = final_text(p, "instagram", "https://digitaltusharjoshi.com/free-growth-audit")
        self.assertTrue(ig["caption"].endswith("#D2C #Shopify"))
        fb = final_text(p, "facebook", "https://digitaltusharjoshi.com/free-growth-audit")
        self.assertIn("https://digitaltusharjoshi.com/free-growth-audit?utm_source=facebook", fb["caption"])

    def test_config_rejects_other_sites(self):
        with self.assertRaises(Exception):
            load_config({"SMM_AUDIT_URL": "https://evil.example"})

    def test_results_pull_and_report(self):
        self.write_week([good_post()])
        self.store.write(self.store.path(WEEK, "published", f"{WEEK}-p1", "instagram"),
                         {"at": "2026-10-26T13:30:00+00:00", "id": "M1", "url": "https://ig/p/1"})
        s = FakeSession([("/M1/insights", FakeResponse({"data": [{"name": "views", "values": [{"value": 1200}]},
                                                                  {"name": "reach", "values": [{"value": 900}]}]}))])
        n = pull(self.store, ENV_LIVE, Http(s, sleep=lambda _: None), now=datetime(2026, 10, 27, 14, 0, tzinfo=timezone.utc))
        self.assertEqual(n, 1)
        text = report(self.store, WEEK)
        self.assertIn("1,200 views", text)
        self.assertIn("Source: Instagram API", text)
        self.assertIn("not available", text)


class DeckTests(Base):
    def test_deck_builds(self):
        from pptx import Presentation

        from smm.deck import build
        wk = self.write_week([good_post(1), good_post(2)])
        out = build(wk, self.tmp / "deck.pptx")
        self.assertEqual(len(Presentation(out).slides), 5)


if __name__ == "__main__":
    unittest.main()
