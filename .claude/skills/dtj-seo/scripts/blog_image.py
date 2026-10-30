"""Make one picture for a DTJ blog article with OpenAI's GPT Image 2.5.

Pictures only illustrate an idea. They are never proof: no numbers, no dashboards or screenshots, no logos, no real or
"client" people, no text at all. The guard below refuses a prompt that asks for any of those, and every prompt gets a
no-text suffix, so a picture can never carry a claim the fact gate has not seen.

Usage (from the repo root):
  python .claude/skills/dtj-seo/scripts/blog_image.py --slug ads-run-no-orders --role featured \
      --prompt "A founder at a small shop counter at night, looking at a phone, calm warm light" \
      --alt "Founder checking orders on a phone after closing the shop" --out .work/seo/<date>/images
  ... --dry-run   writes the request and sidecar only (free, no key)
  ... --via browser   no API key: checks the prompt, writes the sidecar and prints the exact prompt to paste into ChatGPT
                      in Claude's built-in browser (attended sessions only; see SKILL.md)
  python ... --slug ads-run-no-orders --role featured --out <same folder> --record <downloaded file>
                      after the person said yes to the download: copies it in as <slug>-<role>.<ext>, updates the sidecar

Key: OPENAI_API_KEY from the environment (Bitwarden -> GitHub secret). It is never printed or written.
Docs checked 19 Oct 2026: POST /v1/images/generations, models gpt-image-2.5-flare (fast) and gpt-image-2.5-sunburst
(most precise), output_format webp with output_compression, result in data[0].b64_json. Price: not on the docs pages,
see openai.com/api/pricing; the script reports the usage figures the answer returns, if any.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API_URL = "https://api.openai.com/v1/images/generations"
MODELS = ("gpt-image-2.5-flare", "gpt-image-2.5-sunburst")
SIZES = {"featured": "1536x864", "inline": "1536x1024", "square": "1024x1024"}

NO_TEXT_SUFFIX = (
    " Photographic editorial style, realistic light that fits the scene, Indian setting where people appear."
    " No text, no words, no letters, no numbers, no charts with values, no logos, no brand names, no watermarks,"
    " no user interface or screen contents readable."
)

# Each rule: (reason shown to the person, pattern). Case-insensitive.
GUARD = [
    ("numbers, prices or percentages belong in the text with a source, not in a picture",
     r"[₹$%]|\brs\.?\s?\d|\b\d+(\.\d+)?\s?(x|k|l|lakh|cr|crore|%|percent|roas|orders?)\b"),
    ("no dashboards, screenshots, reports or charts (a picture of results reads as proof)",
     r"\b(dashboard|screenshot|screen ?shot|analytics|report|chart|graph|ads manager|shopify admin|invoice|receipt)\b"),
    ("no logos or brand marks", r"\b(logo|brand mark|trademark|watermark)\b"),
    ("no testimonials, reviews, awards or badges", r"\b(testimonial|review|rating|stars?|award|trophy|badge|certificate|certified)\b"),
    ("no real or named people (Tushar, clients, team)", r"\b(tushar|joshi|our client|client named|real person|portrait of)\b"),
    ("no words in the picture", r"\b(text that says|caption reading|sign reading|headline|written|lettering|typography|the words)\b"),
]


def check_prompt(prompt: str, extra_names: list[str]) -> list[str]:
    problems = [reason for reason, pattern in GUARD if re.search(pattern, prompt, re.I)]
    for name in extra_names:
        if name and re.search(r"\b" + re.escape(name) + r"\b", prompt, re.I):
            problems.append(f"names a real brand or person ({name})")
    return problems


def check_alt(alt: str) -> list[str]:
    problems = []
    if not 10 <= len(alt) <= 125:
        problems.append("alt text should be 10-125 characters")
    if re.search(r"\d", alt):
        problems.append("alt text has a number")
    if re.search(r"^(image|picture|photo) of", alt, re.I):
        problems.append("alt text starts with 'image of'; describe the scene instead")
    return problems


def call_api(body: dict, key: str) -> dict:
    data = json.dumps(body).encode()
    for attempt in range(4):  # first try + 3 retries on 429/5xx (CLAUDE.md self-healing)
        req = urllib.request.Request(API_URL, data=data, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")[:500]
            if (err.code == 429 or err.code >= 500) and attempt < 3:
                time.sleep(2 ** (attempt + 1))
                continue
            raise SystemExit(f"OpenAI answered {err.code}: {detail}")
    raise SystemExit("unreachable")


def record(src: Path, out: Path, stem: str) -> int:
    """Bring in a picture downloaded from ChatGPT (after the person's yes) and finish its sidecar."""
    side_path = out / f"{stem}.json"
    if not side_path.exists():
        raise SystemExit(f"{side_path} not found: run --via browser first so the prompt was checked")
    if src.suffix.lower() not in (".png", ".webp", ".jpg", ".jpeg"):
        raise SystemExit("expected a .png, .webp or .jpg picture")
    sidecar = json.loads(side_path.read_text(encoding="utf-8"))
    dest = out / f"{stem}{src.suffix.lower()}"
    dest.write_bytes(src.read_bytes())
    sidecar.update(file=dest.name, status="generated_browser", bytes=dest.stat().st_size,
                   recorded=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    side_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": sidecar["status"], "file": str(dest), "bytes": sidecar["bytes"]}))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slug", required=True, help="the article slug; files are <slug>-<role>.webp/.json")
    ap.add_argument("--role", choices=sorted(SIZES), default="inline")
    ap.add_argument("--prompt", help="what the picture shows, one scene, no text")
    ap.add_argument("--alt", help="alt text: what a blind reader needs, no keyword stuffing, no numbers")
    ap.add_argument("--out", required=True, help="output folder, e.g. .work/seo/<date>/images")
    ap.add_argument("--model", choices=MODELS, default="gpt-image-2.5-flare")
    ap.add_argument("--quality", choices=("low", "medium", "high", "xhigh", "max", "auto"), default="medium")
    ap.add_argument("--size", help="override WIDTHxHEIGHT (default by role)")
    ap.add_argument("--forbid", action="append", default=[], help="extra names that must not appear (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="write the request and sidecar only; no key, no cost")
    ap.add_argument("--via", choices=("api", "browser"), default="api",
                    help="browser = no key; prints the prompt for ChatGPT in the built-in browser")
    ap.add_argument("--record", help="a picture the person approved downloading from ChatGPT; copies it in")
    args = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.slug):
        raise SystemExit("slug must be lowercase words joined by hyphens")
    out = Path(args.out)
    stem = f"{args.slug}-{args.role}"
    if args.record:
        return record(Path(args.record), out, stem)
    if not args.prompt or not args.alt:
        raise SystemExit("--prompt and --alt are required")
    problems = check_prompt(args.prompt, args.forbid) + check_alt(args.alt)
    if problems:
        print("REFUSED, nothing generated:")
        for p in problems:
            print(f"  - {p}")
        return 2

    out.mkdir(parents=True, exist_ok=True)
    body = {
        "model": args.model,
        "prompt": args.prompt.strip().rstrip(".") + "." + NO_TEXT_SUFFIX,
        "size": args.size or SIZES[args.role],
        "quality": args.quality,
        "output_format": "webp",
        "output_compression": 80,
        "background": "opaque",
        "n": 1,
    }
    sidecar = {
        "file": f"{stem}.webp",
        "alt": args.alt,
        "role": args.role,
        "request": body,
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "status": "dry_run" if args.dry_run else "pending",
        "via": args.via,
        "usage": None,
        "note": "Illustration only. Not proof of any result.",
    }

    if args.via == "browser" and not args.dry_run:
        width, height = body["size"].split("x")
        shape = "wide landscape" if int(width) > int(height) else "square" if width == height else "portrait"
        sidecar["status"] = "browser_pending"
        sidecar["file"] = None
        sidecar["browser_prompt"] = f"Create one {shape} image ({body['size']}). {body['prompt']}"
        (out / f"{stem}.json").write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")
        print("PASTE INTO CHATGPT:\n" + sidecar["browser_prompt"])
        print(json.dumps({"status": "browser_pending", "sidecar": str(out / f"{stem}.json")}))
        return 0

    if not args.dry_run:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise SystemExit("OPENAI_API_KEY is not set. Add it from Bitwarden; nothing was generated.")
        answer = call_api(body, key)
        try:
            image = base64.b64decode(answer["data"][0]["b64_json"])
        except (KeyError, IndexError, TypeError):
            raise SystemExit("OpenAI's answer had no image data; nothing saved.")
        (out / f"{stem}.webp").write_bytes(image)
        sidecar["status"] = "generated"
        sidecar["usage"] = answer.get("usage")  # token counts as OpenAI states them; cost is not computed here
        sidecar["bytes"] = len(image)

    (out / f"{stem}.json").write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": sidecar["status"], "file": str(out / sidecar["file"]),
                      "sidecar": str(out / f"{stem}.json"), "model": args.model, "size": body["size"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
