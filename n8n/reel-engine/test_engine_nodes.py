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
                     "6 [CLAUDE] Edit", "7 [PERSON] Approve final reel", "8 [NO AI] Result"):
            self.assertIn(json.dumps(name), code)
        self.assertEqual(len(re.findall(r"url: '" + re.escape(deploy_engine.ENGINE) + "/stage'", code)), 9)

    def test_every_stage_passes_the_loop_counter(self):
        code = deploy_engine.engine_code()
        for stage in ("script", "pictures", "review", "clips", "edit", "result"):
            self.assertRegex(code, rf"stage: '{stage}'[^}}]*loop: \$json\.loop \|\| 0")

    def test_brand_wrapper_fixes_the_brand(self):
        code = deploy_engine.brand_code("branda", "Brand A", "cinematic", "ENGINE_ID")
        self.assertIn('"value": "branda"', code)
        self.assertIn("ENGINE_ID", code)
        self.assertIn('"Reel: Brand A"', code)


if __name__ == "__main__":
    unittest.main()
