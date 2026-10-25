"""Put the words on a product's gallery pictures with real fonts on one grid, so the set looks like a designer made it.

Harsh, 24 Oct 2026, on the first AI gallery: "insanely unproffesional and cluttered with a complete AI SLOP RESULTS, you have to get
better results as same as mojovibe's". What separates a pro D2C gallery (MojoVibe) from AI pictures: one subject per picture on a
flat colour with empty space, and ONE type system across the set. A picture model draws a different font every time and crowds the
frame, so the photo comes from ai_images (no words, the text area left empty) and this module sets the type: the same headline font,
body font, sizes, margins and colours (brand.json) on every picture. Every line printed is checked against facts.json first
(ai_images.check_words: a sourced, non-SAMPLE fact; never a price, an offer, a count or a claim).

    python -m provision.gallery_compose --spec <client>/gallery-v2/compose.json --facts <client>/facts.json --out <client>/gallery-v2/final
    the spec: {"brand": {"primary", "accent", "ink", "heading_font", "body_font"}, "pictures": [{"name", "layout", "ground", ...}]}

Layouts (1080 x 1080, 72 px margins):
  pack     the photo full-bleed (the product to the right); headline and sub top-left; an optional round sticker {value, label}.
  top      the photo full-bleed (the subject low); headline and sub centred at the top.
  bottom   the photo full-bleed (the subject high); headline and sub bottom-left.
  numbers  the photo full-bleed (the product centred); headline at the top; 2 to 4 {value, label} facts, half left, half right.
  tiles    a flat ground; headline at the top; 3 to 6 round photos {photo, label} in a grid (what's inside: each real ingredient).
  stack    a flat ground; the headline's sentences stacked on the left with the sub; 3 square photos {photo, label} on the right.
ground "dark" = the brand's primary colour with the accent headline and white words; "light" = the accent colour with the primary
headline and ink words. Fonts: Google Fonts files fetched once into DTJ_FONT_CACHE (default ~/.cache/dtj-fonts). Rendering: the
page builder's headless Chrome (page_builder.browser). Exit 0 = every picture made, 1 = some could not be (why is printed), 2 = a
printed line was refused (nothing is made).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from page_builder.browser import SANDBOX, find_browser  # noqa: E402
from provision.ai_images import check_words  # noqa: E402

SIZE = 1080
LAYOUTS = ("pack", "top", "bottom", "numbers", "tiles", "stack")
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/{folder}/{file}"
FONT_FILES = {"Shrikhand": {"400": "Shrikhand-Regular.ttf"}, "Poppins": {"600": "Poppins-SemiBold.ttf", "700": "Poppins-Bold.ttf"}}
UNIT = re.compile(r"(\d+(?:[.,]\d+)?) (g|kg|mg|ml|l)\b")  # a number and its unit stay on one line, kept together by an <i> (24 Oct
# 2026: the display font draws a no-break space far wider than a space, "8   g"; 26 Oct 2026: a <span> took the label and pill styles
# of .num span / .shot span, so "14 g" printed as "1" over a small "4 g" and a pill's "100 ml" jumped out of it)
DEFAULT_BRAND = {"primary": "#9E1B22", "accent": "#FFC94A", "ink": "#24090B", "heading_font": "Shrikhand", "body_font": "Poppins"}


class ComposeError(RuntimeError):
    pass


def font_cache() -> Path:
    return Path(os.environ.get("DTJ_FONT_CACHE") or Path.home() / ".cache" / "dtj-fonts")


def font_faces(family: str, alias: str, fetch=urllib.request.urlopen) -> str:
    """@font-face rules for one Google font, from the local cache (fetched once). Unknown families try <Family>-Regular.ttf."""
    files = FONT_FILES.get(family) or {"400": f"{family.replace(' ', '')}-Regular.ttf", "700": f"{family.replace(' ', '')}-Bold.ttf"}
    folder = family.lower().replace(" ", "")
    rules = []
    for weight, name in files.items():
        local = font_cache() / name
        if not local.is_file():
            try:
                req = urllib.request.Request(FONT_URL.format(folder=folder, file=name), headers={"User-Agent": "Mozilla/5.0"})
                data = fetch(req, timeout=60).read()
            except Exception:  # noqa: BLE001 - a missing weight is skipped; the next one or the fallback font is used
                continue
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(data)
        rules.append(f"@font-face{{font-family:'{alias}';src:url('{local.resolve().as_uri()}');font-weight:{weight};}}")
    if not rules:
        raise ComposeError(f"the font {family!r} could not be fetched from Google Fonts")
    return "".join(rules)


def lines_of(pic: dict) -> list[str]:
    """Every line the picture prints, as check_words reads it."""
    out = [pic.get("headline", ""), pic.get("sub", "")]
    sticker = pic.get("sticker") or {}
    if sticker:
        out.append(f"{sticker.get('value', '')} {sticker.get('label', '')}".strip())
    for item in pic.get("items") or []:
        out.append(f"{item.get('value', '')} {item.get('label', '')}".strip())
    return [x for x in out if x and x.strip()]


CSS = """
*{box-sizing:border-box}html,body{margin:0;padding:0}.nb{white-space:nowrap;font-style:normal}
body{width:1080px;height:1080px;overflow:hidden;font-family:'B',sans-serif;-webkit-font-smoothing:antialiased}
.c{position:relative;width:1080px;height:1080px;overflow:hidden;background:var(--ground)}
.bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
h1{font-family:'H',serif;font-weight:400;margin:0;line-height:1.04;color:var(--head);letter-spacing:-0.5px;text-wrap:balance}
.sub{font-weight:600;font-size:36px;line-height:1.28;margin:22px 0 0;color:var(--words)}
.t{position:absolute;left:72px;right:72px}
.pack .t{top:72px;right:auto;width:420px}.pack h1{font-size:104px}.pack .sub{max-width:340px}
.top .t{top:72px;text-align:center}.top h1{font-size:104px}.top .sub{margin-left:auto;margin-right:auto;max-width:820px}
.bottom .t{bottom:72px;width:700px;right:auto}.bottom h1{font-size:110px}
.sticker{position:absolute;left:72px;bottom:96px;width:250px;height:250px;border-radius:50%;background:var(--sticker-bg);
  color:var(--sticker-fg);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:26px;
  transform:rotate(-8deg);box-shadow:0 10px 30px rgba(0,0,0,.18)}
