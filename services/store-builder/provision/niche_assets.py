"""Read the brand's niche before any picture is made: what 5 D2C competitors show on their own websites (Harsh, 22 Oct 2026:
"ensuring you dont generate bad results you will search top 5 competitors in that brand niche, the competitors must not be titans
... our competitors will be those brands which does heavy meta marketing and relies on meta ads only such as blue tea india ... and
then from their websites you will download the banners, 2-3 product images and then you will analyze all the brands assets and then
plan the images").

The Claude session picks the competitors (a web search: D2C brands that live on Meta ads, never the category's giants); this module
reads each one, read only and no login:
    python -m provision.niche_assets https://bluetea.co.in https://brand2.com ... --out <dir> --niche "herbal tea for daily calm"
        per competitor: its home page banners (up to 4, the widest size), its top 3 products (best sellers on a Shopify store, else the
        product pages its sitemap lists) with price, compare-at price and 2-3 pictures, its name and theme colours; files under
        <dir>/<host>/banners/ and <dir>/<host>/products/<handle>/, one contact sheet per brand (<dir>/<host>/sheet.jpg, to look at
        the brand in one picture) and <dir>/niche.json with every competitor and the niche's price range.
        Exit 0 = at least 3 competitors were read, 1 = fewer (each failure is printed).

What the pictures are for: study only. A session looks at them to plan our own pictures (light, background, angles, how the
product sits in the frame, colours); they are never uploaded to the picture maker, never put in a store and never shown as ours.
The prices give realistic sample prices (sample_price) for products that have none (Harsh, 22 Oct 2026: "you can add any price,
compare price, etc. because we will change it later"); the store job tags every such price dtj-sample-price.
Every competitor costs at most MAX_REQUESTS requests, a short pause apart; a 429, a 5xx or no answer is tried again up to 3 times.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from .brand_copy import _NOT_PRODUCT_PICTURE, _meta, _text, base_url, site_product, site_product_urls

Getter = Callable[[str], "tuple[int, str, bytes]"]  # url -> (status, final url, body)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
MAX_REQUESTS = 25      # per competitor
MAX_BANNERS = 4
MAX_PICTURES = 3       # per product
BANNER_WIDTH = 1600    # what a Shopify CDN banner is asked for
PICTURE_WIDTH = 1200
MIN_BANNER_WIDTH = 1200
SHEET_WIDTH = 1600
NOTE = "competitors' pictures are for study only: never uploaded to the picture maker and never put in the store"
SAMPLE_PRICE_TAG = "dtj-sample-price"
# a product link on a collection page, as page_builder.store_scan reads it
PRODUCT_LINK = re.compile(r'href="(?:https?://[^"/]+)?(?:/[a-z]{2}(?:-[a-z]{2})?)?/(?:collections/[^"/]+/)?products/([a-z0-9][a-z0-9-]*)[?"#]', re.I)
_HERO = re.compile(r"hero|slide|slider|slideshow|banner|carousel|swiper|masthead", re.I)
_NOT_HERO = re.compile(r"product|collection|featured|grid|card|logo|footer|header|announcement|review|testimonial|instagram|blog", re.I)
_TAG = re.compile(r"<(img|source)\b([^>]*)>", re.I)
_SECTION = re.compile(r"<(?:section|div)\b[^>]*(?:class|id)=\"[^\"]*(?:shopify-section|section|hero|banner|slide)[^\"]*\"[^>]*>", re.I)
_STYLE_URL = re.compile(r"background(?:-image)?\s*:[^;\"]*url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", re.I)
_COLOUR = re.compile(r"--color-[\w-]+\s*:\s*(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3})")
_SCRIPT = re.compile(r"<script\b[\s\S]*?</script>", re.I)


class CompetitorError(Exception):
    """The competitor's site could not be read at all; the message says why, in plain words."""


