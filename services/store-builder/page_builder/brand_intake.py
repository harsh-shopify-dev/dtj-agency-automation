"""Brand intake for a redesign: everything public about a client's store in ONE folder, before any design starts (Harsh, 19 Oct 2026:
"a scraper which will scrape all the product images max to only 20 products ... and a file that contains the details of the brand and brand
color palette so when a client comes for a redesign then we just get all the data and then start designing").

    cd services/store-builder
    python -m page_builder.brand_intake https://client-store.com --client ../../.work/clients/<client> [--product "Turmeric Latte Mix"]

--product names the product being designed: its words pick that product's pictures first. On a Shopify store its product comes first
among the 20; on any other site (WordPress and the like: no public products.json) the site's own search and links lead to the
matching product pages, and their pictures (the full-size file, not the thumbnails) are saved like a Shopify product's (Harsh,
19 Oct 2026: "the scraping should have applied and uploaded other images").

Writes <client>/intake/:
    images/products/<handle>/<store file name>   every picture of at most 20 products (the first 20 the store lists)
    images/logo.<ext>, images/site/*, images/collections/*   the logo, the share picture and the collection pictures
    videos/products/<handle>/*, videos/site/*   each product's videos (a 720p copy) and the home page's own videos, at most 400 MB in all;
                        YouTube / Vimeo videos are listed as links, not downloaded
    brand-intake.json   every fact with where it came from: shop, products, collections, policies, fonts, colours, the palette
    BRAND.md            the same, readable: the page a designer (or Claude) starts from
    brand.json          a DRAFT brand profile for the page builder (brand-profile schema); the guessed fields are listed in BRAND.md
    palette.png         the colour candidates and the 12-step scales (palette.py) at a glance
    products.png        the first picture of each product

How the colours are chosen (the researched palette method, palette.py): candidates come from the theme's own colour settings (the CSS
variables the theme prints), the logo and the product pictures, each with its source and share. The brand colour is the strongest
saturated candidate (theme button, then logo, then packs); the accent is the next one at least 40 degrees round the colour wheel and
not a dirt colour for the category. A person confirms both before designing.
Reads only public pages and never writes to the store. Personal data (emails, phone numbers) is not collected. Exit 0 = done, 1 = the
site could not be read.
"""
from __future__ import annotations

import argparse
import colorsys
import html
import io
import json
import os
import re
import signal
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

from . import palette
from .progress import Progress
from .fetch_product import as_text, file_name

Getter = Callable[[str], tuple[int, str, bytes]]
MAX_PRODUCTS = 20  # Harsh: "max to only 20 products"; a bigger catalogue is read up to here and the rest is only counted
POLITE_DELAY = 0.25  # seconds between requests: a client's store, not a load test
SOCIAL = ("instagram.com", "facebook.com", "youtube.com", "x.com", "twitter.com", "linkedin.com", "pinterest.", "wa.me", "whatsapp.com")
STATUS = re.compile(r"error|success|warning|stock|sale|badge|notice|alert|rating|star", re.I)  # theme colour names that are signals
POLICIES = ("shipping-policy", "refund-policy", "privacy-policy", "terms-of-service")
# what policy templates and generators leave behind; read in the policy's own words only (Freesoul, 19 Oct 2026: "{{" matched an app's
# script on the page, not the policy)
TEMPLATE_HINTS = ("[insert", "lorem ipsum", "[store name", "[your store", "[company name", "[your company")
VIDEO_HEIGHT = 720  # Harsh, 19 Oct 2026: "it should also download videos if available"; a 720p copy is enough to design with
VIDEO_BUDGET_MB = 400  # all videos of one intake together; the rest are listed, not downloaded
GENERIC_FONTS = {"inherit", "initial", "unset", "sans-serif", "serif", "monospace", "system-ui", "-apple-system", "arial", "helvetica",
                 "var", "cursive", "fantasy", "revert"}
CATEGORY_WORDS = {
    "beauty": r"serum|cream|face|skin|lip|makeup|kajal|sunscreen|moisturi|shampoo|conditioner|hair oil|cleanser|toner|perfume",
    "supplements": r"capsule|tablet|protein|vitamin|gumm|supplement|whey|collagen|omega|probiotic|electrolyte",
    "home-care": r"clean|detergent|toilet|floor|dish|laundry|freshener|disinfect|mop|scrub|kitchen|bathroom",
    "food": r"snack|tea\b|coffee|spice|masala|chocolate|sauce|honey|ghee|pickle|namkeen|cookie|millet|oil\b|flour",
    "apparel": r"shirt|kurta|dress|saree|jeans|shoe|sneaker|trouser|hoodie|jacket|lehenga|top\b|tee\b",
}


def _get(url: str) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (dtj-brand-intake/1)", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=20) as r:  # a stuck request is retried once, not waited on for a minute
        return r.status, r.geturl(), r.read()


def _safe_get(get: Getter, url: str) -> tuple[int, bytes]:
    try:
        status, _, body = get(url)
        return status, body
    except Exception:  # a missing page or a blocked request is a finding, not a crash
        return 0, b""


