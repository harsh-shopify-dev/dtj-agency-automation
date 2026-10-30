"""The reel stages with fake models, a fake Telegram (reel_job.py) and a fake Flow: no login, no credits."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import os
import re
import time

from engine import models, stages
from engine.runs import Run
from tests.test_core import make_brand

REPO = Path(__file__).resolve().parents[3]
JOB_RE = re.search(r'JOB_RE = re\.compile\(r"\^?(.+?)\$?"\)', (REPO / "n8n/store-factory/bot_ask.py").read_text(encoding="utf-8")).group(1)

FACTS = "Baked, not fried. 30 g protein."


def script_json(n=4, line="Baked, not fried.", extra=None):
    shots = [{"id": f"x{i}", "line": line, "seconds": 8, "image_prompt": f"scene {i + 1}, the pack on a table",
              "video_prompt": "slow push-in, the pack stays still", "product": True} for i in range(n)]
    return {"language": "en", "product_name": "Brand A", "shots": shots, **(extra or {})}


class Fakes:
    def __init__(self, tmp: Path):
        self.tmp, self.gemini_calls, self.codex_calls, self.flow_calls, self.person_calls = tmp, [], [], [], []
        self.scripts = [script_json()]
        self.pic_scores = []          # Claude picture scores, popped per check (default 9)
        self.clip_ok = []             # Claude clip verdicts, popped per check (default True)
        self.person_answers = []      # (exit code, dict) popped per review call
        self.factory_calls = []
        self.factory_codes = {}       # stage -> exit code (default 0)
        self.flow_answers = []        # (code, dict) popped per clip (default: two good takes)
        self.clip_files = []          # what Claude was shown for each clip check
        self.gemini_fail = None

    def gemini_json(self, prompt, files, work, **kw):
        self.gemini_calls.append((prompt, [Path(f).name for f in files]))
        if self.gemini_fail:
            raise self.gemini_fail
        if "STYLE CARD" in prompt:
            return {"shots": ["wide", "close"], "pace": "slow"}
        return self.scripts.pop(0) if len(self.scripts) > 1 else self.scripts[0]

    def claude_json(self, prompt, files, work, **kw):
        if "PICTURE CHECK" in prompt:
            return {"score": self.pic_scores.pop(0) if self.pic_scores else 9, "problems": ["label blurred"]}
        self.clip_files.append([Path(f).name for f in files])
        ok = self.clip_ok.pop(0) if self.clip_ok else True
        return {"ok": ok, "problems": [] if ok else ["the pack melts"]}

    def codex_image(self, prompt, refs, out, **kw):
        self.codex_calls.append((Path(out).name, prompt))
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_bytes(f"png {len(self.codex_calls)}".encode())
        return Path(out)

    def flow_clip(self, image, prompt_file, out_dir, products=(), seconds=8, **kw):
        self.flow_calls.append(Path(image).name)
        if self.flow_answers:
            return self.flow_answers.pop(0)
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        files = []
        for k in (1, 2):
            f = Path(out_dir) / f"{Path(image).stem}_t{k}.mp4"
            f.write_bytes(b"mp4")
            files.append(str(f))
        return 0, {"ok": True, "files": files, "assets": ["a1", "a2"], "credits": 24}

    def person(self, args):
        self.person_calls.append(args)
        assert re.fullmatch(JOB_RE, args[args.index("--job") + 1]), f"bot_ask refuses this job id: {args}"
        if args[0] in ("pictures", "final", "plan"):
            return self.person_answers.pop(0) if self.person_answers else (3, {})
        return 0, {"ok": True}

    def factory(self, stage, job_dir, shots=None):
        self.factory_calls.append((stage, shots))
        if self.factory_codes.get(stage):
            return self.factory_codes[stage]
        job = Path(job_dir)
        st = json.loads((job / "state.json").read_text(encoding="utf-8")) if (job / "state.json").is_file() else {}
        if stage == "check":
            for sid in (shots or "").split(","):
                (job / "checks").mkdir(exist_ok=True)
                for t in st["clips"][sid]:          # as reel_factory.job.stage_check writes them
                    stem = Path(t["file"]).stem
                    t["clean"] = str(job / "clean" / f"{stem}.mp4")
                    t["sheet"] = str(job / "checks" / f"{stem}_4fps.jpg")
                    Path(t["sheet"]).write_bytes(b"jpg")
                st.setdefault("pick", {}).setdefault(sid, {})["take"] = st["clips"][sid][0]["clean"]
        if stage == "edit":
            (job / "final").mkdir(exist_ok=True)
            (job / "final" / "reel_final.mp4").write_bytes(b"mp4")
            (job / "final" / "qc.json").write_text(json.dumps({"status": "reel ready", "duration": 31.5, "note": ""}), encoding="utf-8")
        (job / "state.json").write_text(json.dumps(st), encoding="utf-8")
        return 0

    def deps(self):
        return stages.Deps(gemini_json=self.gemini_json, claude_json=self.claude_json, codex_image=self.codex_image,
                           flow_clip=self.flow_clip, person=self.person, factory=self.factory, niche_root=self.tmp / "Niches")


class StageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.brand = make_brand(self.tmp, own=3)
        (self.brand.dir / "facts.md").write_text(FACTS, encoding="utf-8")
        self.f = Fakes(self.tmp)
        self.run = Run(self.tmp, "branda", "r1")
        self.d = self.f.deps()

    def call(self, stage, **body):
        return stages.run_stage(stage, self.run, self.brand, {"style": "cinematic", **body}, deps=self.d)

    def take(self):
        return self.call("take", request="Diwali reel", language="en", chat="123", watcher="Harsh")

    def test_take_writes_factory_request_and_starts_telegram(self):
        r = self.take()
        self.assertTrue(r["ok"])
        req = json.loads((self.run.dir / "job" / "request.json").read_text(encoding="utf-8"))
        self.assertEqual(req["local"]["product_images"], [str(self.brand.products[0])])
        self.assertEqual(self.f.person_calls[0][0], "start")

    def test_style_card_reused_when_refs_unchanged(self):
        self.take()
        self.assertFalse(self.call("style_card")["cached"])
        self.assertTrue(self.call("style_card")["cached"])
        self.assertEqual(sum("STYLE CARD" in p for p, _ in self.f.gemini_calls), 1)

    def test_script_renumbers_shots_and_passes_lint(self):
        self.take(); self.call("style_card")
        r = self.call("script")
        self.assertTrue(r["ok"], r)
        script = json.loads((self.run.dir / "job" / "script.json").read_text(encoding="utf-8"))
        self.assertEqual([s["id"] for s in script["shots"]], ["s1", "s2", "s3", "s4"])

    def test_lint_failure_stops_script(self):
        self.f.scripts = [script_json(line="Now 50% off for Diwali!")]
        self.take(); self.call("style_card")
        r = self.call("script")
        self.assertFalse(r["ok"])
        self.assertTrue(any("50%" in e for e in r["errors"]))
        self.assertEqual(sum("STYLE CARD" not in p for p, _ in self.f.gemini_calls), 2)  # one rewrite with the errors

    def test_cinematic_does_not_need_phone_words(self):
        self.take(); self.call("style_card")
        self.f.scripts = [script_json()]
        self.assertTrue(self.call("script")["ok"])

    def ready_pictures(self):
        self.take(); self.call("style_card"); self.call("script")
        return self.call("pictures")

    def test_low_picture_score_redrawn_at_most_twice(self):
        self.f.pic_scores = [4, 4, 4]
        self.take(); self.call("style_card"); self.call("script")
        r = self.call("pictures")
        self.assertIn("s1", r["redrawn"])
        self.assertEqual(sum(n.startswith("s1_") for n, _ in self.f.codex_calls), 3)
        self.assertEqual(r["needs_look"], ["s1"])

    def test_review_waiting_until_answer(self):
        self.ready_pictures()
        self.assertEqual(self.call("review", gate="pictures", round=1), {"ok": True, "waiting": True, "loop": 0})
        self.f.person_answers = [(0, {"ok": True, "by": "Harsh"})]
        r = self.call("review", gate="pictures", round=1)
        self.assertEqual((r["approved"], r["by"], r["next"]), (True, "Harsh", "clips"))

    def test_change_note_redraws_only_named_scenes(self):
        self.ready_pictures()
        before = {sid: Path(p).read_bytes() for sid, p in self.run.state["pictures"].items()}
        self.f.person_answers = [(0, {"ok": False, "by": "Harsh", "note": "3, 4: the diya is too small"})]
        r = self.call("review", gate="pictures", round=1)
        self.assertEqual((r["approved"], r["next"], r["only"]), (False, "pictures", ["s3", "s4"]))
        self.call("pictures", only=r["only"], note=r["note"])
        after = {sid: Path(p).read_bytes() for sid, p in self.run.state["pictures"].items()}
        self.assertEqual([s for s in before if before[s] != after[s]], ["s3", "s4"])
        self.assertIn("diya is too small", self.f.codex_calls[-1][1])

    def test_loop_counter_carries_the_change_to_the_next_stage(self):
        self.ready_pictures()
        self.f.person_answers = [(0, {"ok": False, "by": "Harsh", "note": "2: no rangoli"})]
        r = self.call("review", gate="pictures")
        self.assertEqual(r["loop"], 1)
        n = len(self.f.codex_calls)
        p = self.call("pictures", loop=r["loop"])           # n8n passes only the loop counter
        self.assertEqual(len(self.f.codex_calls), n + 1)     # only scene 2 redrawn
        self.assertIn("no rangoli", self.f.codex_calls[-1][1])
        self.assertEqual(p["loop"], 1)

    def test_failure_tells_the_person(self):
        self.f.scripts = [script_json(line="Now 50% off!")]
        self.take(); self.call("style_card")
        r = stages.run_stage("script", self.run, self.brand, {}, deps=self.d)
        self.assertFalse(r["ok"])
        self.assertEqual(self.f.person_calls[-1][0], "tell")
        self.assertIn("50%", self.f.person_calls[-1][-1])

    def test_final_note_without_scenes_or_words_ends_with_the_note(self):
        self.ready_pictures()
        self.f.person_answers = [(0, {"ok": False, "by": "Harsh", "note": "make it feel warmer"})]
        r = self.call("review", gate="final")
        self.assertEqual(r["next"], "result")

    def test_note_about_words_routes_to_script(self):
        self.ready_pictures()
        self.f.person_answers = [(0, {"ok": False, "by": "Harsh", "note": "change the line, say it is baked"})]
        r = self.call("review", gate="pictures", round=1)
        self.assertEqual(r["next"], "script")

    def test_final_note_with_scene_numbers_redoes_clips(self):
        self.ready_pictures()
        self.f.person_answers = [(0, {"ok": False, "by": "Harsh", "note": "2: the pack wobbles"})]
        r = self.call("review", gate="final", round=1)
        self.assertEqual((r["next"], r["only"]), ("clips", ["s2"]))

    def test_clips_needs_look_after_3_rounds(self):
        self.ready_pictures()
        self.f.clip_ok = [False, False, False, True, True, True]
        r = self.call("clips")
        self.assertEqual(r["needs_look"], ["s1"])
        self.assertEqual(sum(n.startswith("s1_") for n in self.f.flow_calls), 3)
        self.assertEqual(r["credits"], 24 * 6)

    def test_edit_and_result(self):
        self.ready_pictures(); self.call("clips")
        e = self.call("edit")
        self.assertTrue(Path(e["final"]).is_file())
        self.assertEqual(Path(e["final"]).parent.name, "final")
        r = self.call("result")
        self.assertEqual(r["reel_status"], "reel ready")
        self.assertEqual(self.f.person_calls[-1][0], "finish")

    # ---- the final review's findings ----
    def test_job_id_fits_the_telegram_limit(self):
        long = Run(self.tmp, "a_very_long_brand_name", "r20261030-1215-abcd")
        self.assertRegex(stages._jid(long), "^" + JOB_RE + "$")
        self.assertNotEqual(stages._jid(long), stages._jid(Run(self.tmp, "a_very_long_brand_name", "r20261030-1215-abce")))

    def test_claude_sees_the_real_sheet_of_the_picked_take(self):
        self.ready_pictures()
        r = self.call("clips")
        self.assertEqual(r["needs_look"], [])
        self.assertEqual(len(self.f.flow_calls), 4)   # one round each, no extra Flow spend
        self.assertTrue(self.f.clip_files[0][0].endswith("_4fps.jpg"))
        self.assertTrue(self.f.clip_files[0][0].startswith("s1_"))

    def test_check_crash_stops_without_more_flow(self):
        self.ready_pictures()
        self.f.factory_codes["check"] = 1
        r = self.call("clips")
        self.assertFalse(r["ok"])
        self.assertEqual(len(self.f.flow_calls), 1)
        self.assertIn("check", r["error"])

    def test_retry_after_a_stop_skips_finished_scenes(self):
        self.ready_pictures()
        good = (0, {"ok": True, "files": [str(self.tmp / "a.mp4")], "assets": ["a"], "credits": 24})
        self.f.flow_answers = [good, (1, {"ok": False, "needs_person": True, "error": "sign in"})]
        self.assertTrue(self.call("clips")["needs_person"])
        self.assertEqual(len(self.f.flow_calls), 2)
        self.assertTrue(self.call("clips")["ok"])
        names = [n.split("_")[0] for n in self.f.flow_calls]
        self.assertEqual(names, ["s1", "s2", "s2", "s3", "s4"])

    def test_picture_retry_skips_finished_scenes(self):
        self.take(); self.call("style_card"); self.call("script")
        real, calls = self.f.codex_image, []

        def flaky(prompt, refs, out, **kw):
            calls.append(Path(out).name)
            if len(calls) == 2:
                raise models.NeedsPerson("usage limit")
            return real(prompt, refs, out, **kw)
        self.d.codex_image = flaky
        self.assertTrue(self.call("pictures")["needs_person"])
        self.assertTrue(self.call("pictures")["ok"])
        self.assertEqual([n.split("_")[0] for n in calls], ["s1", "s2", "s2", "s3", "s4"])

    def test_any_failure_is_told_to_the_person(self):
        self.take()
        self.f.gemini_fail = models.ModelError("no JSON object in the answer")
        r = self.call("style_card")
        self.assertFalse(r["ok"])
        self.assertEqual(self.f.person_calls[-1][0], "tell")
        self.assertIn("no JSON", self.f.person_calls[-1][-1])

    def test_no_references_is_told_in_telegram(self):
        brand = make_brand(self.tmp, name="brandb", own=0, niche="none", niche_refs=0)
        run = Run(self.tmp, "brandb", "r2")
        r = stages.run_stage("take", run, brand, {"style": "founder", "request": "x", "chat": "123", "watcher": "H"}, deps=self.d)
        self.assertFalse(r["ok"])
        self.assertEqual([c[0] for c in self.f.person_calls], ["start", "tell"])

    def test_take_refuses_empty_chat(self):
        r = self.call("take", request="x", watcher="Harsh")
        self.assertFalse(r["ok"])
        self.assertIn("Telegram", r["error"])

    def test_only_one_reel_at_a_time(self):
        self.take()
        other = Run(self.tmp, "branda", "r2")
        body = {"style": "cinematic", "request": "x", "chat": "123", "watcher": "H"}
        r = stages.run_stage("take", other, self.brand, body, deps=self.d)
        self.assertFalse(r["ok"])
        self.assertIn("r1", r["error"])
        self.assertEqual(self.f.person_calls[-1][0], "tell")
        old = time.time() - 7 * 3600                        # an abandoned run stops blocking
        os.utime(self.run.dir / "state.json", (old, old))
        self.assertTrue(stages.run_stage("take", other, self.brand, {**body, "redo": True}, deps=self.d)["ok"])

    def test_a_failed_run_does_not_block_the_next(self):
        self.take()
        self.f.gemini_fail = models.ModelError("broken")
        self.call("style_card")
        self.f.gemini_fail = None
        other = Run(self.tmp, "branda", "r2")
        body = {"style": "cinematic", "request": "x", "chat": "123", "watcher": "H"}
        self.assertTrue(stages.run_stage("take", other, self.brand, body, deps=self.d)["ok"])

    def test_review_only_looks_once(self):
        self.ready_pictures()
        self.call("review", gate="pictures")
        args = [c for c in self.f.person_calls if c[0] == "pictures"][-1]
        self.assertEqual(args[args.index("--minutes") + 1], "0")

    def test_review_gives_up_after_two_days(self):
        self.ready_pictures()
        self.call("review", gate="pictures")
        self.run.state["review_since"]["pictures-1"] = time.time() - 49 * 3600
        r = self.call("review", gate="pictures")
        self.assertFalse(r["ok"])
        self.assertIn("2 days", r["error"])

    def test_final_change_reaches_the_result(self):
        self.ready_pictures(); self.call("clips"); self.call("edit")
        self.f.person_answers = [(0, {"ok": False, "by": "Harsh", "note": "make it feel warmer"})]
        self.call("review", gate="final")
        r = self.call("result", loop=1)
        self.assertEqual(r["reel_status"], "needs a look")
        self.assertIn("warmer", r["reel_note"])

    def test_final_caption_note_never_respends(self):
        self.ready_pictures()
        self.f.person_answers = [(0, {"ok": False, "by": "Harsh", "note": "move the caption lower"})]
        self.assertEqual(self.call("review", gate="final")["next"], "result")

    def test_numbers_inside_the_note_are_not_scenes(self):
        self.ready_pictures()
        self.f.person_answers = [(0, {"ok": False, "by": "Harsh", "note": "3: show 2 diyas"})]
        self.assertEqual(self.call("review", gate="pictures")["only"], ["s3"])
        self.assertEqual(stages._route("scene 2 is too dark", ["s1", "s2"], "pictures")["only"], ["s2"])

    def test_script_text_is_escaped_for_telegram(self):
        self.ready_pictures()
        sc = json.loads((self.run.dir / "job" / "script.json").read_text(encoding="utf-8"))
        sc["shots"][0]["line"] = "Baked & <crisp>"
        (self.run.dir / "job" / "script.json").write_text(json.dumps(sc), encoding="utf-8")
        self.call("review", gate="pictures")
        text = [c for c in self.f.person_calls if c[0] == "tell"][-1][-1]
        self.assertIn("Baked &amp; &lt;crisp&gt;", text)

    def test_cinematic_prompt_may_say_cinematic_but_ugc_may_not(self):
        sc = script_json()
        sc["shots"][0]["image_prompt"] = "cinematic wide shot of the pack"
        sc["style"] = "cinematic"
        self.assertEqual(stages._lint(sc, FACTS, "cinematic"), [])
        sc["style"] = "ugc"
        self.assertTrue(any("AI-ad" in e for e in stages._lint(sc, FACTS, "ugc")))

    def test_script_carries_the_requested_style(self):
        self.take(); self.call("style_card"); self.call("script")
        sc = json.loads((self.run.dir / "job" / "script.json").read_text(encoding="utf-8"))
        self.assertEqual(sc["style"], "cinematic")


if __name__ == "__main__":
    unittest.main()
