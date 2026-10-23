"""The picture maker for a new store (provision/ai_images.py, 22 Oct 2026: banners and sample product pictures "with chatgpt").
Stand-ins play OpenAI's API and ChatGPT's Chrome: nothing here reaches OpenAI, ChatGPT or the network, and no money is spent."""
import base64
import contextlib
import io
import json
import os
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
        self.assertEqual((way, seen), ("api", ["DTJ_IMAGE_VPS", "OPENAI_API_KEY", "DTJ_OPENAI_API_KEY"]))  # the VPS is looked for first
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
        self.assertIn("so Codex there makes them", why)


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


HOST = "ai@srv2048145.hstgr.cloud"


class FakeRunner:
    """Plays ssh, scp and the local Codex script: records every argv, answers codex_image.sh with `answer`, writes `data` where scp
    brings the picture back (or where the local script saves it). Nothing reaches the VPS or Codex."""

    def __init__(self, answer=None, data=PNG, fail_on=None):
        self.calls, self.data, self.fail_on = [], data, fail_on
        self.answer = answer

    def __call__(self, argv, timeout):
        self.calls.append(list(argv))
        line = " ".join(argv)
        if self.fail_on and self.fail_on in line:
            return 1, "", "lost connection"
        if argv[0] == "ssh" and "codex_image.sh" in line:
            rdir = line.split("--prompt-file ")[1].split("/prompt.txt")[0]
            got = self.answer if self.answer is not None else {"ok": True, "path": f"{rdir}/out.png", "seconds": 41}
            return 0, "some log line\n" + json.dumps(got) + "\n", ""
        if argv[0] == "bash" and argv[1].endswith("codex_image.sh"):
            out = argv[argv.index("--out") + 1]
            got = self.answer if self.answer is not None else {"ok": True, "path": out, "seconds": 38}
            if got.get("ok"):
                Path(out).write_bytes(self.data)
            return 0, json.dumps(got) + "\n", ""
        if argv[0] == "scp" and argv[-2].startswith(HOST + ":"):
            Path(argv[-1]).write_bytes(self.data)
        return 0, "", ""

    def commands(self):
        return [c[-1] for c in self.calls if c[0] == "ssh"]


