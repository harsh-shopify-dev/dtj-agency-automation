"""Study tool (private, never committed: .work/ is git-ignored). Opens PUBLIC collection pages in a clean headless Edge (no login, no
consent clicks), scrolls once so lazy pictures load, saves a full-page desktop (1280) and phone (390) screenshot and measures what a
collection page is made of: how far down the first product starts, columns, gaps, the card's parts (rating, swatches, button, badge),
the header (title, description, banner) and the sort / filter controls.
usage (system Python with Playwright): python study_capture.py   (all)   |   python study_capture.py minimalist proeffex   (only these)"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parents[4] / ".work" / "collection-page-reference"  # private: screenshots never go into the skill or git
PAGES = [  # (name, url, category, why it is here)
    ("proeffex", "https://www.proeffex.com/collections/all", "beauty", "the block's own brand (visual reference)"),
    ("minimalist", "https://beminimalist.co/collections/skin", "beauty", "Indian D2C skincare, strong CRO"),
    ("plum", "https://plumgoodness.com/collections/skin-care", "beauty", "Indian D2C beauty"),
    ("sugar", "https://in.sugarcosmetics.com/collections/lips", "beauty", "Indian D2C makeup, shades"),
    ("jones-road", "https://www.jonesroadbeauty.com/collections/shop-all", "beauty", "CRO agency client (Convertibles)"),
    ("kylie", "https://kyliecosmetics.com/collections/all", "beauty", "global beauty, shades"),
    ("boat", "https://www.boat-lifestyle.com/collections/true-wireless-earbuds", "electronics", "Indian D2C, big catalogue"),
    ("whole-truth", "https://thewholetruthfoods.com/collections/all", "food", "Indian D2C food"),
    ("bombay-shaving", "https://www.bombayshavingcompany.com/collections/all", "grooming", "Indian D2C grooming"),
    ("blueland", "https://www.blueland.com/collections/all", "home", "home care, clean design"),
    ("gymreapers", "https://gymreapers.com/collections/all", "fitness", "CRO agency client (Convertibles)"),
    ("kittyspout", "https://www.kittyspout.com/collections/all", "pets", "CRO agency client (ConversionWise)"),
]
PHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

HIDE = r"""() => { // study only: hide pop-ups and cookie panels so the page itself is shown (nothing is clicked or accepted)
  let n = 0;
  document.querySelectorAll('body *').forEach(e => { const s = getComputedStyle(e); if (s.position !== 'fixed') return; const r = e.getBoundingClientRect();
    const txt = ((e.id || '') + ' ' + (e.className && e.className.toString ? e.className.toString() : '') + ' ' + (e.getAttribute('role') || '')).toLowerCase();
    if (/header|nav|menu|announcement/.test(txt)) return;
    if (/popup|modal|klaviyo|privacy|cookie|consent|onetrust|gdpr|dialog|newsletter|chat|accessib|launcher|spin-?wheel|preview-bar|wiz/.test(txt) && r.width > 40) { e.style.setProperty('display', 'none', 'important'); n++; } });
  return n; }"""

MEASURE = r"""() => {
  const W = innerWidth;
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 2 && r.height > 2 && s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity || '1') > 0.05; };
  const abs = r => ({ top: Math.round(r.top + scrollY), left: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height) });
  // product cards: the smallest element around a product link that holds a product picture and a price-like text
  const links = [...document.querySelectorAll('a[href*="/products/"]')].filter(a => vis(a) && a.querySelector('img'));
  const cards = [];
  const seen = new Set();
  links.forEach(a => { let c = a; for (let i = 0; i < 8 && c.parentElement; i++) { const t = c.innerText || ''; if (/(₹|Rs\.?|\$|€|£)\s?\d/.test(t) && c.getBoundingClientRect().width < W * 0.6) break; c = c.parentElement; }
    const r = c.getBoundingClientRect(); if (r.width < 80 || r.width > W * 0.6 || seen.has(c)) return; seen.add(c); cards.push(c); });
  const uniq = cards.filter(c => !cards.some(o => o !== c && o.contains(c)));
  uniq.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top || a.getBoundingClientRect().left - b.getBoundingClientRect().left);
  const first = uniq[0];
  const fr = first ? first.getBoundingClientRect() : null;
  const row = first ? uniq.filter(c => Math.abs(c.getBoundingClientRect().top - fr.top) < 12) : [];
  row.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
  const gap = row.length > 1 ? Math.round(row[1].getBoundingClientRect().left - row[0].getBoundingClientRect().right) : null;
  const img = first ? first.querySelector('img') : null;
  const anatomy = c => { if (!c) return null; const t = (c.innerText || '').replace(/\s+/g, ' ');
    const cls = [...c.querySelectorAll('*')].map(e => (e.className && e.className.toString ? e.className.toString() : '') + ' ' + (e.getAttribute('aria-label') || '')).join(' ').toLowerCase();
    const btn = [...c.querySelectorAll('button, a, input[type=submit]')].find(b => vis(b) && /add|cart|buy|choose|select|options/i.test((b.innerText || b.value || b.getAttribute('aria-label') || '')));
    const bs = btn ? getComputedStyle(btn) : null;
    return { text: t.slice(0, 160), rating: /star|rating|review/.test(cls) || /\d\.\d\s*(★|\||\(|stars?)|\(\d+\)|reviews?/i.test(t),
      swatches: /swatch|color-option|shade/.test(cls), button: btn ? (btn.innerText || btn.value || btn.getAttribute('aria-label') || '').trim().slice(0, 30) : '',
      button_h: btn ? Math.round(btn.getBoundingClientRect().height) : null, button_bg: bs ? bs.backgroundColor : null, button_radius: bs ? bs.borderRadius : null,
      badge: /badge|tag|label|sticker/.test(cls) && /(sale|off|new|best|bestseller|save)/i.test(t), sale: /(\d+%\s*off|save)/i.test(t),
      img_ratio: img ? +(img.getBoundingClientRect().height / Math.max(1, img.getBoundingClientRect().width)).toFixed(2) : null,
      frame: (() => { const s = getComputedStyle(c); return s.borderTopWidth !== '0px' || s.boxShadow !== 'none' || (s.backgroundColor !== 'rgba(0, 0, 0, 0)' && s.backgroundColor !== 'rgb(255, 255, 255)'); })() }; };
  const h1 = [...document.querySelectorAll('h1')].find(vis);
  const above = [...document.querySelectorAll('body *')].filter(e => vis(e) && fr && e.getBoundingClientRect().bottom <= fr.top + 2 && e.getBoundingClientRect().top + scrollY > 60);
  const controls = [...document.querySelectorAll('button, select, summary, a, label, span, div')].filter(e => vis(e) && e.children.length < 4 && fr && e.getBoundingClientRect().top < fr.top + 40 && e.getBoundingClientRect().top + scrollY > 60)
    .map(e => (e.innerText || e.getAttribute('aria-label') || '').trim()).filter(t => /^(filter|filters|sort|sort by|featured|best selling|price|availability|refine|category|skin type)/i.test(t)).slice(0, 8);
  const banner = above.filter(e => /^(IMG|VIDEO|PICTURE)$/.test(e.tagName) && e.getBoundingClientRect().width > W * 0.6).map(e => abs(e.getBoundingClientRect())).slice(0, 1);
  const chips = above.filter(e => e.tagName === 'A' && /\/collections\//.test(e.getAttribute('href') || '') && e.getBoundingClientRect().height < 140 && e.getBoundingClientRect().top > (h1 ? h1.getBoundingClientRect().top - 400 : 0)).length;
  const countText = ((document.body.innerText || '').match(/\b\d+\s+(products|items|results)\b/i) || [''])[0];
  const desc = h1 ? (() => { let n = h1.parentElement; const t = n ? (n.innerText || '').replace(h1.innerText, '').trim() : ''; return t.slice(0, 200); })() : '';
  return { width: W, page_height: Math.round(document.documentElement.scrollHeight), cards: uniq.length,
    first_card: fr ? abs(fr) : null, first_image_top: img ? Math.round(img.getBoundingClientRect().top + scrollY) : null, columns: row.length, gap,
    h1: h1 ? { text: h1.innerText.trim().slice(0, 80), px: Math.round(parseFloat(getComputedStyle(h1).fontSize)), top: Math.round(h1.getBoundingClientRect().top + scrollY), align: getComputedStyle(h1).textAlign } : null,
    description: desc, banner, chips_above: chips, controls, count_text: countText,
    card: anatomy(first), card2: anatomy(uniq[1]), font: getComputedStyle(document.body).fontFamily.slice(0, 60) };
}"""


def shoot(p, url, view, out_dir):
    w, h, mobile = (390, 844, True) if view == "phone" else (1280, 900, False)
    b = p.chromium.launch(channel="msedge", headless=True)
    try:
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile, device_scale_factor=1,
                            user_agent=PHONE_UA if mobile else None, locale="en-US")
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        total = page.evaluate("document.documentElement.scrollHeight")
        y = 0
        while y < min(total, 9000):  # one slow scroll so lazy pictures load
            page.evaluate(f"window.scrollTo(0,{y})")
            page.wait_for_timeout(300)
            y += h * 0.8
            total = page.evaluate("document.documentElement.scrollHeight")
        page.evaluate("window.scrollTo(0,0)")
        page.wait_for_timeout(1500)
        page.evaluate(HIDE)
        page.wait_for_timeout(400)
        data = page.evaluate(MEASURE)
        data["final_url"] = page.url
        data["title"] = page.title()
        page.screenshot(path=str(out_dir / f"{view}-top.png"), full_page=False)
        page.screenshot(path=str(out_dir / f"{view}.png"), full_page=True, timeout=60000)
        (out_dir / f"{view}-metrics.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
        return data
    finally:
        b.close()


def main():
    only = set(sys.argv[1:])
    log = {}
    with sync_playwright() as p:
        for name, url, cat, why in PAGES:
            if only and name not in only:
                continue
            d = HERE / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "source.txt").write_text(f"{url}\ncategory: {cat}\nwhy: {why}\ncaptured: {time.strftime('%Y-%m-%d')}\n", encoding="utf-8")
            for view in ("desktop", "phone"):
                try:
                    m = shoot(p, url, view, d)
                    log[f"{name}/{view}"] = f"ok, {m['cards']} cards, {m['columns']} cols, first image at {m['first_image_top']}px"
                except Exception as e:  # noqa: BLE001 - one site failing must not stop the others
                    log[f"{name}/{view}"] = f"FAILED: {str(e)[:120]}"
                print(name, view, log[f"{name}/{view}"], flush=True)
    (HERE / "capture-log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


main()
