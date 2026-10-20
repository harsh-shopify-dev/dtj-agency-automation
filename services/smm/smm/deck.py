"""Step 5: the week's deck for approval. Built by code from week.json, so it always shows exactly what will be posted.

Slides: cover; the calendar (day by day, which post goes on which platform, India time); one slide per post with its picture,
its words per platform, the proof it uses and its gate result; and a last slide listing what needs a yes.

    python -m smm deck <week folder> [--out deck.pptx]
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Inches, Pt

from .gate import check_week, history_of
from .week import Week, publish_time

INK, PAPER, BRAND, GREY = RGBColor(0x11, 0x11, 0x11), RGBColor(0xF7, 0xF5, 0xF2), RGBColor(0xD6, 0x40, 0x00), RGBColor(0x55, 0x55, 0x55)
PLATFORM_ORDER = ["instagram", "facebook", "linkedin", "x", "youtube"]
NAMES = {"instagram": "Instagram", "facebook": "Facebook", "linkedin": "LinkedIn", "x": "X", "youtube": "YouTube"}
FONT = "Figtree"


def _bg(slide, color):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _text(slide, x, y, w, h, text, size=14, bold=False, color=INK, font=FONT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = p.add_run()
        run.text = line
        run.font.size, run.font.bold, run.font.name = Pt(size), bold, font
        run.font.color.rgb = color
    return box


def _picture(slide, path: Path, x, y, max_w, max_h):
    if path.suffix.lower() == ".mp4":
        _text(slide, x, y, max_w, 1, f"Video: {path.name}", 14, color=GREY)
        return
    with Image.open(path) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), Emu(int(Inches(w * scale))), Emu(int(Inches(h * scale))))


def short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def build(wk: Week, out: Path, history_root: Path | None = None) -> Path:
    report = check_week(wk, history_of(history_root or wk.folder.parent, wk.name))
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    posts = sorted(wk.posts, key=publish_time)

    s = prs.slides.add_slide(blank)
    _bg(s, INK)
    first, last = publish_time(posts[0]), publish_time(posts[-1])
    _text(s, 0.8, 2.2, 11.5, 1.2, "DTJ social media", 20, color=RGBColor(0xB9, 0xB9, 0xC0))
    _text(s, 0.8, 2.8, 11.5, 1.6, f"Posts for {first:%d %b} to {last:%d %b %Y}", 44, True, RGBColor(0xFF, 0xFF, 0xFF))
    passing = sum(1 for v in report.values() if not v)
    _text(s, 0.8, 4.3, 11.5, 1.5, f"{len(posts)} posts · {passing} pass every check · week {wk.name}\n"
          "Every number on these posts comes from DTJ's proof list.", 18, color=RGBColor(0xE6, 0xE6, 0xEA))

    s = prs.slides.add_slide(blank)
    _bg(s, PAPER)
    _text(s, 0.6, 0.35, 12, 0.8, "The calendar (India time)", 30, True)
    days = sorted({publish_time(p).date() for p in posts})
    days = [days[0] + timedelta(days=i) for i in range((days[-1] - days[0]).days + 1)]
    cols = [pl for pl in PLATFORM_ORDER if any(pl in p["platforms"] for p in posts)]
    table = s.shapes.add_table(len(days) + 1, len(cols) + 1, Inches(0.6), Inches(1.3), Inches(12.1),
                               Inches(0.55 * (len(days) + 1))).table
    table.cell(0, 0).text = "Day"
    for j, pl in enumerate(cols, 1):
        table.cell(0, j).text = NAMES[pl]
    for i, day in enumerate(days, 1):
        table.cell(i, 0).text = day.strftime("%a %d %b")
        for j, pl in enumerate(cols, 1):
            hits = [p for p in posts if publish_time(p).date() == day and pl in p["platforms"]]
            table.cell(i, j).text = "\n".join(f"{p['id'].split('-')[-1]} {publish_time(p):%H:%M} {p['theme']}" for p in hits) or "no post"
    for row in table.rows:
        for cell in row.cells:
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.name = Pt(12), FONT

    for p in posts:
        s = prs.slides.add_slide(blank)
        _bg(s, PAPER)
        if p["media"]:
            _picture(s, wk.media_path(p["media"][0]), 0.5, 0.5, 5.2, 6.5)
            if len(p["media"]) > 1:
                _text(s, 0.5, 7.0, 5.2, 0.4, f"+ {len(p['media']) - 1} more slides in this carousel", 11, color=GREY)
        x = 6.0
        _text(s, x, 0.35, 7, 0.6, f"{p['id'].split('-')[-1].upper()} · {publish_time(p):%a %d %b, %H:%M} IST · {p['theme']} · {p['format']}",
              14, True, BRAND)
        y = 0.9
        for pl in [pl for pl in PLATFORM_ORDER if pl in p["platforms"]]:
            spec = p["platforms"][pl]
            words = spec.get("caption") or spec.get("text") or f"{spec.get('title', '')}\n{spec.get('description', '')}"
            tags = " ".join(spec.get("hashtags", []))
            _text(s, x, y, 7, 0.3, NAMES[pl], 12, True)
            _text(s, x, y + 0.28, 7, 0.9, short(words.replace("{link}", "[audit link]"), 260) + (f"\n{tags}" if tags else ""), 10, color=GREY)
            y += 1.12
        problems = report[p["id"]]
        proof = ", ".join(p["proof_ids"]) or "no numbers"
        _text(s, x, 6.55, 7, 0.8, f"Proof: {proof}\nChecks: {'all pass' if not problems else '; '.join(problems)[:300]}",
              10, color=INK if not problems else BRAND)

    s = prs.slides.add_slide(blank)
    _bg(s, INK)
    _text(s, 0.8, 0.8, 11.5, 1, "What needs a yes", 34, True, RGBColor(0xFF, 0xFF, 0xFF))
    ok = [p["id"].split("-")[-1] for p in posts if not report[p["id"]]]
    bad = [p["id"].split("-")[-1] for p in posts if report[p["id"]]]
    body = (f"Ready to approve: {', '.join(ok) or 'none'}\n" + (f"Being fixed first: {', '.join(bad)}\n" if bad else "")
            + "\nSay yes with the post numbers (for example 'yes p1-p7'). Each post is then posted at its time.\n"
            "If Harsh can't be reached, a DTJ teammate may approve, by name.\n"
            f"Command: python -m smm approve --week {wk.name} --posts {ok[0] if ok else 'p1'}-{ok[-1] if ok else 'p7'} --by \"<name>\"")
    _text(s, 0.8, 2.0, 11.5, 4.5, body, 18, color=RGBColor(0xE6, 0xE6, 0xEA))
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    return out
