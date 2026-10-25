"""Study tool (private, never committed): the HEADER and FOOTER of strong D2C home pages (the brands of the 19 Oct home-page study), opened in a
clean headless Edge at 1280 and 390 px (no login, no consent clicks). Measures the announcement bar, the header and the footer: colours,
heights, logo position, menu size, icons, footer columns, newsletter, social and payment icons; saves top and bottom screenshots.
usage (system Python with Playwright): python study_capture.py [names...]; then python study_table.py"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parents[4] / ".work" / "chrome-reference"  # private: screenshots never go into the skill or git
SITES = [("boom-beauty", "https://boombeauty.com/"), ("jones-road", "https://www.jonesroadbeauty.com/"), ("minimalist", "https://beminimalist.co/"),
         ("mamaearth", "https://mamaearth.in/"), ("gfuel", "https://gfuel.com/"), ("whole-truth", "https://thewholetruthfoods.com/"),
         ("cooking-guild", "https://thecookingguild.com/"), ("blueland", "https://www.blueland.com/"), ("branch-basics", "https://branchbasics.com/"),
         ("grove", "https://www.grove.co/"), ("sullen", "https://www.sullenclothing.com/"), ("kittyspout", "https://www.kittyspout.com/"),
         ("grubbly-farms", "https://grubblyfarms.com/"), ("carnivore-snax", "https://www.carnivoresnax.com/"), ("glossier", "https://www.glossier.com/"),
         ("sugar", "https://in.sugarcosmetics.com/"), ("method", "https://methodhome.com/"), ("ag1", "https://drinkag1.com/"), ("ritual", "https://ritual.com/"),
         ("dr-squatch", "https://www.drsquatch.com/"), ("allbirds", "https://www.allbirds.com/"), ("boat", "https://www.boat-lifestyle.com/"),
         ("gymreapers", "https://gymreapers.com/"), ("proeffex", "https://www.proeffex.com/")]
PHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"

HIDE = r"""() => { let n = 0; document.querySelectorAll('body *').forEach(e => { const s = getComputedStyle(e); if (s.position !== 'fixed') return;
  const t = ((e.id || '') + ' ' + (e.className && e.className.toString ? e.className.toString() : '') + ' ' + (e.getAttribute('role') || '')).toLowerCase();
  if (/header|nav|menu|announcement/.test(t)) return;
  if (/popup|modal|klaviyo|privacy|cookie|consent|onetrust|gdpr|dialog|newsletter|chat|accessib|launcher|spin-?wheel|preview-bar/.test(t) && e.getBoundingClientRect().width > 40) { e.style.setProperty('display','none','important'); n++; } });
  return n; }"""

MEASURE = r"""() => {
  const W = innerWidth;
  const vis = e => { if (!e) return false; const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 2 && r.height > 2 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const bgOf = e => { for (let x = e; x; x = x.parentElement) { const c = getComputedStyle(x).backgroundColor; const m = /rgba?\(([^)]+)\)/.exec(c);
      if (m) { const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); if ((p.length > 3 ? p[3] : 1) > 0.5) return 'rgb(' + p.slice(0, 3).join(',') + ')'; } } return 'rgb(255,255,255)'; };
  const fg = e => getComputedStyle(e).color;
  const abs = r => ({ top: Math.round(r.top + scrollY), h: Math.round(r.height), w: Math.round(r.width), left: Math.round(r.left) });
  // the header: the <header> element, else the first wide element near the top that holds the logo / cart link
  let header = [...document.querySelectorAll('header, [class*="header" i], [id*="header" i]')].filter(vis).find(e => e.getBoundingClientRect().top < 200 && e.getBoundingClientRect().width > W * 0.8 && e.getBoundingClientRect().height < 260);
  const ann = [...document.querySelectorAll('[class*="announcement" i], [id*="announcement" i], [class*="topbar" i], [class*="top-bar" i], [class*="promo-bar" i], [class*="marquee" i]')]
     .filter(vis).find(e => e.getBoundingClientRect().top < 140 && e.getBoundingClientRect().height < 80 && e.getBoundingClientRect().width > W * 0.8);
  const logo = header ? [...header.querySelectorAll('a[href="/"], a[href$=".com/"], a[href$=".in/"], [class*="logo" i] img, [class*="logo" i] svg, [class*="logo" i]')].filter(vis)[0] : null;
  const lr = logo ? logo.getBoundingClientRect() : null;
  const links = header ? [...header.querySelectorAll('nav a, [class*="menu" i] a')].filter(vis).filter(a => (a.innerText || '').trim().length > 1 && a.getBoundingClientRect().top < 260) : [];
  const footer = [...document.querySelectorAll('footer, [class*="footer" i], [id*="footer" i]')].filter(vis).sort((a, b) => b.getBoundingClientRect().height - a.getBoundingClientRect().height)[0];
  const fr = footer ? footer.getBoundingClientRect() : null;
  const ftext = footer ? (footer.innerText || '') : '';
  const lists = footer ? [...footer.querySelectorAll('ul, nav')].filter(vis).filter(u => u.querySelectorAll('a').length >= 2) : [];
  const cols = footer ? new Set(lists.map(u => Math.round(u.getBoundingClientRect().left / 40))).size : 0;
  const social = footer ? footer.querySelectorAll('a[href*="instagram"], a[href*="facebook"], a[href*="youtube"], a[href*="tiktok"], a[href*="twitter"], a[href*="x.com"], a[href*="linkedin"], a[href*="pinterest"]').length : 0;
  return { width: W, page_height: Math.round(document.documentElement.scrollHeight),
    announcement: ann ? { ...abs(ann.getBoundingClientRect()), bg: bgOf(ann), color: fg(ann), text: (ann.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120) } : null,
    header: header ? { ...abs(header.getBoundingClientRect()), bg: bgOf(header), color: fg(header), sticky: ['sticky', 'fixed'].includes(getComputedStyle(header).position),
      logo_x: lr ? Math.round((lr.left + lr.width / 2) / W * 100) : null, logo_h: lr ? Math.round(lr.height) : null, menu_links: links.length,
      border: getComputedStyle(header).borderBottomWidth } : null,
    footer: footer ? { ...abs(fr), bg: bgOf(footer), color: fg(footer), columns: cols, links: footer.querySelectorAll('a').length,
      newsletter: !!footer.querySelector('input[type="email"], input[name*="email" i]'), social_links: social,
      payment: /visa|mastercard|upi|rupay|paypal|amex|american express/i.test((footer.innerHTML || '').slice(0, 200000)),
      text_sample: ftext.replace(/\s+/g, ' ').trim().slice(0, 300) } : null };
}"""


def shoot(p, url, view, out):
    w, h, mobile = (390, 844, True) if view == "phone" else (1280, 900, False)
    b = p.chromium.launch(channel="msedge", headless=True)
    try:
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile, user_agent=PHONE_UA if mobile else None, locale="en-US")
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        total = page.evaluate("document.documentElement.scrollHeight")
        y = 0
        while y < min(total, 16000):
            page.evaluate(f"window.scrollTo(0,{y})")
            page.wait_for_timeout(200)
            y += h * 0.9
            total = page.evaluate("document.documentElement.scrollHeight")
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(1200)
        page.evaluate(HIDE)
        data = page.evaluate(MEASURE)
        page.screenshot(path=str(out / f"{view}-top.png"))
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_timeout(1500)
        page.evaluate(HIDE)
        page.screenshot(path=str(out / f"{view}-bottom.png"))
        (out / f"{view}.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
        return data
    finally:
        b.close()


def main():
    only = set(sys.argv[1:])
    log = {}
    with sync_playwright() as p:
        for name, url in SITES:
            if only and name not in only:
                continue
            d = HERE / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "source.txt").write_text(f"{url}\ncaptured: {time.strftime('%Y-%m-%d')}\n", encoding="utf-8")
            for view in ("desktop", "phone"):
                try:
                    m = shoot(p, url, view, d)
                    log[f"{name}/{view}"] = "ok, header " + ("yes" if m["header"] else "no") + ", footer " + ("yes" if m["footer"] else "no")
                except Exception as e:  # noqa: BLE001 - one site failing must not stop the others
                    log[f"{name}/{view}"] = f"FAILED: {str(e)[:100]}"
                print(name, view, log[f"{name}/{view}"], flush=True)
    (HERE / "capture-log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


main()
