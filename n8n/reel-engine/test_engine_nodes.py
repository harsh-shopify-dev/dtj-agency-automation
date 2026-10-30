"""Runs the Reel Engine Code nodes in Node with a stand-in $input, and checks the generated workflow code.

    python -m unittest n8n/reel-engine/test_engine_nodes.py
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import deploy_engine  # noqa: E402


def run_node(js_file: str, item: dict):
    body = (HERE / js_file).read_text(encoding="utf-8")
    prog = ("const $input = { first: () => ({ json: " + json.dumps(item) + " }) };\n"
            "const out = (() => {\n" + body + "\n})();\nconsole.log(JSON.stringify(out));")
    p = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
    if p.returncode:
        return None, p.stderr
    return json.loads(p.stdout), ""


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class StartRun(unittest.TestCase):
    def test_run_id_and_defaults(self):
        out, err = run_node("start_run.js", {"brand": "BrandA", "request": "Diwali reel", "watcher": "Harsh", "style": "Cinematic"})
        j = out[0]["json"]
        self.assertEqual((j["brand"], j["style"], j["language"], j["requested_by"]), ("branda", "cinematic", "en", "Harsh"))
        self.assertRegex(j["run"], r"^r\d{8}-\d{4}-[a-z0-9]{1,4}$")

    def test_refuses_without_watcher(self):
        out, err = run_node("start_run.js", {"brand": "branda", "request": "x"})
        self.assertIsNone(out)
        self.assertIn("No watcher", err)

    def test_refuses_without_request(self):
        out, err = run_node("start_run.js", {"brand": "branda", "watcher": "Harsh"})
        self.assertIn("No request", err)


class GeneratedCode(unittest.TestCase):
    def test_engine_has_champfuel_style_stage_nodes(self):
        code = deploy_engine.engine_code()
        for name in ("0 [NO AI] Take request", "1 [GEMINI] Style card", "2 [GEMINI] Script + scenes",
                     "3 [CHATGPT + CLAUDE] Scene pictures", "4 [PERSON] Approve script + pictures", "5 [FLOW + CLAUDE] Clips",
                     "6 [NO AI] Edit", "7 [PERSON] Approve final reel", "8 [NO AI] Result"):
            self.assertIn(json.dumps(name), code)
        self.assertEqual(len(re.findall(r"url: '" + re.escape(deploy_engine.ENGINE) + "/stage'", code)), 9)

    def test_every_stage_passes_the_loop_counter(self):
        code = deploy_engine.engine_code()
        for stage in ("script", "pictures", "review", "clips", "edit", "result"):
            self.assertRegex(code, rf"stage: '{stage}'[^}}]*loop: \$json\.loop \|\| 0")

    def test_every_node_has_a_plain_note(self):
        for code in (deploy_engine.engine_code(), deploy_engine.brand_code("branda", "Brand A", "cinematic", "ENGINE_ID")):
            names = re.findall(r"config: \{ name: (\"[^\"]+\"|'[^']+')", code)
            self.assertGreater(len(names), 3)
            notes = re.findall(r"notes: (\"(?:[^\"\\\\]|\\\\.)*\"|'[^']*')", code)
            self.assertEqual(len(notes), len(names), names)
            for note in notes:
                for jargon in ("agy", "Codex", "stage", "422", "HTTP", "LUFS", "•"):
                    self.assertNotIn(jargon, note)

    def test_edit_step_says_it_uses_no_ai(self):
        self.assertIn('"6 [NO AI] Edit"', deploy_engine.engine_code())

    def test_service_uses_the_reel_python(self):
        unit = (HERE.parents[1] / "services/reel-engine/reel-engine.service").read_text(encoding="utf-8")
        self.assertIn("ExecStart=/home/ai/dtj/reel-venv/bin/python -m engine.server", unit)

    def test_brand_wrapper_starts_from_a_form(self):
        code = deploy_engine.brand_code("branda", "Brand A", "cinematic", "ENGINE_ID")
        self.assertIn("n8n-nodes-base.formTrigger", code)
        self.assertIn('"dtj-reel-branda"', code)

    def test_clips_may_run_for_hours(self):
        code = deploy_engine.engine_code()
        self.assertRegex(code, r"5 \[FLOW \+ CLAUDE\] Clips.*?timeout: 14400000")

    def test_final_answer_never_goes_back_to_the_script(self):
        code = deploy_engine.engine_code()
        self.assertNotIn(".onCase(3, script)))", code)

    def test_brand_wrapper_fixes_the_brand(self):
        code = deploy_engine.brand_code("branda", "Brand A", "cinematic", "ENGINE_ID")
        self.assertIn('"value": "branda"', code)
        self.assertIn("ENGINE_ID", code)
        self.assertIn('"Reel: Brand A"', code)


if __name__ == "__main__":
    unittest.main()