class VpsWay(Base):
    """ChatGPT on DTJ's Hostinger VPS over ssh (Harsh, 22 Oct 2026: "chatgpt cli which will be hosted on our hostinger vps"),
    with our product's photos as the reference."""

    def setUp(self):
        super().setUp()
        self.ref = self.tmp / "1.jpg"
        self.ref.write_bytes(b"\xff\xd8\xff\xe0jpg")

    def test_codex_here_comes_first_then_the_vps(self):
        way, why = ai.route({"DTJ_IMAGE_VPS": HOST, "OPENAI_API_KEY": KEY}, NO_VAR, NO_CDP, lambda h: True, codex_ok=lambda: True)
        self.assertEqual(way, "codex")
        self.assertIn("Codex on this computer", why)

    def test_codex_on_this_computer_makes_it_with_our_photos(self):
        r = FakeRunner()
        side = ai.make("product", "This exact bottle on a plain light background", self.tmp / "p9.webp", refs=[self.ref],
                       environ={}, read_var=NO_VAR, runner=r, codex_ok=lambda: True)
        self.assertEqual((side["backend"], side["model"]), ("codex", "Codex (this computer)"))
        self.assertTrue(side["path"].endswith("p9.png"))
        argv = r.calls[0]
        self.assertEqual(argv[:2], ["bash", str(ai.CODEX_SCRIPT)])
        self.assertEqual(argv[argv.index("--ref") + 1], str(self.ref.resolve()))
        self.assertEqual(argv[argv.index("--timeout") + 1], "600")
        cwd = os.getcwd()  # a relative photo path (brief 12) reaches Codex as an absolute one
        os.chdir(self.ref.parent)
        try:
            r = FakeRunner()
            ai.make("product", "This exact bottle on a plain light background", "p10.webp", refs=[self.ref.name],
                    environ={}, read_var=NO_VAR, runner=r, codex_ok=lambda: True)
        finally:
            os.chdir(cwd)
        argv = r.calls[0]
        self.assertEqual(argv[argv.index("--ref") + 1], str(self.ref.resolve()))
        self.assertTrue(Path(argv[argv.index("--out") + 1]).is_absolute())
        r = FakeRunner(answer={"ok": False, "error": "no picture from codex (exit 1): usage limit reached"})
        with self.assertRaises(ImagesError) as e:
            ai.make("banner", GOOD, self.tmp / "b9.webp", environ={}, read_var=NO_VAR, runner=r, codex_ok=lambda: True)
        self.assertIn("Codex could not make it: no picture from codex (exit 1): usage limit reached", str(e.exception))

    def test_the_vps_comes_first_when_set_and_answering(self):
        asked = []
        way, why = ai.route({"DTJ_IMAGE_VPS": HOST, "OPENAI_API_KEY": KEY}, NO_VAR, NO_CDP, lambda h: asked.append(h) or True,
                            codex_ok=lambda: False)
        self.assertEqual((way, asked), ("vps", [HOST]))
        self.assertIn(HOST, why)
        way, why = ai.route({"DTJ_IMAGE_VPS": HOST, "OPENAI_API_KEY": KEY}, NO_VAR, NO_CDP, lambda h: False, codex_ok=lambda: False)
        self.assertEqual(way, "api")  # a VPS that does not answer: the next way
        way, why = ai.route({"DTJ_IMAGE_VPS": HOST}, NO_VAR, NO_CDP, lambda h: False, codex_ok=lambda: False)
        self.assertIsNone(way)
        self.assertIn("ssh did not answer", why)
        self.assertIn("DTJ_IMAGE_VPS", why)

    def test_the_ssh_check_is_batch_mode_and_short(self):
        r = FakeRunner()
        self.assertTrue(ai._vps_answers(HOST, r))
        self.assertEqual(r.calls, [["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", HOST, "true"]])

    def test_a_picture_with_our_product_comes_back_and_only_its_folder_is_removed(self):
        r = FakeRunner()
        side = ai.make("product", "This exact bottle on a plain light background", self.tmp / "p1.webp", refs=[self.ref],
                       environ={"DTJ_IMAGE_VPS": HOST}, read_var=NO_VAR, runner=r, vps_ok=lambda h: True, codex_ok=lambda: False)
        self.assertEqual((side["backend"], side["model"]), ("vps", f"Codex (VPS {HOST})"))
        self.assertTrue(side["path"].endswith("p1.png"))  # ChatGPT's PNG keeps its real type
        self.assertEqual(side["refs"], [str(self.ref)])
        self.assertEqual((self.tmp / "p1.png").read_bytes(), PNG)
        mk, run, rm = r.commands()
        rdir = mk.split()[-1]
        self.assertRegex(rdir, r"^/tmp/dtj-img-[0-9a-f]{12}$")
        self.assertEqual(mk, f"mkdir -m 700 {rdir}")
        self.assertEqual(rm, f"rm -rf -- {rdir}")
        self.assertIn('cd "$HOME"/dtj-agency-automation && bash tools/vps/codex_image.sh', run)
        self.assertIn(f"--prompt-file {rdir}/prompt.txt --out {rdir}/out.png --ref {rdir}/ref-1.jpg --timeout 600", run)
        sent = next(c for c in r.calls if c[0] == "scp" and c[-1].startswith(HOST))
        self.assertEqual([Path(x).name for x in sent[-3:-1]], ["prompt.txt", "ref-1.jpg"])
        self.assertEqual(sent[-1], f"{HOST}:{rdir}/")
        back = next(c for c in r.calls if c[0] == "scp" and c[-2].startswith(HOST))
        self.assertEqual(back[-2], f"{HOST}:{rdir}/out.png")
        self.assertTrue(all("-o" in c and "BatchMode=yes" in c for c in r.calls))

    def test_the_prompt_sent_says_to_use_the_reference_and_keep_the_label(self):
        r, seen = FakeRunner(), []
        real = ai._vps_make

        def spy(host, chat_prompt, out, refs, folder, runner, timeout=600):
            seen.append((chat_prompt, folder))
            return real(host, chat_prompt, out, refs, folder, runner, timeout)
        with mock.patch.object(ai, "_vps_make", spy):
            ai.make("lifestyle", "A woman pouring the product in the reference photo into a cup", self.tmp / "l.png",
                    refs=[self.ref], backend="vps", environ={"DTJ_IMAGE_VPS": HOST, "DTJ_IMAGE_VPS_DIR": "/srv/dtj/repo"},
                    read_var=NO_VAR, runner=r)
        prompt, folder = seen[0]
        self.assertTrue(prompt.startswith("Create one wide landscape picture (1536x1024). Use the attached photo of our product as the reference."))
        self.assertIn("its label as it is in the reference", prompt)
        self.assertIn("only the product's own label", prompt)
        self.assertNotIn("No words, letters, numbers, labels", prompt)
        self.assertEqual(folder, "/srv/dtj/repo")
        self.assertIn("cd /srv/dtj/repo &&", r.commands()[1])

    def test_a_vps_failure_is_plain_and_the_folder_is_still_removed(self):
        r = FakeRunner(answer={"ok": False, "error": "no picture from codex (exit 1): not logged in"})
        with self.assertRaises(ImagesError) as e:
            ai.make("product", GOOD, self.tmp / "p.webp", refs=[self.ref], backend="vps", environ={"DTJ_IMAGE_VPS": HOST},
                    read_var=NO_VAR, runner=r)
        self.assertIn("Codex on the VPS could not make it: no picture from codex (exit 1): not logged in", str(e.exception))
        self.assertTrue(r.commands()[-1].startswith("rm -rf -- /tmp/dtj-img-"))
        r = FakeRunner(fail_on="scp -q")
        with self.assertRaises(ImagesError) as e:
            ai.make("product", GOOD, self.tmp / "p.webp", backend="vps", environ={"DTJ_IMAGE_VPS": HOST}, read_var=NO_VAR, runner=r)
        self.assertIn("could not copy the prompt", str(e.exception))
        self.assertTrue(r.commands()[-1].startswith("rm -rf -- /tmp/dtj-img-"))

    def test_an_answer_outside_the_job_folder_is_not_copied(self):
        r = FakeRunner(answer={"ok": True, "path": "/home/ai/.ssh/id_ed25519"})
        with self.assertRaises(ImagesError) as e:
            ai.make("product", GOOD, self.tmp / "p.webp", backend="vps", environ={"DTJ_IMAGE_VPS": HOST}, read_var=NO_VAR, runner=r)
        self.assertIn("outside its job folder", str(e.exception))
        self.assertFalse(any(c[0] == "scp" and c[-2].startswith(HOST) for c in r.calls))

    def test_no_ssh_on_this_computer_is_said(self):
        with self.assertRaises(ImagesError) as e:
            ai.make("banner", GOOD, self.tmp / "b.webp", backend="vps", environ={"DTJ_IMAGE_VPS": HOST}, read_var=NO_VAR,
                    runner=lambda argv, t: (127, "", "ssh is not installed on this computer"))
        self.assertIn("ssh is not installed", str(e.exception))
        with self.assertRaises(ImagesError):
            ai.make("banner", GOOD, self.tmp / "b.webp", backend="vps", environ={}, read_var=NO_VAR)  # no DTJ_IMAGE_VPS


