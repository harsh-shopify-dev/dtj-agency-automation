"""Read-only QA gate for DTJ landing-page variants. Submits nothing, changes nothing.

Usage (dev server running, see references/codebase-map.md):
  python check_pages.py --pages ads-no-orders,sales-stuck,website-no-sales [--shots] [--out DIR]

For every page, at phone (390x844, touch) and desktop (1440x900):
  HTTP 200, no console/page errors, robots noindex, no footer, no links that leave the page,
  every button target exists, no horizontal overflow (also swept at 10 widths), no text under
  12px on phones (decorative mock-up text excepted), no broken images, no empty band taller than
  EMPTY_MAX (stacked section paddings; phone 72px, desktop 104px), one heading style for
  every section h2, the review count badge shown once, at most MAX_WORDS words outside the
  reviews/form/FAQ, axe-core WCAG 2.2 AA clean, and no
  scroll trap (a wheel/swipe over any scrollable box in the first two phone screens must move
  the page). Exits 1 if anything fails. --shots also saves full-page screenshots and a
  4-column phone sheet per page for the visual review gate.
"""
import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DTJ = Path(r"D:/CODE CONTAINERR/WEB DEV/DTJ")
AXE = DTJ / "node_modules/axe-core/axe.min.js"
WIDTHS = (320, 360, 375, 390, 412, 430, 768, 1024, 1280, 1440)
# Text inside the before/after phone mock-ups ("9:41", "proeffex.com") is decorative chrome.
DECORATIVE_TINY = {"9:41", "proeffex.com"}
# Word budget outside reviews, form and FAQ. The simple pages sit at ~140-160 (10 Oct 2026); the main page has ~570.
MAX_WORDS = 200
# Tallest allowed stretch with nothing in it (text, image, video, control or a card edge). One section gap is 48px on
# phones and 64px on desktop (components/simple/styles.ts); stacked paddings made 104-184px gaps on 12 Oct 2026.
EMPTY_MAX = {"phone": 72, "desktop": 104}

FACTS = r"""() => {
  const vis = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const hidden = (e) => !!e.closest('[aria-hidden="true"]');
  const txt = (e) => (e.innerText || '').split(String.fromCharCode(10)).join(' ').trim();
  const leaf = [...document.querySelectorAll('body *')].filter(e => vis(e) && !hidden(e)
    && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 2));
  const h2 = [...document.querySelectorAll('main h2')].filter(h => vis(h) && !h.closest('section[aria-labelledby="logos-heading"]'))
    .map(h => { const s = getComputedStyle(h); return {text: txt(h).slice(0, 50), style: Math.round(parseFloat(s.fontSize)) + 'px/' + s.fontWeight + '/' + s.textAlign}; });
  const targets = [...document.querySelectorAll('a[href^="#"]')].map(a => a.getAttribute('href')).filter(h => h.length > 1);
  return {
    robots: document.querySelector('meta[name=robots]')?.content || null,
    overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    footers: document.querySelectorAll('footer').length,
    exits: [...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')).filter(h => !h.startsWith('#')),
    missingTargets: [...new Set(targets)].filter(h => !document.getElementById(h.slice(1))),
    tiny: leaf.filter(e => parseFloat(getComputedStyle(e).fontSize) < 12).map(e => txt(e).slice(0, 30)),
    broken: [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src.split('/').pop()),
    h2,
    reviewBadges: (document.body.innerText.match(/208\+/g) || []).length,
    // Words a visitor reads outside the reviews, the form and the FAQ (the founders scan, they don't read).
    words: (() => { const m = document.querySelector('main').cloneNode(true);
      m.querySelectorAll('section[aria-labelledby="reviews-heading"], #audit, section[aria-labelledby="faq-heading"], [aria-hidden="true"], .sr-only, [aria-label="Ad creative examples"]').forEach(e => e.remove());
      return m.textContent.split(/\s+/).filter(w => /[A-Za-z0-9₹]/.test(w)).length; })(),
    height: document.documentElement.scrollHeight,
  };
}"""

AXE_RUN = """async () => { const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}});
  return r.violations.map(v => ({id: v.id, impact: v.impact, count: v.nodes.length,
    where: v.nodes.slice(0, 3).map(n => n.target.join(' ').slice(0, 70))})); }"""

