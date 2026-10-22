"""The picture maker for a new store (provision/ai_images.py, 22 Oct 2026: banners and sample product pictures "with chatgpt").
Stand-ins play OpenAI's API and ChatGPT's Chrome: nothing here reaches OpenAI, ChatGPT or the network, and no money is spent."""
import base64
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provision import ai_images as ai  # noqa: E402
from provision.ai_images import ImagesError  # noqa: E402

KEY = "sk-test-SECRET-1234567890"
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 24
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
NO_VAR = lambda _name: None  # noqa: E731 - no Windows user variable
NO_CDP = lambda _url: False  # noqa: E731
GOOD = "Amber glass bottle of herbal hair oil on a wooden table, morning light"


def answer(data: bytes = WEBP) -> tuple[int, dict]:
    return 200, {"data": [{"b64_json": base64.b64encode(data).decode()}], "usage": {"total_tokens": 1200}}


class FakePost:
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, body, key):
        self.calls.append((body, key))
        return self.answers.pop(0)


class FakeChatGPT:
    def __init__(self, data: bytes = PNG):
        self.data, self.prompts, self.closed = data, [], False

    def image(self, prompt, out, files=()):
        self.prompts.append(prompt)
        Path(out).write_bytes(self.data)
        return Path(out)

    def close(self):
        self.closed = True


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class Route(unittest.TestCase):
    def test_a_key_in_the_environment_means_the_api(self):
        way, why = ai.route({"OPENAI_API_KEY": KEY}, NO_VAR, NO_CDP)
        self.assertEqual(way, "api")
        self.assertIn("OPENAI_API_KEY", why)
        self.assertNotIn(KEY, why)

    def test_the_windows_user_variable_counts_too(self):
        seen = []
        way, why = ai.route({}, lambda n: seen.append(n) or (KEY if n == "DTJ_OPENAI_API_KEY" else None), NO_CDP)
        self.assertEqual((way, seen), ("api", ["OPENAI_API_KEY", "DTJ_OPENAI_API_KEY"]))
        self.assertIn("DTJ_OPENAI_API_KEY", why)
        self.assertNotIn(KEY, why)

    def test_no_key_but_chrome_answers_means_chatgpt(self):
        asked = []
        way, why = ai.route({"DTJ_CHATGPT_CDP": "http://10.0.0.5:9333/"}, NO_VAR, lambda u: asked.append(u) or True)
        self.assertEqual(way, "chatgpt")
        self.assertEqual(asked, ["http://10.0.0.5:9333/json/version"])
        self.assertIn("10.0.0.5:9333", why)

    def test_the_default_chrome_address(self):
        asked = []
        ai.route({}, NO_VAR, lambda u: asked.append(u) or False)
        self.assertEqual(asked, ["http://127.0.0.1:9222/json/version"])

    def test_neither_says_what_to_set_up(self):
        way, why = ai.route({}, NO_VAR, NO_CDP)
        self.assertIsNone(way)
        self.assertIn("OPENAI_API_KEY", why)
        self.assertIn("reel VPS", why)


class Guard(unittest.TestCase):
    def test_refuses_words_claims_and_people(self):
        for prompt in ("Serum bottle with 50% off sticker", "Jar of ghee priced ₹499", "Rs 299 combo pack", "clinically proven face cream",
                       "certified organic honey jar", "five-star reviews around the bottle", "4.8 stars rating under the product",
                       "before and after skin photo", "a jar with the Nike logo", "a famous actress holding the bottle",
                       "a mug with text that says good morning", "banner with the headline Fresh Every Day", "best seller tea box",
                       "trusted by 10k customers", "weight loss shake glass"):
            with self.subTest(prompt=prompt), self.assertRaises(ValueError):
                ai.guard(prompt, "product")

    def test_extra_names_are_refused(self):
        with self.assertRaises(ValueError) as e:
            ai.guard("A tea cup like Chaayos serves", "lifestyle", forbid=["Chaayos"])
        self.assertIn("Chaayos", str(e.exception))

    def test_a_plain_description_passes_with_its_suffixes(self):
        text = ai.guard(GOOD + ".", "product")
        self.assertTrue(text.startswith(GOOD + ". "))
        self.assertIn("ONE product", text)
        self.assertIn("plain light background", text)
        self.assertIn("No words, letters, numbers, labels, logos", text)
        banner = ai.guard("Kitchen counter with fresh herbs", "banner")
        self.assertIn("empty calm area on one side", banner)
        self.assertIn("the picture never does", banner)
        self.assertIn("No words", ai.guard("Family at breakfast", "lifestyle"))

    def test_sizes_in_a_description_are_allowed(self):
        self.assertIn("250 ml", ai.guard("A 250 ml amber bottle of oil", "product"))

    def test_kind_and_empty_prompt(self):
        with self.assertRaises(ValueError):
            ai.guard(GOOD, "poster")
        with self.assertRaises(ValueError):
            ai.guard("   ", "banner")


