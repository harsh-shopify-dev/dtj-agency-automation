"""The code nodes of "Reel Factory: Find References" run in Node exactly as n8n runs them (../store-factory/node_harness.py). The
.js files are the source of truth: deploy_find_refs.py sends them to n8n byte for byte. The Apify outputs below are trimmed copies of
the sample outputs on the actors' Apify Store pages (the field names the readers rely on), with made-up values.

    python -m unittest discover -s n8n/reel-factory -t n8n/reel-factory
"""
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "store-factory"))
from node_harness import HAS_NODE  # noqa: E402
from node_harness import run_node as _run  # noqa: E402

ADMINS = [{"telegram_user_id": "111", "name": "Harsh", "role": "admin", "active": True},
          {"telegram_user_id": "222", "name": "Asha", "role": "designer", "active": True},
          {"telegram_user_id": "333", "name": "Old", "role": "admin", "active": False}]
WATCH = [{"brand": "Mamaearth", "niche": "skincare", "instagram": "@mamaearth.in", "pinterest_query": "onion hair oil video",
          "meta_advertiser": "Mamaearth", "per_source": 4, "active": True},
         {"brand": "Paused", "niche": "tea", "instagram": "paused", "pinterest_query": "", "meta_advertiser": "", "active": False}]


def ago(**kw) -> str:
    return (datetime.now(timezone.utc) - timedelta(**kw)).strftime("%Y-%m-%dT%H:%M:%S.000Z")