# Scrollable boxes (overflow auto/scroll with real overflow) in the first two phone screens.
SCROLLERS = r"""() => [...document.querySelectorAll('main *')].filter(e => {
  const s = getComputedStyle(e); const r = e.getBoundingClientRect();
  return /(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 4 && r.height > 80
    && r.top + scrollY < innerHeight * 2 && s.pointerEvents !== 'none';
}).map(e => { const r = e.getBoundingClientRect(); return {x: r.x + r.width / 2, y: r.y + r.height / 2 + scrollY, label: e.getAttribute('aria-label') || e.className.toString().slice(0, 40)}; })"""


# Vertical stretches of the page with no visible content. A coloured or bordered box counts by its top and
# bottom edges only (its inside may be empty padding); text, images, video, svg and form controls count whole.
EMPTY_BANDS = r"""(min) => {
  const paper = getComputedStyle(document.body).backgroundColor;
  const vis = (e) => { const s = getComputedStyle(e); const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity) > 0.05; };
  const boxes = [];
  for (const e of document.querySelectorAll('main *')) {
    if (!vis(e) || e.closest('.sr-only')) continue;
    const s = getComputedStyle(e);
    if (s.position === 'fixed') continue;
    const hasText = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    const media = ['IMG','VIDEO','svg','INPUT','SELECT','TEXTAREA','BUTTON','CANVAS'].includes(e.tagName);
    const bg = !['rgba(0, 0, 0, 0)', 'transparent', paper].includes(s.backgroundColor);
    const edge = parseFloat(s.borderTopWidth) > 0 || parseFloat(s.borderBottomWidth) > 0 || s.boxShadow !== 'none';
    if (!(hasText || media || bg || edge)) continue;
    const r = e.getBoundingClientRect(), t = r.top + scrollY, b = r.bottom + scrollY;
    if (bg || edge) { boxes.push([t, t + 1, e]); boxes.push([b - 1, b, e]); if (!(hasText || media)) continue; }
    boxes.push([t, b, e]);
  }
  boxes.sort((a, b) => a[0] - b[0]);
  const where = (e) => { const sec = e.closest('section'); return sec ? (sec.getAttribute('aria-labelledby') || sec.id || '?') : '?'; };
  const out = []; let end = null, last = null;
  for (const [t, b, e] of boxes) {
    if (end !== null && t - end > min) out.push(`${Math.round(t - end)}px at y=${Math.round(end)} (${where(last)} -> ${where(e)})`);
    if (end === null || b > end) { end = b; last = e; }
  }
  return out;
}"""


def settle(pg):
    h, vh, pos = pg.evaluate("document.documentElement.scrollHeight"), pg.evaluate("innerHeight"), 0
    while pos < h:
        pg.mouse.wheel(0, vh * 0.8)
        pg.wait_for_timeout(120)
        pos += int(vh * 0.8)
        h = pg.evaluate("document.documentElement.scrollHeight")
    pg.wait_for_timeout(800)
    pg.evaluate("scrollTo(0, 0)")
    pg.wait_for_timeout(400)