.sticker b{font-family:'H',serif;font-weight:400;font-size:78px;line-height:1}.sticker span{font-weight:700;font-size:25px;line-height:1.15;margin-top:6px}
.numbers .t{top:64px;text-align:center}.numbers h1{font-size:84px}
.num{position:absolute;width:210px;color:var(--words)}.num b{display:block;font-family:'H',serif;font-weight:400;font-size:92px;line-height:1;color:var(--head)}
.num span{display:block;font-weight:600;font-size:27px;line-height:1.2;margin-top:8px}
.num.l{left:72px}.num.r{right:72px;text-align:right}.num.y0{top:420px}.num.y1{top:720px}
.tiles .t{top:110px;text-align:center}.tiles h1{font-size:96px}
.grid{position:absolute;left:60px;right:60px;top:290px;bottom:56px;display:grid;grid-template-columns:repeat(3,1fr);align-content:start;row-gap:40px}
.grid.g2{grid-template-columns:repeat(2,1fr);left:190px;right:190px}
.tile{display:flex;flex-direction:column;align-items:center}
.tile img{width:250px;height:250px;border-radius:50%;object-fit:cover;border:7px solid var(--ring);box-shadow:0 8px 24px rgba(0,0,0,.14)}
.tile span{margin-top:16px;font-weight:700;font-size:28px;line-height:1.15;text-align:center;color:var(--words);max-width:300px}
.stack .t{top:0;bottom:0;width:520px;right:auto;display:flex;flex-direction:column;justify-content:center}
.stack h1{font-size:108px;line-height:1.08}.stack h1 em{display:block;font-style:normal;white-space:nowrap}
.col{position:absolute;right:66px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:22px}
.shot{position:relative;width:318px;height:300px;border-radius:26px;overflow:hidden;box-shadow:0 10px 28px rgba(0,0,0,.25)}
.shot img{width:100%;height:100%;object-fit:cover}
.shot span{position:absolute;left:14px;bottom:14px;background:var(--pill-bg);color:var(--pill-fg);font-weight:700;font-size:24px;
  padding:8px 16px;border-radius:999px}
