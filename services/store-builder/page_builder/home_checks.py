"""Home page design checks (Harsh, 19 Oct 2026: our home page "looks cramped and flat"). The targets come from 23 reference home pages
measured by code (.claude/skills/dtj-home-page/scripts/study_numbers.py; ranges in home_profiles.json).

    cd services/store-builder
    python -m page_builder.home_checks --run ../../.work/clients/<client>/home-run [--html <page.html>] [--profile home-care]

--run is a folder with template.json and home-report.json (run_home / ship_home). --html is that page rendered locally (preview_home.py,
or render.home_page_html); with it the page is measured in a real browser at 1280 and 390 px. The result goes to <run>/home-checks.json.
Exit 0 = every check passes, 2 = a check failed (each failure says what and where).

  HC1 rhythm   every section's top and bottom padding (the theme wrapper's plus the block's own) is the home rhythm's step for its place
               (styling.home_rhythm): the full step, the tighter one next to a related neighbour, 0 for the hero and thin strips
  HC2 colour   neighbouring sections never share a background colour (the hero, thin strips and the wave are exempt: they sit on or
               between bands by design)
  HC3 bands    the strong bands (solid or dark) and where they sit: REPORTED, never failed. Each brand's palette decides how many
               (Harsh, 19 Oct 2026: "every brand has their own color palette and aesthetics"); the direction's own limits are lint L05.
  HC4 order    the section-order rule in home_profiles.json "order", measured on the pages rated 85+: the hero first; a way to shop
               within shop_within sections under it; the first proof by first_proof_by of the page; the story after the first way to
               shop (no page of the 23 tells it earlier); the FAQ within the last faq_within_last sections
  HC5 type     section headings sit on the home type scale (styling.HOME_TYPE)
  HC6 measured (with --html) the empty space between each section's edge and its first / last words, the study's own measure: the
               page's median within the profile's range on a laptop (1280) and a phone (390), and no section below the floor
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
from pathlib import Path

from . import palette, styling
from .catalog import Catalog

HERE = Path(__file__).resolve().parent
PROFILES = HERE / "home_profiles.json"
EXEMPT = ("hero_home",) + styling.HOME_STRIPS  # sit on or between bands by design
SHOP = ("categories_home", "best_sellers_home", "concerns_home")
PROOF = ("press_home", "video_reviews_home", "before_after_home", "trust_band_home")
CATEGORY_PROFILE = {"home-care": "home-care", "cleaning": "home-care", "hygiene": "home-care", "laundry": "home-care", "home": "home-care",
                    "skincare": "beauty", "beauty": "beauty", "cosmetics": "beauty", "haircare": "beauty", "personal-care": "beauty",
                    "supplements": "supplements", "wellness": "supplements", "nutrition": "supplements", "ayurveda": "supplements",
                    "food": "food", "snacks": "food", "beverages": "food", "pet": "pets", "pets": "pets", "pet-care": "pets"}

# the study's measure (remeasure.py), run inside the local preview: per section, the empty space between its edge and its first and last
# words or buttons; a full-width photo is not padding; sections under 80 px are strips
RHYTHM_PROBE = r"""<script>(function(){
function vis(e){var r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>20&&r.height>8&&s.display!=='none'&&s.visibility!=='hidden'&&parseFloat(s.opacity||'1')>0.05;}
function run(){var W=window.innerWidth,rows=[];var secs=document.querySelectorAll('[data-pb-section]');
for(var i=0;i<secs.length;i++){var s=secs[i];var r=s.getBoundingClientRect();if(r.height<80)continue;var top=Infinity,bot=-Infinity,n=0;
 var els=s.querySelectorAll('h1,h2,h3,h4,p,button,a,li,span,label');
 for(var j=0;j<els.length;j++){var e=els[j];if(!vis(e))continue;var own=false;for(var k=0;k<e.childNodes.length;k++){var c=e.childNodes[k];if(c.nodeType===3&&c.nodeValue.trim().length>1){own=true;break;}}
  if(!own&&!/^(BUTTON|A)$/.test(e.tagName))continue;if(e.querySelector('img,picture,video'))continue;var q=e.getBoundingClientRect();if(q.height>400)continue;
  top=Math.min(top,q.top);bot=Math.max(bot,q.bottom);n++;}
 var bleed=false,media=s.querySelectorAll('img,video');for(var m=0;m<media.length;m++){var q2=media[m].getBoundingClientRect();if(q2.width>=W*0.9&&q2.height>200)bleed=true;}
 var h=s.querySelector('h1,h2,h3');
 rows.push({section:s.getAttribute('data-pb-section'),top:Math.round(r.top+window.scrollY),height:Math.round(r.height),text_gap_top:isFinite(top)?Math.round(top-r.top):null,
  text_gap_bottom:isFinite(bot)?Math.round(r.bottom-bot):null,text_items:n,full_bleed_picture:bleed,heading_px:h?Math.round(parseFloat(getComputedStyle(h).fontSize)):null});}
var last=secs.length?secs[secs.length-1].getBoundingClientRect().bottom+window.scrollY:0;var out={width:W,page_height:Math.ceil(last),sections:rows};
var sink=parent&&parent.document&&parent.document.getElementById('pbm');var json='PBRESULT'+JSON.stringify(out)+'PBEND';
if(sink&&parent!==window)sink.textContent=json;else{var p=document.createElement('pre');p.id='pbm';p.textContent=json;document.body.appendChild(p);}}
window.addEventListener('load',function(){setTimeout(run,800);});})();</script>"""


def load_profile(category: str | None = None, path: Path = PROFILES) -> tuple[str, dict, dict]:
    """(profile name, its targets, the order rule) for a brand category; an unknown category gets the default profile."""
    data = json.loads(path.read_text(encoding="utf-8"))
    name = CATEGORY_PROFILE.get((category or "").lower(), "default")
    if name not in data["profiles"]:
        name = "default"
    return name, data["profiles"][name]["targets"], data["order"]


def _sections(template: dict, report: dict) -> list[dict]:
    """The page's DTJ sections in order with their kind, role, block, settings and the background a shopper sees."""
    built = {s["id"]: s for s in report.get("sections_built", [])}
    page_bg = (report.get("direction", {}).get("roles") or {}).get("bg", "#FFFFFF")
    out = []
    for sid in template["order"]:
        sec = template["sections"][sid]
        info = built.get(sid)
        if not info or not sec.get("block_order"):
            continue  # one of the theme's own sections, or one this build did not make
        key = sec["block_order"][0]
        settings = sec["blocks"][key].get("settings", {})
        wrap = sec.get("settings", {})
        out.append({"id": sid, "kind": info["kind"], "role": info.get("role"), "block": info["block"].split("/")[-1], "app": info["block"].split("/")[0],
                    "settings": settings, "wrapper": wrap,
                    "bg": (settings.get("background") or wrap.get("background_color") or page_bg).upper()})
    return out