def sheet(full_png: Path, out_png: Path):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    m = Image.open(full_png).convert("RGB")
    w, h = m.size
    step = (h + 3) // 4
    s = Image.new("RGB", (4 * w + 36, step), "white")
    for i in range(4):
        s.paste(m.crop((0, i * step, w, min(h, (i + 1) * step))), (i * (w + 12), 0))
    s.resize((int(s.width * 0.62), int(s.height * 0.62))).save(out_png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:3100")
    ap.add_argument("--pages", required=True, help="comma-separated slugs, e.g. ads-no-orders,v2")
    ap.add_argument("--out", default=str(Path.cwd() / "qa-out"))
    ap.add_argument("--axe", default=str(AXE))
    ap.add_argument("--shots", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    failures = []
    report = {}

    with sync_playwright() as p:
        b = p.chromium.launch()
        for slug in [s.strip().strip("/") for s in args.pages.split(",") if s.strip()]:
            url = f"{args.base}/{slug}"
            report[slug] = {}
            for name, w, h, mobile in (("phone", 390, 844, True), ("desktop", 1440, 900, False)):
                ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile, reduced_motion="reduce")
                pg = ctx.new_page()
                errors = []
                pg.on("console", lambda m: errors.append(m.text[:200]) if m.type == "error" else None)
                pg.on("pageerror", lambda e: errors.append("PAGEERROR " + str(e)[:200]))
                resp = pg.goto(url, wait_until="networkidle", timeout=180000)
                pg.wait_for_timeout(1200)
                settle(pg)
                f = pg.evaluate(FACTS)
                empty = pg.evaluate(EMPTY_BANDS, EMPTY_MAX[name])
                pg.add_script_tag(path=args.axe)
                axe = pg.evaluate(AXE_RUN)
                if args.shots and f["height"] < 16000:  # Chromium can't render taller full-page shots
                    full = out / f"{slug}-{name}-full.png"
                    pg.screenshot(path=str(full), full_page=True)
                    if mobile:
                        sheet(full, out / f"{slug}-phone-sheet.png")
                ctx.close()

                tiny = [t for t in f["tiny"] if t not in DECORATIVE_TINY] if mobile else []
                styles = sorted({x["style"] for x in f["h2"]})
                checks = {
                    "http 200": resp.status == 200,
                    "no console errors": not errors,
                    "noindex": bool(f["robots"]) and "noindex" in f["robots"],
                    "no footer": f["footers"] == 0,
                    "no exit links": not f["exits"],
                    "button targets exist": not f["missingTargets"],
                    "no overflow": not f["overflow"],
                    "no text under 12px (phone)": not tiny,
                    "no broken images": not f["broken"],
                    "no empty bands": not empty,
                    "one heading style": len(styles) <= 1,
                    "review badge once": f["reviewBadges"] <= 1,
                    "axe clean": not axe,
                    f"few words (<= {MAX_WORDS})": f["words"] <= MAX_WORDS,
                }
                report[slug][name] = {"checks": checks, "errors": errors, "exits": f["exits"], "missingTargets": f["missingTargets"],
                                      "tiny": tiny[:8], "empty": empty, "h2Styles": styles, "h2": f["h2"], "axe": axe, "height": f["height"], "words": f["words"]}
                for k, ok in checks.items():
                    if not ok:
                        failures.append(f"/{slug} {name}: {k}")

            # Scroll trap: on a touch phone, wheel over each scrollable box near the top must move the page.
            ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            pg = ctx.new_page()
            pg.goto(url, wait_until="networkidle", timeout=180000)
            pg.wait_for_timeout(1200)
            traps = []
            for s in pg.evaluate(SCROLLERS):
                pg.evaluate(f"scrollTo(0, {max(0, s['y'] - 422)})")
                pg.wait_for_timeout(300)
                y0 = pg.evaluate("scrollY")
                pg.mouse.move(s["x"], 422)  # over the box itself, not the page centre
                for _ in range(3):
                    pg.mouse.wheel(0, 300)
                    pg.wait_for_timeout(120)
                pg.wait_for_timeout(400)
                if pg.evaluate("scrollY") <= y0:
                    traps.append(s["label"])
            ctx.close()
            report[slug]["scrollTraps"] = traps
            if traps:
                failures.append(f"/{slug}: scroll trap over {traps}")

            # Horizontal overflow at every common width.
            wide = []
            for w in WIDTHS:
                c = b.new_context(viewport={"width": w, "height": 900}, is_mobile=w < 768, has_touch=w < 768)
                pg = c.new_page()
                pg.goto(url, wait_until="networkidle", timeout=180000)
                pg.wait_for_timeout(700)
                sw, cw = pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
                if sw > cw:
                    wide.append(w)
                c.close()
            report[slug]["overflowAt"] = wide
            if wide:
                failures.append(f"/{slug}: overflow at {wide}")
        b.close()

    (out / "qa-report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    for slug, r in report.items():
        print(f"===== /{slug}")
        for name in ("phone", "desktop"):
            bad = [k for k, ok in r[name]["checks"].items() if not ok]
            print(f"  {name}: {'PASS' if not bad else 'FAIL ' + ', '.join(bad)} | words {r[name]['words']} | height {r[name]['height']} | h2 {r[name]['h2Styles']}")
            for a in r[name]["axe"]:
                print(f"     axe {a['impact']} {a['id']} x{a['count']} {a['where']}")
            for e in r[name]["empty"]:
                print(f"     empty band {e}")
            if r[name]["errors"]:
                print("     errors:", r[name]["errors"][:3])
            if r[name]["exits"]:
                print("     exit links:", r[name]["exits"])
            if r[name]["tiny"]:
                print("     tiny text:", r[name]["tiny"])
        print(f"  scroll traps: {r['scrollTraps'] or 'none'} | overflow at: {r['overflowAt'] or 'none'}")
    print("\nRESULT:", "PASS" if not failures else "FAIL")
    for f in failures:
        print("  -", f)
    print(f"Report: {out / 'qa-report.json'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
