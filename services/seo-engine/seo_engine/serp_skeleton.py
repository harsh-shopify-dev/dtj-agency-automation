"""Before writing: read the top 3 Google results for the page's main keyword and learn their shape.

We take their headings (h1-h3), length, questions, FAQ and structured data, and hand that outline to the writer: cover what
they cover, go deeper, in DTJ's own words. Their text is never stored or sent to the model; only a fingerprint of their
10-word phrases is kept in memory so gates.copy_check can block any sentence copied from them.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

from . import site_scan
from .dataforseo import Client

SKIP_HOSTS = {"youtube.com", "quora.com", "reddit.com", "facebook.com", "instagram.com", "linkedin.com", "justdial.com",
              "indiamart.com", "sulekha.com", "clutch.co", "goodfirms.co", "wikipedia.org", "amazon.in", "amazon.com",
              "x.com", "twitter.com", "designrush.com", "upwork.com", "fiverr.com", "digitaltusharjoshi.com"}
TOP = 3
SHINGLE = 10
GUJARAT_CITIES = {"Rajkot", "Ahmedabad", "Surat", "Vadodara"}


def location_name(place: str | None) -> str | None:
    """DataForSEO's place names (format 'City,Region,Country'; checked on the first live run, India is the fallback)."""
    if place in GUJARAT_CITIES:
        return f"{place},Gujarat,India"
    if place == "Gujarat":
        return "Gujarat,India"
    return None


def shingles(text: str, n: int = SHINGLE) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {hashlib.blake2b(" ".join(words[i:i + n]).encode(), digest_size=8).hexdigest() for i in range(max(0, len(words) - n + 1))}


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.").removeprefix("m.")


def build(client: Client, keyword: str, place: str | None = None, fetch=site_scan.http_fetch) -> dict:
    note = None
    try:
        results = client.serp(keyword, location_name=location_name(place))
    except Exception as exc:  # noqa: BLE001 - an unknown place name: fall back to all of India once
        if not location_name(place):
            raise
        note = f"{place}: {exc}; used India instead"
        results = client.serp(keyword)
    pages, fingerprint = [], set()
    for r in results:
        if len(pages) == TOP:
            break
        if not r.get("url") or any(_host(r["url"]) == h or _host(r["url"]).endswith("." + h) for h in SKIP_HOSTS):
            continue
        resp = fetch(r["url"])
        if resp.status != 200 or "html" not in resp.content_type.lower():
            continue
        parser = site_scan._PageParser()
        parser.feed(resp.text)
        p = site_scan.parse_page(r["url"], resp.text)
        fingerprint |= shingles(" ".join(parser.text))
        pages.append({"rank": r.get("rank"), "url": r["url"], "title": p.title, "words": p.words,
                      "outline": [f"{lvl}: {t}" for lvl, t in parser.outline if t][:40], "questions": p.questions[:15],
                      "has_faq": "FAQPage" in p.schema_types or len(p.questions) >= 3, "schema_types": p.schema_types})
    words = [p["words"] for p in pages]
    return {
        "keyword": keyword, "place": place, "note": note, "source": "DataForSEO Google mobile top 10, then each page fetched",
        "pages": pages, "target_words": max(words) + 150 if words else None,
        "_fingerprint": fingerprint,  # in memory only: never saved, never sent to the model
    }


def for_model(skeleton: dict | None) -> dict | None:
    if not skeleton:
        return None
    return {k: v for k, v in skeleton.items() if not k.startswith("_")}
