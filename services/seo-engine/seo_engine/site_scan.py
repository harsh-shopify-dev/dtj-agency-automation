"""Tier 0 site scan: reads the public sitemap and every listed page, and turns what it finds into ranked findings.

Free (no SEO-tool credits, no AI). Every finding names the page and the evidence that caused it, so the weekly report never states a
problem the code did not see.

    from seo_engine.site_scan import scan
    result = scan("https://digitaltusharjoshi.com")
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import unquote

USER_AGENT = "dtj-seo-scan/1.0 (+https://digitaltusharjoshi.com)"
MAX_PAGES = 80
STALE_DAYS = 180
TITLE_MAX, DESC_MIN, DESC_MAX = 60, 70, 160
THIN_WORDS = 300
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Response:
    status: int
    url: str
    content_type: str
    text: str


Fetcher = Callable[[str], Response]


def http_fetch(url: str, timeout: int = 25) -> Response:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.5"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(3_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")
            return Response(r.status, r.geturl(), r.headers.get("Content-Type", ""), body)
    except urllib.error.HTTPError as exc:
        return Response(exc.code, url, exc.headers.get("Content-Type", "") if exc.headers else "", "")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return Response(0, url, "", f"fetch error: {type(exc).__name__}")


class _PageParser(HTMLParser):
    """Collects only what the rules need. Script and style text is not counted as words."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.meta, self.canonical = "", {}, None
        self.h1, self.headings, self.jsonld, self.text = [], [], [], []
        self.outline: list[tuple[str, str]] = []  # (h1|h2|h3, text) in page order
        self.img_total = self.img_no_alt = 0
        self.images_no_alt: list[dict] = []  # src and WordPress media id (class "wp-image-N"), for the alt-text fixes
        self._stack: list[str] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta" and (a.get("name") or a.get("property")):
            self.meta[(a.get("name") or a.get("property")).lower()] = a.get("content", "")
        elif tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonical = a.get("href")
        elif tag == "img":
            self.img_total += 1
            if not a.get("alt", "").strip():
                self.img_no_alt += 1
                wp = re.search(r"wp-image-(\d+)", a.get("class", ""))
                src = a.get("src") or a.get("data-src") or a.get("data-lazy-src") or ""
                if src.startswith("http"):
                    self.images_no_alt.append({"src": src, "media_id": int(wp.group(1)) if wp else None})
        if tag in ("title", "h1", "h2", "h3", "script", "style", "noscript"):
            self._stack.append(tag if tag != "script" or a.get("type", "") == "application/ld+json" else "js")
            self._buf = []

    def handle_endtag(self, tag):
        if not self._stack or tag not in ("title", "h1", "h2", "h3", "script", "style", "noscript"):
            return
        top = self._stack.pop()
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        if top == "title":
            self.title = text
        elif top == "h1":
            self.h1.append(text)
            self.headings.append(text)
            self.outline.append((top, text))
        elif top in ("h2", "h3"):
            self.headings.append(text)
            self.outline.append((top, text))
        elif top == "script":
            self.jsonld.append("".join(self._buf))
        self._buf = []

    def handle_data(self, data):
        if self._stack:
            self._buf.append(data)
            if self._stack[-1] in ("script", "js", "style", "noscript"):
                return
        self.text.append(data)


def _schema_types(blobs: list[str]) -> list[str]:
    found: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type")
            for v in t if isinstance(t, list) else [t]:
                if isinstance(v, str):
                    found.add(v)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for blob in blobs:
        try:
            walk(json.loads(blob))
        except ValueError:
            found.add("INVALID_JSON_LD")
    return sorted(found)


@dataclass
class Page:
    url: str
    status: int
    lastmod: str | None = None
    title: str = ""
    description: str = ""
    robots: str = ""
    canonical: str | None = None
    h1: list = field(default_factory=list)
    questions: list = field(default_factory=list)  # headings that are questions: the raw material of AI answers
    schema_types: list = field(default_factory=list)
    words: int = 0
    img_total: int = 0
    img_no_alt: int = 0
    images_no_alt: list = field(default_factory=list)
    excerpt: str = ""  # the first visible words, for writing a meta description