@unittest.skipUnless(HAS_NODE, "Node.js is needed to run n8n code nodes")
class Nodes(unittest.TestCase):
    def run_node(self, name, given, refs=None):
        got = _run(HERE / name, given, refs or {})
        self.assertTrue(got["ok"], got)
        return [i["json"] for i in got["out"]]

    # ---- Plan the Searches
    def plan(self, bot=None, watch=WATCH, audiences=None):
        refs = {"Load Bot Users": ADMINS, "Load Watchlist": watch, "Load Audiences": audiences or [{}]}
        if bot is not None:
            refs["From the Telegram Bot"] = bot
        return self.run_node("refs_plan.js", [{}], refs)

    def test_a_handle_from_the_bot_searches_all_three_sources_with_its_limit(self):
        out = self.plan({"query": "@boat.nirvana", "sources": "", "limit": "3", "requested_by": "Harsh", "chat_id": "111"})
        self.assertEqual(sorted(p["source"] for p in out), ["instagram", "meta", "pinterest"])
        for p in out:
            self.assertEqual((p["mode"], p["chat_ids"], p["found_for"], p["keep_n"]), ("bot", ["111"], "Harsh", 3))
            self.assertEqual(p["max_items"], 9 if p["source"] == "meta" else 3)   # ads: 3x, the longest running are kept
            self.assertTrue(p["actor"] and p["input"] and p["max_usd"] > 0, p)
        ig = next(p for p in out if p["source"] == "instagram")
        self.assertIn("boat.nirvana", json.dumps(ig["input"]))
        self.assertEqual(self.plan({"query": "@sugar_official", "sources": "pinterest", "limit": "", "chat_id": "1"})[0]["input"]["queries"],
                         ["sugar"])

    def test_sources_and_limits_are_checked(self):
        out = self.plan({"query": "#skincareindia", "sources": "ig, ads", "limit": "500", "requested_by": "Harsh", "chat_id": "111"})
        self.assertEqual(sorted(p["source"] for p in out), ["instagram", "meta"])
        self.assertTrue(all(p["keep_n"] == 10 and p["max_items"] <= 30 for p in out))   # never more than 10 per source
        bad = self.plan({"query": "", "sources": "tiktok", "limit": "", "requested_by": "Harsh", "chat_id": "111"})
        self.assertEqual(len(bad), 1)
        self.assertFalse(bad[0].get("actor"))
        self.assertTrue(bad[0]["summary"])
        self.assertEqual(bad[0]["chat_id"], "111")
        self.assertIn("/refs", bad[0]["text"])

    def test_a_watchlist_brand_by_name_uses_its_row(self):
        out = self.plan({"query": "mamaearth", "sources": "pinterest", "limit": "", "requested_by": "Asha", "chat_id": "222"})
        self.assertEqual(len(out), 1)
        self.assertIn("onion hair oil video", json.dumps(out[0]["input"]))
        self.assertEqual((out[0]["brand"], out[0]["niche"], out[0]["keep_n"], out[0]["query"]), ("Mamaearth", "skincare", 4, "onion hair oil video"))

    def test_the_weekly_scan_covers_active_rows_and_tells_active_admins(self):
        out = self.plan()
        self.assertEqual(sorted(p["source"] for p in out), ["instagram", "meta", "pinterest"])   # the paused row is left out
        self.assertTrue(all(p["mode"] == "weekly" and p["chat_ids"] == ["111"] and p["found_for"] == "weekly scan" for p in out))
        self.assertEqual(self.plan(watch=[{}]), [])   # an empty watchlist: nothing to do, nothing sent

    # ---- Read the Results
    def test_each_source_is_read_into_library_rows_and_failures_are_reported(self):
        plans = [{"source": "instagram", "query": "@boat.nirvana", "actor": "apify/instagram-reel-scraper", "keep_n": 3, "brand": "",
                  "found_for": "Harsh"},
                 {"source": "pinterest", "query": "skincare ugc video", "actor": "apt_marble/pinterest-video-scraper", "keep_n": 3},
                 {"source": "meta", "query": "boat", "actor": "automation-lab/facebook-ads-library", "keep_n": 2, "brand": "boAt"},
                 {"source": "meta", "query": "x", "actor": "apify/facebook-ads-scraper", "keep_n": 2},
                 {"source": "instagram", "query": "#none", "actor": "apify/instagram-hashtag-scraper", "keep_n": 3}]
        answers = [
            {"statusCode": 201, "body": [
                {"url": "https://www.instagram.com/reel/A1/", "videoUrl": "https://scontent.cdninstagram.com/v/a.mp4?x=1", "caption": "Bass",
                 "videoPlayCount": 1200, "likesCount": 30, "ownerUsername": "boat.nirvana", "timestamp": "2026-10-01T10:00:00.000Z",
                 "productType": "clips"},
                {"url": "https://www.instagram.com/p/B2/", "caption": "a photo", "productType": "feed"}]},
            {"statusCode": 201, "body": [{"url": "https://www.pinterest.com/pin/9/", "mp4Url": "https://v1.pinimg.com/videos/a_720w.mp4",
                                          "title": "Glow", "saveCount": 260, "creatorUsername": "glow", "createdAt": "2026-01-10T11:01:14.000Z"}]},
            {"statusCode": 201, "body": [
                {"adArchiveId": "1", "adLibraryUrl": "https://www.facebook.com/ads/library/?id=1", "pageName": "boAt", "startDate": ago(days=10)[:10],
                 "bodyText": "new", "videoUrls": ["https://video.xx.fbcdn.net/1.mp4"]},
                {"adArchiveId": "2", "adLibraryUrl": "https://www.facebook.com/ads/library/?id=2", "pageName": "boAt", "startDate": ago(days=90)[:10],
                 "bodyText": "old", "videoUrls": ["https://video.xx.fbcdn.net/2.mp4"]},
                {"adArchiveId": "3", "adLibraryUrl": "https://www.facebook.com/ads/library/?id=3", "pageName": "boAt", "startDate": ago(days=40)[:10],
                 "bodyText": "image ad", "videoUrls": []}]},
            {"statusCode": 402, "body": {"error": {"type": "not-enough-usage", "message": "Not enough credit (Bearer abc123)"}}},
            {"statusCode": 201, "body": []}]
        out = self.run_node("refs_read.js", answers, {"Plan the Searches": plans})
        rows, marker = out[:-1], out[-1]
        self.assertEqual([(r["source"], r["url"]) for r in rows],
                         [("instagram", "https://www.instagram.com/reel/A1/"), ("pinterest", "https://www.pinterest.com/pin/9/"),
                          ("meta", "https://www.facebook.com/ads/library/?id=2"), ("meta", "https://www.facebook.com/ads/library/?id=1")])
        ig, pin, old_ad = rows[0], rows[1], rows[2]
        self.assertEqual((ig["views"], ig["likes"], ig["brand"], ig["found_for"], ig["keep"]), (1200, 30, "boat.nirvana", "Harsh", ""))
        self.assertEqual((pin["video_url"], pin["likes"], pin["views"]), ("https://v1.pinimg.com/videos/a_720w.mp4", 260, None))
        self.assertEqual((old_ad["days_running"], old_ad["brand"], old_ad["caption"]), (90, "boAt", "old"))
        self.assertEqual((marker["marker"], marker["url"], marker["found"]), (True, "", 4))
        self.assertEqual(len(marker["problems"]), 2)
        self.assertIn("Not enough credit", marker["problems"][0])
        self.assertNotIn("abc123", marker["problems"][0])
        self.assertIn("#none: nothing found", marker["problems"][1])

    def test_the_fallback_ad_actor_and_a_failed_call_are_read_too(self):
        plans = [{"source": "meta", "query": "x", "actor": "apify/facebook-ads-scraper", "keep_n": 5}, {"source": "pinterest", "query": "y"}]
        answers = [{"statusCode": 201, "body": [{"adArchiveID": "77", "pageName": "Brand", "startDate": 1700000000,
                                                 "snapshot": {"body": {"text": "hi"}, "videos": [{"videoHdUrl": "https://video.fbcdn.net/hd.mp4"}]}}]},
                   {"error": {"message": "Credentials not found"}}]
        out = self.run_node("refs_read.js", answers, {"Plan the Searches": plans})
        self.assertEqual(out[0]["url"], "https://www.facebook.com/ads/library/?id=77")
        self.assertEqual(out[0]["video_url"], "https://video.fbcdn.net/hd.mp4")
        self.assertGreater(out[0]["days_running"], 700)
        self.assertEqual(out[-1]["problems"], ["pinterest y: Credentials not found"])

    # ---- Pick the New Ones
    def test_only_new_links_are_kept_once_and_an_empty_run_still_reaches_the_digest(self):
        rows = [{"source": "instagram", "url": "https://www.instagram.com/reel/A1/", "video_url": "https://cdn/a.mp4", "views": 5},
                {"source": "instagram", "url": "https://www.instagram.com/reel/A1/", "video_url": "https://cdn/a.mp4"},
                {"marker": True, "url": "", "found": 3, "problems": []}]
        out = self.run_node("refs_pick_new.js", rows)
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["url"], out[0]["views"], out[0]["likes"], out[0]["keep"]), ("https://www.instagram.com/reel/A1/", 5, None, ""))
        self.assertNotIn("marker", out[0])
        self.assertEqual(self.run_node("refs_pick_new.js", [{}]), [{"url": ""}])

    # ---- Write the Digest
    def digest(self, saved, plans, marker):
        return self.run_node("refs_digest.js", saved, {"Plan the Searches": plans, "Read the Results": [marker]})

    def test_the_digest_is_a_summary_then_one_message_per_reference_with_keep_and_skip(self):
        plans = [{"mode": "bot", "label": "@boat.nirvana", "query": "@boat.nirvana", "chat_ids": ["111"]}]
        saved = [{"id": 41, "source": "instagram", "url": "https://www.instagram.com/reel/A1/", "brand": "boAt", "caption": "Bass <3",
                  "views": 1250000, "likes": 30200},
                 {"id": 42, "source": "meta", "url": "https://www.facebook.com/ads/library/?id=9", "brand": "boAt", "days_running": 63}]
        out = self.digest(saved, plans, {"marker": True, "found": 3, "problems": ["pinterest: Apify said 402"]})
        self.assertEqual(len(out), 3)
        head = out[0]
        self.assertTrue(head["summary"])
        for must in ("2 new reference videos", "Meta Ad Library 1", "Instagram 1", "1 found were already", "Notes: pinterest: Apify said 402", "Keep"):
            self.assertIn(must, head["text"])
        self.assertEqual([o["keep_data"] for o in out[1:]], ["a:refs-42:keep:0", "a:refs-41:keep:0"])  # long-running ads first
        self.assertEqual(out[2]["skip_data"], "a:refs-41:keep:1")
        self.assertIn("1.3M views", out[2]["text"])
        self.assertIn("Bass &lt;3", out[2]["text"])
        self.assertIn("running 63 days", out[1]["text"])
        for o in out:
            self.assertLessEqual(len(o["keep_data"]), 64)

    def test_nothing_new_is_one_summary_and_the_weekly_digest_goes_to_every_admin(self):
        plans = [{"mode": "weekly", "chat_ids": ["111", "444"]}]
        out = self.digest([{"url": ""}], plans, {"marker": True, "found": 2, "problems": []})
        self.assertEqual([(o["chat_id"], o["summary"]) for o in out], [("111", True), ("444", True)])
        self.assertIn("No new reference videos from the weekly scan", out[0]["text"])

    # ---- Match the Taps
    def test_the_last_recent_tap_per_reference_decides(self):
        rows = [{"id": 1, "job": "refs-41", "key": "keep", "value": "Keep", "choice": "0", "by": "Harsh", "at": ago(minutes=30)},
                {"id": 2, "job": "refs-41", "key": "keep", "value": "Skip", "choice": "1", "by": "Asha", "at": ago(minutes=5)},
                {"id": 3, "job": "refs-42", "key": "keep", "value": "Keep", "choice": "0", "by": "Harsh", "at": ago(days=5)},
                {"id": 4, "job": "store-x", "key": "keep", "value": "Keep", "choice": "0", "by": "Harsh", "at": ago(minutes=1)},
                {"id": 5, "job": "refs-43", "key": "keep", "value": "Keep", "choice": "", "by": "", "at": ago(minutes=2)}]
        out = sorted(self.run_node("refs_taps.js", rows), key=lambda r: r["row_id"])
        self.assertEqual([(r["row_id"], r["keep"], r["kept_by"]) for r in out],
                         [(41, "no", "Asha"), (43, "yes", "someone on the DTJ bot")])
        self.assertEqual(self.run_node("refs_taps.js", [{}]), [])

    # ---- audience scans (25 Oct 2026)
    def test_an_audience_scan_from_the_bot_plans_reels_followers_and_trending_audio(self):
        out = self.plan({"mode": "audience", "audience": "Gen Z urban India", "hashtags": "#genz, aesthetic", "creators": '["@Rj.Abhinav", "https://www.instagram.com/komal.pandey/"]',
                         "limit": "3", "requested_by": "Harsh", "chat_id": "111"})
        kinds = [(p["kind"], p["query"], p["actor"]) for p in out]
        self.assertEqual(kinds, [("audience", "#genz", "apify/instagram-hashtag-scraper"), ("audience", "#aesthetic", "apify/instagram-hashtag-scraper"),
                                 ("audience", "@rj.abhinav", "apify/instagram-reel-scraper"), ("audience", "@komal.pandey", "apify/instagram-reel-scraper"),
                                 ("profiles", "@rj.abhinav @komal.pandey", "apify/instagram-profile-scraper"),
                                 ("trending", "trending Reels audio, India", "s_actors/instagram-trending-audio")])
        for p in out:
            self.assertEqual((p["audience"], p["slug"], p["chat_ids"], p["mode"]), ("Gen Z urban India", "gen-z-urban-india", ["111"], "bot"))
            self.assertLessEqual(p["max_usd"], 0.5)
        self.assertEqual(out[0]["input"], {"hashtags": ["genz"], "resultsType": "reels", "resultsLimit": 3})
        self.assertEqual(out[4]["input"], {"usernames": ["rj.abhinav", "komal.pandey"]})
        self.assertEqual(out[5]["input"]["countries"], ["IN"])
        self.assertEqual(out[5]["max_items"], 3)
        big = self.plan({"mode": "audience", "audience": "Moms", "hashtags": "momlife", "limit": "", "chat_id": "111"})
        self.assertEqual(big[0]["keep_n"], 30)          # default 30 reels per hashtag or creator, never more
        self.assertEqual([p["kind"] for p in big], ["audience", "trending"])   # no creators: no follower call

    def test_a_saved_audience_by_name_and_the_weekly_scan_use_dtj_reel_audiences(self):
        saved = [{"audience": "Gujarati home cooks 30-50", "slug": "gujarati-home-cooks", "hashtags": "gujaratifood,gujjurecipes", "creators": "",
                  "per_source": 4, "active": True},
                 {"audience": "Paused", "hashtags": "x1", "active": False}]
        out = self.plan({"mode": "audience", "audience": "gujarati home cooks 30-50", "chat_id": "222"}, audiences=saved)
        self.assertEqual([p["query"] for p in out], ["#gujaratifood", "#gujjurecipes", "trending Reels audio, India"])
        self.assertEqual((out[0]["slug"], out[0]["keep_n"]), ("gujarati-home-cooks", 4))
        weekly = self.plan(watch=[{}], audiences=saved)
        self.assertEqual([p["query"] for p in weekly], ["#gujaratifood", "#gujjurecipes", "trending Reels audio, India"])
        self.assertTrue(all(p["chat_ids"] == ["111"] and p["mode"] == "weekly" for p in weekly))
        bad = self.plan({"mode": "audience", "audience": "", "hashtags": "", "chat_id": "222"})
        self.assertEqual(len(bad), 1)
        self.assertIn("audience scan needs", bad[0]["text"])

    def test_audience_reels_get_followers_comments_audio_and_are_ranked(self):
        common = {"source": "audience", "audience": "Gen Z", "keep_n": 3, "found_for": "Harsh"}
        plans = [{**common, "kind": "audience", "query": "#genz", "actor": "apify/instagram-hashtag-scraper"},
                 {**common, "kind": "audience", "query": "@big", "actor": "apify/instagram-reel-scraper"},
                 {**common, "kind": "profiles", "query": "@big", "actor": "apify/instagram-profile-scraper"},
                 {**common, "kind": "trending", "source": "trending_audio", "query": "trending Reels audio, India", "keep_n": 3}]
        reel = lambda code, owner, views, comments, song="Original audio": {  # noqa: E731
            "url": f"https://www.instagram.com/reel/{code}/", "videoUrl": f"https://cdn/{code}.mp4", "ownerUsername": owner, "videoPlayCount": views,
            "likesCount": 10, "commentsCount": comments, "caption": "c", "productType": "clips",
            "musicInfo": {"song_name": song, "artist_name": owner}}
        answers = [{"statusCode": 201, "body": [reel("H1", "small", 50000, 500), reel("H2", "mid", 900000, 90)]},
                   {"statusCode": 201, "body": [reel("B1", "big", 2000000, 200, "Kesariya")]},
                   {"statusCode": 201, "body": [{"username": "big", "followersCount": 4000000}]},
                   {"statusCode": 201, "body": [{"title": "Sahiba", "artist": "Aditya Rikhari", "audioUrl": "https://www.instagram.com/reels/audio/1/",
                                                 "reelsCountText": "23.2K reels", "isTrending": True, "isOriginalAudio": False}]}]
        out = self.run_node("refs_read.js", answers, {"Plan the Searches": plans})
        rows, marker = out[:-1], out[-1]
        sound = rows[0]
        self.assertEqual((sound["source"], sound["url"], sound["video_url"], sound["audio_name"], sound["audience"]),
                         ("trending_audio", "https://www.instagram.com/reels/audio/1/", "", "Sahiba · Aditya Rikhari", "Gen Z"))
        self.assertIn("23.2K reels", sound["caption"])
        reels = rows[1:]
        self.assertEqual([r["url"][-3:-1] for r in reels], ["B1", "H2", "H1"])   # with followers first, then by views
        b1 = reels[0]
        self.assertEqual((b1["followers"], b1["views_per_follower"], b1["comments"], b1["comments_per_view"], b1["audio_name"], b1["brand"]),
                         (4000000, 0.5, 200, 0.0001, "Kesariya · big", "@big"))
        self.assertIsNone(reels[2]["followers"])
        self.assertEqual(reels[2]["comments_per_view"], 0.01)
        self.assertEqual((marker["by_audience"], marker["found_refs"]), ({"Gen Z": 3}, 0))

    def test_the_audience_summary_is_one_message_without_buttons(self):
        plans = [{"kind": "audience", "source": "audience", "audience": "Gen Z", "slug": "gen-z", "query": "#genz", "chat_ids": ["111"], "mode": "bot"},
                 {"kind": "trending", "source": "trending_audio", "audience": "Gen Z", "slug": "gen-z", "query": "trending Reels audio, India",
                  "chat_ids": ["111"], "mode": "bot"}]
        saved = [{"id": 7, "source": "audience", "audience": "Gen Z", "url": "https://www.instagram.com/reel/A/", "brand": "@a", "views": 1500000,
                  "views_per_follower": 3.25, "comments_per_view": 0.0042, "audio_name": "Original audio · a"},
                 {"id": 8, "source": "audience", "audience": "Gen Z", "url": "https://www.instagram.com/reel/B/", "brand": "@b", "views": 9000},
                 {"id": 9, "source": "trending_audio", "audience": "Gen Z", "url": "https://www.instagram.com/reels/audio/1/", "audio_name": "Sahiba · Aditya Rikhari"}]
        out = self.digest(saved, plans, {"marker": True, "found": 4, "found_refs": 0, "by_audience": {"Gen Z": 3}, "problems": []})
        self.assertEqual(len(out), 1)
        text = out[0]["text"]
        for must in ("Audience scan Gen Z</b>: 2 reels saved (1 more were already in the library), from #genz", "Top 2 by views per follower",
                     "1. <a href=\"https://www.instagram.com/reel/A/\">@a</a> · 1.5M views · 3.3× followers · 0.42% comments · audio Original audio · a",
                     "2. <a", "Trending audio in India: Sahiba · Aditya Rikhari", "audiences/gen-z.md"):
            self.assertIn(must, text)
        self.assertEqual((out[0]["keep_data"], out[0]["summary"]), ("", True))

    def test_the_same_reel_is_saved_once_per_audience(self):
        rows = [{"source": "audience", "audience": "A", "url": "https://x/1"}, {"source": "audience", "audience": "B", "url": "https://x/1"},
                {"source": "audience", "audience": "A", "url": "https://x/1"}]
        out = self.run_node("refs_pick_new.js", rows)
        self.assertEqual([(r["audience"], r["comments"]) for r in out], [("A", None), ("B", None)])


if __name__ == "__main__":
    unittest.main()