class Api(Base):
    def test_makes_the_picture_and_its_sidecar(self):
        post = FakePost(answer())
        side = ai.make("banner", GOOD, self.tmp / "banner-1.webp", post=post, environ={"OPENAI_API_KEY": KEY}, read_var=NO_VAR,
                       cdp_ok=NO_CDP, sleep=lambda s: None)
        body, key = post.calls[0]
        self.assertEqual(key, KEY)
        self.assertEqual((body["model"], body["size"], body["output_format"], body["n"]), ("gpt-image-2.5-flare", "1536x864", "webp", 1))
        self.assertIn("empty calm area", body["prompt"])
        self.assertEqual((self.tmp / "banner-1.webp").read_bytes(), WEBP)
        on_disk = json.loads((self.tmp / "banner-1.json").read_text(encoding="utf-8"))
        self.assertEqual(on_disk, side)
        self.assertEqual((side["backend"], side["kind"], side["sample"], side["size"]), ("api", "banner", True, "1536x864"))
        self.assertIn("replace with the brand's own picture", side["note"])
        self.assertEqual(side["usage"], {"total_tokens": 1200})
        self.assertNotIn(KEY, (self.tmp / "banner-1.json").read_text(encoding="utf-8"))

    def test_product_is_square_and_png_stays_png(self):
        post = FakePost(answer(PNG))
        side = ai.make("product", GOOD, self.tmp / "p1.png", post=post, environ={"DTJ_OPENAI_API_KEY": KEY}, read_var=NO_VAR,
                       cdp_ok=NO_CDP)
        self.assertEqual(post.calls[0][0]["size"], "1024x1024")
        self.assertNotIn("output_compression", post.calls[0][0])
        self.assertTrue(side["path"].endswith("p1.png"))

    def test_another_extension_becomes_webp(self):
        side = ai.make("product", GOOD, self.tmp / "p1.jpeg", post=FakePost(answer()), environ={"OPENAI_API_KEY": KEY},
                       read_var=NO_VAR, cdp_ok=NO_CDP)
        self.assertTrue(side["path"].endswith("p1.webp"))

    def test_retries_a_busy_api_with_growing_pauses(self):
        post, slept = FakePost((429, {"error": "slow down"}), (503, {"error": "busy"}), (0, {"error": "reset"}), answer()), []
        ai.make("product", GOOD, self.tmp / "p.webp", post=post, environ={"OPENAI_API_KEY": KEY}, read_var=NO_VAR, cdp_ok=NO_CDP,
                sleep=slept.append)
        self.assertEqual((len(post.calls), slept), (4, [2, 4, 8]))

    def test_gives_up_after_three_retries_without_the_key_in_the_message(self):
        post = FakePost(*[(500, {"error": f"Incorrect API key provided: {KEY}"})] * 4)
        with self.assertRaises(ImagesError) as e:
            ai.make("product", GOOD, self.tmp / "p.webp", post=post, environ={"OPENAI_API_KEY": KEY}, read_var=NO_VAR,
                    cdp_ok=NO_CDP, sleep=lambda s: None)
        self.assertEqual(len(post.calls), 4)
        self.assertIn("500", str(e.exception))
        self.assertNotIn(KEY, str(e.exception))
        self.assertNotIn("SECRET", str(e.exception))
        self.assertFalse((self.tmp / "p.json").exists())

    def test_a_refusal_from_openai_is_not_retried(self):
        post = FakePost((400, {"error": "bad request"}))
        with self.assertRaises(ImagesError):
            ai.make("product", GOOD, self.tmp / "p.webp", post=post, environ={"OPENAI_API_KEY": KEY}, read_var=NO_VAR, cdp_ok=NO_CDP,
                    sleep=lambda s: None)
        self.assertEqual(len(post.calls), 1)

    def test_an_answer_without_a_picture(self):
        with self.assertRaises(ImagesError):
            ai.make("product", GOOD, self.tmp / "p.webp", post=FakePost((200, {"data": []})), environ={"OPENAI_API_KEY": KEY},
                    read_var=NO_VAR, cdp_ok=NO_CDP)

    def test_a_refused_prompt_never_calls_anyone(self):
        post = FakePost(answer())
        with self.assertRaises(ValueError):
            ai.make("banner", "Banner with 30% off", self.tmp / "b.webp", post=post, environ={"OPENAI_API_KEY": KEY}, read_var=NO_VAR)
        self.assertEqual(post.calls, [])

    def test_auto_with_no_way_stops_and_says_why(self):
        with self.assertRaises(ImagesError) as e:
            ai.make("banner", GOOD, self.tmp / "b.webp", environ={}, read_var=NO_VAR, cdp_ok=NO_CDP)
        self.assertIn("OPENAI_API_KEY", str(e.exception))

    def test_api_chosen_without_a_key(self):
        with self.assertRaises(ImagesError):
            ai.make("banner", GOOD, self.tmp / "b.webp", backend="api", environ={}, read_var=NO_VAR)