# ------------------------------------------------------------------------------------------------------------------- fetching
def http_get(url: str) -> tuple[int, str, bytes]:
    """One read-only request with a browser's User-Agent: (status, final url, body); 0 = no answer."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-IN,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, url, b""
    except (urllib.error.URLError, OSError, ValueError):
        return 0, url, b""


def retrying(get: Getter, sleep: Callable[[float], None] = time.sleep) -> Getter:
    """The same getter, with a 429, a 5xx or no answer tried again up to 3 times (2, 4, 6 s apart; CLAUDE.md self-healing)."""
    def got(url: str) -> tuple[int, str, bytes]:
        for attempt in range(4):
            status, final, body = get(url)
            if status == 429 or status == 0 or status >= 500:
                if attempt < 3:
                    sleep(2 * (attempt + 1))
                    continue
            return status, final, body
        return status, final, body
    return got


class Budget:
    """At most `limit` requests for one competitor, `pause` seconds apart; past the limit every request answers (0, url, b"")."""

    def __init__(self, get: Getter, limit: int = MAX_REQUESTS, pause: Callable[[], None] = lambda: time.sleep(0.4)):
        self.get, self.limit, self.pause, self.used = get, limit, pause, 0

    def __call__(self, url: str) -> tuple[int, str, bytes]:
        if self.used >= self.limit:
            return 0, url, b""
        if self.used:
            self.pause()
        self.used += 1
        return self.get(url)

    @property
    def spent(self) -> bool:
        return self.used >= self.limit


# ------------------------------------------------------------------------------------------------------------------- pictures
def absolute(src: str, base: str) -> str:
    src = html.unescape(src.strip())
    if src.startswith("//"):
        return "https:" + src
    return urljoin(base + "/", src)


def is_shopify_cdn(url: str) -> bool:
    return "cdn.shopify.com" in url or "/cdn/shop/" in url


def sized(url: str, width: int) -> str:
    """A Shopify CDN picture asked for at `width` (its own resizer); any other address unchanged."""
    if not is_shopify_cdn(url):
        return url
    u = urlparse(url)
    path = re.sub(r"_(\d+x\d*|x\d+)(@\dx)?(?=\.[A-Za-z0-9]+$)", "", u.path)  # the old "_1200x.jpg" size in the name
    query = [(k, v) for k, v in parse_qsl(u.query) if k not in ("width", "height", "crop")] + [("width", str(width))]
    return urlunparse(u._replace(path=path, query=urlencode(query)))


def _attr(attrs: str, name: str) -> str:
    m = re.search(rf'\b{name}\s*=\s*"([^"]*)"', attrs, re.I) or re.search(rf"\b{name}\s*=\s*'([^']*)'", attrs, re.I)
    return m.group(1) if m else ""


def _widest(attrs: str) -> tuple[str, int]:
    """The widest picture an <img> or <source> offers: from srcset (or data-srcset), else src (or data-src) and its width."""
    best, width = "", 0
    for key in ("srcset", "data-srcset"):
        for url, w in re.findall(r"(\S+)\s+(\d+)w", _attr(attrs, key)):
            if int(w) > width:
                best, width = url.rstrip(","), int(w)
    if not best:
        best = _attr(attrs, "src") or _attr(attrs, "data-src")
        w, m = _attr(attrs, "width"), re.search(r"[?&]width=(\d+)", best)
        width = int(w) if w.isdigit() else int(m.group(1)) if m else 0
    return best, width


def _section_before(page: str, at: int) -> str:
    """The opening tag of the section a picture sits in (the nearest section-like tag before it)."""
    last = None
    for m in _SECTION.finditer(page, 0, at):
        last = m
    return last.group(0) if last else ""


def banners_of(page: str, base: str, limit: int = MAX_BANNERS) -> list[str]:
    """The home page's banner pictures in page order: a hero / slideshow / banner section's pictures, or any picture offered at
    MIN_BANNER_WIDTH or wider outside a product grid; never a logo or an icon; og:image only when nothing else is found."""
    page = _SCRIPT.sub("", page)
    found: list[str] = []
    seen: set[str] = set()

    def keep(src: str) -> None:
        if not src or src.startswith("data:"):
            return
        url = absolute(src, base)
        key = urlparse(url).path.lower()
        name = Path(key).name
        if key in seen or _NOT_PRODUCT_PICTURE.search(name) or not re.search(r"\.(jpe?g|png|webp|avif|gif)$", name):
            return
        seen.add(key)
        found.append(sized(url, BANNER_WIDTH))

    for m in _TAG.finditer(page):
        attrs = m.group(2)
        if re.search(r"logo|icon", _attr(attrs, "class") + " " + _attr(attrs, "alt"), re.I):
            continue
        src, width = _widest(attrs)
        section = _section_before(page, m.start())
        hero = bool(_HERO.search(section))
        if hero or (width >= MIN_BANNER_WIDTH and not _NOT_HERO.search(section)):
            keep(src)
        if len(found) >= limit:
            return found
    for m in _STYLE_URL.finditer(page):  # a hero drawn as a background
        if _HERO.search(_section_before(page, m.start())):
            keep(m.group(1))
        if len(found) >= limit:
            return found
    if not found:
        keep(_meta(page, "og:image") or "")
    return found[:limit]


def _kind(body: bytes) -> str | None:
    """A picture's file type from its first bytes (a page or an error page is not a picture)."""
    if body[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return ".webp"
    if body[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if body[4:12] in (b"ftypavif", b"ftypavis"):
        return ".avif"
    return None


def download(url: str, folder: Path, stem: str, get: Getter) -> str | None:
    status, _, body = get(url)
    ext = _kind(body) if status == 200 else None
    if not ext:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{stem}{ext}"
    path.write_bytes(body)
    return str(path)


# ------------------------------------------------------------------------------------------------------------------- one competitor
def _money(v) -> float | None:
    try:
        n = float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def colours_of(page: str, limit: int = 10) -> list[str]:
    """The theme's colour settings as the page's CSS variables carry them (Shopify themes: --color-...), as #rrggbb."""
    out: list[str] = []
    for value in _COLOUR.findall(page):
        if value.startswith("#"):
            hexa = value[1:]
            hexa = "".join(c * 2 for c in hexa) if len(hexa) == 3 else hexa
        else:
            parts = [int(x) for x in re.findall(r"\d+", value)]
            if any(x > 255 for x in parts):
                continue
            hexa = "".join(f"{x:02x}" for x in parts)
        c = "#" + hexa.lower()
        if c not in out:
            out.append(c)
        if len(out) >= limit:
            break
    return out


def _host(base: str) -> str:
    return re.sub(r"[^a-z0-9.-]+", "-", urlparse(base).netloc.lower().removeprefix("www.")) or "site"


def _shopify_products(base: str, get: Getter, count: int) -> list[dict] | None:
    """The store's best sellers (its /collections/all page sorted by best-selling; the product list's order when that page is hidden),
    from /products.json; None when the site is not a Shopify store."""
    status, _, body = get(f"{base}/products.json?limit=250")
    try:
        items = json.loads(body.decode("utf-8")).get("products") if status == 200 else None
    except (ValueError, UnicodeDecodeError, AttributeError):
        items = None
    if not isinstance(items, list):
        return None
    by_handle = {p["handle"]: p for p in items if p.get("handle") and p.get("variants")}
    order: list[str] = []
    status, _, body = get(f"{base}/collections/all?sort_by=best-selling")
    if status == 200:
        for h in PRODUCT_LINK.findall(body.decode("utf-8", "replace")):
            if h.lower() in by_handle and h.lower() not in order:
                order.append(h.lower())
    order += [h for h in by_handle if h not in order]
    return [by_handle[h] for h in order[:count]]


def read_competitor(url: str, out: Path, get: Getter = http_get, max_products: int = 3, *,
                    pause: Callable[[], None] = lambda: time.sleep(0.4), limit: int = MAX_REQUESTS) -> dict:
    """One competitor's banners, top products (price, compare-at price, 2-3 pictures), name and colours, downloaded under
    out/<host>/. Raises CompetitorError when its home page does not answer."""
    base = base_url(url)
    budget = Budget(retrying(get) if get is http_get else get, limit, pause)
    status, final, body = budget(base + "/")
    if status != 200 or not body:
        raise CompetitorError(f"{base} did not answer ({status or 'no answer'})")
    base = base_url(final or base)  # brand.com -> www.brand.com
    home = body.decode("utf-8", "replace")
    title = re.search(r"<title[^>]*>([\s\S]*?)</title>", home, re.I)
    name = (_meta(home, "og:site_name") or (_text(title.group(1)).split("|")[0].split(" - ")[0].strip() if title else "")
            or urlparse(base).netloc)
    host = _host(base)
    folder = out / host
    problems: list[str] = []
    banners = []
    for i, src in enumerate(banners_of(home, base), 1):
        got = download(src, folder / "banners", str(i), budget)
        if got:
            banners.append(got)
        else:
            problems.append(f"banner {src[:120]} could not be downloaded")
    if not banners:
        problems.append("no banner found on the home page")
    products: list[dict] = []
    shop = _shopify_products(base, budget, max_products)
    if shop is not None:
        platform = "shopify"
        for p in shop:
            v = p["variants"][0]
            price, compare = _money(v.get("price")), _money(v.get("compare_at_price"))
            pics = []
            for i, img in enumerate((p.get("images") or [])[:MAX_PICTURES], 1):
                got = download(sized(absolute(str(img.get("src") or ""), base), PICTURE_WIDTH), folder / "products" / p["handle"], str(i), budget)
                if got:
                    pics.append(got)
            products.append({"title": html.unescape(str(p.get("title") or p["handle"])), "handle": p["handle"],
                             "url": f"{base}/products/{p['handle']}", "price": price,
                             "compare_at_price": compare if compare and price and compare > price else None,
                             "product_type": p.get("product_type") or "", "pictures": pics})
    else:
        platform = "website"
        for page_url in site_product_urls(base, budget):
            if len(products) >= max_products or budget.spent:
                break
            st, _, pb = budget(page_url)
            item = site_product(page_url, pb.decode("utf-8", "replace"), name) if st == 200 else None
            if not item:
                continue
            pics = []
            for i, img in enumerate(item["images"][:MAX_PICTURES], 1):
                got = download(sized(img["src"], PICTURE_WIDTH), folder / "products" / item["handle"], str(i), budget)
                if got:
                    pics.append(got)
            price = None if item.get("price_needed") else _money(item["variants"][0].get("price"))
            products.append({"title": item["title"], "handle": item["handle"], "url": page_url, "price": price,
                             "compare_at_price": None, "product_type": "", "pictures": pics})
    if not products:
        problems.append("no products could be read")
    for p in products:
        if not p["pictures"]:
            problems.append(f"{p['title']}: no picture could be downloaded")
    if budget.spent:
        problems.append(f"stopped at {limit} requests (this competitor's limit)")
    return {"name": html.unescape(name)[:120], "url": base, "host": host, "platform": platform, "colours": colours_of(home),
            "banners": banners, "products": products, "requests": budget.used, "problems": problems}


# ------------------------------------------------------------------------------------------------------------------- the niche
def price_range(competitors: list[dict]) -> dict:
    """The niche's prices from every competitor product that shows one (a number from their own pages, nothing estimated)."""
    prices = [p["price"] for c in competitors for p in c["products"] if p.get("price")]
    ratios = [p["compare_at_price"] / p["price"] for c in competitors for p in c["products"]
              if p.get("price") and p.get("compare_at_price") and p["compare_at_price"] > p["price"]]
    if not prices:
        return {"min": None, "median": None, "max": None, "compare_ratio_median": None, "count": 0}
    return {"min": min(prices), "median": statistics.median(prices), "max": max(prices),
            "compare_ratio_median": round(statistics.median(ratios), 3) if ratios else None, "count": len(prices)}


def contact_sheet(comp: dict, path: Path, width: int = SHEET_WIDTH) -> str | None:
    """One picture of a competitor: its banners on top, its product pictures under them, its name and prices in the corner
    (Pillow; None when Pillow is missing or no picture opens)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    rows: list[list] = []
    for group, per_row in ((comp["banners"], 2), ([x for p in comp["products"] for x in p["pictures"]], 5)):
        tiles = []
        for f in group:
            try:
                with Image.open(f) as raw:
                    im = raw.convert("RGB")
            except Exception:  # noqa: BLE001 - a picture Pillow cannot open (avif without the plugin, a broken file) is left out
                continue
            tile_w = width // per_row  # banners two a row (half as tall as wide), product pictures five a row
            im.thumbnail((tile_w - 8, tile_w if per_row > 2 else tile_w // 2), Image.LANCZOS)
            tiles.append(im)
        for i in range(0, len(tiles), per_row):
            rows.append(tiles[i:i + per_row])
    if not rows:
        return None
    head = 40
    height = head + sum(max(t.height for t in row) + 8 for row in rows)
    sheet = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(sheet)
    prices = ", ".join(f"{p['price']:g}" for p in comp["products"] if p.get("price"))
    draw.text((8, 12), f"{comp['name']} ({comp['host']})" + (f"  prices: {prices}" if prices else ""), fill="black")
    y = head
    for row in rows:
        x = 4
        for t in row:
            sheet.paste(t, (x, y))
            x += t.width + 8
        y += max(t.height for t in row) + 8
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, "JPEG", quality=85)
    return str(path)


def research(urls: list[str], out: Path, get: Getter = http_get, niche: str = "", *,
             pause: Callable[[], None] = lambda: time.sleep(0.4), now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> dict:
    """Every competitor read (one that fails is listed under problems; the rest go on), a contact sheet each, and niche.json."""
    out.mkdir(parents=True, exist_ok=True)
    competitors, problems = [], []
    for url in urls:
        try:
            comp = read_competitor(url, out, get, pause=pause)
        except (CompetitorError, ValueError) as exc:
            problems.append(f"{url}: {exc}")
            continue
        if not comp["products"] and not comp["banners"]:
            problems.append(f"{url}: nothing could be read ({'; '.join(comp['problems'][:3])})")
            continue
        comp["sheet"] = contact_sheet(comp, out / comp["host"] / "sheet.jpg")
        competitors.append(comp)
    sheets = "made" if any(c.get("sheet") for c in competitors) else "not made (Pillow is missing or no picture opened)"
    data = {"niche": niche, "made_at": now().strftime("%Y-%m-%dT%H:%M:%SZ"), "competitors": competitors,
            "prices": price_range(competitors), "sheets": sheets, "problems": problems, "note": NOTE}
    (out / "niche.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return data


# ------------------------------------------------------------------------------------------------------------------- sample prices
def retail(value: float) -> int:
    """The nearest Indian retail ending: ...49 or ...99 (299, 349, 999, 1049); never below 49."""
    v = max(float(value), 49.0)
    h = int(v // 100) * 100
    return min((c for c in (h - 1, h + 49, h + 99) if c >= 49), key=lambda c: (abs(c - v), c))


def sample_price(prices: dict, rank: int, count: int) -> tuple[str, str]:
    """A realistic SAMPLE price and compare-at price for our product number `rank` (1-based) of `count`: spread evenly from the
    niche's lowest price to its median, rounded to a retail ending; compare-at = price x the niche's median compare ratio (x1.25
    when no competitor shows one), above the price. Harsh, 22 Oct 2026: "you can add any price, compare price, etc. because we will
    change it later": the store job tags every such product dtj-sample-price, so each one is found and replaced."""
    lo, mid = prices.get("min"), prices.get("median")
    if not lo or not mid:
        raise ValueError("no competitor prices to base a sample price on: read the niche first (provision.niche_assets)")
    share = (rank - 1) / (count - 1) if count > 1 else 0.5
    price = retail(lo + (mid - lo) * min(max(share, 0.0), 1.0))
    ratio = prices.get("compare_ratio_median") or 1.25
    compare = retail(price * max(ratio, 1.05))
    while compare <= price:
        compare = retail(compare + 50)
    return f"{price}.00", f"{compare}.00"


# ------------------------------------------------------------------------------------------------------------------- command line
def main(argv=None, get: Getter = http_get) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+", help="the competitors' websites (D2C brands that live on Meta ads, not the category's giants)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--niche", default="", help="one line: what the brand sells")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data = research(a.urls, a.out, get, a.niche)
    for c in data["competitors"]:
        prices = ", ".join(f"{p['price']:g}" for p in c["products"] if p.get("price")) or "no prices"
        print(f"{c['name']} ({c['host']}, {c['platform']}): {len(c['banners'])} banners, {len(c['products'])} products "
              f"({sum(len(p['pictures']) for p in c['products'])} pictures; {prices}), {c['requests']} requests")
        for x in c["problems"]:
            print(f"  - {x}")
    for x in data["problems"]:
        print(f"not read: {x}")
    pr = data["prices"]
    print(f"prices: {pr['count']} found, {pr['min']:g} to {pr['max']:g}, median {pr['median']:g}, compare ratio "
          f"{pr['compare_ratio_median'] or 'not shown'}" if pr["count"] else "prices: none found")
    print(f"contact sheets: {data['sheets']}; {a.out / 'niche.json'}")
    return 0 if len(data["competitors"]) >= 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