def check_template(template: dict, report: dict, order_rule: dict, cat: Catalog | None = None) -> tuple[list[dict], dict]:
    cat = cat or Catalog()
    secs = _sections(template, report)
    findings: list[dict] = []

    def fail(check, where, msg):
        findings.append({"check": check, "section": where, "message": msg})

    # HC1 rhythm
    expected = styling.home_rhythm([s["kind"] for s in secs])
    rhythm = []
    for s, want in zip(secs, expected):
        if want is None:  # the hero keeps its own look
            continue
        want_top, want_bottom = want
        top = (s["wrapper"].get("padding-block-start") or 0) + (s["settings"].get("padding_top") or 0)
        bottom = (s["wrapper"].get("padding-block-end") or 0) + (s["settings"].get("padding_bottom") or 0)
        rhythm.append({"section": s["id"], "kind": s["kind"], "top": top, "bottom": bottom, "want": [want_top, want_bottom]})
        if (top, bottom) != (want_top, want_bottom):
            fail("HC1", s["id"], f"padding {top}/{bottom} px, the home rhythm wants {want_top}/{want_bottom} px")
    # HC2 neighbouring colours
    for a, b in zip(secs, secs[1:]):
        if a["kind"] in EXEMPT or b["kind"] in EXEMPT:
            continue
        if a["bg"] == b["bg"]:
            fail("HC2", f"{a['id']} + {b['id']}", f"neighbours share the background {a['bg']}")
    # HC3 strong bands: reported only
    strong = [{"section": s["id"], "kind": s["kind"], "bg": s["bg"]} for s in secs
              if s["kind"] not in EXEMPT and palette.oklch(s["bg"])[0] < 0.78]
    # HC4 order
    kinds = [s["kind"] for s in secs]
    content = [k for k in kinds if k not in styling.HOME_STRIPS]
    order = {"content": content}
    if content and content[0] != "hero_home":
        fail("HC4", content[0], "the hero is not the first section")
    after = content[1:] if content and content[0] == "hero_home" else content
    first_shop = next((i for i, k in enumerate(after) if k in SHOP), None)
    if first_shop is None or first_shop >= order_rule["shop_within"]:
        fail("HC4", "shop", f"no way to shop in the first {order_rule['shop_within']} sections under the hero (categories, best sellers or concerns)")
    proofs = [i for i, k in enumerate(kinds) if k in order_rule["proof_kinds"]]
    order["first_proof_at"] = round(proofs[0] / max(1, len(kinds) - 1), 2) if proofs else None
    if not proofs or proofs[0] / max(1, len(kinds) - 1) > order_rule["first_proof_by"]:
        fail("HC4", "proof", f"no proof ({', '.join(order_rule['proof_kinds'])}) in the first {int(order_rule['first_proof_by'] * 100)} % of the page")
    if order_rule.get("story_after_shop", True) and "story_home" in after and first_shop is not None and after.index("story_home") < first_shop:
        fail("HC4", "story_home", "the brand story comes before any way to shop (no page in the study does that)")
    last = order_rule.get("faq_within_last", 1)
    if "faq" in content and len(content) - content.index("faq") > last:
        fail("HC4", "faq", f"the FAQ is not within the last {last} sections ({len(content) - content.index('faq') - 1} follow it)")
    # HC5 type scale
    for s in secs:
        step = styling.HOME_TYPE["hero" if s["kind"] == "hero_home" else "nav" if s["block"] in styling.NAV_BLOCKS else "section"]
        for key, want in (("heading_size_desktop", step[0]), ("heading_size_mobile", step[1])):
            if cat.has(s["app"], s["block"], key) and s["settings"].get(key, cat.default(s["app"], s["block"], key)) != want:
                fail("HC5", s["id"], f"{key} {s['settings'].get(key, cat.default(s['app'], s['block'], key))} px, the scale says {want}")
    return findings, {"rhythm": rhythm, "strong_bands": strong, "order": order, "backgrounds": [s["bg"] for s in secs]}


