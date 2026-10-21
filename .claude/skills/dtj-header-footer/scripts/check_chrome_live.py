"""The header and footer as shoppers see them, on the DRAFT theme after the write (read-only: a clean headless Edge opens the preview pages).

    python .claude/skills/dtj-header-footer/scripts/check_chrome_live.py --client .work/clients/<client> --store <store>.myshopify.com --theme <id>
        [--paths / /collections/all]       (the system Python with Playwright; reads <client>/chrome-run/; writes <client>/chrome-live/)

  K1 the announcement bar shows the designed lines on the designed colour, or is gone when switched off
  K2 the header is the designed colour, with readable words
  K3 the footer and its bottom strip are the designed colour, every word readable (4.5:1 or more)
  K4 no theme placeholder left (Welcome to our store, "exclusive deals"), no link to a bare social site, no "Powered by Shopify"
  K5 no sideways scroll at 390 and 1280 px, no Liquid error
Exit 0 = pass, 2 = findings.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
PLACEHOLDERS = ("welcome to our store", "get exclusive deals and early access", "powered by shopify")
READ = r"""(ids) => {
  const solid = (e, stop, fallback) => { for (let x = e; x && x !== stop; x = x.parentElement) { const c = getComputedStyle(x).backgroundColor; const m = /rgba?\(([^)]+)\)/.exec(c);
      if (m) { const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); if ((p.length > 3 ? p[3] : 1) > 0.5) return p.slice(0, 3); } } return fallback || [255, 255, 255]; };
  const rgb = c => { const m = /rgba?\(([^)]+)\)/.exec(c); return m ? m[1].split(/[\s,\/]+/).filter(Boolean).slice(0, 3).map(Number) : [0, 0, 0]; };
  const vis = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 1 && r.height > 1 && s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0'; };
  const part = sid => { const s = document.querySelector('[id$="__' + sid + '"]'); if (!s || !vis(s)) return null;
    const layer = s.querySelector('.section-background');  // Horizon paints a section's colour on its own layer BEHIND the words
    const inner = (layer && vis(layer) ? layer : null) || [...s.querySelectorAll('*')].find(e => vis(e) && e.getBoundingClientRect().height > 20) || s;
    const own = solid(inner, null, null);
    const texts = [...s.querySelectorAll('a, p, span, h2, h3, li, button, div')].filter(e => vis(e) && [...e.childNodes].some(n => n.nodeType === 3 && n.nodeValue.trim()))
      .slice(0, 60).map(e => ({ text: [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.nodeValue).join(' ').trim().slice(0, 80), color: rgb(getComputedStyle(e).color), bg: solid(e, s.parentElement, own) }));
    return { h: Math.round(s.getBoundingClientRect().height), bg: own, texts, links: [...s.querySelectorAll('a[href]')].map(a => a.getAttribute('href')) }; };
  const out = {}; for (const [k, sid] of Object.entries(ids)) out[k] = part(sid);
  out.page_width = document.documentElement.scrollWidth; out.width = innerWidth;
  out.body_text = (document.body.innerText || '').slice(0, 200000).toLowerCase();
  return out; }"""


def hex_of(rgb: list[int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb[:3])


def lum(rgb) -> float:
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def close(a: list[int], hexcode: str, tol: int = 6) -> bool:
    h = hexcode.lstrip("#")
    want = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return all(abs(x - y) <= tol for x, y in zip(a, want))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--paths", nargs="+", default=["/", "/collections/all"])
    a = ap.parse_args()
    run = Path(a.client) / "chrome-run"
    header = json.loads((run / "header" / "template.json").read_text(encoding="utf-8"))
    footer = json.loads((run / "footer" / "template.json").read_text(encoding="utf-8"))
    rep = json.loads((run / "chrome-report.json").read_text(encoding="utf-8"))
    col = rep["colours"]

    def first(group, kind):
        return next((sid for sid in group["order"] if group["sections"][sid].get("type") == kind), None)

    ids = {"announcement": first(header, "header-announcements"), "header": first(header, "header"), "footer": first(footer, "footer"),
           "utilities": first(footer, "footer-utilities")}
    ann = header["sections"][ids["announcement"]] if ids["announcement"] else None
    lines = [] if not ann or ann.get("disabled") else [ann["blocks"][b]["settings"]["text"] for b in ann["block_order"]]
    findings, seen = [], {}
    out = Path(a.client) / "chrome-live"
    out.mkdir(parents=True, exist_ok=True)

    def add(check, where, msg):
        findings.append({"check": check, "where": where, "message": msg})

    with sync_playwright() as p:
        for path in a.paths:
            for view, w, h in (("phone", 390, 844), ("desktop", 1280, 900)):
                where = f"{path} {view}"
                b = p.chromium.launch(channel="msedge", headless=True)
                try:
                    ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 750, has_touch=w < 750, user_agent=PHONE_UA if w < 750 else None)
                    page = ctx.new_page()
                    page.goto(f"https://{a.store}{path}{'&' if '?' in path else '?'}preview_theme_id={a.theme}", wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(3000)
                    m = page.evaluate(READ, ids)
                    slug = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-") or "home"
                    page.screenshot(path=str(out / f"{slug}-{view}-top.png"))
                    page.evaluate("""() => { const f = [...document.querySelectorAll('[id*="__footer"], [id*="__utilities"], footer')].pop();
                                     if (f) f.scrollIntoView({block: 'end'}); }""")
                    page.wait_for_timeout(1000)
                    page.screenshot(path=str(out / f"{slug}-{view}-bottom.png"))
                finally:
                    b.close()
                seen[where] = {k: ({"h": v["h"], "bg": hex_of(v["bg"])} if isinstance(v, dict) else v) for k, v in m.items() if k not in ("body_text",)}
                # K1
                if lines:
                    if not m["announcement"]:
                        add("K1", where, "the announcement bar is not shown")
                    else:
                        if not close(m["announcement"]["bg"], col["announcement"]):
                            add("K1", where, f"announcement bar {hex_of(m['announcement']['bg'])}, designed {col['announcement']}")
                        shown = " ".join(t["text"] for t in m["announcement"]["texts"])
                        if not any(ln[:20] in shown for ln in lines):
                            add("K1", where, f"none of the designed lines is shown: {shown[:120]!r}")
                elif m["announcement"]:
                    add("K1", where, "the announcement bar was switched off but still shows")
                # K2, K3: colours and readable words
                for key, want in (("header", col["header"]), ("footer", col["footer"]), ("utilities", col["footer"])):
                    part = m.get(key)
                    if not part:
                        add("K2" if key == "header" else "K3", where, f"the {key} is not shown")
                        continue
                    if not close(part["bg"], want):
                        add("K2" if key == "header" else "K3", where, f"{key} {hex_of(part['bg'])}, designed {want}")
                for key in ("announcement", "header", "footer", "utilities"):
                    for t in (m.get(key) or {}).get("texts", []):
                        r = ratio(t["color"], t["bg"])
                        if t["text"] and r < 4.5:
                            add("K3" if key in ("footer", "utilities") else "K2", where, f"{key}: {t['text'][:40]!r} reads at {r:.1f}:1")
                            break
                # K4
                for ph in PLACEHOLDERS:
                    if ph in m["body_text"]:
                        add("K4", where, f"theme placeholder on the page: {ph!r}")
                for key in ("footer", "utilities"):
                    for href in (m.get(key) or {}).get("links", []):
                        if re.match(r"^https?://(www\.)?(facebook|instagram|youtube|tiktok|twitter|x)\.com/?$", href or "", re.I):
                            add("K4", where, f"a link to a bare social site: {href}")
                # K5
                if m["page_width"] > w + 1:
                    add("K5", where, f"the page is {m['page_width']} px wide on a {w} px screen")
                if "liquid error" in m["body_text"]:
                    add("K5", where, "a Liquid error on the page")
    result = {"pass": not findings, "findings": findings, "measured": seen}
    (out / "live-check.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    for f in findings:
        print(f"  {f['check']} {f['where']}: {f['message']}")
    print("header and footer live check: " + ("PASS" if not findings else f"{len(findings)} finding(s)"))
    return 0 if not findings else 2


if __name__ == "__main__":
    sys.exit(main())
