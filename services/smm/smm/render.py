"""DTJ post pictures: HTML templates in DTJ's own style, turned into JPEGs by a real browser (Playwright).

The AI never draws words or numbers. A template places the text, the real dashboard pictures and the logo; an AI-made picture
(ChatGPT on the VPS) can only be a background (`background`). Every word a template puts on the picture is returned, so it goes
into the post's overlay_text and through the gate.

Templates (size 1080x1350, the 4:5 shape every platform takes):
    result        a client's real Shopify sales chart with its headline figure          fields: proof_id, kicker?, line?
    pain          one founder pain in big words                                          fields: headline, sub?, background?
    before_after  the Pro Effex product page before and after                           fields: headline, line
    slide         one carousel slide                                                     fields: number?, headline, body?, dark?
    cta           the closing slide: the free growth audit                              fields: headline?, link_text?

Text marked *like this* is set in DTJ's orange serif accent.

Run:  python -m smm.render <spec.json> <out folder>     spec: [{"file": "p1.jpg", "template": "result", "fields": {...}}, ...]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

from .gate import load_proof

ASSETS = Path(__file__).resolve().parents[1] / "assets"
W, H = 1080, 1350
INK, PAPER, BRAND, BRAND_DARK, TEXT2 = "#111111", "#f7f5f2", "#ff5500", "#d64000", "#555555"

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&family=Instrument+Serif:ital@1&display=block');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; }}
body {{ font-family: Figtree, Arial, sans-serif; color: #151515; background: {PAPER}; -webkit-font-smoothing: antialiased; }}
.frame {{ position: relative; width: {W}px; height: {H}px; padding: 72px 72px 64px; display: flex; flex-direction: column; }}
.dark {{ background: {INK}; color: #fff; }}
.accent {{ font-family: 'Instrument Serif', Georgia, serif; font-style: italic; font-weight: 400; color: {BRAND_DARK}; letter-spacing: -0.01em; }}
.dark .accent {{ color: {BRAND}; }}
.kicker {{ font-size: 26px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: {TEXT2}; }}
.dark .kicker {{ color: #b9b9c0; }}
h1 {{ font-weight: 700; letter-spacing: -0.035em; line-height: 1.04; }}
.foot {{ margin-top: auto; display: flex; align-items: center; justify-content: space-between; gap: 24px; }}
.logo {{ height: 58px; }}
.chip {{ background: #fff; border-radius: 18px; padding: 12px 18px; display: inline-flex; }}
.chip .logo {{ height: 50px; }}
.pill {{ background: {BRAND_DARK}; color: #fff; font-weight: 700; font-size: 26px; letter-spacing: 0.06em; text-transform: uppercase;
        border-radius: 999px; padding: 18px 30px; white-space: nowrap; }}
.note {{ font-size: 24px; color: {TEXT2}; line-height: 1.35; }}
.dark .note {{ color: #b9b9c0; }}
.bg {{ position: absolute; inset: 0; background-size: cover; background-position: center; }}
.shade {{ position: absolute; inset: 0; background: linear-gradient(180deg, rgba(17,17,17,.55) 0%, rgba(17,17,17,.88) 70%); }}
.frame > * {{ position: relative; }}
"""


def asset_url(rel: str) -> str:
    return (ASSETS / rel).resolve().as_uri()


def rich(text: str) -> str:
    """Escape, then *phrase* becomes the orange serif accent and a newline a line break."""
    out = html.escape(text)
    out = re.sub(r"\*([^*]+)\*", r'<span class="accent">\1</span>', out)
    return out.replace("\n", "<br>")


def plain(text: str) -> str:
    return re.sub(r"\*([^*]+)\*", r"\1", text)


def logo(dark: bool) -> str:
    img = f'<img class="logo" src="{asset_url("brand/dtj-logo.webp")}" alt="">'
    return f'<span class="chip">{img}</span>' if dark else img


def page(body: str, dark: bool = False, background: str | None = None) -> str:
    bg = ""
    if background:
        bg = f'<div class="bg" style="background-image:url(\'{Path(background).resolve().as_uri()}\')"></div><div class="shade"></div>'
        dark = True
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head>"
            f"<body><div class='frame{' dark' if dark else ''}'>{bg}{body}</div></body></html>")


def t_result(f: dict) -> tuple[str, list[str]]:
    item = load_proof()["items"][f["proof_id"]]
    kicker = f.get("kicker", "Real Shopify sales report")
    figure = item["headline_figure"]
    line = f.get("line", f"{figure} in sales")
    note = "Numbers from the brand's own Shopify sales report."
    body = f"""
      <div class="kicker">{rich(kicker)}</div>
      <div style="display:flex;align-items:center;gap:22px;margin-top:34px">
        <img src="{asset_url(item['logo'])}" style="height:84px;max-width:260px;object-fit:contain;border-radius:{'50%' if item['logo'].endswith(('proeffex.webp','royal-dosa-paper.webp')) else '0'}" alt="">
        <div style="font-size:40px;font-weight:700;letter-spacing:-0.02em">{html.escape(item['brand'])}</div>
      </div>
      <h1 style="font-size:104px;margin-top:30px">{rich(line)}</h1>
      <div style="margin-top:40px;background:#fff;border-radius:32px;padding:22px;border:1px solid rgba(21,21,21,.1);box-shadow:0 18px 50px rgba(0,0,0,.08)">
        <img src="{asset_url(item['asset'])}" style="width:100%;display:block;border-radius:18px" alt="">
      </div>
      <div class="foot"><div class="note" style="max-width:520px">{note}</div>{logo(False)}</div>"""
    return page(body), [plain(kicker), item["brand"], plain(line), note]


