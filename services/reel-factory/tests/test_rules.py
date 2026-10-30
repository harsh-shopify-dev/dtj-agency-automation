"""The reel factory's rules that need no browser, GPU or video: script lint, request check, take pick, caption pages, beat cuts.

    cd services/reel-factory && python -m unittest discover -s tests -t .
"""
import json
import tempfile
import unittest
from pathlib import Path

from reel_factory import beats, captions, checks, job

FACTS = "SENSO Instant Detox Green Tea Kahwa. With natural ingredients. Just add hot water. Net Quantity 3g x 10 Sachets = 30g."


def shot(i, **kw):
    return {"id": f"s{i}", "line": "Just add hot water.", "seconds": 4, "image_prompt": "a", "video_prompt": "handheld selfie", **kw}


class Lint(unittest.TestCase):
    def script(self, shots, **kw):
        return {"language": "en", "shots": shots, **kw}

    def test_a_clean_script_passes(self):
        s = self.script([shot(1), shot(2), shot(3, product=True, video_prompt="handheld selfie; she holds the same box steady, label to camera")])
        self.assertEqual(job.lint_script(s, FACTS), [])

    def test_an_invented_number_is_refused(self):
        bad = job.lint_script(self.script([shot(1), shot(2), shot(3, line="Loved by 10,000 customers")]), FACTS)
        self.assertTrue(any("not in the approved facts" in b for b in bad), bad)

    def test_a_number_in_the_facts_is_allowed(self):
        self.assertEqual(job.lint_script(self.script([shot(1), shot(2), shot(3, line="10 sachets in a box")]), FACTS + " 10 sachets"), [])

    def test_too_many_words_and_odd_lengths(self):
        bad = job.lint_script(self.script([shot(1, line=" ".join(["word"] * 13)), shot(2, seconds=5), shot(3)]), FACTS)
        self.assertTrue(any("too fast" in b for b in bad) and any("seconds must be" in b for b in bad), bad)

    def test_a_product_shot_must_say_how_the_product_stays(self):
        bad = job.lint_script(self.script([shot(1), shot(2), shot(3, product=True, video_prompt="propped phone; she shows the box")]), FACTS)
        self.assertTrue(any("how the product stays" in b for b in bad), bad)

    def test_shot_count_and_language(self):
        bad = job.lint_script({"language": "fr", "shots": [shot(1)]}, FACTS)
        self.assertTrue(any("3 to 10" in b for b in bad) and any("language" in b for b in bad), bad)

    def test_credits_known_only_for_4_and_8_seconds(self):
        self.assertEqual(job.credits([shot(1), shot(2, seconds=8)]), 38)
        self.assertIsNone(job.credits([shot(1, seconds=6)]))


    def test_ai_ad_words_and_a_missing_phone_setup_are_refused(self):
        bad = job.lint_script(self.script([shot(1, image_prompt="cinematic studio portrait, flawless skin"), shot(2, video_prompt="she talks"),
                                           shot(3)]), FACTS)
        self.assertTrue(any("AI-ad words" in b and "cinematic" in b for b in bad), bad)
        self.assertTrue(any("how the phone films it" in b for b in bad), bad)


class Request(unittest.TestCase):
    def test_missing_fields(self):
        self.assertEqual(len(job.check_request({})), 4)
        self.assertIn(f"language must be one of {job.LANGS}",
                      job.check_request({"product_name": "x", "product_images": ["a"], "reference_reels": ["b"], "language": "de"}))


class Pick(unittest.TestCase):
    def test_best_passing_take_wins_and_none_when_all_fail(self):
        a = {"clean": "a", "check": {"ok": True, "visible_pct": 80}}
        b = {"clean": "b", "check": {"ok": True, "visible_pct": 95}}
        c = {"clean": "c", "check": {"ok": False, "visible_pct": 100}}
        self.assertEqual(job.auto_pick([a, b, c])["clean"], "b")
        self.assertIsNone(job.auto_pick([c]))