def parse_page(url: str, html: str, status: int = 200, lastmod: str | None = None) -> Page:
    p = _PageParser()
    p.feed(html)
    words = len(re.findall(r"[A-Za-zऀ-૿]{2,}", " ".join(p.text)))
    return Page(url=url, status=status, lastmod=lastmod, title=p.title, description=p.meta.get("description", "").strip(),
                robots=p.meta.get("robots", ""), canonical=p.canonical, h1=p.h1,
                questions=[h for h in p.headings if h.endswith("?")], schema_types=_schema_types(p.jsonld), words=words,
                img_total=p.img_total, img_no_alt=p.img_no_alt, images_no_alt=p.images_no_alt[:30],
                excerpt=re.sub(r"\s+", " ", " ".join(p.text)).strip()[:700])


SITEMAP_TRIES = 3
DROP_SHARE = 0.75  # fewer pages than this share of the last complete check: say the check may have missed pages


def _is_sitemap(r: Response) -> bool:
    return r.status == 200 and ("<urlset" in r.text or "<sitemapindex" in r.text)


def _fetch_sitemap(url: str, fetch: Fetcher, tries: int, wait: float) -> tuple[Response, int]:
    """Fetches a sitemap, trying again (wait, then 2x wait) on 429, 5xx, a timeout or a body that is not a sitemap. A 404 is final."""
    for n in range(1, tries + 1):
        r = fetch(url)
        if _is_sitemap(r) or n == tries or not (r.status in (0, 200, 429) or r.status >= 500):
            return r, n
        if wait:
            time.sleep(wait * 2 ** (n - 1))
    raise AssertionError("unreachable")


def _why(r: Response) -> str:
    if r.status == 0:
        return r.text or "no answer"
    return f"HTTP {r.status}" + (", not a sitemap" if r.status == 200 else "")


def read_sitemaps(site: str, fetch: Fetcher, *, tries: int = SITEMAP_TRIES, wait: float = 2.0
                  ) -> tuple[list[tuple[str, str | None]], list[dict]]:
    """(url, lastmod) for every page in the Yoast sitemap index (or a plain sitemap), and every sitemap that could not be read
    after `tries` tries ({url, status, tries, why}), so a scan never quietly checks only part of the site."""
    def locs(xml: str):
        return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>(?:\s*<lastmod>\s*([^<\s]+)\s*</lastmod>)?", xml)

    out, seen, problems = [], set(), []
    unread = lambda u, r, n: problems.append({"url": u, "status": r.status, "tries": n, "why": _why(r)})  # noqa: E731
    for index in (f"{site}/sitemap_index.xml", f"{site}/sitemap.xml"):
        r, n = _fetch_sitemap(index, fetch, tries, wait)
        if not _is_sitemap(r):
            if r.status != 404:
                unread(index, r, n)
            continue
        problems = []  # the first index failed but this one works: nothing is missing
        children = [u for u, _ in locs(r.text)] if "<sitemapindex" in r.text else [index]
        for child in children:
            body = r.text
            if child != index:
                c, n = _fetch_sitemap(child, fetch, tries, wait)
                if not _is_sitemap(c):
                    unread(child, c, n)
                    continue
                body = c.text
            for u, lm in locs(body):
                if u not in seen and not u.endswith(".xml"):
                    seen.add(u)
                    out.append((u, lm or None))
        break
    else:
        if not problems:  # both answered 404: there is no sitemap to read
            problems.append({"url": f"{site}/sitemap_index.xml", "status": 404, "tries": 1, "why": "HTTP 404 (and no sitemap.xml)"})
    return out, problems


def sitemap_urls(site: str, fetch: Fetcher) -> list[tuple[str, str | None]]:
    """(url, lastmod) for every page in the sitemap; read_sitemaps also says which sitemaps could not be read."""
    return read_sitemaps(site, fetch)[0]


