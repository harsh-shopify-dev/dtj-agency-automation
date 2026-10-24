"""Make the pictures a NEW store needs with ChatGPT's picture model: home-page banners and sample product pictures.

Harsh, 22 Oct 2026: "on a complete new store designing we will use chatgpt to generate banners and product images so our assets
gets ready", then "we will use chatgpt cli which will be hosted on our hostinger vps using which you can generate the images ...
where you have to upload the referennce images of our products". The "ChatGPT CLI" is Codex (OpenAI's command-line tool, logged
in with DTJ's ChatGPT account) on the VPS, as ~/work/run-ref.sh there already used it (found 23 Oct 2026). The ways, in this order:
  codex    Codex on THIS computer (the VPS, where the worker runs the store job): tools/vps/codex_image.sh. No API key.
  vps      the same script on DTJ's Hostinger VPS from another computer, over ssh: DTJ_IMAGE_VPS is the ssh target (e.g.
           ai@srv2048145.hstgr.cloud; this process's environment first, then the Windows user variable), DTJ_IMAGE_VPS_DIR the
           repo there (default ~/dtj-agency-automation). The prompt and the reference pictures go to a fresh /tmp/dtj-img-<id>
           folder on the VPS, the picture comes back, and only that folder is removed. No API key.
  api      OpenAI's Images API (GPT Image 2.5, the model behind ChatGPT's pictures). Needs OPENAI_API_KEY or DTJ_OPENAI_API_KEY
           (this process's environment first, then the Windows user variable). Unattended; costs a little per picture
           (openai.com/api/pricing). The key is never printed, written or returned.
  chatgpt  ChatGPT in the logged-in Chrome on the reel VPS over its DevTools port (services/reel-factory/reel_factory/chatgpt.py),
           no API key. DTJ_CHATGPT_CDP is that Chrome's address (default http://127.0.0.1:9222).
  auto     codex when this computer has it, else vps when DTJ_IMAGE_VPS is set and answers ssh, else api when a key is saved,
           else chatgpt when that Chrome answers, else it stops and says what to set up.
Reference pictures (--ref, refs=): photos of OUR product, uploaded with the prompt so the picture shows the real product (ChatGPT:
attached to the chat; the API: /v1/images/edits). The prompt then also says to keep the product exactly as in the reference.

Every picture is a SAMPLE for the design, never proof: the guard refuses a prompt that asks for words, prices, percentages, claims
(clinically, certified...), reviews or stars, before/after results, logos or real or famous people, and every prompt gets a suffix
that keeps words, numbers, labels and logos off the picture (the page adds the words; a picture can never carry a claim). The
sidecar <picture>.json says so, for the samples list.

Product pages (Harsh, 23 Oct 2026: "a product image is always 1:1 ... there should be 5 - 6 images explaining the product perfectly
such as whats the prodcuct, why this products, features, benefits, lifestyle like that a pro DTC brand applies the images"):
  gallery  a square picture for the product's own gallery. It MAY print a few short lines (--word, repeatable, the first is the
           headline), and only lines that stand in the page's facts.json (--facts) on a fact whose source is not a SAMPLE: the
           words are checked here, not trusted. Quoted text in the prompt must be one of those lines. Never prices or offers.
  section  a square picture for a section of the page (story, ingredients, uses, final push): no words, like the others.

Usage (from services/store-builder):
    python -m provision.ai_images --kind banner --prompt "Morning kitchen counter, warm light, fresh herbs" --out <dir>/banner-1.webp
    ... --kind product | lifestyle | section    sizes in KINDS
    ... --kind gallery --facts <client>/facts.json --word "High Protein Peri Spread" --word "26g protein per 100g"
    ... --ref <photo of our product>    (repeatable, up to 4)
    ... --backend codex|vps|api|chatgpt|auto  (default auto)
    ... --dry-run                       prints the guarded prompt and the route only (free, nothing is made)
Exit 0 = made (the sidecar is printed), 1 = could not (the reason is printed; a key never is), 2 = the prompt was refused.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

ROOT = Path(__file__).resolve().parents[3]

# from .claude/skills/dtj-seo/scripts/blog_image.py (docs checked 19 Oct 2026): endpoint, models, b64 answer
API_URL = "https://api.openai.com/v1/images/generations"
# With reference pictures: the edits endpoint, multipart with image[] (not re-checked against the docs on 22 Oct 2026: they were not
# reachable offline; the call sends only model, prompt, size, quality, output_format, n and the pictures, the fields the
# generations call above already uses)
EDITS_URL = "https://api.openai.com/v1/images/edits"
MODELS = ("gpt-image-2.5-flare", "gpt-image-2.5-sunburst")  # fast, most precise
KINDS = {"banner": "1536x864", "product": "1024x1024", "lifestyle": "1536x1024", "gallery": "1024x1024", "section": "1024x1024",
         "studio": "1024x1024"}
MAX_WORDS, MAX_WORD_CHARS = 7, 60  # a gallery picture: a headline and a few short lines, readable on a phone
KEY_NAMES = ("OPENAI_API_KEY", "DTJ_OPENAI_API_KEY")
CDP_DEFAULT = "http://127.0.0.1:9222"
VPS_VAR, VPS_DIR_VAR = "DTJ_IMAGE_VPS", "DTJ_IMAGE_VPS_DIR"
VPS_DIR_DEFAULT = "~/dtj-agency-automation"  # the repo on the VPS: tools/vps/codex_image.sh
CODEX_SCRIPT = ROOT / "tools" / "vps" / "codex_image.sh"
CODEX_SECONDS = 600  # run-ref.sh's own limit for one picture
SSH_OPTS = ("-o", "BatchMode=yes", "-o", "ConnectTimeout=10")
MAX_REFS = 4
REF_TYPES = (".jpg", ".jpeg", ".png", ".webp")
NOTE = "made by AI for the design; replace with the brand's own picture before the store goes live"

NO_TEXT = " No words, letters, numbers, labels, logos, brand names or watermarks anywhere on the picture."
# with a reference photo the product keeps its own label; nothing else gets words (Harsh, 22 Oct 2026: our real product in the picture)
REF_LINE = (" Keep the product exactly as in the reference photo: the same shape, colour, cap and pack, its label as it is in the"
            " reference (do not redraw it, change it or invent a label).")
NO_TEXT_REF = " No other words, letters, numbers, logos or watermarks anywhere on the picture: only the product's own label."
SUFFIX = {
    "product": " A clean e-commerce studio photo of ONE product, plain light background, the whole product in frame and centred,"
               " soft natural shadow, true-to-life colours, sharp focus.",
    "banner": " A wide home-page banner photo, realistic light, with an empty calm area on one side (plain background) where the"
              " page places its headline: the page adds the words, the picture never does.",
    "lifestyle": " A realistic everyday lifestyle photo, natural light, Indian setting where people appear, phone-camera feel,"
                 " no glossy AI look.",
    "gallery": " One square picture for the product's own gallery on its product page, the way a pro D2C brand explains its"
               " product picture by picture: the product big and sharp, the brand's colours, the food or the product in action,"
               " realistic and appetising, never plastic or AI-glossy.",
    "section": " One square picture for a section of the product page: it shows exactly what that section says, realistic and"
               " appetising, the product or its use in action, warm natural light, never plastic or AI-glossy.",
    # the gallery's photos (Harsh, 24 Oct 2026: the busy first set was "AI SLOP"; MojoVibe's standard): words come later, by code
    "studio": " Editorial studio photography for a premium D2C brand's product gallery: ONE subject only, a perfectly plain seamless"
              " paper backdrop in one flat colour, one hard key light from the top-left with a soft rim light and one crisp clean"
              " shadow. Nothing else in the frame: no flying ingredients, no floating pieces, no crumbs, no splashes, no props, no"
              " table edge, no garnish. A real camera photo (100mm macro lens, f/8), true colours, natural texture, sharp detail,"
              " no CGI, no AI-glossy or plastic look.",
}
WORDS_LINE = (" Print exactly these words, spelled exactly as written, and no other words: {quoted}. The first is the headline, the"
              " biggest; the others are smaller. A bold, clean, highly legible font that suits the brand.")
WORDS_END = " No other words, letters, numbers, logos or watermarks anywhere on the picture: only these lines{label}."

# (why, pattern), case-insensitive. Sizes in a description ("a 250 ml bottle") are allowed: they describe, they do not claim.
GUARD = [
    ("prices, discounts and percentages belong in the page's text with a source, not in a picture",
     r"[₹$€£%]|\brs\.?\s?\d|\b\d+(\.\d+)?\s?(percent|off|x|k|lakh|lac|cr|crore|reviews?|customers?|orders?|sold)\b"),
    ("no claims in a picture (clinically, certified, proven, approved, guaranteed, best seller, number one)",
     r"\b(clinical(ly)?|dermatologist|doctor[- ]recommended|certified|certificate|approved|proven|guarantee[d]?|cures?|heals?"
     r"|best[- ]?sell(er|ing)|number one|no\.?\s?1)\b|#\s?1\b|\b100\s?%"),
    ("no reviews, ratings, stars, testimonials, awards or badges",
     r"\b(reviews?|ratings?|stars?|five[- ]star|testimonials?|awards?|trophy|badges?|seal)\b"),
    ("no before/after or body-result pictures",
     r"\bbefore\s*(and|&|/|-)?\s*after\b|\b(transformation|weight loss|lose weight|slimmer|fat loss|acne[- ]free|wrinkle[- ]free"
     r"|hair regrowth)\b"),
    ("no logos or brand marks of anyone", r"\b(logos?|brand marks?|trademarks?|watermarks?)\b"),
    ("no real or famous people", r"\b(celebrit(y|ies)|famous|actor|actress|cricketer|influencer|lookalike|look[- ]alike"
                                  r"|real person|portrait of|tushar|joshi)\b"),
    ("no words on the picture (the page adds them)",
     r"\b(text that says|caption|headline|written|lettering|typography|the words?|saying|slogan|tagline|quote|label reading"
     r"|sign reading)\b"),
]


NO_WORDS_RULE = GUARD[-1][0]
# the printed lines of a gallery picture: facts only, and never a price, an offer, a count of customers or a result claim
WORD_GUARD = [
    ("prices and offers never go on a picture (they change; the page shows them)",
     r"[₹$€£]|\brs\.?\s?\d|\b(off|sale|discount|deal|offer|free|cashback|coupon)\b"),
    ("no counts of reviews, customers or orders", r"\b\d+\s?(k|lakh|lac|cr|crore)?\+?\s?(reviews?|customers?|orders?|sold|users)\b"),
    *[(why, pattern) for why, pattern in GUARD[1:4]],
]


class ImagesError(RuntimeError):
    """A picture could not be made; the message is plain and never holds a key."""


FREE_HEADINGS = ("what's inside", "inside the jar", "inside the pack", "ingredients", "how to use", "how to use it", "ways to use it",
                 "serving ideas", "nutrition facts")  # plain headings that claim nothing


def _norm(text: str) -> str:
    """For matching a printed line to a fact: lower case, letters, digits and % only, "and" = "&" ("26g" = "26 g")."""
    return re.sub(r"[^0-9a-z%]+", "", re.sub(r"\band\b|&", " ", (text or "").lower()))


def fact_lines(facts: dict) -> list[tuple[str, str]]:
    """Every text in facts.json with the source of the object it sits in: (normalised text, source). A list of strings takes the
    source of its parent object; a SAMPLE source stays SAMPLE. A real source is a text too: it quotes the pack ("pack serving
    ideas: dip for nachos")."""
    found: list[tuple[str, str]] = []

    def walk(node, source: str) -> None:
        if isinstance(node, dict):
            here = str(node.get("source") or source)
            if node.get("source") and not here.upper().startswith("SAMPLE"):
                found.append((_norm(here), here))
            for key, value in node.items():
                if key != "source":
                    walk(value, here)
        elif isinstance(node, list):
            for value in node:
                walk(value, source)
        elif isinstance(node, str) and _norm(node):
            found.append((_norm(node), source))

    walk(facts, "")
    return found


def check_words(words: list[str] | tuple, facts: dict | None) -> list[dict]:
    """The printed lines of a gallery picture, each with the fact it stands on, or ValueError with every reason. A line must stand
    inside one text of facts.json (two texts of one fact count too: "88%" + "peanut butter") whose source is not a SAMPLE."""
    words = [re.sub(r"\s+", " ", w or "").strip() for w in words]
    words = [w for w in words if w]
    if not words:
        return []
    if facts is None:
        raise ValueError("printed words need the page's facts.json (--facts): every line must stand on a fact")
    why = []
    if len(words) > MAX_WORDS:
        why.append(f"{len(words)} lines: at most {MAX_WORDS} on one picture")
    lines = fact_lines(facts)
    pairs: dict[str, str] = {}
    if isinstance(facts, dict):
        for node in _objects(facts):
            texts = [(k, _norm(v)) for k, v in node.items() if isinstance(v, str) and k != "source" and _norm(v)]
            for (_, a), (_, b) in ((x, y) for x in texts for y in texts if x != y):
                pairs.setdefault(a + b, str(node.get("source") or ""))
    out = []
    for w in words:
        if len(w) > MAX_WORD_CHARS:
            why.append(f"{w[:30]!r}...: longer than {MAX_WORD_CHARS} characters")
            continue
        why += [f"{w!r}: {reason}" for reason, pattern in WORD_GUARD if re.search(pattern, w, re.I)]
        key = _norm(w)
        if key in {_norm(h) for h in FREE_HEADINGS}:
            out.append({"text": w, "source": "a plain heading (claims nothing)"})
            continue
        real = [src for text, src in lines if key in text and src and not src.upper().startswith("SAMPLE")]  # a named source only
        real += [src for text, src in pairs.items() if key == text and src and not src.upper().startswith("SAMPLE")]
        if not real:
            sample = any(key in text for text, _src in lines)
            why.append(f"{w!r}: " + ("stands only on a SAMPLE fact or a text with no source; a picture prints only sourced facts"
                                    if sample else "is not in facts.json; a picture prints only the page's own facts"))
            continue
        out.append({"text": w, "source": real[0]})
    if why:
        raise ValueError("refused: " + "; ".join(why))
    return out


def _objects(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _objects(value)
    elif isinstance(node, list):
        for value in node:
            yield from _objects(value)


def guard(prompt: str, kind: str, forbid: tuple[str, ...] | list[str] = (), refs: bool = False, words: list[str] | tuple = ()) -> str:
    """The prompt with the no-text suffix and the kind's own suffix, or ValueError with every reason it is refused. With reference
    photos of our product (refs=True) the product keeps its own label and nothing else carries words. A prompt that points at the
    reference ("the product in the reference photo", "this exact bottle") is fine. `words` (gallery only, already checked against
    the facts by check_words): the only text the picture prints; the prompt may then place them ("the headline top-left"), and any
    quoted text in it must be one of them."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    text = re.sub(r"\s+", " ", prompt or "").strip()
    if not text:
        raise ValueError("the prompt is empty")
    words = [re.sub(r"\s+", " ", w).strip() for w in words if w and w.strip()]
    if words and kind != "gallery":
        raise ValueError("refused: only a gallery picture prints words (--kind gallery)")
    rules = [(r, p) for r, p in GUARD if not (words and r == NO_WORDS_RULE)]
    why = [reason for reason, pattern in rules if re.search(pattern, text, re.I)]
    why += [f"names a brand or person that must not appear ({n})" for n in forbid if n and re.search(r"\b" + re.escape(n) + r"\b", text, re.I)]
    if words:
        known = {_norm(w) for w in words}
        why += [f"quotes {q!r}, which is not one of the printed lines" for q in re.findall(r'["“]([^"”]+)["”]', text)
                if _norm(q) not in known]
    if why:
        raise ValueError("refused: " + "; ".join(why))
    if words:
        quoted = ", ".join(f'"{w}"' for w in words)
        end = WORDS_END.format(label=" and the product's own label" if refs else "")
        return text.rstrip(".") + "." + SUFFIX[kind] + (REF_LINE if refs else "") + WORDS_LINE.format(quoted=quoted) + end
    return text.rstrip(".") + "." + SUFFIX[kind] + (REF_LINE + NO_TEXT_REF if refs else NO_TEXT)


# ------------------------------------------------------------------------------------------------ which way the pictures are made
def _windows_var(name: str) -> str | None:
    sys.path.insert(0, str(ROOT / "services" / "install-catcher" / "tools"))
    from deploy import read_var  # noqa: PLC0415 - the same reader the install service's tools use
    return read_var(name)


def _reader(environ: Mapping[str, str], read_var: Callable[[str], str | None] | None) -> Callable[[str], str | None]:
    return read_var if read_var is not None else (_windows_var if environ is os.environ else (lambda _n: None))


def _var(name: str, environ: Mapping[str, str], read_var: Callable[[str], str | None] | None) -> str | None:
    return (environ.get(name) or _reader(environ, read_var)(name) or "").strip() or None


def _key(environ: Mapping[str, str], read_var: Callable[[str], str | None] | None) -> tuple[str | None, str | None]:
    """(the key, the variable's name) or (None, None). Only the name is ever shown."""
    reader = _reader(environ, read_var)
    for name in KEY_NAMES:
        value = environ.get(name) or reader(name)
        if value:
            return value, name
    return None, None


Runner = Callable[[list, float], "tuple[int, str, str]"]  # argv, timeout -> (exit code, stdout, stderr)


def _run(argv: list, timeout: float) -> tuple[int, str, str]:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except FileNotFoundError:
        return 127, "", f"{argv[0]} is not installed on this computer"
    except subprocess.TimeoutExpired:
        return 124, "", f"no answer within {int(timeout)} s"
    return r.returncode, r.stdout, r.stderr


def _vps_answers(host: str, runner: Runner = _run) -> bool:
    return runner(["ssh", *SSH_OPTS, host, "true"], 25)[0] == 0


def _codex_here() -> bool:
    """Codex on this computer (the VPS): the worker's store job makes pictures right here."""
    return os.name != "nt" and bool(shutil.which("codex") or Path("~/.npm-global/bin/codex").expanduser().exists())


def _cdp_base(environ: Mapping[str, str]) -> str:
    base = (environ.get("DTJ_CHATGPT_CDP") or CDP_DEFAULT).strip().rstrip("/")
    return base[: -len("/json/version")] if base.endswith("/json/version") else base


def _cdp_answers(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status == 200 and "webSocketDebuggerUrl" in json.loads(r.read() or b"{}")
    except (OSError, ValueError):
        return False


def route(environ: Mapping[str, str] = os.environ, read_var: Callable[[str], str | None] | None = None,
          cdp_ok: Callable[[str], bool] | None = None, vps_ok: Callable[[str], bool] | None = None,
          codex_ok: Callable[[], bool] | None = None) -> tuple[str | None, str]:
    """("codex" | "vps" | "api" | "chatgpt" | None, a plain reason). Never returns or prints the key."""
    if (codex_ok or _codex_here)():
        return "codex", "Codex on this computer (DTJ's ChatGPT account)"
    host = _var(VPS_VAR, environ, read_var)
    if host and (vps_ok or _vps_answers)(host):
        return "vps", f"Codex on the VPS ({host}, over ssh)"
    key, name = _key(environ, read_var)
    if key:
        return "api", f"OpenAI Images API (key saved as {name})"
    base = _cdp_base(environ)
    if (cdp_ok or _cdp_answers)(base + "/json/version"):
        return "chatgpt", f"ChatGPT in the logged-in Chrome at {base}"
    down = f" ({VPS_VAR} is {host} but ssh did not answer: is this computer's key in the VPS user's authorized_keys?)" if host else ""
    return None, (f"No way to make pictures yet{down}: set the Windows user variable {VPS_VAR} to the VPS's ssh target (e.g. "
                  "ai@srv2048145.hstgr.cloud) so Codex there makes them, or save an OpenAI key as OPENAI_API_KEY (or "
                  "DTJ_OPENAI_API_KEY) on this computer, or open the logged-in Chrome with its DevTools port "
                  f"(DTJ_CHATGPT_CDP, now {base}).")


# ------------------------------------------------------------------------------------------------ the two makers
def _scrub(text: str, key: str | None) -> str:
    text = text.replace(key, "***") if key else text
    return re.sub(r"sk-[A-Za-z0-9_\-*]{6,}", "sk-***", text)


def _multipart(fields: dict, files: list[Path]) -> tuple[bytes, str]:
    boundary = "dtj" + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for f in files:
        kind = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="{f.name}"\r\n'
                     f"Content-Type: {kind}\r\n\r\n".encode() + f.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _post(body: dict, key: str) -> tuple[int, dict]:
    """The generations call (JSON), or with body["image"] (our product's photos) the edits call (multipart, image[])."""
    if body.get("image"):
        data, ctype = _multipart({k: v for k, v in body.items() if k != "image"}, [Path(x) for x in body["image"]])
        req = urllib.request.Request(EDITS_URL, data=data, method="POST", headers={"Authorization": f"Bearer {key}", "Content-Type": ctype})
    else:
        req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as err:
        return err.code, {"error": err.read().decode("utf-8", "replace")[:500]}
    except urllib.error.URLError as err:
        return 0, {"error": str(err.reason)[:300]}


def _call_api(body: dict, key: str, post, sleep) -> dict:
    status, got = 0, {}
    for attempt in range(4):  # first try + 3 retries on a dropped connection, 429 or 5xx (CLAUDE.md self-healing)
        status, got = post(body, key)
        if status == 200:
            return got
        if (status in (0, 429) or status >= 500) and attempt < 3:
            sleep(2 ** (attempt + 1))
            continue
        break
    detail = got.get("error") if isinstance(got, dict) else got
    detail = json.dumps(detail) if not isinstance(detail, str) else detail
    raise ImagesError(_scrub(f"OpenAI answered {status or 'no connection'}: {detail[:300]}", key))


def _suffix_for(path: Path) -> str:
    head = path.read_bytes()[:12]
    if head.startswith(b"\x89PNG"):
        return ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    if head.startswith(b"\xff\xd8"):
        return ".jpg"
    return path.suffix


def _fix_suffix(path: Path) -> Path:
    """ChatGPT may hand back a PNG for a .webp name: the file keeps its real type's extension."""
    real = _suffix_for(path)
    if real and real != path.suffix.lower():
        fixed = path.with_suffix(real)
        fixed.unlink(missing_ok=True)
        path.rename(fixed)
        return fixed
    return path


def _attach_chatgpt(base: str):
    sys.path.insert(0, str(ROOT / "services" / "reel-factory"))
    from reel_factory.chatgpt import ChatGPT  # noqa: PLC0415
    return ChatGPT.attach(base)


def _chat_prompt(text: str, size: str, refs: list[Path]) -> str:
    width, height = (int(x) for x in size.split("x"))
    shape = "wide landscape" if width > height else "square" if width == height else "portrait"
    ref = (f"Use the attached photo{'s' if len(refs) > 1 else ''} of our product as the reference. " if refs else "")
    return f"Create one {shape} picture ({size}). {ref}{text}"


def _remote_dir(base: str) -> str:
    """The VPS folder for the shell: ~/ stays the user's home, the rest is quoted."""
    return '"$HOME"/' + shlex.quote(base[2:]) if base.startswith("~/") else shlex.quote(base)


def _answer(stdout: str) -> dict:
    lines = [ln for ln in stdout.strip().splitlines() if ln.strip().startswith("{")]
    try:
        return json.loads(lines[-1]) if lines else {}
    except ValueError:
        return {}


def _codex_make(chat_prompt: str, out: Path, refs: list[Path], runner: Runner, timeout: int = CODEX_SECONDS) -> Path:
    """One picture by Codex on this computer (tools/vps/codex_image.sh), saved as a PNG next to `out`."""
    png = out.with_suffix(".png")
    with tempfile.TemporaryDirectory() as tmp:
        prompt = Path(tmp) / "prompt.txt"
        prompt.write_text(chat_prompt, encoding="utf-8")
        argv = ["bash", str(CODEX_SCRIPT), "--prompt-file", str(prompt), "--out", str(png), "--timeout", str(timeout)]
        for r in refs:
            argv += ["--ref", str(r)]
        code, so, err = runner(argv, timeout + 60)
    answer = _answer(so)
    if not answer.get("ok"):
        raise ImagesError(f"Codex could not make it: {answer.get('error') or err.strip()[:200] or f'exit {code}'}")
    return png


def _vps_make(host: str, chat_prompt: str, out: Path, refs: list[Path], folder: str, runner: Runner,
              timeout: int = CODEX_SECONDS) -> Path:
    """One picture by Codex on the VPS (tools/vps/codex_image.sh): a fresh /tmp/dtj-img-<id> there, the prompt and our product's
    photos copied in, the script run, the picture copied back, and only that folder removed."""
    rdir = f"/tmp/dtj-img-{uuid.uuid4().hex[:12]}"
    assert re.fullmatch(r"/tmp/dtj-img-[0-9a-f]{12}", rdir)

    def run(argv: list, wait: float) -> tuple[int, str, str]:
        code, so, se = runner(argv, wait)
        if code in (124, 127):
            raise ImagesError(f"{argv[0]} to {host}: {se.strip()[:200]}")
        return code, so, se
    code, _, err = run(["ssh", *SSH_OPTS, host, f"mkdir -m 700 {rdir}"], 60)
    if code:
        raise ImagesError(f"the VPS {host} did not take the job (ssh exit {code}): {err.strip()[:200]}")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / "prompt.txt"
            local.write_text(chat_prompt, encoding="utf-8")
            sent = [local]
            for i, r in enumerate(refs, 1):  # unique names: two products' "1.jpg" never overwrite each other
                copy = Path(tmp) / f"ref-{i}{r.suffix.lower()}"
                shutil.copyfile(r, copy)
                sent.append(copy)
            code, _, err = run(["scp", "-q", *SSH_OPTS, *[str(x) for x in sent], f"{host}:{rdir}/"], 180)
            if code:
                raise ImagesError(f"could not copy the prompt and photos to {host} (scp exit {code}): {err.strip()[:200]}")
        refs_args = "".join(f" --ref {shlex.quote(f'{rdir}/ref-{i}{r.suffix.lower()}')}" for i, r in enumerate(refs, 1))
        command = (f"cd {_remote_dir(folder)} && bash tools/vps/codex_image.sh --prompt-file {shlex.quote(rdir + '/prompt.txt')} "
                   f"--out {shlex.quote(rdir + '/out.png')}{refs_args} --timeout {int(timeout)}")
        code, so, err = run(["ssh", *SSH_OPTS, host, command], timeout + 120)
        answer = _answer(so)
        if not answer.get("ok"):
            why = answer.get("error") or err.strip()[:200] or f"exit {code}"
            raise ImagesError(f"Codex on the VPS could not make it: {why}")
        path = str(answer.get("path") or "")
        if not path.startswith(rdir + "/"):
            raise ImagesError("the VPS answered with a picture outside its job folder: nothing copied")
        code, _, err = run(["scp", "-q", *SSH_OPTS, f"{host}:{path}", str(out)], 180)
        if code:
            raise ImagesError(f"could not copy the picture back from {host} (scp exit {code}): {err.strip()[:200]}")
    finally:
        runner(["ssh", *SSH_OPTS, host, f"rm -rf -- {rdir}"], 60)  # only the folder this call made
    return out


def make(kind: str, prompt: str, out: Path | str, *, backend: str = "auto", post=None, chatgpt=None,
         environ: Mapping[str, str] = os.environ, read_var: Callable[[str], str | None] | None = None,
         cdp_ok: Callable[[str], bool] | None = None, sleep=time.sleep, model: str = MODELS[0], quality: str = "medium",
         forbid: tuple[str, ...] | list[str] = (), refs: list[Path | str] | tuple = (), runner: Runner | None = None,
         vps_ok: Callable[[str], bool] | None = None, codex_ok: Callable[[], bool] | None = None,
         words: list[str] | tuple = (), facts: dict | str | Path | None = None) -> dict:
    """Make one picture at `out` (.webp or .png; another extension becomes .webp) and its sidecar <stem>.json; returns the sidecar.
    `refs`: up to 4 photos of OUR product (jpg, png, webp) the picture must show as they are. ValueError when the prompt is
    refused, ImagesError when no picture could be made. `words` + `facts` (gallery only): the lines it prints, each checked against
    facts.json (a dict or its path) by check_words."""
    refs = [Path(r).resolve() for r in refs]  # absolute: Codex runs in its own folder, where a relative path finds nothing
    if len(refs) > MAX_REFS:
        raise ImagesError(f"{len(refs)} reference photos: at most {MAX_REFS}")
    bad = [r.name for r in refs if r.suffix.lower() not in REF_TYPES or not r.is_file() or not r.stat().st_size]
    if bad:
        raise ImagesError(f"reference photo missing or not a jpg, png or webp: {', '.join(bad)}")
    if isinstance(facts, (str, Path)):
        facts = json.loads(Path(facts).read_text(encoding="utf-8"))
    printed = check_words(words, facts)
    text = guard(prompt, kind, forbid, refs=bool(refs), words=[w["text"] for w in printed])
    out = Path(out).resolve()
    if out.suffix.lower() not in (".webp", ".png"):
        out = out.with_suffix(".webp")
    out.parent.mkdir(parents=True, exist_ok=True)
    if backend == "auto":
        backend, why = route(environ, read_var, cdp_ok, vps_ok, codex_ok)
        if backend is None:
            raise ImagesError(why)
    size, usage = KINDS[kind], None
    if backend == "codex":
        out = _codex_make(_chat_prompt(text, size, refs), out, refs, runner or _run)
        made_with = "Codex (this computer)"
    elif backend == "vps":
        host = _var(VPS_VAR, environ, read_var)
        if not host:
            raise ImagesError(f"{VPS_VAR} is not set: the VPS's ssh target, e.g. ai@srv2048145.hstgr.cloud")
        folder = _var(VPS_DIR_VAR, environ, read_var) or VPS_DIR_DEFAULT
        out = _vps_make(host, _chat_prompt(text, size, refs), out, refs, folder, runner or _run)
        made_with = f"Codex (VPS {host})"
    elif backend == "api":
        key, _name = _key(environ, read_var)
        if not key:
            raise ImagesError("no OpenAI key saved (OPENAI_API_KEY or DTJ_OPENAI_API_KEY): nothing was made")
        fmt = out.suffix.lower().lstrip(".")
        body = {"model": model, "prompt": text, "size": size, "quality": quality, "output_format": fmt, "background": "opaque", "n": 1}
        if fmt == "webp":
            body["output_compression"] = 85
        if refs:  # our product's photos: the edits call (multipart image[]); "background" is left to the model there
            body.pop("background")
            body["image"] = [str(r) for r in refs]
        answer = _call_api(body, key, post or _post, sleep)
        try:
            out.write_bytes(base64.b64decode(answer["data"][0]["b64_json"]))
        except (KeyError, IndexError, TypeError, ValueError):
            raise ImagesError("OpenAI's answer had no picture: nothing saved") from None
        usage, made_with = answer.get("usage"), model
    elif backend == "chatgpt":
        mine = chatgpt is None
        try:
            cg = chatgpt or _attach_chatgpt(_cdp_base(environ))
        except Exception as exc:  # noqa: BLE001 - Chrome not open, playwright missing: said plainly
            raise ImagesError(f"could not reach ChatGPT's Chrome: {str(exc)[:200]}") from None
        try:
            out = Path(cg.image(_chat_prompt(text, size, refs), out, files=[str(r) for r in refs]))
        except Exception as exc:  # noqa: BLE001 - ChatGPTError / NeedsPerson: a person looks at that Chrome window
            raise ImagesError(f"ChatGPT could not make it: {str(exc)[:300]}") from None
        finally:
            if mine and hasattr(cg, "close"):
                cg.close()
        made_with = "chatgpt.com"
    else:
        raise ImagesError("backend must be codex, vps, api, chatgpt or auto")
    if not out.exists() or not out.stat().st_size:
        raise ImagesError("no picture was saved")
    out = _fix_suffix(out)
    side = {"path": str(out), "kind": kind, "prompt": text, "backend": backend, "model": made_with, "size": size,
            "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "sample": True, "note": NOTE}
    if refs:
        side["refs"] = [str(r) for r in refs]
    if printed:
        side["words"] = printed  # each printed line with the fact it stands on: read them on the picture before it is used
    if usage is not None:
        side["usage"] = usage  # token counts as OpenAI states them; no cost is worked out here
    out.with_suffix(".json").write_text(json.dumps(side, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return side


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", choices=sorted(KINDS), required=True)
    ap.add_argument("--prompt", required=True, help="what the picture shows: one scene, no words")
    ap.add_argument("--out", required=True, help="the picture's file (.webp or .png); the sidecar is <stem>.json next to it")
    ap.add_argument("--backend", choices=("auto", "codex", "vps", "api", "chatgpt"), default="auto")
    ap.add_argument("--ref", action="append", default=[], help="a photo of our product the picture must show as it is (repeatable)")
    ap.add_argument("--model", choices=MODELS, default=MODELS[0])
    ap.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="medium")
    ap.add_argument("--forbid", action="append", default=[], help="a name that must not appear (repeatable)")
    ap.add_argument("--word", action="append", default=[], help="gallery only: a line the picture prints, from facts.json (repeatable; "
                    "the first is the headline)")
    ap.add_argument("--facts", help="gallery with --word: the page's facts.json; every printed line must stand on a real fact in it")
    ap.add_argument("--dry-run", action="store_true", help="the guarded prompt and the route only: nothing is made")
    a = ap.parse_args(argv)
    try:
        facts = json.loads(Path(a.facts).read_text(encoding="utf-8")) if a.facts else None
        printed = check_words(a.word, facts)
        text = guard(a.prompt, a.kind, a.forbid, refs=bool(a.ref), words=[w["text"] for w in printed])
    except (OSError, ValueError) as exc:
        print(f"REFUSED, nothing made: {str(exc).removeprefix('refused: ')}")
        return 2
    if a.dry_run:
        way, why = route() if a.backend == "auto" else (a.backend, "chosen with --backend")
        print(json.dumps({"prompt": text, "size": KINDS[a.kind], "refs": a.ref, "words": printed, "route": way, "why": why}, indent=1,
                         ensure_ascii=False))
        return 0
    try:
        side = make(a.kind, a.prompt, a.out, backend=a.backend, model=a.model, quality=a.quality, forbid=a.forbid, refs=a.ref,
                    words=a.word, facts=facts)
    except ImagesError as exc:
        print(f"could not make the picture: {exc}")
        return 1
    print(json.dumps(side, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
