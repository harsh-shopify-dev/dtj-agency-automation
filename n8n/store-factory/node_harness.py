"""Run one n8n Code node file in Node.js the way n8n runs it (mode Run Once for All Items): $input, $('Node name') and $execution
are stand-ins; the node's own code is untouched. Used by the test_*_nodes.py files in this folder."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
HAS_NODE = shutil.which("node") is not None
_HARNESS = r"""
const fs = require('fs');
const [file, inputJson, refsJson] = process.argv.slice(-3);
const code = fs.readFileSync(file, 'utf8');
const given = JSON.parse(inputJson), refs = JSON.parse(refsJson);
const items = Array.isArray(given) ? given : [given];
const $input = { first: () => ({ json: items[0] }), all: () => items.map((json) => ({ json })) };
const $ = (name) => {
  if (!(name in refs)) throw new Error('node ' + name + ' has not run');
  return { first: () => ({ json: refs[name] }) };
};
const $execution = { resumeUrl: refs.__resume };
try {
  // n8n's Code sandbox has no URL / URLSearchParams (test execution 330): hide them here too, so a node that needs them fails in tests
  const out = new Function('$input', '$', '$execution', 'URL', 'URLSearchParams', code)($input, $, $execution, undefined, undefined);
  process.stdout.write(JSON.stringify({ ok: true, out }));
} catch (e) {
  process.stdout.write(JSON.stringify({ ok: false, error: String(e.message) }));
}
"""


def run_node(file: str | Path, given, refs: dict | None = None) -> dict:
    """given: the input item's json (or a list of them). refs: outputs of earlier nodes by name ('__resume' = $execution.resumeUrl).
    Returns {"ok": True, "out": [...items]} or {"ok": False, "error": "..."}."""
    path = file if isinstance(file, Path) else HERE / file
    p = subprocess.run(["node", "-e", _HARNESS, str(path), json.dumps(given), json.dumps(refs or {})],
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)