def t_pain(f: dict) -> tuple[str, list[str]]:
    sub = f.get("sub", "")
    cta = f.get("cta", "Free growth audit · link in bio")
    body = f"""
      <div class="kicker">{rich(f.get('kicker', 'Sound familiar?'))}</div>
      <h1 style="font-size:{f.get('size', 118)}px;margin-top:auto">{rich(f['headline'])}</h1>
      {f'<p style="font-size:38px;line-height:1.3;margin-top:36px;color:#d9d9de;max-width:880px">{rich(sub)}</p>' if sub else ''}
      <div class="foot" style="margin-top:72px">{logo(True)}<span class="pill">{html.escape(cta)}</span></div>"""
    words = [plain(f.get("kicker", "Sound familiar?")), plain(f["headline"]), cta] + ([plain(sub)] if sub else [])
    return page(body, dark=True, background=f.get("background")), words


def t_before_after(f: dict) -> tuple[str, list[str]]:
    def phone(src: str, label: str, hot: bool) -> str:
        return f"""<div style="flex:1;display:flex;flex-direction:column;gap:18px;align-items:center">
          <div style="font-size:28px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:{BRAND_DARK if hot else TEXT2}">{label}</div>
          <div style="width:100%;height:690px;border-radius:44px;border:10px solid #151515;overflow:hidden;background:#fff">
            <img src="{asset_url(src)}" style="width:100%;display:block" alt=""></div></div>"""
    body = f"""
      <h1 style="font-size:78px">{rich(f['headline'])}</h1>
      <div style="display:flex;gap:40px;margin-top:44px">{phone('shopify/before-pdp.webp', 'Before', False)}{phone('shopify/after-pdp.webp', 'After', True)}</div>
      <p style="font-size:38px;font-weight:600;line-height:1.25;margin-top:40px">{rich(f['line'])}</p>
      <div class="foot">{f'<div class="note">{rich(f["note"])}</div>' if f.get('note') else '<span></span>'}{logo(False)}</div>"""
    return page(body), [plain(f["headline"]), "Before", "After", plain(f["line"])] + ([plain(f["note"])] if f.get("note") else [])


def t_slide(f: dict) -> tuple[str, list[str]]:
    dark = bool(f.get("dark"))
    num = f.get("number")
    body = f"""
      {f'<div style="font-size:150px;font-weight:800;line-height:1;color:{BRAND if dark else BRAND_DARK}">{html.escape(str(num))}</div>' if num else ''}
      <h1 style="font-size:{f.get('size', 92)}px;margin-top:{'40px' if num else 'auto'}">{rich(f['headline'])}</h1>
      {f'<p style="font-size:40px;line-height:1.32;margin-top:36px;opacity:.85">{rich(f["body"])}</p>' if f.get('body') else ''}
      <div class="foot" style="margin-top:auto;padding-top:48px">{logo(dark)}<span class="note">{html.escape(f.get('swipe', ''))}</span></div>"""
    words = ([str(num)] if num else []) + [plain(f["headline"])] + ([plain(f["body"])] if f.get("body") else []) + ([f["swipe"]] if f.get("swipe") else [])
    return page(body, dark=dark, background=f.get("background")), words


def t_cta(f: dict) -> tuple[str, list[str]]:
    headline = f.get("headline", "Find out where your sales are *leaking*")
    line = "Get a free growth audit of your ads, store and product pages."
    nxt = "We check your details first, then our team gets in touch."
    link_text = f.get("link_text", "Link in bio")
    body = f"""
      <div style="margin-top:auto">{logo(True)}</div>
      <h1 style="font-size:100px;margin-top:48px">{rich(headline)}</h1>
      <p style="font-size:40px;line-height:1.3;margin-top:36px;color:#e6e6ea">{line}</p>
      <p class="note" style="margin-top:22px;font-size:30px">{nxt}</p>
      <div class="foot" style="margin-top:72px"><span class="pill">Free growth audit</span><span style="font-size:32px;font-weight:600">{html.escape(link_text)} →</span></div>"""
    return page(body, dark=True), [plain(headline), line, nxt, "Free growth audit", link_text]


TEMPLATES = {"result": t_result, "pain": t_pain, "before_after": t_before_after, "slide": t_slide, "cta": t_cta}


def build_html(template: str, fields: dict) -> tuple[str, list[str]]:
    if template not in TEMPLATES:
        raise ValueError(f"unknown template {template!r}; use one of {', '.join(TEMPLATES)}")
    return TEMPLATES[template](fields)


def render(specs: list[dict], out_dir: str | Path) -> dict[str, list[str]]:
    """Render every spec to out_dir/<file> (JPEG, quality 90). Returns {file: words on the picture}."""
    from playwright.sync_api import sync_playwright

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    words: dict[str, list[str]] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for spec in specs:
            doc, said = build_html(spec["template"], spec.get("fields", {}))
            tmp = out_dir / f".{spec['file']}.html"
            tmp.write_text(doc, encoding="utf-8")
            pg.goto(tmp.resolve().as_uri(), wait_until="networkidle")
            pg.evaluate("document.fonts.ready")
            pg.screenshot(path=str(out_dir / spec["file"]), type="jpeg", quality=90, clip={"x": 0, "y": 0, "width": W, "height": H})
            tmp.unlink()
            words[spec["file"]] = said
        browser.close()
    return words


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render DTJ post pictures from templates")
    ap.add_argument("spec")
    ap.add_argument("out_dir")
    args = ap.parse_args(argv)
    words = render(json.loads(Path(args.spec).read_text(encoding="utf-8")), args.out_dir)
    print(json.dumps(words, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
