"""The three AI tools on the VPS host, each on its own subscription login (no API key; a person watches every run):

- Gemini through the Antigravity CLI `agy` (Google login in GEMINI_HOME; the old Gemini CLI login is refused by Google,
  docs/ugc-reels/2026-10-30-engine-checks.md). Files are copied into the work folder and mentioned as @name: that is how agy
  watches a video; without it the model tries a shell command and is denied.
- Codex + GPT Image (ChatGPT login in CODEX_HOME), the exact command Champfuel's brand-engine uses. OPENAI_API_KEY is removed
  from its environment so a picture can never be billed to the API.
- Claude Code (`claude -p`, the host's Claude login).

A sign-in, captcha, quota or usage-limit answer raises NeedsPerson: the run waits for the person on duty.
`run` is subprocess.run (tests pass a fake).
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .server import NeedsPerson

TIMEOUT = 900
GEMINI_MODEL = "gemini-3.8-flash-high"
CODEX_MODEL = "gpt-6.1-sol"
PERSON = re.compile(r"sign.?in|log.?in|authenticat|captcha|verify you|quota|usage limit|rate limit|ineligible", re.I)


class ModelError(RuntimeError):
    pass


def extract_json(text: str) -> dict:
    """The first JSON object in a model's answer (fences and prose around it are fine)."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text or "", re.S)
    candidates = [m.group(1)] if m else []
    if "{" in (text or ""):
        candidates.append(text[text.index("{"): text.rindex("}") + 1])
    for c in candidates:
        try:
            value = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ModelError(f"no JSON object in the answer: {(text or '')[:300]!r}")


def _env(env: dict | None, **extra: str) -> dict:
    base = dict(os.environ if env is None else env)
    base.pop("OPENAI_API_KEY", None)
    base.update(extra)
    return base


def _stage_files(files: list[Path], work: Path) -> list[str]:
    work.mkdir(parents=True, exist_ok=True)
    names = []
    for f in files:
        dest = work / Path(f).name
        if Path(f).resolve() != dest.resolve():
            shutil.copy(f, dest)
        names.append(dest.name)
    return names


def gemini(prompt: str, files: list[Path], work: Path, run=subprocess.run, env: dict | None = None,
           model: str = GEMINI_MODEL) -> str:
    e = _env(env)
    home = e.get("GEMINI_HOME", "/home/ai/gemini-home")
    names = _stage_files(files, Path(work))
    text = " ".join(f"@{n}" for n in names) + (" Open these files with your file viewer (do not run shell commands).\n" if names else "") + prompt
    cmd = [e.get("AGY_BIN", f"{home}/.local/bin/agy"), "--model", model, "-p", text, "--output-format", "json"]
    p = run(cmd, cwd=str(work), env={**e, "HOME": home}, capture_output=True, text=True, timeout=TIMEOUT,
            stdin=subprocess.DEVNULL)
    try:
        wrapper = json.loads(p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "{}")
    except json.JSONDecodeError:
        wrapper = {"status": "ERROR", "error": (p.stdout or "")[-500:] + (p.stderr or "")[-500:]}
    if wrapper.get("status") != "SUCCESS" or not wrapper.get("response"):
        err = str(wrapper.get("error") or p.stderr or "no answer")
        if PERSON.search(err):
            raise NeedsPerson(f"Gemini (agy) needs a person: {err[:300]}")
        raise ModelError(f"Gemini (agy) failed: {err[:300]}")
    return wrapper["response"]


def gemini_json(prompt: str, files: list[Path], work: Path, run=subprocess.run, env: dict | None = None) -> dict:
    """Gemini's answer as JSON; one more try when the first answer has none."""
    for attempt in (1, 2):
        text = gemini(prompt + ("\nAnswer with ONE JSON object only." if attempt == 2 else ""), files, work, run=run, env=env)
        try:
            return extract_json(text)
        except ModelError:
            if attempt == 2:
                raise


def claude_json(prompt: str, files: list[Path], work: Path, run=subprocess.run, env: dict | None = None) -> dict:
    """Claude Code reads the files itself (pictures, contact sheets) and answers with a JSON object."""
    e = _env(env)
    listing = "\n".join(f"- {Path(f).resolve()}" for f in files)
    text = (f"Look at these files with the Read tool:\n{listing}\n\n" if files else "") + prompt + "\nAnswer with ONE JSON object only."
    Path(work).mkdir(parents=True, exist_ok=True)
    cmd = [e.get("CLAUDE_BIN", "claude"), "-p", text, "--output-format", "json", "--allowedTools", "Read"]
    p = run(cmd, cwd=str(work), env=e, capture_output=True, text=True, timeout=TIMEOUT, stdin=subprocess.DEVNULL)
    try:
        wrapper = json.loads(p.stdout or "{}")
    except json.JSONDecodeError:
        wrapper = {"is_error": True, "result": (p.stdout or "")[-500:] + (p.stderr or "")[-500:]}
    result = str(wrapper.get("result") or "")
    if wrapper.get("is_error") or not result:
        if PERSON.search(result or p.stderr or ""):
            raise NeedsPerson(f"Claude needs a person: {result[:300]}")
        raise ModelError(f"Claude failed: {(result or p.stderr or 'no answer')[:300]}")
    return extract_json(result)


def codex_image(prompt: str, refs: list[Path], out: Path, run=subprocess.run, env: dict | None = None,
                codex_home: Path | None = None, model: str = CODEX_MODEL) -> Path:
    """One 9:16 picture from GPT Image through Codex, with our product photos attached (Champfuel's generate_image.py)."""
    e = _env(env)
    home = Path(codex_home or e.get("CODEX_HOME", "/home/ai/codex-accounts/plus-3"))
    work = Path(out).parent / f".codex-{Path(out).stem}"
    work.mkdir(parents=True, exist_ok=True)
    msg = ("Use your image generation tool to create ONE image (portrait 9:16, photographic, highest quality) from the prompt "
           "below. The attached pictures are our REAL product: keep its shape, label and colours exactly. Do not run shell "
           "commands, and do not try to save or copy the file; just generate it and reply 'done'.\n<prompt>\n" + prompt + "\n</prompt>")
    cmd = [e.get("CODEX_BIN", "codex"), "exec", "--skip-git-repo-check", "-s", "danger-full-access", "-C", str(work),
           "-m", model, *[f"--image={p}" for p in refs], "--", msg]
    p = run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, env={**e, "HOME": str(work), "CODEX_HOME": str(home)},
            timeout=TIMEOUT)
    both = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"session id:\s*([0-9a-f-]{20,})", both)
    new = glob.glob(os.path.join(home, "generated_images", m.group(1), "*.png")) if m else []
    shutil.rmtree(work, ignore_errors=True)
    if not new:
        if PERSON.search(both):
            raise NeedsPerson(f"Codex needs a person: {both[-300:]}")
        raise ModelError(f"Codex made no picture: {both[-300:]}")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(max(new, key=os.path.getmtime), out)
    return Path(out)
