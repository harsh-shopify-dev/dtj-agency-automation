"""Before / after look at the header and footer BEFORE anything is written: opens the DRAFT theme's real page (read-only, a clean headless
Edge), screenshots it as it is, then paints the designed colours and words over it (CSS and text only, in the browser; the store is not
touched) and screenshots again. A stand-in: the real result is checked on the draft after the write (check_chrome_live.py).

    python .claude/skills/dtj-header-footer/scripts/preview_chrome.py --client .work/clients/<client> --store <store>.myshopify.com --theme <id>
        (the system Python with Playwright; reads <client>/chrome-run/ from run_chrome; writes <client>/chrome-preview/)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BOTTOM = """() => { const f = [...document.querySelectorAll('[id*="__footer"], [id*="__utilities"], footer')].pop();
  if (f) f.scrollIntoView({block: 'end'}); else window.scrollTo(0, document.body.scrollHeight); }"""
PHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"


def ids(group: dict, kind: str) -> list[str]:
    return [sid for sid in group.get("order", []) if group["sections"].get(sid, {}).get("type") == kind]


def paint_css(header: dict, footer: dict, c: dict) -> str:
    rules = []
    for sid in ids(header, "header-announcements"):
        sel = f'[id$="__{sid}"]'
        if header["sections"][sid].get("disabled"):
            rules.append(f"{sel}{{display:none !important}}")
            continue
        rules.append(f"{sel} .section-background,{sel} .section{{background:{c['announcement']} !important}}"
                     f"{sel},{sel} *{{color:{c['announcement_text']} !important;--color-foreground:{c['announcement_text']}}}")
    for sid in ids(header, "header"):
        sel = f'[id$="__{sid}"]'
        rules.append(f"{sel} header,{sel} .header,{sel} .header__row,{sel} .header__columns{{background:{c['header']} !important;color:{c['header_text']} !important}}"
                     f"{sel} header,{sel} .header{{border-bottom:1px solid {c['header_border']} !important}}"
                     f"{sel} .cart-bubble,{sel} .cart-bubble__background{{background:{c['bubble']} !important;color:{c['bubble_text']} !important}}")
    for sid in ids(footer, "footer") + ids(footer, "footer-utilities"):
        sel = f'[id$="__{sid}"]'
        rules.append(f"{sel},{sel} .section-background{{background:{c['footer']} !important}}"
                     f"{sel},{sel} *:not(input){{color:{c['footer_text']} !important;--color-foreground:{c['footer_text']}}}"
                     f"{sel} input{{background:{c['signup_input']} !important;color:{c['signup_input_text']} !important}}"
                     f"{sel} button{{background:{c['signup_button']} !important;color:{c['signup_button_text']} !important;border-color:{c['signup_button']} !important}}")
    return "".join(rules)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--path", default="/", help="the page to show (default: the home page)")
    a = ap.parse_args()
    run = Path(a.client) / "chrome-run"
    header = json.loads((run / "header" / "template.json").read_text(encoding="utf-8"))
    footer = json.loads((run / "footer" / "template.json").read_text(encoding="utf-8"))
    rep = json.loads((run / "chrome-report.json").read_text(encoding="utf-8"))
    css = paint_css(header, footer, rep["colours"])
    new_lines = [header["sections"][sid]["blocks"][b]["settings"]["text"] for sid in ids(header, "header-announcements")
                 if not header["sections"][sid].get("disabled") for b in header["sections"][sid]["block_order"]]
    swaps = {p: "" for p in rep["removed_placeholders"] if not p.startswith("http")}
    for k, v in rep["provenance"].items():
        if "/" in k or k.startswith("footer"):
            for p in rep["removed_placeholders"]:
                if "exclusive deals" in p.lower():
                    swaps[p] = v["text"]
    out = Path(a.client) / "chrome-preview"
    out.mkdir(parents=True, exist_ok=True)
    url = f"https://{a.store}{a.path}{'&' if '?' in a.path else '?'}preview_theme_id={a.theme}"
    js = """([css, lines, swaps]) => {
      const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); const hits = [];
      while (walker.nextNode()) { const n = walker.currentNode; const t = (n.nodeValue || '').trim(); if (t && t in swaps) hits.push(n); }
      let k = 0;
      for (const n of hits) { const t = n.nodeValue.trim(); n.nodeValue = /welcome to our store/i.test(t) ? (lines[k++ % Math.max(1, lines.length)] || '') : swaps[t]; }
      document.querySelectorAll('a[href="https://www.facebook.com"],a[href="https://www.instagram.com"],a[href="https://www.youtube.com"],a[href="https://www.tiktok.com"],a[href="https://www.twitter.com"]').forEach(a => a.closest('li') ? a.closest('li').remove() : a.remove());
      return hits.length; }"""
    with sync_playwright() as p:
        for view, w, h in (("phone", 390, 844), ("desktop", 1280, 900)):
            b = p.chromium.launch(channel="msedge", headless=True)
            try:
                ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 750, has_touch=w < 750, user_agent=PHONE_UA if w < 750 else None)
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3000)
                page.screenshot(path=str(out / f"{view}-before-top.png"))
                page.evaluate(BOTTOM)
                page.wait_for_timeout(1200)
                page.screenshot(path=str(out / f"{view}-before-bottom.png"))
                page.evaluate("window.scrollTo(0, 0)")
                swapped = page.evaluate(js, [css, new_lines, swaps])
                page.wait_for_timeout(600)
                page.screenshot(path=str(out / f"{view}-after-top.png"))
                page.evaluate(BOTTOM)
                page.wait_for_timeout(1200)
                page.screenshot(path=str(out / f"{view}-after-bottom.png"))
                print(f"{view}: {swapped} text(s) swapped; screenshots in {out}")
            finally:
                b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