def _json(get: Getter, url: str) -> dict | None:
    status, body = _safe_get(get, url)
    if status != 200:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


# ------------------------------------------------------------------------------------------------ the home page
def read_home(base: str, page: str, css: str = "") -> dict:
    """Name, description, logo, share picture, socials, theme, currency and fonts from the home page's HTML (and the theme's stylesheet)."""
    meta = lambda prop: (re.search(rf'<meta[^>]+(?:property|name)="{prop}"[^>]+content="([^"]*)"', page, re.I) or [None, None])[1]  # noqa: E731
    title = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
    logo = None
    for tag in re.findall(r"<img[^>]+>", page, re.I):
        if re.search(r"logo", tag, re.I):
            src = re.search(r'\ssrc="([^"]+)"', tag)
            if src:
                logo = urljoin(base, html.unescape(src.group(1)))
                break
    socials = sorted({html.unescape(u) for u in re.findall(r'href="(https?://[^"]+)"', page) if any(s in u for s in SOCIAL)})
    theme = re.search(r'Shopify\.theme\s*=\s*(\{.*?\});', page)
    currency = re.search(r'Shopify\.currency\s*=\s*\{"active":"([A-Z]{3})"', page)
    fonts = {}
    for role in ("heading", "body"):
        found = re.search(rf"--font-{role}--?family:\s*([^;(]+);", page)  # Dawn: --font-heading-family, Horizon: --font-heading--family
        if found:
            fonts[role] = found.group(1).split(",")[0].strip().strip("\"'")
    if not fonts:  # a custom theme: the font its CSS uses most (Freesoul: "ESPark")
        used = Counter(f.split(",")[0].strip().strip("\"'") for f in re.findall(r"font-family\s*:\s*([^;}!]+)", page + css))
        named = [f for f, _ in used.most_common() if f and f.lower() not in GENERIC_FONTS and not f.lower().startswith("var(")]
        if named:
            fonts = {"heading": named[0], "body": named[1] if len(named) > 1 else named[0], "from": "the theme's CSS (most used font)"}
    return {
        "name": html.unescape(meta("og:site_name") or (title.group(1).split("|")[-1].split("–")[-1].strip() if title else "")),
        "title": html.unescape(title.group(1).strip()) if title else "",
        "description": html.unescape(meta("description") or meta("og:description") or ""),
        "share_picture": urljoin(base, html.unescape(meta("og:image"))) if meta("og:image") else None,
        "logo": logo,
        "socials": socials,
        "theme": json.loads(theme.group(1)).get("name") if theme else None,
        "currency": currency.group(1) if currency else None,
        "fonts": fonts,
    }


def theme_colours(page: str, css: str = "") -> list[dict]:
    """The colours the theme prints as CSS variables (Dawn writes '--color-button: 18,18,18', Horizon 'rgb(...)' or hex), most used first."""
    seen: Counter = Counter()
    names: dict[str, set] = {}
    for name, value in re.findall(r"(--[a-z0-9-]*colou?r[a-z0-9-]*)\s*:\s*([^;]+);", page, re.I):
        value = value.strip().lower()
        if m := re.fullmatch(r"#([0-9a-f]{6})", value):
            hexv = "#" + m.group(1).upper()
        elif m := re.search(r"(\d{1,3})[ ,]+(\d{1,3})[ ,]+(\d{1,3})", value):
            hexv = _hex(*(min(255, int(x)) for x in m.groups()))
        else:
            continue
        if STATUS.search(name):  # error red, success green, stock and sale colours are shop signals, not the brand
            continue
        seen[hexv] += 1
        names.setdefault(hexv, set()).add(name)
    # the button colour first: it is the theme's brand colour far more often than the most used one (a sale badge, a border grey)
    order = sorted(seen, key=lambda h: (not any("button" in n for n in names[h]), -seen[h]))
    out = [{"hex": h, "uses": seen[h], "names": sorted(names[h])[:6], "source": "theme CSS variables on the home page"} for h in order[:12]]
    # a custom theme keeps its colours in its stylesheet (Freesoul: a Tailwind build, no colour variables on the page): the colours its
    # rules paint with, most used first
    painted: Counter = Counter()
    for value in re.findall(r"(?:background(?:-color)?|(?<![a-z-])color|border-color|fill)\s*:\s*(#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\([^)]*\))", css):
        if value.startswith("#"):
            v = value[1:]
            painted["#" + ("".join(c * 2 for c in v) if len(v) == 3 else v).upper()] += 1
        elif m := re.search(r"(\d{1,3})[ ,]+(\d{1,3})[ ,]+(\d{1,3})", value):
            painted[_hex(*(min(255, int(x)) for x in m.groups()))] += 1
    out += [{"hex": h, "uses": n, "source": "the theme's stylesheet"} for h, n in painted.most_common(10) if h not in seen]
    return out


