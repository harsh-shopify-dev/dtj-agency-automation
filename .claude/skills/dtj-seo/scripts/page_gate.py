"""Run the engine's code gate on one page written in this session, then save it (and, only if the switches allow, a WordPress DRAFT).

The gate is gates.check, the same one the Monday run uses: approved numbers only, no ranking/guarantee/Tushar-call/RTO/AI talk,
links only to DTJ's site, the answer-first shape, and (with --top3) no 10-word phrase copied from Google's top 3 pages.

Input article JSON = writer.SCHEMA (title, slug, meta_description, short_answer, sections, faq, facts_used, internal_links,
sources), plus an optional "images" list made with blog_image.py:
  "images": [{"file": "<slug>-featured.webp", "role": "featured"}, {"file": "<slug>-inline.webp", "after_section": 1}]
Images never go into WordPress from here (the engine has no media upload yet): they are checked, shown in draft-preview.html,
and listed in images.md for the person who opens the draft.

  python .claude/skills/dtj-seo/scripts/page_gate.py <folder>/article.json --out <folder> [--kind city] \
      [--top3 URL URL URL] [--images-dir <folder>/images] [--wordpress]
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from _engine import WORK, read_json, write_json
from seo_engine import actionlog, city_page, config, gates, serp_skeleton, site_scan, wordpress, writer


def fingerprint_of(urls: list[str]) -> tuple[set[str], list[str]]:
    prints, notes = set(), []
    for url in urls:
        resp = site_scan.http_fetch(url)
        if resp.status != 200 or "html" not in resp.content_type.lower():
            notes.append(f"top-3 page not read ({resp.status}): {url}")
            continue
        parser = site_scan._PageParser()
        parser.feed(resp.text)
        prints |= serp_skeleton.shingles(" ".join(parser.text))
    return prints, notes


PENDING = ("dry_run", "browser_pending", "pending")


def check_images(article: dict, images_dir: Path | None) -> tuple[list[dict], list[dict], list[str]]:
    """(ready, pending, problems). A picture whose prompt passed but that isn't made yet (no key, or waiting for a person in
    the browser) is pending: it doesn't hold the text back, because WordPress gets the text only anyway. A bad alt text, a
    missing sidecar or a missing file after "generated" are problems and block."""
    ready, pending, problems = [], [], []
    for img in article.get("images", []):
        if images_dir is None:
            problems.append("images listed but no --images-dir given")
            break
        side = images_dir / (Path(img["file"]).stem + ".json")
        if not side.exists():
            problems.append(f"{img['file']}: no sidecar (make the picture with blog_image.py)")
            continue
        meta = read_json(side)
        alt_problems = gates.check_snippet(meta.get("alt", ""), min_len=5, max_len=125)
        if alt_problems:
            problems.append(f"{img['file']} alt text: {'; '.join(alt_problems)}")
            continue
        entry = {**img, "alt": meta["alt"], "via": meta.get("via", "api"), "status": meta.get("status")}
        if meta.get("status") in PENDING:
            pending.append(entry)
        elif meta.get("status") in ("generated", "generated_browser"):
            if (images_dir / img["file"]).exists():
                ready.append(entry)
            else:
                problems.append(f"{img['file']}: marked {meta['status']} but the picture file is missing")
        else:
            problems.append(f"{img['file']}: unknown picture status {meta.get('status')!r}")
    return ready, pending, problems


def preview(article: dict, body: str, images: list[dict]) -> str:
    """draft.html with the pictures placed, for a person to look at locally (relative paths into images/)."""
    e = html.escape
    for img in images:
        if img.get("role") == "featured":
            continue
        idx = img.get("after_section")
        if idx is None or not 0 <= idx < len(article["sections"]):
            continue
        heading = f"<h2>{e(article['sections'][idx]['heading'])}</h2>"
        start = body.find(heading)
        if start < 0:
            continue
        nxt = body.find("<h2>", start + len(heading))
        nxt = len(body) if nxt < 0 else nxt
        fig = f'<figure><img src="images/{e(img["file"])}" alt="{e(img["alt"])}" loading="lazy" width="1536"></figure>\n'
        body = body[:nxt] + fig + body[nxt:]
    featured = next((i for i in images if i.get("role") == "featured"), None)
    top = f'<img src="images/{e(featured["file"])}" alt="{e(featured["alt"])}" style="width:100%">\n' if featured else ""
    return (f"<!doctype html><meta charset=utf-8><title>{e(article['title'])}</title>"
            f"<body style='max-width:760px;margin:2rem auto;font:17px/1.6 system-ui;padding:0 16px'>"
            f"<h1>{e(article['title'])}</h1>{top}{body}</body>")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("article")
    ap.add_argument("--out", required=True)
    ap.add_argument("--kind", choices=("article", "city"), default="article")
    ap.add_argument("--top3", nargs="*", default=[], help="URLs of Google's top 3 for the main keyword (copy check)")
    ap.add_argument("--images-dir")
    ap.add_argument("--wordpress", action="store_true", help="also save a WordPress DRAFT if the switches allow (Tier 1)")
    ap.add_argument("--log", default=str(WORK / "actions.jsonl"), help="action log (default .work/seo/actions.jsonl)")
    ap.add_argument("--topic-id", help="the data/topics.json id this page answers; on PASS it is marked written so the Monday "
                                       "run doesn't write a second page on the same question")
    ap.add_argument("--state", default=str(WORK / "state.json"), help="engine state file (default .work/seo/state.json)")
    args = ap.parse_args()

    out = Path(args.out)
    article = read_json(args.article)
    images_dir = Path(args.images_dir) if args.images_dir else None
    fp, notes = fingerprint_of(args.top3) if args.top3 else (None, ["no top-3 URLs given: copy check not run"])
    core = {k: v for k, v in article.items() if k != "images"}
    result = gates.check(core, kind=args.kind, fingerprint=fp)
    blocks = list(result.blocks)
    if args.kind == "city" and result.ok:
        similar, score, other = city_page.too_similar(gates.article_text(core), WORK / "city-pages")
        if similar:
            blocks.append(f"reads {score:.0%} like the {other} page: make it about this city")
    images, pending, img_problems = check_images(article, images_dir)
    blocks += img_problems
    passed = not blocks

    cfg = config.load()
    log = actionlog.ActionLog(args.log)
    target = f"wordpress {'page' if args.kind == 'city' else 'post'} draft: {core.get('slug')}"
    report = {"status": "passed" if passed else "blocked", "blocks": blocks, "warnings": result.warnings,
              "words": result.words, "notes": notes, "images": images, "images_pending": pending, "wordpress": None,
              "topic_marked_written": None}

    if not passed:
        log.record(tier=0, mode=cfg.mode, target=target, action=f"gate {args.kind}", reason=core.get("title", ""),
                   result="blocked", evidence={"blocks": blocks})
    else:
        body = writer.to_html(core)
        (out).mkdir(parents=True, exist_ok=True)
        (out / "draft.html").write_text(body, encoding="utf-8")
        (out / "draft-preview.html").write_text(preview(core, body, images), encoding="utf-8")
        if images or pending:
            lines = [f"# Pictures for \"{core['title']}\"", "",
                     "Upload each in WordPress (Media > Add New), paste the alt text, and place it as shown.", ""]
            for img in images + pending:
                where = "Featured image" if img.get("role") == "featured" else \
                    f"After the section \"{core['sections'][img['after_section']]['heading']}\""
                state = "" if img in images else " **PENDING: not made yet (needs the OpenAI key, or ChatGPT in the browser).**"
                lines.append(f"- `{img['file']}`: {where}. Alt text: {img['alt']}{state}")
            (out / "images.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if args.topic_id:
            state_path = Path(args.state)
            state = read_json(state_path) if state_path.exists() else {}
            if args.topic_id not in state.setdefault("written", []):
                state["written"].append(args.topic_id)  # same as run_weekly: a passed page counts, so Monday won't redo it
                state["last_kind"] = args.kind
                write_json(state_path, state)
            report["topic_marked_written"] = args.topic_id
        if args.wordpress:
            decision = cfg.decide(1)
            if not decision.allowed:
                report["wordpress"] = f"not saved: {decision.reason}"
                log.record(tier=1, mode=cfg.mode, target=target, action="save as WordPress draft", reason=decision.reason,
                           result="recommended", after={"title": core["title"], "slug": core["slug"]})
            else:
                saved = wordpress.create_draft(cfg, title=core["title"], slug=core["slug"], html=body,
                                               excerpt=core["meta_description"], kind="pages" if args.kind == "city" else "posts")
                report["wordpress"] = saved
                log.record(tier=1, mode=cfg.mode, target=target, action="save as WordPress draft", reason=core["title"],
                           result="success", after=saved)
        else:
            log.record(tier=0, mode=cfg.mode, target=target, action=f"gate {args.kind}", reason=core["title"],
                       result="recommended", after={"title": core["title"], "slug": core["slug"], "files": str(out)})

    write_json(out / "gate.json", report)
    print(f"Gate: {report['status'].upper()} ({result.words} words).")
    for b in blocks:
        print(f"  BLOCK: {b}")
    for w in result.warnings:
        print(f"  warn: {w}")
    for n in notes:
        print(f"  note: {n}")
    for img in pending:
        print(f"  picture pending: {img['file']} ({img['status']}); see images.md")
    if report["topic_marked_written"]:
        print(f"  topic marked written: {report['topic_marked_written']}")
    if report["wordpress"]:
        print(f"  WordPress: {report['wordpress']}")
    print(f"Files: {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
