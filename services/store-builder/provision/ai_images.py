"""Make the pictures a NEW store needs with ChatGPT's picture model: home-page banners and sample product pictures.

Harsh, 22 Oct 2026: "on a complete new store designing we will use chatgpt to generate banners and product images so our assets
gets ready". Two ways to the same pictures:
  api      OpenAI's Images API (GPT Image 2.5, the model behind ChatGPT's pictures). Needs OPENAI_API_KEY or DTJ_OPENAI_API_KEY
           (this process's environment first, then the Windows user variable). Unattended; costs a little per picture
           (openai.com/api/pricing). The key is never printed, written or returned.
  chatgpt  ChatGPT in the logged-in Chrome on the reel VPS over its DevTools port (services/reel-factory/reel_factory/chatgpt.py),
           no API key. DTJ_CHATGPT_CDP is that Chrome's address (default http://127.0.0.1:9222).
  auto     api when a key is saved, else chatgpt when that Chrome answers, else it stops and says what to set up.

Every picture is a SAMPLE for the design, never proof: the guard refuses a prompt that asks for words, prices, percentages, claims
(clinically, certified...), reviews or stars, before/after results, logos or real or famous people, and every prompt gets a suffix
that keeps words, numbers, labels and logos off the picture (the page adds the words; a picture can never carry a claim). The
sidecar <picture>.json says so, for the samples list.

Usage (from services/store-builder):
    python -m provision.ai_images --kind banner --prompt "Morning kitchen counter, warm light, fresh herbs" --out <dir>/banner-1.webp
    ... --kind product | lifestyle      sizes in KINDS
    ... --backend api|chatgpt|auto      (default auto)
    ... --dry-run                       prints the guarded prompt and the route only (free, nothing is made)
Exit 0 = made (the sidecar is printed), 1 = could not (the reason is printed; a key never is), 2 = the prompt was refused.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

ROOT = Path(__file__).resolve().parents[3]

# from .claude/skills/dtj-seo/scripts/blog_image.py (docs checked 19 Oct 2026): endpoint, models, b64 answer
API_URL = "https://api.openai.com/v1/images/generations"
MODELS = ("gpt-image-2.5-flare", "gpt-image-2.5-sunburst")  # fast, most precise
KINDS = {"banner": "1536x864", "product": "1024x1024", "lifestyle": "1536x1024"}
KEY_NAMES = ("OPENAI_API_KEY", "DTJ_OPENAI_API_KEY")
CDP_DEFAULT = "http://127.0.0.1:9222"
NOTE = "made by AI for the design; replace with the brand's own picture before the store goes live"

NO_TEXT = " No words, letters, numbers, labels, logos, brand names or watermarks anywhere on the picture."
SUFFIX = {
    "product": " A clean e-commerce studio photo of ONE product, plain light background, the whole product in frame and centred,"
               " soft natural shadow, true-to-life colours, sharp focus.",
    "banner": " A wide home-page banner photo, realistic light, with an empty calm area on one side (plain background) where the"
              " page places its headline: the page adds the words, the picture never does.",
    "lifestyle": " A realistic everyday lifestyle photo, natural light, Indian setting where people appear, phone-camera feel,"
                 " no glossy AI look.",
}

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


class ImagesError(RuntimeError):
    """A picture could not be made; the message is plain and never holds a key."""


def guard(prompt: str, kind: str, forbid: tuple[str, ...] | list[str] = ()) -> str:
    """The prompt with the no-text suffix and the kind's own suffix, or ValueError with every reason it is refused."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    text = re.sub(r"\s+", " ", prompt or "").strip()
    if not text:
        raise ValueError("the prompt is empty")
    why = [reason for reason, pattern in GUARD if re.search(pattern, text, re.I)]
    why += [f"names a brand or person that must not appear ({n})" for n in forbid if n and re.search(r"\b" + re.escape(n) + r"\b", text, re.I)]
    if why:
        raise ValueError("refused: " + "; ".join(why))
    return text.rstrip(".") + "." + SUFFIX[kind] + NO_TEXT


# ------------------------------------------------------------------------------------------------ which way the pictures are made
def _windows_var(name: str) -> str | None:
    sys.path.insert(0, str(ROOT / "services" / "install-catcher" / "tools"))
    from deploy import read_var  # noqa: PLC0415 - the same reader the install service's tools use
    return read_var(name)


def _key(environ: Mapping[str, str], read_var: Callable[[str], str | None] | None) -> tuple[str | None, str | None]:
    """(the key, the variable's name) or (None, None). Only the name is ever shown."""
    reader = read_var if read_var is not None else (_windows_var if environ is os.environ else (lambda _n: None))
    for name in KEY_NAMES:
        value = environ.get(name) or reader(name)
        if value:
            return value, name
    return None, None


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
          cdp_ok: Callable[[str], bool] | None = None) -> tuple[str | None, str]:
    """("api" | "chatgpt" | None, a plain reason). Never returns or prints the key."""
    key, name = _key(environ, read_var)
    if key:
        return "api", f"OpenAI Images API (key saved as {name})"
    base = _cdp_base(environ)
    if (cdp_ok or _cdp_answers)(base + "/json/version"):
        return "chatgpt", f"ChatGPT in the logged-in Chrome at {base}"
    return None, ("No way to make pictures yet: save an OpenAI key as the Windows user variable OPENAI_API_KEY (or "
                  "DTJ_OPENAI_API_KEY) on this computer, or open the logged-in Chrome on the reel VPS with its DevTools port "
                  f"(DTJ_CHATGPT_CDP, now {base}) so ChatGPT makes them.")