def summarise(rows: list[dict], kinds: dict[str, str]) -> dict:
    """The study's pad: the median of every top and bottom gap of the sections that are not a full-width photo, hero or strip."""
    gaps, per = [], []
    for r in rows:
        if r["full_bleed_picture"] or kinds.get(r["section"]) in EXEMPT:
            continue
        g = [v for v in (r["text_gap_top"], r["text_gap_bottom"]) if v is not None]
        gaps += g
        per.append({"section": r["section"], "top": r["text_gap_top"], "bottom": r["text_gap_bottom"]})
    return {"median": round(st.median(gaps)) if gaps else None, "min": min(gaps) if gaps else None, "max": max(gaps) if gaps else None,
            "n": len(gaps), "sections": per}


def check_rendered(doc: str, kinds: dict[str, str], targets: dict, browser) -> tuple[list[dict], dict]:
    findings, numbers = [], {}
    for width, key in ((1280, "desktop"), (390, "phone")):
        page = browser.measure(doc, width, probe=RHYTHM_PROBE, height=16000)
        s = summarise(page["sections"], kinds)
        s["page_px"] = page["page_height"]
        numbers[key] = s
        lo, hi = targets[f"pad_{key}"]
        if s["median"] is None or not lo <= s["median"] <= hi:
            findings.append({"check": "HC6", "section": key, "message": f"{key} pad median {s['median']} px, the target is {lo}-{hi} px"})
        floor = targets[f"pad_floor_{key}"]
        for row in s["sections"]:
            low = [v for v in (row["top"], row["bottom"]) if v is not None and v < floor]
            if low:
                findings.append({"check": "HC6", "section": row["section"], "message": f"{key}: {min(low)} px between the edge and the words, under the floor of {floor} px"})
    return findings, numbers


def _read(path: Path):
    return json.loads(re.sub(r"^\s*/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.S))


def main(argv: list[str] | None = None, browser=None) -> int:
    ap = argparse.ArgumentParser(description="Home page design checks: rhythm, colour, order, type and measured spacing.")
    ap.add_argument("--run", required=True, help="the folder with template.json and home-report.json")
    ap.add_argument("--html", help="the page rendered locally (preview_home.py page.html): measured at 1280 and 390 px")
    ap.add_argument("--profile", help="a brand category (home-care, beauty, supplements, food, pets ...); default: the report's niche")
    a = ap.parse_args(argv)
    run = Path(a.run)
    template, report = _read(run / "template.json"), _read(run / "home-report.json")
    name, targets, order_rule = load_profile(a.profile or report.get("category") or report.get("niche"))
    findings, numbers = check_template(template, report, order_rule)
    if a.html:
        if browser is None:
            from .browser import EdgeBrowser  # noqa: PLC0415  (only when a page is measured)
            browser = EdgeBrowser(work=run / "home-checks-work")
        kinds = {s["id"]: s["kind"] for s in report.get("sections_built", [])}
        more, measured = check_rendered(Path(a.html).read_text(encoding="utf-8"), kinds, targets, browser)
        findings += more
        numbers["measured"] = measured
    result = {"profile": name, "targets": targets, "pass": not findings, "findings": findings, "numbers": numbers}
    (run / "home-checks.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    for f in findings:
        print(f"{f['check']} {f['section']}: {f['message']}")
    if "measured" in numbers:
        for key in ("desktop", "phone"):
            m = numbers["measured"][key]
            print(f"{key}: pad median {m['median']} px (min {m['min']}, max {m['max']}, n {m['n']}), page {m['page_px']} px")
    print(f"strong bands: {len(numbers['strong_bands'])} ({', '.join(b['kind'] for b in numbers['strong_bands']) or 'none'}) | profile {name} | "
          f"{'PASS' if not findings else f'{len(findings)} findings'}")
    return 0 if not findings else 2


if __name__ == "__main__":
    sys.exit(main())
