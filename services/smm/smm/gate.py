"""The code gate: a post that fails any check is never offered for approval (and approve.py refuses it).

Checks: numbers only from the cited proof, no blocked figure, no "never say" words (DTJ's process, promises, prices, a call with
Tushar, jargon), platform limits, links only to the audit page, files present and the right shape, AI pictures of people
labelled and never passed off as real, no repeat of the last 8 weeks, and the time slot.

Run:  python -m smm.gate <week folder> [--history <weeks folder>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image

from .platforms import PLATFORMS, URL_LENGTH_ON_X
from .week import LINK, Week, WeekError, load, publish_time

DATA = Path(__file__).resolve().parent / "data"
_NUMBER = re.compile(r"(?<![\w#.,])(₹\s?)?(\d[\d,]*(?:\.\d+)?)(\s?(?:%|x|X|L|Cr|lakh|crore|k|K)(?![A-Za-z]))?(\+)?")
_HASH_ONE = re.compile(r"(?<![\w])#1(?!\d)")
_URL = re.compile(r"https?://[^\s)]+")


def load_proof() -> dict:
    return json.loads((DATA / "proof.json").read_text(encoding="utf-8"))


def load_never_say() -> dict:
    return json.loads((DATA / "never_say.json").read_text(encoding="utf-8"))


def norm(token: str) -> str:
    """'₹40.18 lakh' -> '40.18l', '3,071' -> '3071', '4.42X' -> '4.42x'."""
    t = token.replace("₹", "").replace(",", "").replace(" ", "").lower()
    return t.replace("lakh", "l").replace("crore", "cr")


def numbers_in(text: str) -> list[str]:
    found = []
    for m in _NUMBER.finditer(text):
        whole = m.group(0).strip()
        bare = not m.group(1) and not m.group(3) and not m.group(4) and "," not in m.group(2) and "." not in m.group(2)
        if bare and int(m.group(2)) <= 10:
            continue  # "3 signs", "1 product": counting words, not claims
        found.append(whole)
    found += [m.group(0) for m in _HASH_ONE.finditer(text)]
    return found


def texts_of(post: dict) -> list[tuple[str, str]]:
    """(where, text) for every word that will be seen."""
    out = [(f"picture text {i + 1}", t) for i, t in enumerate(post.get("overlay_text") or [])]
    out += [(f"alt text {i + 1}", m["alt"]) for i, m in enumerate(post["media"])]
    for platform, spec in post["platforms"].items():
        for key, value in spec.items():
            if isinstance(value, str):
                out.append((f"{platform} {key}", value))
            elif key in ("hashtags", "tags"):
                out.append((f"{platform} {key}", " ".join(value)))
    return out


def x_length(text: str) -> int:
    text = text.replace(LINK, "x" * URL_LENGTH_ON_X)
    return len(_URL.sub("x" * URL_LENGTH_ON_X, text))


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_post(week: Week, post: dict, proof: dict, never: dict, history: list[dict], now: datetime | None = None) -> list[str]:
    problems: list[str] = []
    items = proof["items"]

    # proof and numbers
    unknown = [pid for pid in post["proof_ids"] if pid not in items]
    problems += [f"proof id {pid} is not in the proof list" for pid in unknown]
    allowed = {norm(f) for pid in post["proof_ids"] if pid in items for f in items[pid]["figures"]}
    blocked = {norm(f): why for pid in post["proof_ids"] if pid in items for f, why in items[pid]["blocked"].items()}
    blocked_all = {norm(f): why for f, why in proof["blocked_everywhere"].items()}
    for where, text in texts_of(post):
        for token in numbers_in(text):
            n = norm(token)
            if n in blocked or n in blocked_all:
                problems.append(f"{where}: '{token}' may not be used on social: {blocked.get(n) or blocked_all[n]}")
            elif n not in allowed and n.lstrip("+") not in allowed:
                problems.append(f"{where}: '{token}' is not a figure of the proof this post cites ({', '.join(post['proof_ids']) or 'none'})")

    # words
    for where, text in texts_of(post):
        low = text.lower()
        for group, phrases in never.items():
            if group.startswith("_") or (group == "jargon" and post.get("explains_jargon")):
                continue
            for phrase in phrases:
                if re.search(rf"(?<![a-z]){re.escape(phrase.lower())}(?![a-z])", low):
                    problems.append(f"{where}: says '{phrase}' ({group.replace('_', ' ')})")

    # platforms
    for platform, spec in post["platforms"].items():
        rules = PLATFORMS[platform]
        if post["format"] not in rules["formats"]:
            problems.append(f"{platform}: does not take a {post['format']} post")
        for field, limit in rules["text_fields"].items():
            value = spec.get(field, "")
            length = x_length(value) if platform == "x" else len(value.replace(LINK, "x" * 120)) + sum(len(t) + 1 for t in spec.get("hashtags", []))
            if length > limit:
                problems.append(f"{platform} {field}: {length} characters, the limit is {limit}")
        tags = spec.get("hashtags") or re.findall(r"(?<![\w&])#[A-Za-z]\w*", spec.get("text", ""))
        if len(tags) > rules["house_max_hashtags"]:
            problems.append(f"{platform}: {len(tags)} hashtags, DTJ's style is at most {rules['house_max_hashtags']}")
        joined = " ".join(v for v in spec.values() if isinstance(v, str))
        if not rules["links_clickable"] and (LINK in joined or _URL.search(joined)):
            problems.append(f"{platform}: links are not clickable there; write 'link in bio' instead")
        for url in _URL.findall(joined):
            problems.append(f"{platform}: write {LINK} instead of a typed link ({url}); code adds the tracked audit link")
        used = min(len(post["media"]), spec.get("first_media") or len(post["media"]))
        if post["format"] == "carousel" and used > rules["carousel_max"]:
            problems.append(f"{platform}: {used} pictures, the most is {rules['carousel_max']} (set first_media to use fewer)")

    # files
    if post["format"] == "text" and post["media"]:
        problems.append("a text post has no files")
    if post["format"] in ("image", "video") and len(post["media"]) != 1:
        problems.append(f"an {post['format']} post has exactly one file")
    if post["format"] == "carousel" and len(post["media"]) < 2:
        problems.append("a carousel has at least 2 pictures")
    for item in post["media"]:
        path = week.media_path(item)
        if not path.exists():
            problems.append(f"{item['file']}: file is missing")
            continue
        ext = path.suffix.lower()
        if post["format"] == "video":
            if ext != ".mp4":
                problems.append(f"{item['file']}: videos must be .mp4")
            for platform in post["platforms"]:
                limit = PLATFORMS[platform]["video_max_seconds"]
                if item.get("seconds") and item["seconds"] > limit:
                    problems.append(f"{item['file']}: {item['seconds']} s is too long for {platform} (max {limit} s)")
            continue
        try:
            with Image.open(path) as im:
                w, h = im.size
        except OSError:
            problems.append(f"{item['file']}: not a picture")
            continue
        for platform in post["platforms"]:
            rules = PLATFORMS[platform]
            if rules["image_types"] and ext not in rules["image_types"]:
                problems.append(f"{item['file']}: {platform} needs {'/'.join(sorted(rules['image_types']))}")
            lo, hi = rules["image_ratio"]
            if rules["image_types"] and not lo - 0.01 <= w / h <= hi + 0.01:
                problems.append(f"{item['file']}: shape {w}x{h} is outside what {platform} accepts")
        if path.stat().st_size > 8 * 1024 * 1024:
            problems.append(f"{item['file']}: over 8 MB")
        if min(w, h) < 1080 and post["format"] != "video":
            problems.append(f"{item['file']}: {w}x{h} is too small (at least 1080 px on the short side)")

    # AI-made media
    ai = post.get("ai_media") or {}
    if ai.get("realistic_person") and not ai.get("label_on"):
        problems.append("a realistic AI-made person needs the platform's 'made with AI' label switched on (label_on)")
    if ai.get("realistic_person") and post["theme"] in ("client-result", "founder"):
        problems.append("an AI-made person may not stand for a real client, a DTJ team member or Tushar")

    # repeats
    my_hashes = {file_hash(week.media_path(m)) for m in post["media"] if week.media_path(m).exists()}
    my_hook = first_line(post)
    for old in history:
        if my_hashes & set(old["hashes"]):
            problems.append(f"uses the same picture as {old['id']} (last 8 weeks)")
        if my_hook and my_hook == old["hook"]:
            problems.append(f"opens with the same line as {old['id']} (last 8 weeks)")

    # time
    if now is not None and publish_time(post) <= now:
        problems.append(f"publish time {post['publish_at']} has already passed")
    return problems


def first_line(post: dict) -> str:
    for spec in post["platforms"].values():
        text = spec.get("caption") or spec.get("text") or spec.get("title") or ""
        if text.strip():
            return re.sub(r"\s+", " ", text.strip().splitlines()[0]).lower()
    return ""


def history_of(weeks_root: Path | None, current: str, weeks_back: int = 8) -> list[dict]:
    """Earlier weeks' posts (picture fingerprints and opening lines) for the repeat check."""
    if not weeks_root or not weeks_root.exists():
        return []
    out = []
    for folder in sorted(weeks_root.iterdir()):
        if not folder.is_dir() or folder.name >= current:
            continue
        try:
            wk = load(folder)
        except (WeekError, ValueError):
            continue
        for p in wk.posts:
            out.append({"id": p["id"], "hook": first_line(p),
                        "hashes": [file_hash(wk.media_path(m)) for m in p["media"] if wk.media_path(m).exists()],
                        "when": publish_time(p)})
    if out:
        newest = max(o["when"] for o in out)
        out = [o for o in out if o["when"] >= newest - timedelta(weeks=weeks_back)]
    return out