class References(Base):
    """Our product's photos reach every way: the API's edits call, ChatGPT's chat, the VPS."""

    def setUp(self):
        super().setUp()
        self.ref = self.tmp / "front.png"
        self.ref.write_bytes(PNG)

    def test_the_api_gets_them_as_an_edit(self):
        post = FakePost(answer())
        ai.make("product", GOOD, self.tmp / "p.webp", refs=[self.ref], post=post, environ={"OPENAI_API_KEY": KEY}, read_var=NO_VAR,
                vps_ok=lambda h: False, cdp_ok=NO_CDP)
        body, _ = post.calls[0]
        self.assertEqual(body["image"], [str(self.ref)])
        self.assertNotIn("background", body)
        self.assertIn("Keep the product exactly as in the reference photo", body["prompt"])

    def test_without_them_the_api_call_is_unchanged(self):
        post = FakePost(answer())
        ai.make("product", GOOD, self.tmp / "p.webp", post=post, environ={"OPENAI_API_KEY": KEY}, read_var=NO_VAR, cdp_ok=NO_CDP)
        self.assertNotIn("image", post.calls[0][0])
        self.assertEqual(post.calls[0][0]["background"], "opaque")

    def test_the_edits_call_is_multipart_with_image_fields(self):
        sent = {}

        class Answer:
            status = 200

            def read(self):
                return json.dumps({"data": []}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def urlopen(req, timeout):
            sent.update(url=req.full_url, ctype=req.headers["Content-type"], data=req.data)
            return Answer()
        with mock.patch.object(ai.urllib.request, "urlopen", urlopen):
            ai._post({"model": "m", "prompt": "p", "n": 1, "image": [str(self.ref)]}, KEY)
        self.assertEqual(sent["url"], ai.EDITS_URL)
        self.assertTrue(sent["ctype"].startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="image[]"; filename="front.png"', sent["data"])
        self.assertIn(b'name="model"\r\n\r\nm\r\n', sent["data"])
        self.assertNotIn(KEY.encode(), sent["data"])

    def test_chatgpt_gets_them_attached(self):
        class Seen(FakeChatGPT):
            def image(self, prompt, out, files=()):
                self.files = list(files)
                return super().image(prompt, out, files)
        cg = Seen(PNG)
        side = ai.make("banner", GOOD, self.tmp / "b.webp", refs=[self.ref], chatgpt=cg, backend="chatgpt", environ={})
        self.assertEqual(cg.files, [str(self.ref)])
        self.assertIn("Use the attached photo of our product as the reference.", cg.prompts[0])
        self.assertEqual(side["refs"], [str(self.ref)])

    def test_missing_wrong_type_or_too_many_are_refused_before_anything_runs(self):
        post = FakePost()
        for refs, why in (([self.tmp / "nope.jpg"], "missing or not a jpg"), ([self.tmp / "a.gif"], "missing or not a jpg"),
                          ([self.ref] * 5, "at most 4")):
            if refs[0].suffix == ".gif":
                refs[0].write_bytes(b"GIF89a")
            with self.assertRaises(ImagesError) as e:
                ai.make("product", GOOD, self.tmp / "p.webp", refs=refs, post=post, environ={"OPENAI_API_KEY": KEY}, read_var=NO_VAR)
            self.assertIn(why, str(e.exception))
        self.assertEqual(post.calls, [])

    def test_the_guard_with_and_without_references(self):
        plain = ai.guard(GOOD, "product")
        self.assertTrue(plain.endswith(ai.NO_TEXT))
        with_ref = ai.guard("This exact bottle, the product in the reference photo, on a stone slab", "product", refs=True)
        self.assertIn(ai.REF_LINE.strip(), with_ref)
        self.assertTrue(with_ref.endswith(ai.NO_TEXT_REF))
        with self.assertRaises(ValueError):
            ai.guard("This exact bottle with 20% off", "product", refs=True)  # the guard still applies


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

    def test_ref_reaches_make_and_the_dry_run(self):
        ref = self.tmp / "r.jpg"
        ref.write_bytes(b"\xff\xd8")
        with mock.patch.object(ai, "route", return_value=("vps", "ChatGPT on the VPS")):
            code, out = self.run_cli("--kind", "product", "--prompt", GOOD, "--out", str(self.tmp / "p.webp"), "--ref", str(ref),
                                     "--dry-run")
        shown = json.loads(out)
        self.assertEqual((code, shown["refs"], shown["route"]), (0, [str(ref)], "vps"))
        self.assertIn("Keep the product exactly as in the reference photo", shown["prompt"])
        with mock.patch.object(ai, "make", return_value={"path": "x"}) as made:
            self.run_cli("--kind", "product", "--prompt", GOOD, "--out", str(self.tmp / "p.webp"), "--ref", str(ref), "--backend", "vps")
        self.assertEqual((made.call_args.kwargs["refs"], made.call_args.kwargs["backend"]), ([str(ref)], "vps"))

    def test_no_way_exits_1(self):
        with mock.patch.object(ai, "make", side_effect=ImagesError("No way to make pictures yet")):
            code, out = self.run_cli("--kind", "banner", "--prompt", GOOD, "--out", str(self.tmp / "b.webp"))
        self.assertEqual(code, 1)
        self.assertIn("No way to make pictures yet", out)


if __name__ == "__main__":
    unittest.main()