@dataclass
class Finding:
    severity: str  # high | medium | low
    rule: str
    page: str
    evidence: str
    fix: str


def _age_days(lastmod: str | None, now: datetime) -> int | None:
    if not lastmod:
        return None
    try:
        dt = datetime.fromisoformat(lastmod.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (now - (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))).days


def page_findings(pg: Page, now: datetime) -> list[Finding]:
    f: list[Finding] = []
    add = lambda sev, rule, ev, fix: f.append(Finding(sev, rule, pg.url, ev, fix))  # noqa: E731
    if pg.status != 200:
        add("high", "page-not-ok", f"HTTP {pg.status}", "Fix or remove the page from the sitemap.")
        return f
    if re.search(r"/sample-page/?$|/hello-world/?$", pg.url):
        add("high", "wordpress-default-page", "WordPress's default page is listed for Google", "Delete it or set it to noindex.")
    if re.search(r"/elementor-hf/|/elementor_library/", pg.url):
        add("high", "template-in-sitemap", "a theme building block (header/footer template) is listed for Google as a page",
            "In Yoast, hide this content type from search results so it leaves the sitemap.")
        return f  # its other problems don't matter: it should not be a page at all
    if "/author/" in pg.url:
        add("medium", "author-archive", "posts are credited to the login name in the URL",
            "Credit posts to a real person or 'DTJ Team' (AI answers weigh who wrote it); hide author archives in Yoast.")
        return f
    if "noindex" in pg.robots.lower():
        add("high", "noindex-in-sitemap", f"robots meta: {pg.robots}", "Either remove it from the sitemap or allow indexing.")
    if not pg.title:
        add("high", "title-missing", "no <title>", "Add a title that says what the page answers.")
    elif len(pg.title) > TITLE_MAX:
        add("low", "title-long", f"{len(pg.title)} characters: {pg.title!r}", f"Keep it under {TITLE_MAX} so Google shows it whole.")
    if not pg.description:
        add("medium", "description-missing", "no meta description", "Write one: the page's answer in one sentence.")
    elif not DESC_MIN <= len(pg.description) <= DESC_MAX:
        add("low", "description-length", f"{len(pg.description)} characters", f"Aim for {DESC_MIN}-{DESC_MAX} characters.")
    if re.search(r"\bWe Helping\b", pg.description):
        add("medium", "description-grammar", repr(pg.description[:120]), "Fix the grammar: it is the first line people read on Google.")
    if len(pg.h1) != 1:
        add("medium", "h1-count", f"{len(pg.h1)} H1 headings", "Use exactly one H1 that matches the search question.")
    if pg.canonical and unquote(pg.canonical).rstrip("/").lower() != unquote(pg.url).rstrip("/").lower():
        add("medium", "canonical-elsewhere", f"canonical -> {pg.canonical}", "Check this page is meant to point elsewhere.")
    if "INVALID_JSON_LD" in pg.schema_types:
        add("high", "schema-broken", "a JSON-LD block does not parse", "Fix the structured data; AI engines and Google skip it.")
    if not pg.questions:
        add("medium", "no-question-headings", "no heading ends with '?'",
            "Add 3-5 real founder questions as headings, each answered in the first 1-2 sentences (AI answer engines lift these).")
    elif "FAQPage" not in pg.schema_types:
        add("low", "faq-schema-missing", f"{len(pg.questions)} question headings, no FAQPage data", "Add FAQPage structured data.")
    if pg.words < THIN_WORDS:
        add("medium", "thin-page", f"{pg.words} words", "Say more that answers the founder's question (proof, steps, FAQs).")
    if pg.img_no_alt:
        add("low", "images-without-alt", f"{pg.img_no_alt} of {pg.img_total} images have no alt text", "Describe each image in a few words.")
    age = _age_days(pg.lastmod, now)
    if age is not None and age > STALE_DAYS:
        add("low", "stale", f"last updated {age} days ago ({pg.lastmod[:10]})", "Refresh it: AI engines prefer recent pages.")
    return f


