"""The exact brief the engine's writer would get for one page (writer.build_request), so a page can be written in this session.
It also warns before writing when the site already has a page on the same question, or the Monday run has it queued, because
two DTJ pages on one question split Google's attention and neither ranks well.

Free: reads data/*.json and the newest scan.json; calls nothing.

  python .claude/skills/dtj-seo/scripts/page_brief.py --topic ads-no-orders --keywords "meta ads no sales,facebook ads no orders"
  python .claude/skills/dtj-seo/scripts/page_brief.py --keyword "meta ads not giving sales" \
      --keywords "facebook ads no sales,meta ads no orders" --pain "ads run, no orders" --out <folder>/brief.json
"""
from __future__ import annotations

import argparse
import json
import re

from _engine import WORK, latest_run, read_json, write_json
from seo_engine import gates, keywords, writer

STOP = {"a", "an", "the", "and", "or", "but", "if", "when", "still", "yet", "i", "my", "your", "you", "is", "are", "to", "of", "for", "in", "on", "with",
        "what", "why", "how", "do", "does", "should", "check", "first", "get", "it", "no", "not", "we", "our", "d2c", "brand",
        "brands", "india", "best", "guide", "2025", "2026",
        # words on nearly every DTJ page: they say nothing about the question
        "marketing", "agency", "digital", "tushar", "joshi", "dtj", "company", "services", "store", "website", "site"}
SAME = {"facebook": "meta", "instagram": "meta", "fb": "meta", "orders": "sales", "order": "sales", "sale": "sales",
        "ad": "ads", "running": "run", "runs": "run"}


def words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        w = SAME.get(w, w)
        if w not in STOP and len(w) > 1:
            out.add(w)
    return out


def overlap(a: set[str], b: set[str]) -> float:
    shared = len(a & b)
    if not a or not b or shared < min(2, len(a)):
        return 0.0
    return shared / min(len(a), len(b))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic", help="a topic id from data/topics.json (keeps its slug, so Monday knows it is done)")
    ap.add_argument("--keyword", help="main keyword (an ad-hoc page, or overrides the topic's)")
    ap.add_argument("--keywords", default="", help="other keywords, comma-separated (checked ones from Job 3)")
    ap.add_argument("--question", help="the founder's question (default: the keyword)")
    ap.add_argument("--pain", default="")
    ap.add_argument("--words", default="", help="the founder's own words, comma-separated")
    ap.add_argument("--place", help="Rajkot, Ahmedabad, Surat, Vadodara, Gujarat (city pages need proof)")
    ap.add_argument("--scan", help="scan.json to take linkable pages from (default: newest run)")
    ap.add_argument("--out", help="save the brief here")
    args = ap.parse_args()
    extra = [k.strip() for k in args.keywords.split(",") if k.strip()]

    topics = {t["id"]: t for t in gates.load_json("topics.json")["topics"]}
    if args.topic:
        if args.topic not in topics:
            raise SystemExit(f"unknown topic; known: {', '.join(topics)}")
        topic = dict(topics[args.topic])
        if args.keyword:
            topic["main_keyword"] = args.keyword
        topic["keywords"] = list(dict.fromkeys(topic.get("keywords", []) + extra))
    elif args.keyword:
        topic = {"id": keywords.slugify(args.keyword), "slug": keywords.slugify(args.keyword),
                 "question": args.question or args.keyword, "main_keyword": args.keyword, "keywords": extra,
                 "pain": args.pain, "words_they_use": [w.strip() for w in args.words.split(",") if w.strip()],
                 "place": args.place}
    else:
        raise SystemExit("give --topic or --keyword")

    scan_path = args.scan or latest_run("scan.json")
    pages = read_json(scan_path)["pages"] if scan_path else []

    # Same question already on the site, or queued for Monday?
    mine = words(" ".join([topic.get("question", ""), topic.get("main_keyword", "") or ""]))
    state_path = WORK / "state.json"
    written = set(read_json(state_path).get("written", [])) if state_path.exists() else set()
    clashes = []
    for tid, t in topics.items():
        if tid != topic["id"] and overlap(mine, words(t["question"] + " " + t["slug"].replace("-", " "))) >= 0.5:
            clashes.append({"kind": "queued topic" if tid not in written else "topic already written",
                            "id": tid, "slug": t["slug"], "question": t["question"],
                            "do": f"use --topic {tid} (or keep your keyword and pass --topic-id {tid} to page_gate.py) so the Monday run counts it as done"})
    for p in pages:
        if "/elementor-hf/" in p["url"] or p.get("status", 200) != 200:
            continue
        slug_words = p["url"].rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
        title = re.split(r"\s[-|]\s?(Digital Tushar Joshi|DTJ)", p.get("title") or "")[0]
        if overlap(mine, words(title + " " + slug_words)) >= 0.5:
            clashes.append({"kind": "existing page", "url": p["url"], "title": p.get("title"),
                            "do": "update that page instead, or make this one clearly different and link the two"})

    brief = {"topic_id": topic["id"], "slug": topic.get("slug"), "scan": str(scan_path) if scan_path else None,
             "possible_overlap": clashes, "request": writer.build_request(topic, pages),
             "rules": "Write to seo_engine/prompts/writer.md (+ city.md for a city page); output the article JSON in writer.SCHEMA."}
    if not pages:
        brief["warning"] = "no scan.json found: run the free website check first, or internal links cannot be checked"
    if args.out:
        write_json(args.out, brief)
        print(f"Saved: {args.out}")
    else:
        print(json.dumps(brief, indent=2, ensure_ascii=False))
    for c in clashes:
        print(f"OVERLAP ({c['kind']}): {c.get('id') or c.get('url')} - {c.get('question') or c.get('title')}. {c['do']}.")
    if not topic.get("keywords"):
        print("NOTE: no checked keywords besides the main one; run Job 3 first or say search demand is unchecked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