class ChatGPTWay(Base):
    def test_no_key_uses_chatgpt_and_keeps_the_real_file_type(self):
        cg = FakeChatGPT(PNG)
        side = ai.make("banner", GOOD, self.tmp / "banner-1.webp", chatgpt=cg, environ={}, read_var=NO_VAR, cdp_ok=lambda u: True)
        self.assertEqual((side["backend"], side["model"]), ("chatgpt", "chatgpt.com"))
        self.assertTrue(cg.prompts[0].startswith("Create one wide landscape picture (1536x864). "))
        self.assertIn("No words", cg.prompts[0])
        self.assertTrue(side["path"].endswith("banner-1.png"))
        self.assertEqual((self.tmp / "banner-1.png").read_bytes(), PNG)
        self.assertFalse((self.tmp / "banner-1.webp").exists())
        self.assertTrue((self.tmp / "banner-1.json").exists())
        self.assertFalse(cg.closed)  # a ChatGPT window handed in stays open for the next picture
        self.assertNotIn("usage", side)

    def test_a_chatgpt_failure_is_plain(self):
        class Broken(FakeChatGPT):
            def image(self, prompt, out, files=()):
                raise RuntimeError("ChatGPT is signed out in the reel Chrome window: a person must sign in once")
        with self.assertRaises(ImagesError) as e:
            ai.make("product", GOOD, self.tmp / "p.webp", backend="chatgpt", chatgpt=Broken(), environ={})
        self.assertIn("signed out", str(e.exception))


class Cli(Base):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ai.main(list(argv))
        return code, buf.getvalue()

    def test_dry_run_makes_nothing(self):
        with mock.patch.object(ai, "route", return_value=("api", "OpenAI Images API (key saved as OPENAI_API_KEY)")):
            code, out = self.run_cli("--kind", "product", "--prompt", GOOD, "--out", str(self.tmp / "p.webp"), "--dry-run")
        self.assertEqual(code, 0)
        shown = json.loads(out)
        self.assertEqual((shown["route"], shown["size"]), ("api", "1024x1024"))
        self.assertIn("ONE product", shown["prompt"])
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_a_refused_prompt_exits_2(self):
        code, out = self.run_cli("--kind", "banner", "--prompt", "Sale banner 50% off", "--out", str(self.tmp / "b.webp"))
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", out)

    def test_no_way_exits_1(self):
        with mock.patch.object(ai, "make", side_effect=ImagesError("No way to make pictures yet")):
            code, out = self.run_cli("--kind", "banner", "--prompt", GOOD, "--out", str(self.tmp / "b.webp"))
        self.assertEqual(code, 1)
        self.assertIn("No way to make pictures yet", out)


if __name__ == "__main__":
    unittest.main()
