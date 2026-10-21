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


if __name__ == "__main__":
    unittest.main()
