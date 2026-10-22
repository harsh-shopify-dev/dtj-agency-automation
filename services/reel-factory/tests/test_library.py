import unittest

from reel_factory.adlibrary import squash
from reel_factory.library import features
from reel_factory import slop


class BrandMatch(unittest.TestCase):
    def test_brand_page_and_creator_partnership_match(self):
        self.assertIn(squash("Blue Tea"), squash("BLUE TEA INDIA"))
        self.assertIn(squash("Blue Tea"), squash("faizahfett with BLUE TEA INDIA"))
        self.assertNotIn(squash("Girnar Tea"), squash("Girnar Ayurvedic Pharmacy Pvt Ltd"))


class Slop(unittest.TestCase):
    STYLE = {"ranges": {"hindi_share": {"p20": 0.84, "median": 0.99, "p80": 1.0},
                        "words_per_s": {"p20": 1.71, "median": 2.77, "p80": 3.47}}}

    def test_ad_speak_is_caught(self):
        res = slop.check({"clips": [{"seconds": 4, "spoken_line": "Elevate your mornings with the perfect blend."}]})
        self.assertFalse(res["ok"])
        self.assertTrue(any(t["why"] == "ad-speak" for t in res["tells"]))

    def test_roman_hindi_not_judged_on_devanagari_share(self):
        script = {"language": "hi", "clips": [{"seconds": 4, "spoken_line": "Kuch khaate hi pet phool jaata hai? Senso Kahwa piyo."}]}
        self.assertNotIn("hindi_share", slop.check(script, self.STYLE)["outside_real_range"])

    def test_devanagari_script_is_judged(self):
        script = {"language": "hi", "clips": [{"seconds": 4, "spoken_line": "This is mostly English with one शब्द only here."}]}
        self.assertIn("hindi_share", slop.check(script, self.STYLE)["outside_real_range"])


class Policy(unittest.TestCase):
    def rules(self, line, **extra):
        script = {"ai_label": True, "phrases": ["Senso Detox Green Tea Kahwa"], "clips": [{"seconds": 8, "spoken_line": line}], **extra}
        return [p["rule"] for p in slop.check(script)["policy"]]

    def test_claims_are_caught(self):
        self.assertTrue(any("100%" in r for r in self.rules("Yeh 100% natural hai, aaj hi try karo yaar.")))
        self.assertTrue(any("outcome" in r for r in self.rules("Yeh chai charbi jad se khatam kar degi, try karo.")))
        self.assertTrue(any("body or health" in r for r in self.rules("Kya aapka pet phool jaata hai khaane ke baad?")))
        self.assertTrue(any("customer" in r for r in self.rules("હવે અમારા રસોડામાં આ જ મસાલા આવે છે, તમે પણ ટ્રાય કરો.")))

    def test_product_name_and_label(self):
        self.assertEqual(self.rules("Khaane ke baad ek cup Senso Detox Green Tea Kahwa, bas itna."), [])
        self.assertTrue(any("Video created using AI" in r for r in self.rules("Khaane ke baad ek cup, bas itna.", ai_label=False)))


class Features(unittest.TestCase):
    def test_speech_numbers(self):
        import reel_factory.library as lib
        real, lib.duration = lib.duration, (lambda path: 10.0)
        try:
            ws = [("Kya", 0.0, 0.3), ("aap", 0.3, 0.5), ("chai", 0.5, 0.9), ("peete", 0.9, 1.2), ("ho?", 1.2, 1.5)]
            f = features("x.mp4", ws, [2.0, 5.0])
        finally:
            lib.duration = real
        self.assertEqual(f["first_word_s"], 0.0)
        self.assertEqual(f["words_first_3s"], 5)
        self.assertEqual(f["cuts_per_10s"], 2.0)
        self.assertGreater(f["you_per_100w"], 0)


class RomanCaptions(unittest.TestCase):
    def test_roman_line_takes_devanagari_timing(self):
        from reel_factory.captions import needs_retime, retime_script
        heard = [("मैं", 0.2, 0.4), ("हलदी", 0.4, 0.8), ("हूं", 0.8, 1.0), ("तो", 5.0, 5.2), ("सुनो", 5.2, 5.6)]
        lines = ["Main haldi hoon", "Toh suno"]
        self.assertTrue(needs_retime(heard, " ".join(lines)))
        out = retime_script(heard, lines, [(0.0, 4.0), (4.0, 8.0)])
        self.assertEqual([w for w, _, _ in out], ["Main", "haldi", "hoon", "Toh", "suno"])
        self.assertAlmostEqual(out[1][1], 0.4)
        self.assertAlmostEqual(out[3][1], 5.0)
        self.assertFalse(needs_retime([("hello", 0, 1)], "hello"))


if __name__ == "__main__":
    unittest.main()