# ------------------------------------------------------------------------------------------------ the two makers
def _scrub(text: str, key: str | None) -> str:
    text = text.replace(key, "***") if key else text
    return re.sub(r"sk-[A-Za-z0-9_\-*]{6,}", "sk-***", text)


def _post(body: dict, key: str) -> tuple[int, dict]:
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


def make(kind: str, prompt: str, out: Path | str, *, backend: str = "auto", post=None, chatgpt=None,
         environ: Mapping[str, str] = os.environ, read_var: Callable[[str], str | None] | None = None,
         cdp_ok: Callable[[str], bool] | None = None, sleep=time.sleep, model: str = MODELS[0], quality: str = "medium",
         forbid: tuple[str, ...] | list[str] = ()) -> dict:
    """Make one picture at `out` (.webp or .png; another extension becomes .webp) and its sidecar <stem>.json; returns the sidecar.
    ValueError when the prompt is refused, ImagesError when no picture could be made."""
    text = guard(prompt, kind, forbid)
    out = Path(out)
    if out.suffix.lower() not in (".webp", ".png"):
        out = out.with_suffix(".webp")
    out.parent.mkdir(parents=True, exist_ok=True)
    if backend == "auto":
        backend, why = route(environ, read_var, cdp_ok)
        if backend is None:
            raise ImagesError(why)
    size, usage = KINDS[kind], None
    if backend == "api":
        key, _name = _key(environ, read_var)
        if not key:
            raise ImagesError("no OpenAI key saved (OPENAI_API_KEY or DTJ_OPENAI_API_KEY): nothing was made")
        fmt = out.suffix.lower().lstrip(".")
        body = {"model": model, "prompt": text, "size": size, "quality": quality, "output_format": fmt, "background": "opaque", "n": 1}
        if fmt == "webp":
            body["output_compression"] = 85
        answer = _call_api(body, key, post or _post, sleep)
        try:
            out.write_bytes(base64.b64decode(answer["data"][0]["b64_json"]))
        except (KeyError, IndexError, TypeError, ValueError):
            raise ImagesError("OpenAI's answer had no picture: nothing saved") from None
        usage, made_with = answer.get("usage"), model
    elif backend == "chatgpt":
        width, height = (int(x) for x in size.split("x"))
        shape = "wide landscape" if width > height else "square" if width == height else "portrait"
        mine = chatgpt is None
        try:
            cg = chatgpt or _attach_chatgpt(_cdp_base(environ))
        except Exception as exc:  # noqa: BLE001 - Chrome not open, playwright missing: said plainly
            raise ImagesError(f"could not reach ChatGPT's Chrome: {str(exc)[:200]}") from None
        try:
            out = Path(cg.image(f"Create one {shape} picture ({size}). {text}", out))
        except Exception as exc:  # noqa: BLE001 - ChatGPTError / NeedsPerson: a person looks at that Chrome window
            raise ImagesError(f"ChatGPT could not make it: {str(exc)[:300]}") from None
        finally:
            if mine and hasattr(cg, "close"):
                cg.close()
        made_with = "chatgpt.com"
    else:
        raise ImagesError("backend must be api, chatgpt or auto")
    if not out.exists() or not out.stat().st_size:
        raise ImagesError("no picture was saved")
    out = _fix_suffix(out)
    side = {"path": str(out), "kind": kind, "prompt": text, "backend": backend, "model": made_with, "size": size,
            "made_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "sample": True, "note": NOTE}
    if usage is not None:
        side["usage"] = usage  # token counts as OpenAI states them; no cost is worked out here
    out.with_suffix(".json").write_text(json.dumps(side, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return side


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", choices=sorted(KINDS), required=True)
    ap.add_argument("--prompt", required=True, help="what the picture shows: one scene, no words")
    ap.add_argument("--out", required=True, help="the picture's file (.webp or .png); the sidecar is <stem>.json next to it")
    ap.add_argument("--backend", choices=("auto", "api", "chatgpt"), default="auto")
    ap.add_argument("--model", choices=MODELS, default=MODELS[0])
    ap.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="medium")
    ap.add_argument("--forbid", action="append", default=[], help="a name that must not appear (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="the guarded prompt and the route only: nothing is made")
    a = ap.parse_args(argv)
    try:
        text = guard(a.prompt, a.kind, a.forbid)
    except ValueError as exc:
        print(f"REFUSED, nothing made: {str(exc).removeprefix('refused: ')}")
        return 2
    if a.dry_run:
        way, why = route() if a.backend == "auto" else (a.backend, "chosen with --backend")
        print(json.dumps({"prompt": text, "size": KINDS[a.kind], "route": way, "why": why}, indent=1, ensure_ascii=False))
        return 0
    try:
        side = make(a.kind, a.prompt, a.out, backend=a.backend, model=a.model, quality=a.quality, forbid=a.forbid)
    except ImagesError as exc:
        print(f"could not make the picture: {exc}")
        return 1
    print(json.dumps(side, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