# ------------------------------------------------------------------------------------------------ pictures
def picture_colours(data: bytes, source: str, top: int = 5) -> list[dict]:
    """The main colours of one picture, its plain background left out (white, near-white, transparent)."""
    from PIL import Image  # noqa: PLC0415  (Pillow is in the venv; imported here so the module loads without it)
    head = data[:400].lstrip().lower()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in data[:2000].lower()):  # a drawn logo: read its fill colours
        text = data.decode("utf-8", "replace")
        found: Counter = Counter()
        for value in re.findall(r"(?:fill|stroke|stop-color)\s*[:=]\s*[\"']?\s*#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", text):
            value = "".join(ch * 2 for ch in value) if len(value) == 3 else value
            if value.upper() not in ("FFFFFF",):
                found["#" + value.upper()] += 1
        total = sum(found.values()) or 1
        return [{"hex": h, "share": round(n / total, 3), "source": source} for h, n in found.most_common(top)]
    try:
        im = Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        return []
    im.thumbnail((160, 160))
    counts: Counter = Counter()
    for r, g, b, a in im.getdata():
        if a < 128 or min(r, g, b) > 235:
            continue
        counts[(r // 16 * 16 + 8, g // 16 * 16 + 8, b // 16 * 16 + 8)] += 1
    total = sum(counts.values()) or 1
    return [{"hex": _hex(*c), "share": round(n / total, 3), "source": source} for c, n in counts.most_common(top)]


def _saturated(hexv: str) -> bool:
    L, C, _ = palette.oklch(hexv)
    return C >= 0.06 and 0.15 <= L <= 0.9  # dark brand colours (maroon, navy, forest) count: Freesoul's logo is #39000B


def _distinct(a: str, b: str) -> bool:
    """Two colours read as two: 40+ degrees apart on the wheel, or clearly lighter or darker (Freesoul pairs a deep maroon #39000B with a
    pink #D83B9E: close in hue, far apart in lightness)."""
    return palette.hue_gap(a, b) >= 40 or abs(palette.oklch(a)[0] - palette.oklch(b)[0]) >= 0.25


def choose_colours(candidates: list[dict], category: str) -> dict:
    """Brand colour = the first saturated candidate (theme, then logo, then packs); accent = the next one at least 40 degrees away that
    is not a dirt colour for the category. Text and background = the theme's darkest and lightest colours, else near-black and white."""
    def rank(c: dict, for_accent: bool) -> int:
        # brand colour: the theme's button, then the logo, then the packs, then any other theme colour. Accent: brand identity first (logo,
        # packs); the theme's other colours last, because they are often utility colours (a sale badge red, a warning yellow)
        button = c["source"].startswith("theme") and any("button" in n for n in c.get("names", []))
        order = ["logo", "product", "theme", "button"] if for_accent else ["button", "logo", "product", "theme"]
        kind = "button" if button else ("logo" if c["source"] == "the logo" else ("product" if c["source"].startswith("product") else "theme"))
        return order.index(kind)

    strong = [c for c in candidates if _saturated(c["hex"]) and c.get("products", 2) >= 2]  # one product's colour is not the brand's
    primary = min(strong, key=lambda c: rank(c, False)) if strong else None
    accent = None
    if primary:
        accent = next((c for c in sorted(strong, key=lambda c: rank(c, True))
                       if c is not primary and _distinct(c["hex"], primary["hex"]) and not palette.avoided(c["hex"], category)
                       and c.get("products", 2) >= 2), None)  # a colour on ONE product (a stray book cover) is not the brand's accent
    theme = [c["hex"] for c in candidates if c["source"].startswith("theme")]
    text = min(theme, key=palette.luminance) if theme else "#111111"
    background = max(theme, key=palette.luminance) if theme else "#FFFFFF"
    if palette.contrast(text, background) < 4.5:
        text, background = "#111111", "#FFFFFF"
    return {"primary": primary["hex"] if primary else None, "primary_from": primary["source"] if primary else None,
            "accent": accent["hex"] if accent else None, "accent_from": accent["source"] if accent else None,
            "text": text, "background": background}


# ------------------------------------------------------------------------------------------------ guesses (marked as guesses)
def guess_category(products: list[dict]) -> tuple[str, dict]:
    # the description too: a title can be just the brand ("TOILOVA") while the description says "toilet cleaning foam"
    text = " ".join(f"{p['title']} {p['type']} {' '.join(p['tags'])} {p.get('description', '')}" for p in products).lower()
    scores = {cat: len(re.findall(rx, text)) for cat, rx in CATEGORY_WORDS.items()}
    best = max(scores, key=scores.get) if any(scores.values()) else "other"
    return best, scores


def guess_price_tier(products: list[dict], currency: str | None) -> str | None:
    prices = sorted(p["price_min"] for p in products if p.get("price_min"))
    if not prices or (currency and currency != "INR"):
        return None
    median = prices[len(prices) // 2]
    return "value" if median < 500 else ("mid" if median < 2000 else "premium")


# ------------------------------------------------------------------------------------------------ the whole intake
STOP_WORDS = {"with", "and", "the", "for", "mix", "pack", "box", "new", "from", "buy", "online", "best"}
MIN_PICTURE_SIDE = 400  # smaller pictures are thumbnails or icons
MAX_SITE_PAGES = 6
MAX_SITE_PICTURES = 30


def product_words(name: str) -> list[str]:
    """The words that find a product: 'Turmeric Latte Mix with Saffron' -> ['turmeric', 'latte', 'saffron']."""
    return [w for w in re.findall(r"[a-z]+", (name or "").lower()) if len(w) >= 3 and w not in STOP_WORDS][:6]


def word_score(text: str, words: list[str]) -> int:
    t = (text or "").lower()
    return sum(1 for w in words if w in t)


def _needed(words: list[str]) -> int:
    return 1 if len(words) < 2 else 2


def site_product_pages(base: str, page: str, get: Getter, words: list[str]) -> list[str]:
    """A non-Shopify site's pages for this product: links on its home page and on its own search page (?s=, WordPress) whose
    address names at least two of the product's words, best match first."""
    host = urlparse(base).netloc
    sources = [page]
    status, body = _safe_get(get, f"{base}/?s={'+'.join(words)}")
    if status == 200:
        sources.append(body.decode("utf-8", "replace"))
    scores: dict[str, int] = {}
    for text in sources:
        for href in re.findall(r'<a[^>]+href="([^"#]+)"', text, re.I):
            link = urljoin(base + "/", html.unescape(href)).split("#")[0]
            u = urlparse(link)
            if u.netloc != host or u.query or re.search(r"\.(jpe?g|png|webp|gif|pdf|css|js|xml)$", u.path, re.I):
                continue
            slug = u.path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").replace("_", " ")
            score = word_score(slug, words)
            if score >= _needed(words):
                key = f"{u.scheme}://{u.netloc}{u.path.rstrip('/')}/"
                scores[key] = max(scores.get(key, 0), score)
    return [k for k, _ in sorted(scores.items(), key=lambda kv: (-kv[1], len(kv[0]), kv[0]))][:MAX_SITE_PAGES]  # the closest name first


def page_pictures(text: str, base: str, words: list[str]) -> list[str]:
    """The pictures of one product page: its share picture (og:image) and every picture whose file name names the product,
    as the full-size file (WordPress serves '-300x300' copies), never logos or icons, never another host's."""
    host = urlparse(base).netloc
    share = re.findall(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', text, re.I)
    share += re.findall(r'<meta[^>]+content="([^"]+)"[^>]+property="og:image"', text, re.I)
    tags = re.findall(r'<img[^>]+?(?:data-lazy-src|data-src|src)="([^"]+)"', text, re.I)
    found: list[str] = []
    for src in share + tags:
        u = urlparse(urljoin(base + "/", html.unescape(src.split()[0])))
        name = u.path.rsplit("/", 1)[-1].lower()
        if u.netloc != host or not re.search(r"\.(jpe?g|png|webp)$", name) or re.search(r"logo|icon|favicon|placeholder|sprite|flag|avatar", name):
            continue
        full = re.sub(r"-\d{2,4}x\d{2,4}(\.\w+)$", r"\1", f"{u.scheme}://{u.netloc}{u.path}")
        named = word_score(re.sub(r"[-_.]", " ", name), words) >= _needed(words)
        if (src in share or named) and full not in found:
            found.append(full)
    return found


def _big_enough(data: bytes) -> bool:
    try:
        from PIL import Image  # noqa: PLC0415
        with Image.open(io.BytesIO(data)) as im:
            return min(im.size) >= MIN_PICTURE_SIDE
    except Exception:  # noqa: BLE001  (not a picture Pillow can read)
        return False


def intake(url: str, out: Path, get: Getter = _get, max_products: int = MAX_PRODUCTS, delay: float = POLITE_DELAY,
           progress: Callable[..., None] | None = None, product: str = "") -> dict:
    """progress(stage, done, total), when given, hears where the work is (progress.py: the Telegram bar)."""
    tick = progress or (lambda *a: None)
    words = product_words(product)
    base = url if url.startswith("http") else "https://" + url
    base = f"{urlparse(base).scheme}://{urlparse(base).netloc}"
    pause = lambda: time.sleep(delay) if delay else None  # noqa: E731
    status, body = _safe_get(get, base + "/")
    if status != 200:
        raise RuntimeError(f"the home page did not answer ({status or 'no response'})")
    page = body.decode("utf-8", "replace")
    css = ""
    for link in re.findall(r'<link[^>]+href="([^"]+\.css[^"]*)"', page)[:12]:  # the theme's own stylesheets (not apps'), at most 3
        if "/cdn/shop/t/" in link and css.count("/*sheet*/") < 3:
            status, body = _safe_get(get, urljoin(base, "https:" + link if link.startswith("//") else link))
            if status == 200:
                css += "/*sheet*/" + body.decode("utf-8", "replace")
    shop = read_home(base, page, css)
    tick("read", 1, 2)
    images = out / "images"
    notes: list[str] = []
    candidates = theme_colours(page, css)
    video_bytes = [0]

    def save(src: str, dest: Path) -> bytes | None:
        if dest.is_file() and dest.stat().st_size:  # a re-run keeps what it already has
            return dest.read_bytes()
        link = "https:" + src if src.startswith("//") else src
        if ("cdn.shopify.com" in link or "/cdn/shop/" in link) and not re.search(r"/videos/|\.(mp4|mov|webm|m4v)(\?|$)", link):
            link += ("&" if "?" in link else "?") + "width=2048"  # the store's own CDN serves a sharp, bounded size
        status, data = 0, b""
        for attempt in range(2):  # one retry (CLAUDE.md self-healing): a slow CDN answer is usually fine the second time
            pause()
            status, data = _safe_get(get, link)
            if status == 200 and data:
                break
        if status != 200 or not data:
            notes.append(f"picture not downloaded: {src}")
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return data

    if shop["logo"]:
        data = save(shop["logo"], images / ("logo" + (Path(urlparse(shop["logo"]).path).suffix or ".png")))
        if data:
            candidates += picture_colours(data, "the logo", top=4)
    if shop["share_picture"]:
        save(shop["share_picture"], images / "site" / file_name(shop["share_picture"]))

    def save_video(src: str, dest: Path) -> str | None:
        if video_bytes[0] > VIDEO_BUDGET_MB * 1024 * 1024:
            notes.append(f"video not downloaded (the {VIDEO_BUDGET_MB} MB budget is used up): {src}")
            return None
        data = save(src, dest)
        if data:
            video_bytes[0] += len(data)
            return dest.name
        return None

    site_videos = []
    for src in re.findall(r'<(?:video|source)[^>]+src="([^"]+\.(?:mp4|webm|mov|m4v)[^"]*)"', page, re.I):  # videos on the home page
        name = save_video(urljoin(base, html.unescape(src)), out / "videos" / "site" / file_name(src))
        if name:
            site_videos.append(name)

    # products (Shopify's public catalogue): at most max_products, every picture of each
    feed = _json(get, base + "/products.json?limit=250")
    platform = "shopify" if feed is not None else "other"
    all_products = (feed or {}).get("products", [])
    if words:  # the product being designed first (a stable sort keeps the store's order otherwise)
        all_products = sorted(all_products, key=lambda p: -word_score(f"{p.get('title', '')} {p.get('handle', '')}", words))
    products = []
    todo = min(len(all_products), max_products)
    tick("products", 0, todo)
    packs: Counter = Counter()  # the pack colours, counted once per product: the colour most products share is the brand's
    for p in all_products[:max_products]:
        variants = p.get("variants", [])
        prices = [float(v["price"]) for v in variants if v.get("price")]
        compare = [float(v["compare_at_price"]) for v in variants if v.get("compare_at_price")]
        pics = [i["src"] for i in p.get("images", [])]
        saved = []
        for k, src in enumerate(pics):
            data = save(src, images / "products" / p["handle"] / file_name(src))
            if data:
                saved.append(file_name(src))
                if k == 0:
                    packs.update({c["hex"] for c in picture_colours(data, p["handle"], top=3)})
        videos, external = [], []
        detail = _json(get, f"{base}/products/{p['handle']}.js") if platform == "shopify" else None  # .js lists videos, products.json not
        for media in (detail or {}).get("media", []):
            if media.get("media_type") == "video":
                mp4 = [s for s in media.get("sources", []) if "mp4" in (s.get("format", "") + s.get("mime_type", ""))]
                if mp4:
                    best = min(mp4, key=lambda s: abs((s.get("height") or VIDEO_HEIGHT) - VIDEO_HEIGHT))
                    name = save_video(best["url"], out / "videos" / "products" / p["handle"] / file_name(best["url"]))
                    if name:
                        videos.append(name)
            elif media.get("media_type") == "external_video":
                host, vid = media.get("host", ""), media.get("external_id", "")
                external.append(f"https://www.youtube.com/watch?v={vid}" if "youtube" in host else (f"https://vimeo.com/{vid}" if "vimeo" in host else f"{host}:{vid}"))
        products.append({
            "videos": videos, "external_videos": external,
            "title": p.get("title", ""), "handle": p["handle"], "url": f"{base}/products/{p['handle']}", "type": p.get("product_type", ""),
            "vendor": p.get("vendor", ""), "tags": p.get("tags", []) if isinstance(p.get("tags"), list) else [t.strip() for t in str(p.get("tags", "")).split(",") if t.strip()],
            "price_min": min(prices) if prices else None, "price_max": max(prices) if prices else None,
            "compare_at_max": max(compare) if compare else None, "variants": len(variants),
            "options": [o.get("name") for o in p.get("options", [])], "pictures": saved,
            "description": as_text(p.get("body_html", ""))[:600],
        })
        tick("products", len(products), todo)
    candidates += [{"hex": h, "share": round(n / max(1, len(products)), 2), "products": n, "source": f"product pictures ({n} of {len(products)} products)"}
                   for h, n in packs.most_common(8)]
    if len(all_products) > max_products:
        notes.append(f"the store lists {len(all_products)}{'+' if len(all_products) == 250 else ''} products; only the first {max_products} were read")
    if platform == "other" and words:
        seen: set[str] = set()
        for link in site_product_pages(base, page, get, words):
            pause()
            status, body = _safe_get(get, link)
            if status != 200:
                continue
            text = body.decode("utf-8", "replace")
            title = html.unescape((re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S) or [None, ""])[1] or "")
            title = re.split(r"\s[|\u2013-]\s", re.sub(r"\s+", " ", title).strip())[0]
            slug = re.sub(r"[^a-z0-9-]+", "-", urlparse(link).path.rstrip("/").rsplit("/", 1)[-1].lower()).strip("-")[:60] or "page"
            saved = []
            for src in page_pictures(text, base, words):
                if src in seen or len(seen) >= MAX_SITE_PICTURES:
                    continue
                seen.add(src)
                dest = images / "products" / slug / file_name(src)
                data = save(src, dest)
                if data and _big_enough(data):
                    saved.append(dest.name)
                elif data:
                    dest.unlink(missing_ok=True)  # a thumbnail or an icon after all
            if saved:
                products.append({"videos": [], "external_videos": [], "title": title or slug, "handle": slug, "url": link, "type": "",
                                 "vendor": "", "tags": [], "price_min": None, "price_max": None, "compare_at_max": None, "variants": 0,
                                 "options": [], "pictures": saved, "description": ""})
            tick("products", len(products), MAX_SITE_PAGES)
        notes.append(f"not a Shopify store: {len(products)} product page(s) matching '{' '.join(words)}' were read through the site's "
                     "own search and links; check which pack each picture shows (a site often shows several versions)")
    elif platform == "other":
        notes.append("not a Shopify store (no public products.json): products and collections were not read, only the home page "
                     "(give --product to read the matching product pages)")

    tick("extras")
    collections = []
    for c in (_json(get, base + "/collections.json?limit=250") or {}).get("collections", []):
        entry = {"title": c.get("title"), "handle": c.get("handle"), "products": c.get("products_count"), "picture": None}
        if c.get("image") and c["image"].get("src"):
            if save(c["image"]["src"], images / "collections" / f"{c['handle']}{Path(urlparse(c['image']['src']).path).suffix or '.jpg'}"):
                entry["picture"] = f"images/collections/{c['handle']}{Path(urlparse(c['image']['src']).path).suffix or '.jpg'}"
        collections.append(entry)

    policies = {}
    for name in POLICIES:
        pause()
        status, body = _safe_get(get, f"{base}/policies/{name}")
        raw = body.decode("utf-8", "replace") if status == 200 else ""
        raw = re.sub(r"<(script|style|template|noscript)\b.*?</\1>", " ", raw, flags=re.S | re.I)  # apps print code and JSON on every page
        text = as_text(raw)
        policies[name] = {"found": status == 200, "url": f"{base}/policies/{name}",
                          "looks_like_a_template": any(h in text.lower() for h in TEMPLATE_HINTS) if text else None}

    category, scores = guess_category(products)
    tier = guess_price_tier(products, shop["currency"])
    chosen = choose_colours(candidates, category)
    pal = None
    if chosen["primary"]:
        pal = palette.roles(chosen["primary"], chosen["accent"] or chosen["primary"], category)
        notes += pal.pop("_warnings")
    else:
        notes.append("no saturated brand colour found in the theme, logo or packs: choose the brand colour by hand")

    result = {
        "source": base, "read_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "platform": platform, "shop": shop,
        "counts": {"products_listed": len(all_products), "products_read": len(products), "collections": len(collections),
                   "videos": sum(len(p["videos"]) for p in products) + len(site_videos), "video_mb": round(video_bytes[0] / 1048576, 1)},
        "site_videos": site_videos,
        "products": products, "collections": collections, "policies": policies,
        "colours": {"candidates": candidates, "chosen": chosen},
        "palette": {"ramps": pal.pop("_ramps"), "roles": pal} if pal else None,
        "guesses": {"category": category, "category_scores": scores, "price_tier": tier}, "notes": notes,
    }
    tick("write")
    _write(out, result)
    return result


def _write(out: Path, r: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "brand-intake.json").write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    chosen = r["colours"]["chosen"]
    colors = {k: chosen[k] for k in ("primary", "accent", "background", "text") if chosen.get(k)}
    brand = {"brand_name": r["shop"]["name"] or urlparse(r["source"]).netloc, "category": r["guesses"]["category"], "colors": colors}
    if r["guesses"]["price_tier"]:
        brand["price_tier"] = r["guesses"]["price_tier"]
    if chosen.get("primary"):
        brand["palette"] = "ramps"
    fonts = {k: v for k, v in r["shop"]["fonts"].items() if k in ("heading", "body") and re.fullmatch(r"[A-Za-z0-9 ]{2,40}", v)}
    if fonts:
        brand["fonts"] = fonts
    (out / "brand.json").write_text(json.dumps(brand, indent=2) + "\n", encoding="utf-8")
    (out / "BRAND.md").write_text(_markdown(r, brand), encoding="utf-8")
    _sheets(out, r)


def _markdown(r: dict, brand: dict) -> str:
    s, c = r["shop"], r["colours"]["chosen"]
    lines = [f"# Brand intake: {s['name'] or r['source']}", "",
             f"Read {r['read_at']} from {r['source']} ({r['platform']}). Public pages only. Start every redesign from this page.", "",
             "## The brand", f"- Name: {s['name']}", f"- Says about itself: {s['description'] or 'nothing (no meta description)'}",
             f"- Theme: {s['theme'] or 'unknown'}; currency {s['currency'] or 'unknown'}; fonts {s['fonts'] or 'not found'}",
             f"- Social: {', '.join(s['socials']) or 'none linked'}",
             f"- Products: {r['counts']['products_listed']} listed, {r['counts']['products_read']} read; collections: {r['counts']['collections']}",
             f"- Videos downloaded: {r['counts']['videos']} ({r['counts']['video_mb']} MB, in `videos/`); YouTube/Vimeo links: "
             f"{sum(len(p['external_videos']) for p in r['products'])}", "",
             "## Colours (confirm before designing)",
             f"- Brand colour: {c['primary'] or 'NOT FOUND: choose by hand'} (from {c['primary_from'] or '-'})",
             f"- Accent: {c['accent'] or 'none found: the brand colour is used alone, or choose one'} (from {c['accent_from'] or '-'})",
             f"- Text {c['text']} on background {c['background']}", "", "| Candidate | Where | Share or uses |", "|---|---|---|"]
    lines += [f"| {x['hex']} | {x['source']} | {x.get('share', x.get('uses'))} |" for x in r["colours"]["candidates"][:14]]
    if r["palette"]:
        roles = r["palette"]["roles"]
        lines += ["", "Palette roles (palette.py, every pair checked):", "",
                  f"- Page {roles['bg']}, text {roles['text']}, soft band {roles['band']}, solid band {roles['accent_fill']}, dark {roles['dark']}",
                  f"- Buttons: {roles['button_bg']} on white, {roles['fill_button_bg']} on the brand band, {roles['dark_button_bg']} on dark"]
    lines += ["", "## Guesses (check them: they are NOT facts)",
              f"- Category: {r['guesses']['category']} (keyword scores {r['guesses']['category_scores']})",
              f"- Price tier: {r['guesses']['price_tier'] or 'unknown'}", "", "## Policies"]
    for name, p in r["policies"].items():
        state = "missing" if not p["found"] else ("found, LOOKS LIKE A TEMPLATE" if p["looks_like_a_template"] else "found")
        lines.append(f"- {name}: {state}")
    lines += ["", "## Collections", "| Collection | Products |", "|---|---|"]
    lines += [f"| {x['title']} (`{x['handle']}`) | {x['products']} |" for x in r["collections"]]
    lines += ["", "## Products read", "| Product | Price | Pictures | Videos | Type |", "|---|---|---|---|---|"]
    for p in r["products"]:
        price = f"{p['price_min']:g}" if p["price_min"] is not None else "-"
        if p["price_max"] and p["price_max"] != p["price_min"]:
            price += f"-{p['price_max']:g}"
        vids = str(len(p["videos"])) + (f" + {len(p['external_videos'])} linked" if p["external_videos"] else "")
        lines.append(f"| [{p['title']}]({p['url']}) | {price} | {len(p['pictures'])} | {vids} | {p['type'] or '-'} |")
    lines += ["", "## Notes"] + [f"- {n}" for n in r["notes"] or ["none"]]
    lines += ["", "`brand.json` here is a DRAFT for the page builder: category, price tier and colours are the guesses above."]
    return "\n".join(lines) + "\n"


def _sheets(out: Path, r: dict) -> None:
    from PIL import Image, ImageDraw  # noqa: PLC0415
    rows = [("candidates", [x["hex"] for x in r["colours"]["candidates"][:12]])]
    if r["palette"]:
        rows += [(name, ramp) for name, ramp in r["palette"]["ramps"].items()]
    sheet = Image.new("RGB", (130 + 12 * 64, 20 + 54 * len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    for y, (name, colours) in enumerate(rows):
        draw.text((8, 30 + 54 * y), name, fill="black")
        for x, colour in enumerate(colours):
            draw.rectangle((130 + 64 * x, 12 + 54 * y, 188 + 64 * x, 56 + 54 * y), fill=colour, outline="#DDDDDD")
    sheet.save(out / "palette.png")
    firsts = [out / "images" / "products" / p["handle"] / p["pictures"][0] for p in r["products"] if p["pictures"]]
    if firsts:
        cols = 5
        grid = Image.new("RGB", (cols * 210, ((len(firsts) + cols - 1) // cols) * 230), "white")
        gd = ImageDraw.Draw(grid)
        for k, (f, p) in enumerate(zip(firsts, [p for p in r["products"] if p["pictures"]])):
            try:
                im = Image.open(f).convert("RGB")
                im.thumbnail((200, 200))
                grid.paste(im, ((k % cols) * 210 + 5, (k // cols) * 230 + 5))
            except Exception:
                pass
            gd.text(((k % cols) * 210 + 5, (k // cols) * 230 + 210), p["title"][:30], fill="black")
        grid.save(out / "products.png")


def drive_folder_name(name: str, source: str) -> str:
    """The brand's folder name in Drive: the shop's name, without characters that make paths ambiguous."""
    clean = re.sub(r'[\\/:*?"<>|]+', " ", name or urlparse(source).netloc).strip()
    return re.sub(r"\s+", " ", clean)[:80] or urlparse(source).netloc


def to_drive(out: Path, r: dict, root: str, drive=None, today: str | None = None, progress: Callable[..., None] | None = None) -> dict:
    """Upload the intake folder to <root>/<brand>/Brand intake <date> in DTJ's Drive (drive_upload.py) and note the link."""
    from .drive_upload import Drive  # noqa: PLC0415  (only when --drive is asked for)
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = f"{root.strip('/')}/{drive_folder_name(r['shop']['name'], r['source'])}/Brand intake {today}"
    tick = progress or (lambda *a: None)
    res = (drive or Drive()).upload_tree(out, path, tick=lambda done, total: tick("drive", done, total))
    res["path"] = path
    r["drive"] = res
    (out / "brand-intake.json").write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return res


def main(argv: list[str] | None = None, *, get: Getter = _get, drive=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="the store's address, e.g. https://brand.com or brand.myshopify.com")
    ap.add_argument("--client", required=True, help="the client folder (.work/clients/<client>); the intake goes to <client>/intake")
    ap.add_argument("--max-products", type=int, default=MAX_PRODUCTS)
    ap.add_argument("--product", default="", help="the product being designed, e.g. 'Turmeric Latte Mix with Saffron': its pictures first")
    ap.add_argument("--drive", metavar="ROOT", help="also upload the intake to DTJ's Google Drive under ROOT, e.g. 'DTJ Clients' "
                    "(needs the DTJ_GDRIVE_* keys: drive_upload.py)")
    args = ap.parse_args(argv)
    out = Path(args.client) / "intake"
    bar = Progress(args.url)  # the Telegram progress message: on only in a GitHub run started from the bot
    bar.start()
    old = signal.signal(signal.SIGTERM, _stop_on_term) if _main_thread() else None  # a cancelled GitHub run: SIGINT, then SIGTERM
    try:
        return _run(args, out, bar, get, drive)
    except KeyboardInterrupt:  # the bot's Stop button cancelled the GitHub run
        spent = bar.finish(False, "Stopped on request. Files already in Google Drive stay there.")
        print(f"stopped on request after {spent}", file=sys.stderr)
        return 130
    finally:
        if old is not None:
            signal.signal(signal.SIGTERM, old)


def _stop_on_term(*_):
    raise KeyboardInterrupt


def _main_thread() -> bool:
    import threading  # noqa: PLC0415
    return threading.current_thread() is threading.main_thread()


def _run(args, out: Path, bar: Progress, get: Getter, drive) -> int:
    try:
        r = intake(args.url, out, get=get, max_products=min(args.max_products, MAX_PRODUCTS), delay=POLITE_DELAY, progress=bar.update,
                   product=args.product)
    except RuntimeError as exc:
        bar.finish(False)
        print(f"could not read {args.url}: {exc}", file=sys.stderr)
        return 1
    c = r["colours"]["chosen"]
    pics = sum(len(p["pictures"]) for p in r["products"])
    read = (f"{r['counts']['products_read']} product pages" if r["platform"] == "other"
            else f"{r['counts']['products_read']} of {r['counts']['products_listed']} products")
    print(f"{r['shop']['name'] or args.url}: {read}, {pics} pictures, "
          f"{r['counts']['collections']} collections | brand {c['primary']} accent {c['accent']} | category guess {r['guesses']['category']}")
    for n in r["notes"]:
        print(f"  note: {n}")
    print(f"written: {out}")
    if args.drive:
        from .drive_upload import DriveError  # noqa: PLC0415
        try:
            res = to_drive(out, r, args.drive, drive=drive, progress=bar.update)
        except DriveError as exc:
            bar.finish(False)
            print(f"could not upload to Drive: {exc}", file=sys.stderr)
            return 1
        print(f"Drive: {res['path']} ({res['uploaded']} files uploaded, {res['skipped']} already there)")
        print(f"DRIVE_LINK={res['link']}")
        res["took"] = bar.finish(True)
        print(f"took {res['took']}")
        _github_outputs(r, res)
    else:
        print(f"took {bar.finish(True, 'Saved on this computer (no Drive upload asked).')}")
    return 0


def _github_outputs(r: dict, res: dict) -> None:
    """In GitHub Actions: the link as a step output and a short summary on the run's page (no client data beyond the counts)."""
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"link={res['link']}\nbrand={r['shop']['name']}\ntook={res.get('took', '')}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        c = r["colours"]["chosen"]
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(f"### Brand intake: {r['shop']['name']}\n\n- {r['counts']['products_read']} of {r['counts']['products_listed']} products, "
                     f"{r['counts']['videos']} videos\n- Brand colour {c['primary']}, accent {c['accent']}\n- Drive: {res['link']}\n")


if __name__ == "__main__":
    sys.exit(main())
