"""Collect proven video ads for a niche library from Meta's public Ad Library (no login, no API key).

    python -m reel_factory.adlibrary --out <lib> --q chai --q "healthy snacks" --match "chai|snack|..." [--ids 123,456] [--max 60]

Why Ad Library: an ad that a brand has kept paying for over 30+ days is a proven winner, and creator-partnership ads
("<creator> with <brand>") are real Indian creators speaking in their own style - the language we want to learn.
It opens a headless Chrome/Edge on this computer, searches each query (India, active, video, sorted by impressions), keeps ads
running since --min-days ago whose advertiser or text matches --match (or exactly --ids), downloads each video and writes
<lib>/manifest.json (id, file, advertiser, started, days_running, creator_partnership, query, copy, keep: null = a person decides).
Downloads are for studying only; nothing is reposted.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SEARCH = ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={country}&media_type=video"
          "&q={q}&search_type=keyword_unordered")
CARDS_JS = r"""() => {
  const leaves=[...document.querySelectorAll('span,div')].filter(e=>e.childElementCount===0 && /^Library ID:/.test((e.textContent||'').trim()));
  const seen=new Set(), out=[];
  for (const l of leaves){ let c=l;
    while(c && !(c.querySelectorAll('video').length>=1 && (c.innerText.match(/Library ID:/g)||[]).length===1)){ c=c.parentElement;
      if(c && (c.innerText.match(/Library ID:/g)||[]).length>1){c=null;break;} }
    if(!c) continue; const t=c.innerText; const id=(t.match(/Library ID:\s*(\d+)/)||[])[1]; if(!id||seen.has(id)) continue; seen.add(id);
    const lines=t.split('\n').map(s=>s.trim()).filter(Boolean); const si=lines.indexOf('Sponsored'); const v=c.querySelector('video');
    out.push({id, started:(t.match(/Started running on ([^\n]+)/)||[])[1]||'', advertiser: si>0?lines[si-1]:'',
              copy: si>=0?lines.slice(si+1,si+3).join(' ').slice(0,300):'', src: v.currentSrc||v.src||''}); }
  return out; }"""


def parse_date(s: str) -> dt.date | None:
    try:
        return dt.datetime.strptime(s.strip(), "%d %b %Y").date()
    except ValueError:
        return None


def squash(s: str) -> str:
    """'Blue Tea' and 'BlueTea India' compare equal on the brand part."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def collect(queries: list[str], country: str, scrolls: int) -> list[dict]:
    from playwright.sync_api import sync_playwright
    found: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = None
        for channel in ("chrome", "msedge"):
            try:
                browser = p.chromium.launch(channel=channel, headless=True)
                break
            except Exception:
                continue
        if browser is None:
            raise RuntimeError("no Chrome or Edge found for Playwright")
        page = browser.new_page(locale="en-US", viewport={"width": 1280, "height": 2000})
        for q in queries:
            page.goto(SEARCH.format(country=country, q=urllib.parse.quote(q)), wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            for _ in range(scrolls):
                page.mouse.wheel(0, 6000)
                page.wait_for_timeout(1500)
            cards = page.evaluate(CARDS_JS)
            for c in cards:
                found.setdefault(c["id"], {**c, "query": q})
            print(f"{q}: {len(cards)} ads on the page", flush=True)
        browser.close()
    return list(found.values())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--q", action="append", required=True)
    ap.add_argument("--country", default="IN")
    ap.add_argument("--min-days", type=int, default=30)
    ap.add_argument("--match", default="", help="regex on advertiser + ad text (case-insensitive)")
    ap.add_argument("--exclude", default="", help="regex on advertiser to skip (apps, deals pages...)")
    ap.add_argument("--advertiser", default="",
                    help="regex the advertiser (page name) must match, e.g. 'blue tea' also keeps '<creator> with Blue Tea'")
    ap.add_argument("--brand", action="store_true",
                    help="each --q is a brand name: keep only that brand's own ads and its creator partnerships")
    ap.add_argument("--ids", default="", help="comma-separated ad ids: take exactly these")
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--per-query", type=int, default=0, help="keep at most N ads per query (brand), longest-running first")
    ap.add_argument("--scrolls", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true", help="only count what would be taken, per query; download nothing")
    a = ap.parse_args(argv)
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    lib = Path(a.out); lib.mkdir(parents=True, exist_ok=True)
    mpath = lib / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else []
    have = {e["id"] for e in manifest}
    today = dt.date.today()
    ids = {x.strip() for x in a.ids.split(",") if x.strip()}
    picks = []
    for c in collect(a.q, a.country, a.scrolls):
        d = parse_date(c["started"])
        days = (today - d).days if d else None
        if c["id"] in have or not c["src"]:
            continue
        if ids:
            if c["id"] not in ids:
                continue
        else:
            if days is None or days < a.min_days:
                continue
            if a.match and not re.search(a.match, c["advertiser"] + " " + c["copy"], re.I):
                continue
            if a.exclude and re.search(a.exclude, c["advertiser"], re.I):
                continue
            if a.advertiser and not re.search(a.advertiser, c["advertiser"], re.I):
                continue
            if a.brand and squash(c["query"]) not in squash(c["advertiser"]):
                continue
        picks.append({**c, "days_running": days})
    if a.per_query:
        picks.sort(key=lambda c: -(c["days_running"] or 0))
        count: dict[str, int] = {}
        kept = []
        for c in picks:
            if count.get(c["query"], 0) < a.per_query:
                count[c["query"]] = count.get(c["query"], 0) + 1
                kept.append(c)
        picks = kept
    if a.dry_run:
        for q in a.q:
            mine = [c for c in picks if c["query"] == q]
            names = sorted({c["advertiser"] for c in mine})
            print(f"{q}: {len(mine)} ads 30+ days | longest {max((c['days_running'] for c in mine), default=0)} days | {names[:6]}")
        return 0
    picks = picks[: a.max]
    for c in picks:
        f = f"fb_{c['id']}.mp4"
        try:
            with urllib.request.urlopen(urllib.request.Request(c["src"], headers={"User-Agent": "Mozilla/5.0"}), timeout=120) as r:
                (lib / f).write_bytes(r.read())
        except Exception as exc:
            print(f"{c['id']}: download failed ({exc})", file=sys.stderr)
            continue
        manifest.append({"id": c["id"], "file": f, "source": f"https://www.facebook.com/ads/library/?id={c['id']}",
                         "advertiser": c["advertiser"], "started": c["started"], "days_running": c["days_running"],
                         "creator_partnership": " with " in c["advertiser"], "query": c["query"],
                         **({"brand": c["query"]} if a.brand else {}), "copy": c["copy"], "keep": None})
        print(f"saved {f}  {c['advertiser'][:40]}  ({c['days_running']} days)", flush=True)
        time.sleep(0.5)
    mpath.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(picks)} new; manifest has {len(manifest)} reels: {mpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