def site_findings(site: str, pages: list[Page], fetch: Fetcher) -> list[Finding]:
    f: list[Finding] = []
    llms = fetch(f"{site}/llms.txt")
    if llms.status != 200 or "text/plain" not in llms.content_type and "markdown" not in llms.content_type:
        f.append(Finding("medium", "llms-txt-missing", f"{site}/llms.txt", f"HTTP {llms.status}", "Turn on Yoast's llms.txt."))
    elif re.search(r"#\s?1\b|\bbest\b", llms.text.split("\n", 3)[0], re.I):
        f.append(Finding("medium", "llms-txt-claim", f"{site}/llms.txt", llms.text.split("\n", 1)[0][:120],
                         "The first line AI engines read makes a ranking claim we cannot prove; use a plain description."))
    home = next((p for p in pages if p.url.rstrip("/") == site), None)
    if home and not {"Organization", "LocalBusiness", "ProfessionalService"} & set(home.schema_types):
        f.append(Finding("medium", "entity-schema-missing", home.url, f"schema types: {home.schema_types}",
                         "Add Organization data (name, logo, sameAs links to Google Business Profile, LinkedIn, Clutch) and one "
                         "LocalBusiness entry per real office (Rajkot, Ahmedabad) with the exact address and phone on the contact page."))
    posts = [p for p in pages if p.lastmod]
    newest = max((p.lastmod for p in posts), default=None)
    if newest:
        age = _age_days(newest, datetime.now(timezone.utc))
        if age is not None and age > 45:
            f.append(Finding("medium", "no-new-content", site, f"newest page change {newest[:10]} ({age} days ago)",
                             "Publish answer articles regularly (this engine drafts one a week)."))
    return f


def coverage(urls: int, problems: list[dict], previous_pages: int | None) -> dict:
    """Did the check read the whole site? Unreadable sitemaps, and far fewer pages than the last complete check, both say no."""
    fewer = bool(previous_pages) and urls < previous_pages * DROP_SHARE
    return {"complete": not problems and not fewer, "pages_read": urls, "previous_pages": previous_pages,
            "fewer_than_before": fewer, "unreadable_sitemaps": problems}


def scan(site: str, fetch: Fetcher = http_fetch, *, max_pages: int = MAX_PAGES, delay: float = 0.5,
         now: datetime | None = None, previous_pages: int | None = None, retry_wait: float = 2.0) -> dict:
    """previous_pages: pages_in_sitemap of the last complete check, to notice when far fewer pages were read this time."""
    now = now or datetime.now(timezone.utc)
    urls, problems = read_sitemaps(site, fetch, wait=retry_wait)
    urls = urls[:max_pages]
    pages: list[Page] = []
    for i, (url, lastmod) in enumerate(urls):
        if i and delay:
            time.sleep(delay)  # polite: one page at a time
        r = fetch(url)
        pages.append(parse_page(url, r.text, r.status, lastmod) if r.status == 200 else Page(url=url, status=r.status, lastmod=lastmod))
    findings = [x for p in pages for x in page_findings(p, now)] + site_findings(site, pages, fetch)
    findings += [Finding("high", "sitemap-unreadable", p["url"], f"{p['why']} after {p['tries']} tries",
                         "The pages listed in this sitemap were not checked, so this report is incomplete. Run the check again; if it "
                         "keeps failing, open the sitemap in a browser and check Yoast and the hosting.") for p in problems]
    findings.sort(key=lambda x: (SEVERITY_ORDER[x.severity], x.rule, x.page))
    return {
        "site": site, "scanned_at": now.isoformat(), "pages_in_sitemap": len(urls), "pages": [asdict(p) for p in pages],
        "coverage": coverage(len(urls), problems, previous_pages),
        "findings": [asdict(x) for x in findings],
        "counts": {s: sum(1 for x in findings if x.severity == s) for s in SEVERITY_ORDER},
        "source": f"{site}/sitemap_index.xml and each listed page, fetched by site_scan.py",
    }