"""

FIT = """<script>
// the fonts are loaded BEFORE measuring (24 Oct 2026: fonts.ready resolved early, the fallback font was measured and the real
// headline then ran into the jar)
Promise.all([document.fonts.load("400 100px H"), document.fonts.load("600 36px B"), document.fonts.load("700 28px B")])
.then(function(){ return document.fonts.ready; }).then(function(){
  document.querySelectorAll('h1').forEach(function(h){
    var max = parseFloat(h.dataset.maxh || '0'), size = parseFloat(getComputedStyle(h).fontSize);
    while (size > 40 && (h.scrollWidth > h.clientWidth + 1 || (max && h.getBoundingClientRect().height > max))) {
      size -= 3; h.style.fontSize = size + 'px';
    }
  });
  document.body.setAttribute('data-ready', '1');
});
</script>"""


def _img(path: str | Path, base: Path) -> str:
    p = Path(path)
    p = p if p.is_absolute() else base / p
    if not p.is_file():
        raise ComposeError(f"photo missing: {p}")
    return html.escape(p.resolve().as_uri(), quote=True)


def _label(item: dict) -> str:
    return f"{item.get('value', '')} {item.get('label', '')}".strip()  # exactly the line check_words read


def page(pic: dict, brand: dict, base: Path, faces: str) -> str:
    """The HTML for one picture."""
    layout = pic.get("layout")
    if layout not in LAYOUTS:
        raise ComposeError(f"{pic.get('name')}: layout must be one of {', '.join(LAYOUTS)}")
    dark = pic.get("ground", "dark") == "dark"
    primary, accent, ink = brand["primary"], brand["accent"], brand["ink"]
    colours = {"ground": primary if dark else accent, "head": accent if dark else primary, "words": "#FFFFFF" if dark else ink,
               "sticker-bg": accent if dark else primary, "sticker-fg": primary if dark else accent, "ring": accent if dark else "#FFFFFF",
               "pill-bg": accent, "pill-fg": primary}
    style = ";".join(f"--{k}:{v}" for k, v in colours.items())
    e = lambda s: UNIT.sub(r'<i class="nb">\1 \2</i>', html.escape(s or ""))  # noqa: E731 - "100 g" never breaks
    head, sub = e(pic.get("headline")), e(pic.get("sub"))
    maxh = {"pack": 330, "top": 240, "bottom": 360, "numbers": 200, "tiles": 170, "stack": 560}[layout]
    if layout == "stack":  # one sentence per line: "Spread it." / "Dip it." / "Stuff it."; one sentence alone wraps as usual
        parts = [p.strip() for p in (pic.get("headline") or "").replace(". ", ".|").split("|") if p.strip()]
        if len(parts) > 1:
            head = "".join(f"<em>{e(p)}</em>" for p in parts)
    text = f'<div class="t"><h1 data-maxh="{maxh}">{head}</h1>' + (f'<p class="sub">{sub}</p>' if sub else "") + "</div>"
    body = ""
    if pic.get("photo"):
        body += f'<img class="bg" src="{_img(pic["photo"], base)}" alt="">'
    if layout == "pack" and pic.get("sticker"):
        s = pic["sticker"]
        body += f'<div class="sticker"><b>{e(s.get("value"))}</b><span>{e(s.get("label"))}</span></div>'
    items = pic.get("items") or []
    if layout == "numbers":
        for i, it in enumerate(items[:4]):
            side, row = ("l" if i % 2 == 0 else "r"), f"y{i // 2}"
            body += f'<div class="num {side} {row}"><b>{e(it.get("value"))}</b><span>{e(it.get("label"))}</span></div>'
    if layout == "tiles":
        body += f'<div class="grid{" g2" if len(items) == 4 else ""}">' + "".join(  # four tiles sit 2 x 2, not 3 + 1
            f'<div class="tile"><img src="{_img(it["photo"], base)}" alt=""><span>{e(_label(it))}</span></div>' for it in items[:6]) + "</div>"
    if layout == "stack":
        body += '<div class="col">' + "".join(
            f'<div class="shot"><img src="{_img(it["photo"], base)}" alt=""><span>{e(_label(it))}</span></div>' for it in items[:3]) + "</div>"
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{faces}{CSS}</style></head>"
            f"<body><div class='c {layout}' style='{style}'>{body}{text}</div>{FIT}</body></html>")


def render(doc: str, out_png: Path, exe: Path | None = None, timeout: int = 120) -> Path:
    exe = exe or find_browser()
    if not exe:
        raise ComposeError("no headless Chrome or Edge found (page_builder.browser)")
    src = out_png.with_suffix(".html")
    src.write_text(doc, encoding="utf-8")
    r = subprocess.run([str(exe), "--headless=new", "--disable-gpu", *SANDBOX, "--hide-scrollbars", "--allow-file-access-from-files",
                        f"--window-size={SIZE},{SIZE}", "--virtual-time-budget=8000", f"--screenshot={out_png.resolve()}",
                        src.resolve().as_uri()], capture_output=True, text=True, timeout=timeout)
    if not out_png.is_file():
        raise ComposeError(f"no picture rendered (exit {r.returncode}): {r.stderr[-300:]}")
    return out_png


def compose(spec: dict, facts: dict, out_dir: Path, base: Path, renderer=render, faces: str | None = None) -> list[dict]:
    """Check every printed line first (all pictures), then render each picture; returns one record per picture."""
    brand = {**DEFAULT_BRAND, **(spec.get("brand") or {})}
    pictures = spec.get("pictures") or []
    checked = {pic["name"]: check_words(lines_of(pic), facts) for pic in pictures}  # ValueError before anything is made
    if faces is None:
        faces = font_faces(brand["heading_font"], "H") + font_faces(brand["body_font"], "B")
    out_dir.mkdir(parents=True, exist_ok=True)
    done = []
    for pic in pictures:
        out = out_dir / f"{pic['name']}.png"
        try:
            renderer(page(pic, brand, base, faces), out)
            done.append({"name": pic["name"], "path": str(out), "words": checked[pic["name"]], "sample": True,
                         "note": "AI photo + DTJ type; replace or sign off before live"})
        except (ComposeError, OSError, subprocess.TimeoutExpired) as exc:
            done.append({"name": pic["name"], "error": str(exc)[:300]})
    (out_dir / "gallery.json").write_text(json.dumps(done, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return done


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True, help="compose.json: brand and pictures (photos relative to the spec's folder)")
    ap.add_argument("--facts", required=True, help="the page's facts.json: every printed line must stand on a sourced fact")
    ap.add_argument("--out", required=True, help="folder for the finished pictures (<name>.png) and gallery.json")
    ap.add_argument("--only", default="", help="comma-separated picture names")
    a = ap.parse_args(argv)
    spec_path = Path(a.spec)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if a.only:
        keep = set(a.only.split(","))
        spec["pictures"] = [p for p in spec.get("pictures", []) if p["name"] in keep]
    facts = json.loads(Path(a.facts).read_text(encoding="utf-8"))
    try:
        done = compose(spec, facts, Path(a.out), spec_path.parent)
    except ValueError as exc:
        print(f"REFUSED, nothing made: {str(exc).removeprefix('refused: ')}")
        return 2
    except ComposeError as exc:
        print(f"could not make the pictures: {exc}")
        return 1
    for d in done:
        print(f"{d['name']}: " + (d.get("path") or f"FAILED {d['error']}"))
    return 0 if all("path" in d for d in done) else 1


if __name__ == "__main__":
    sys.exit(main())