class Reply(unittest.TestCase):
    def test_no_final_means_could_not_make(self):
        with tempfile.TemporaryDirectory() as d:
            j = job.Job(d)
            self.assertEqual(job.reply_body(j)["reel_status"], "could not make")
            (Path(d) / "final").mkdir()
            (Path(d) / "final" / "qc.json").write_text(json.dumps({"status": "reel ready", "final": "x.mp4", "duration": 26.5,
                                                                    "lufs": -14.0}), encoding="utf-8")
            body = job.reply_body(j)
            self.assertEqual((body["reel_status"], body["duration_s"], body["lufs"]), ("reel ready", 26.5, -14.0))


class Captions(unittest.TestCase):
    def test_pages_never_cross_a_cut_and_skip_opted_out_clips(self):
        words = [("Boil", 0.2, 0.5), ("it.", 0.5, 0.8), ("Ten", 1.0, 1.3), ("whole", 1.3, 1.6), ("minutes.", 1.6, 2.4),
                 ("Senso", 2.7, 3.0), ("Kahwa.", 3.0, 3.6)]
        spans = captions.clip_spans([{"start": 0, "end": 2.5}, {"start": 0, "end": 1.5, "cap_margin": -1}])
        pages = captions.build_pages(words, spans, 4.0)
        self.assertTrue(pages)
        for p in pages:
            self.assertLessEqual(p["startMs"] + p["durationMs"], 2500 + 1)   # nothing on the opted-out second clip
            self.assertLessEqual(len(p["tokens"]), 3)

    def test_skipped_script_words_come_back(self):
        heard = [("add", 0.4, 0.6), ("hot", 0.6, 0.8), ("water", 0.8, 1.2)]
        got = captions.align_to_script(heard, "Just add hot water.")
        self.assertEqual([w[0] for w in got], ["Just", "add", "hot", "water."])


    def test_digits_and_near_spellings_take_the_script_word_once(self):
        heard = [("Boil", 0.1, 0.4), ("it", 0.4, 0.6), ("for", 0.6, 0.7), ("10", 0.7, 1.0), ("whole", 1.0, 1.3), ("minutes.", 1.3, 1.8),
                 ("Arey,", 2.0, 2.5), ("this", 2.6, 2.8)]
        got = [w[0] for w in captions.align_to_script(heard, "Boil it. Ten whole minutes. Arre... this")]
        self.assertEqual(got, ["Boil", "it.", "for", "Ten", "whole", "minutes.", "Arre...", "this"])
        self.assertFalse(captions.same_word("it", "at"))   # words under 4 letters must match exactly


class Beats(unittest.TestCase):
    def test_cuts_land_on_beats(self):
        beat = 60 / 129.2
        out = beats.plan_cuts([{"start": 0, "end": 3.9}, {"start": 0, "end": 3.9}], [(1.5, 3.2), (0.3, 2.9)], beat)
        acc = 0.0
        for c in out:
            acc += c["end"] - c["start"]
            self.assertAlmostEqual(acc / beat, round(acc / beat), delta=0.05)
        self.assertAlmostEqual(out[0]["start"], 0.6, places=2)    # dead air before the first word trimmed to 0.9 s

    def test_a_cut_never_runs_past_the_take(self):
        out = beats.plan_cuts([{"start": 2.37, "end": 4.0, "max_end": 4.0}], [(2.62, 3.96)], 60 / 129.2)
        self.assertLessEqual(out[0]["end"], 4.0)


class Claims(unittest.TestCase):
    def test_numbers_and_result_words_are_found(self):
        self.assertEqual(checks.claims_in("Results in 7 days, clinically proven"), ["7 days", "clinically", "proven"])
        self.assertEqual(checks.claims_in("Loved by 2 lakh families"), ["2 lakh"])
        self.assertEqual(checks.claims_in("Boil it. Ten whole minutes."), [])



class SilentAndNonPhoneShots(unittest.TestCase):
    def test_a_silent_shot_needs_no_words(self):
        from reel_factory.checks import words_check
        self.assertTrue(words_check([], "")["ok"])
        self.assertFalse(words_check([], "Baked not fried")["ok"])

    def test_cinematic_and_founder_are_not_phone_footage(self):
        from reel_factory.job import animation
        self.assertTrue(animation({"style": "cinematic"}))
        self.assertTrue(animation({"style": "founder"}))
        self.assertFalse(animation({"style": "ugc"}))
        self.assertFalse(animation({}))


if __name__ == "__main__":
    unittest.main()