def check_week(week: Week, history: list[dict] | None = None, now: datetime | None = None) -> dict[str, list[str]]:
    proof, never = load_proof(), load_never_say()
    report = {}
    seen_ids, slots = set(), {}
    for post in week.posts:
        problems = check_post(week, post, proof, never, history or [], now)
        if post["id"] in seen_ids:
            problems.append("the same post id is used twice")
        if not post["id"].startswith(week.name):
            problems.append(f"post id must start with {week.name}")
        seen_ids.add(post["id"])
        for platform in post["platforms"]:
            day = (platform, publish_time(post).date())
            if day in slots:
                problems.append(f"{platform} already has {slots[day]} on {day[1]}: one post a day per platform")
            slots[day] = post["id"]
        report[post["id"]] = problems
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check a week of posts before anyone is asked to approve it")
    ap.add_argument("week_folder")
    ap.add_argument("--history", help="the weeks/ folder, for the repeat check (default: the week folder's parent)")
    args = ap.parse_args(argv)
    try:
        wk = load(args.week_folder)
    except WeekError as e:
        print(f"BLOCKED: {e}")
        return 2
    root = Path(args.history) if args.history else Path(args.week_folder).resolve().parent
    report = check_week(wk, history_of(root, wk.name))
    bad = 0
    for pid, problems in report.items():
        print(f"{pid}: {'PASS' if not problems else 'BLOCKED'}")
        for p in problems:
            print(f"   - {p}")
        bad += bool(problems)
    print(f"\n{len(report) - bad} of {len(report)} posts pass.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
