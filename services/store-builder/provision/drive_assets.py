"""Read a client's product folder from Google Drive for a NEW store (Harsh, 22 Oct 2026: "in a new store development it should ask
if products are available if yes then we will provide a gdrive link from which it will download all the assets"), with no key and
no login: the person shares the folder as "Anyone with the link -> Viewer" and Drive's own public pages list and serve it.

The folder (the layout agreed for the store factory; names are matched loosely: any case, the number in front is optional):
    <Brand name>/
      1 Brand/      logo.png (or .jpg / .svg / .webp), logo-white.png (optional: for dark backgrounds), "Brand details" (Google Doc
                    or .txt: Name, Tagline, Colours, Fonts, About, Email, Phone, Address, Instagram / Facebook / YouTube / WhatsApp)
      2 Products/   one folder per product, named as the product: "Details" (Google Doc or .txt: Price, Compare at price or MRP,
                    Sizes "250 g = 499, 500 g = 899", Collection, SKU, Tags, Description) + pictures 1.jpg, 2.jpg ... (1 = main)
      3 Banners/    optional: pictures for the home page
      4 Policies/   optional: Refund, Shipping, Privacy, Terms (Google Docs or .txt)

    python -m provision.drive_assets read <folder link> --out <dir>
        downloads the folder into <dir>/files/..., writes <dir>/drive.json (the brand in the shape provision/brand_copy.make_plan
        takes) and prints a short summary and every problem found (a product without pictures, a price that is not a number).
        Exit 0 = read, 1 = the folder could not be read (the reason, in plain words for the person who sent it).

What it never does: invent a price (no price -> 0.00 with the tag dtj-price-needed, as brand_copy does for a website brand), write
anything to Drive, or need a key. Pictures are local files here (images[].path): the store job uploads them and fills images[].src.
Drive pages used (checked live on 22 Oct 2026 on gdown's public test folder): drive.google.com/embeddedfolderview?id=<folder>
(the listing), docs.google.com/document/d/<id>/export?format=txt (a Google Doc's text), drive.usercontent.google.com/download
?id=<id>&export=download&confirm=t (a file's bytes). Videos are listed with their Drive link, not downloaded.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from .brand_copy import PRICE_TAG

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
LIST_URL = "https://drive.google.com/embeddedfolderview?id={id}"
DOC_URL = "https://docs.google.com/document/d/{id}/export?format=txt"
FILE_URL = "https://drive.usercontent.google.com/download?id={id}&export=download&confirm=t"
MAX_PRODUCTS = 150
MAX_PICTURES = 10  # per product
PICTURE = re.compile(r"\.(jpe?g|png|webp|gif)$", re.I)
LOGO_PICTURE = re.compile(r"\.(jpe?g|png|webp|gif|svg)$", re.I)
VIDEO = re.compile(r"\.(mp4|mov|webm|m4v)$", re.I)
TEXT = re.compile(r"\.(txt|docx)$", re.I)
POLICY_WORDS = (("REFUND_POLICY", ("refund", "return")), ("SHIPPING_POLICY", ("shipping", "delivery")),
                ("PRIVACY_POLICY", ("privacy",)), ("TERMS_OF_SERVICE", ("terms", "condition", "service")))
SHARE_HELP = ("In Drive: right-click the folder > Share > General access: \"Anyone with the link\", Viewer; then send its link again.")

Getter = Callable[[str], "tuple[int, str, bytes]"]  # url -> (status, final url, body)


class DriveError(Exception):
    """The folder cannot be read; the message is for the person who sent the link."""


def _once(url: str) -> tuple[int, str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.geturl(), r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, url, b""
    except (urllib.error.URLError, OSError):
        return 0, url, b""


def http_get(url: str, sleep: Callable[[float], None] = time.sleep) -> tuple[int, str, bytes]:
    """One GET; a 429, a 5xx or no answer is tried again up to 3 times with a growing pause (CLAUDE.md self-healing)."""
    for attempt in range(4):
        status, final, body = _once(url)
        if (status == 0 or status == 429 or status >= 500) and attempt < 3:
            sleep(2 * (attempt + 1))
            continue
        return status, final, body
    return status, final, body


def folder_id(link: str) -> str:
    link = (link or "").strip()
    if re.search(r"/file/d/|/document/d/|/spreadsheets/d/", link):
        raise DriveError("That is a link to one file. Send the link of the whole folder (open the folder, then Share > Copy link).")
    m = (re.search(r"/folders/([A-Za-z0-9_-]{10,})", link) or re.search(r"[?&]id=([A-Za-z0-9_-]{10,})", link)
         or re.fullmatch(r"([A-Za-z0-9_-]{20,})", link))
    if not m or ("/" in link and "google.com" not in link.lower()):
        raise DriveError(f"{link[:120]!r} is not a Google Drive folder link (it looks like https://drive.google.com/drive/folders/...).")
    return m.group(1)


# ---------------------------------------------------------------------------------------------------------- Drive's public pages
def _signed_out(final: str) -> bool:
    return "accounts.google.com" in (final or "") or "ServiceLogin" in (final or "")


def list_folder(fid: str, get: Getter) -> tuple[str, list[dict]]:
    """The folder's title and its entries: {"id", "name", "kind" (folder / doc / sheet / slides / file), "mime", "link"}."""
    status, final, body = get(LIST_URL.format(id=fid))
    if status == 0:
        raise DriveError("Google Drive did not answer. Try again in a few minutes.")
    page = body.decode("utf-8", "replace") if status == 200 else ""
    if status != 200 or _signed_out(final) or "flip-entries" not in page and "flip-contents" not in page:
        raise DriveError("I cannot open that Drive folder: it is not shared with \"Anyone with the link\", or the link is wrong. "
                         + SHARE_HELP)
    m = re.search(r"<title>([\s\S]*?)</title>", page)
    title = html.unescape(m.group(1)).strip() if m else ""
    entries = []
    for block in page.split('class="flip-entry"')[1:]:
        eid = re.search(r'id="entry-([A-Za-z0-9_-]+)"', block)
        href = re.search(r'<a href="([^"]+)"', block)
        name = re.search(r'<div class="flip-entry-title">([\s\S]*?)</div>', block)
        if not (eid and href and name):
            continue
        link = html.unescape(href.group(1))
        kind = ("folder" if "/folders/" in link else "doc" if "/document/d/" in link else "sheet" if "/spreadsheets/d/" in link
                else "slides" if "/presentation/d/" in link else "file")
        mime = re.search(r"/type/([a-z0-9.+-]+/[a-z0-9.+-]+)", block)
        entries.append({"id": eid.group(1), "name": html.unescape(name.group(1)).strip(), "kind": kind,
                        "mime": mime.group(1) if mime else "", "link": link})
    return title, entries


def _is_html(body: bytes) -> bool:
    head = body[:400].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def read_text(entry: dict, get: Getter) -> str | None:
    """The words of a Google Doc, a .txt or a .docx; None when it cannot be read."""
    if entry["kind"] == "doc":
        status, final, body = get(DOC_URL.format(id=entry["id"]))
        if status != 200 or _signed_out(final) or _is_html(body):
            return None
        return body.decode("utf-8-sig", "replace").replace("\r\n", "\n")
    if entry["kind"] != "file" or not TEXT.search(entry["name"]):
        return None
    status, final, body = get(FILE_URL.format(id=entry["id"]))
    if status != 200 or _signed_out(final) or _is_html(body):
        return None
    if entry["name"].lower().endswith(".docx"):
        try:
            xml = zipfile.ZipFile(io.BytesIO(body)).read("word/document.xml").decode("utf-8", "replace")
        except (zipfile.BadZipFile, KeyError):
            return None
        paras = [html.unescape("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))) for p in re.findall(r"<w:p[ >][\s\S]*?</w:p>", xml)]
        return "\n".join(paras)
    return body.decode("utf-8-sig", "replace").replace("\r\n", "\n")


def _safe(part: str) -> str:
    part = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", part).strip().rstrip(".")
    return part[:120] or "_"


class _Downloads:
    """Files fetched into <out>/files/<folder path>/<name>; a re-run keeps a file whose Drive id it already fetched."""

    def __init__(self, root: Path, get: Getter):
        self.root, self.get = root, get
        self.manifest_path = root / "files.json"
        self.done = json.loads(self.manifest_path.read_text(encoding="utf-8")) if self.manifest_path.exists() else {}

    def fetch(self, entry: dict, parts: list[str]) -> Path | None:
        dest = self.root.joinpath(*[_safe(p) for p in parts], _safe(entry["name"]))
        if self.done.get(entry["id"]) == str(dest) and dest.exists() and dest.stat().st_size:
            return dest
        status, final, body = self.get(FILE_URL.format(id=entry["id"]))
        if status != 200 or _signed_out(final) or not body or _is_html(body):
            return None  # Drive sent a page instead of the file (not shared, or a warning page)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        self.done[entry["id"]] = str(dest)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(self.done, indent=1, ensure_ascii=False), encoding="utf-8")
        return dest


# ---------------------------------------------------------------------------------------------------------- the words in the docs
def _plain(name: str) -> str:
    """'2 Products' -> 'products', '01 - Masala Mix.txt' -> 'masala mix'."""
    stem = re.sub(r"\.(txt|docx|pdf|jpe?g|png|webp|gif|svg|mp4|mov|webm|m4v)$", "", name.strip(), flags=re.I)
    return re.sub(r"\s+", " ", re.sub(r"^\d+\s*[.)\-_:]*\s*", "", stem)).strip().lower()


def _title(name: str) -> str:
    """'01 - Masala Mix' -> 'Masala Mix' (a number only for the order); '3 in 1 Coffee' stays as it is."""
    return re.sub(r"^\d+\s*[.)\-_:]+\s*", "", name.strip()).strip() or name.strip()


def _natural(name: str) -> list:
    return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", name)]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:200] or "product"


PRODUCT_KEYS = {
    "price": "price", "selling price": "price", "sale price": "price", "our price": "price",
    "compare at price": "compare", "compare-at price": "compare", "compare price": "compare", "mrp": "compare",
    "original price": "compare", "size": "options", "sizes": "options", "option": "options", "options": "options",
    "variant": "options", "variants": "options", "colour": "options", "colours": "options", "color": "options", "colors": "options",
    "flavour": "options", "flavours": "options", "flavor": "options", "flavors": "options", "packs": "options",
    "weights": "options", "collection": "collection", "collections": "collection", "category": "collection",
    "categories": "collection", "sku": "sku", "tags": "tags", "tag": "tags", "name": "title", "title": "title",
    "product name": "title", "description": "description",
}
BRAND_KEYS = {
    "name": "name", "brand": "name", "brand name": "name", "tagline": "tagline", "slogan": "tagline",
    "colours": "colours", "colors": "colours", "colour": "colours", "color": "colours", "brand colours": "colours",
    "brand colors": "colours", "fonts": "fonts", "font": "fonts", "about": "about", "about us": "about", "story": "about",
    "email": "email", "e-mail": "email", "phone": "phone", "mobile": "phone", "whatsapp number": "phone", "address": "address",
    "website": "website", "instagram": "instagram", "facebook": "facebook", "youtube": "youtube", "whatsapp": "whatsapp",
    "twitter": "twitter", "x": "twitter", "linkedin": "linkedin", "pinterest": "pinterest",
}
_KEY_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z \-]{0,30}?)\s*:\s*(.*)$")


_EQ_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z ]{0,20}?)\s*=\s*\S")
_GOES_ON = {"description", "about", "address", "colours", "fonts", "options", "collection", "tags", "_other"}  # may take more lines


def parse_fields(text: str, keys: dict, rest_key: str | None = None) -> dict:
    """"Key: value" lines into {field: value}. A plain line continues the field above it when that field may run over lines (a
    description, sizes one per line), else it goes to "_other"; once `rest_key` is reached (a product's Description) everything
    after it belongs to it."""
    fields: dict[str, str] = {}
    current = "_other"
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        if current == rest_key and current in fields:
            fields[current] += "\n" + line
            continue
        m = _KEY_LINE.match(line)
        key = keys.get(re.sub(r"\s+", " ", m.group(1).strip().lower())) if m else None
        eq = _EQ_LINE.match(line) if not key else None
        if eq and keys.get(eq.group(1).strip().lower()) == "options" and "options" not in fields:  # "Size = S, M, L" on its own
            fields["_option_key"], fields["options"], current = eq.group(1).strip().lower(), line.strip(), "options"
        elif key:
            current = key
            if key == "options" and "options" in fields:  # a second option line: kept apart, only the first is read
                current = "_more_options"
            elif key == "options":
                fields["_option_key"] = m.group(1).strip().lower()
            fields[current] = fields[current] + "\n" + m.group(2) if current in fields else m.group(2)
        elif not line.strip():
            if current in _GOES_ON and current in fields:
                fields[current] += "\n"  # keeps the paragraphs of a description or an about text
        else:  # "Weight: 250 g" (a key this reader does not use) never runs into the field above it
            into = current if current in _GOES_ON and not m else "_other"
            fields[into] = fields[into] + "\n" + line if into in fields else line
    return {k: v.strip() for k, v in fields.items()}


def money(text: str) -> str | None:
    """'Rs. 1,299/-' -> '1299'; None when there is no number."""
    t = re.sub(r"(?i)\b(rs|inr|mrp)\b\.?|[₹$€£]|/-", " ", (text or "").replace(",", "")).strip()
    m = re.fullmatch(r"(\d{1,9}(?:\.\d{1,2})?)\s*(?:only)?", t, re.I)
    return m.group(1) if m else None


def _option_name(key: str, value: str) -> str:
    for word, name in (("size", "Size"), ("colo", "Colour"), ("flavo", "Flavour"), ("pack", "Pack"), ("weight", "Weight")):
        if key.startswith(word):
            return name
    return "Option"


def _paragraphs(text: str) -> str:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", (text or "").strip()) if b.strip()]
    return "".join("<p>" + "<br>".join(html.escape(x.strip()) for x in b.split("\n") if x.strip()) + "</p>" for b in blocks)


def product_from(title: str, fields: dict, brand_name: str) -> tuple[dict, list[str]]:
    """One product in brand_copy's shape (as /products.json shows it) from its Details fields, and the problems found."""
    problems = []
    title = (fields.get("title") or title).strip()[:255]
    price_text = fields.get("price", "")
    price = money(price_text)
    if price_text and price is None:
        problems.append(f"{title}: the price \"{price_text[:40]}\" is not a number (left at 0.00)")
    compare = money(fields.get("compare", ""))
    options = [{"name": "Title", "position": 1, "values": ["Default Title"]}]
    variants = [{"option1": "Default Title", "price": price, "compare_at_price": compare, "sku": fields.get("sku", "")}]
    raw = fields.get("options", "")
    if raw:
        parts = [x.strip() for x in re.split(r"[,|;\n]", raw) if x.strip()]
        name = _option_name(fields.get("_option_key", ""), raw)
        if parts and all("=" in x for x in parts):  # "250 g = 499, 500 g = 899": a price for each value
            pairs = [(x.split("=", 1)[0].strip(), x.split("=", 1)[1].strip()) for x in parts]
            if len(pairs) > 1 or money(pairs[0][1]) is not None:
                variants = []
                for value, p in pairs:
                    vp = money(p)
                    if vp is None:
                        problems.append(f"{title}: the price for {value} \"{p[:30]}\" is not a number (left at 0.00)")
                    variants.append({"option1": value[:255], "price": vp, "compare_at_price": None, "sku": ""})
                values = [v["option1"] for v in variants]
            else:  # "Size = S" alone: a name and one value
                name, values = pairs[0][0][:255] or name, [pairs[0][1]]
        elif parts and "=" in parts[0]:  # "Size = S, M, L": the name, then its values at the one price
            name, first = (x.strip() for x in parts[0].split("=", 1))
            values = [first] + parts[1:]
        else:
            values = parts
        if not variants or variants[0]["option1"] == "Default Title":
            variants = [{"option1": v[:255], "price": price, "compare_at_price": compare, "sku": ""} for v in values]
        seen, unique = set(), []
        for v in variants:
            if v["option1"].lower() not in seen:
                seen.add(v["option1"].lower())
                unique.append(v)
        variants = unique[:100]
        options = [{"name": (name or "Option")[:255], "position": 1, "values": [v["option1"] for v in variants]}]
    if fields.get("_more_options"):
        problems.append(f"{title}: only the first option line is read ({options[0]['name']}); add the others in Shopify")
    needs_price = any(v["price"] is None for v in variants)
    for v in variants:
        if v["price"] is None:
            v["price"], v["compare_at_price"] = "0.00", None  # never a guessed price: 0.00 and the tag, set in Shopify later
        elif v["compare_at_price"] and float(v["compare_at_price"]) <= float(v["price"]):
            v["compare_at_price"] = None
    if not price_text and needs_price:
        problems.append(f"{title}: no price in its Details (left at 0.00, tagged {PRICE_TAG})")
    tags = [t.strip() for t in re.split(r"[,\n]", fields.get("tags", "")) if t.strip()]
    if needs_price:
        tags.append(PRICE_TAG)
    product = {"handle": slug(title), "title": title, "body_html": _paragraphs(fields.get("description") or fields.get("_other", "")),
               "vendor": brand_name, "product_type": "", "tags": tags, "options": options, "variants": variants,
               "images": [], "price_needed": needs_price}
    return product, problems


def brand_from(fields: dict) -> dict:
    colours = []
    for six, three in re.findall(r"(?:#|\b)([0-9a-fA-F]{6})\b|#([0-9a-fA-F]{3})\b", fields.get("colours", "")):
        c = six.lower() if six else "".join(ch * 2 for ch in three.lower())  # 3 digits only with a #: "bad" is not a colour
        if f"#{c}" not in colours:
            colours.append(f"#{c}")
    email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", fields.get("email", ""))
    social = {k: fields[k].split()[0] for k in ("instagram", "facebook", "youtube", "whatsapp", "twitter", "linkedin", "pinterest", "website")
              if fields.get(k)}
    return {"name": fields.get("name", "").strip()[:120], "tagline": fields.get("tagline", "").strip()[:300], "colours": colours,
            "colours_text": fields.get("colours", "").strip()[:300],
            "fonts": [f.strip() for f in re.split(r"[,\n]", fields.get("fonts", "")) if f.strip()],
            "about": fields.get("about", "").strip(), "email": email.group(0) if email else "", "phone": fields.get("phone", "").strip(),
            "address": fields.get("address", "").strip(), "social": social}


# ---------------------------------------------------------------------------------------------------------- the whole folder
def _section(entries: list[dict], word: str) -> dict | None:
    return next((e for e in entries if e["kind"] == "folder" and word in _plain(e["name"])), None)


def _details_doc(entries: list[dict], words: tuple[str, ...]) -> dict | None:
    docs = [e for e in entries if e["kind"] == "doc" or (e["kind"] == "file" and TEXT.search(e["name"]))]
    named = [e for e in docs if any(w in _plain(e["name"]) for w in words)]
    return (named or (docs if len(docs) == 1 else [None]))[0]


def read_folder(link: str, out: Path, get: Getter = http_get, max_products: int = MAX_PRODUCTS,
                pause: Callable[[], None] = lambda: time.sleep(0.2)) -> dict:
    """Read the whole Drive folder (see the module's docstring) into <out>; returns the brand (also written to <out>/drive.json)."""
    fid = folder_id(link)
    out = Path(out)
    files = _Downloads(out / "files", get)
    root_title, root = list_folder(fid, get)
    if not root:
        raise DriveError("That Drive folder is empty. Put the brand's folders in it (1 Brand, 2 Products, 3 Banners, 4 Policies).")
    problems: list[str] = []
    products_dir = _section(root, "product")
    if not products_dir:
        found = ", ".join(e["name"] for e in root if e["kind"] == "folder")[:200] or "no folders"
        raise DriveError(f"No \"2 Products\" folder in it (found: {found}). Make one folder \"2 Products\" with one folder per product.")
    brand_dir = next((e for e in root if e["kind"] == "folder" and "brand" in _plain(e["name"]) and e is not products_dir), None)
    banners_dir = _section(root, "banner")
    policies_dir = _section(root, "polic")

    # the brand: its details, its logo
    brand = brand_from({})
    logo = logo_white = None
    if brand_dir:
        pause()
        _, inside = list_folder(brand_dir["id"], get)
        doc = _details_doc(inside, ("detail", "brand", "about", "info"))
        if doc:
            pause()
            text = read_text(doc, get)
            if text is None:
                problems.append(f"the brand's \"{doc['name']}\" could not be read (save it as a Google Doc or .txt)")
            brand = brand_from(parse_fields(text or "", BRAND_KEYS))
        else:
            problems.append("no Brand details doc in the brand folder (name, colours, fonts, contact)")
        pictures = sorted((e for e in inside if e["kind"] == "file" and LOGO_PICTURE.search(e["name"])), key=lambda e: _natural(e["name"]))
        logos = [e for e in pictures if "logo" in _plain(e["name"])] or (pictures if len(pictures) == 1 else [])
        light = [e for e in logos if re.search(r"white|light|invers|negative|reverse", e["name"], re.I)]
        main = [e for e in logos if e not in light]
        for picked, which in ((main[:1], "logo"), (light[:1], "logo_white")):
            if picked:
                pause()
                got = files.fetch(picked[0], [root_title or "folder", brand_dir["name"]])
                if got is None:
                    problems.append(f"the {which.replace('_', ' ')} {picked[0]['name']} could not be downloaded")
                elif which == "logo":
                    logo = str(got)
                else:
                    logo_white = str(got)
        if not main:
            problems.append("no logo in the brand folder (a picture named logo.png)")
    else:
        problems.append("no \"1 Brand\" folder: no logo, colours or contact details")
    name = brand["name"] or _title(root_title) or "Brand"
    brand.update({"name": name, "logo": logo, "logo_white": logo_white})

    # the products, one folder each, in the folder's order
    pause()
    _, product_entries = list_folder(products_dir["id"], get)
    folders = sorted((e for e in product_entries if e["kind"] == "folder"), key=lambda e: _natural(e["name"]))
    if not folders:
        raise DriveError("The \"2 Products\" folder has no product folders. Make one folder per product, named as the product.")
    if len(folders) > max_products:
        problems.append(f"{len(folders) - max_products} more product folders left out (the first {max_products} are read)")
    products, collections, handles = [], {}, set()
    for folder in folders[:max_products]:
        pause()
        _, inside = list_folder(folder["id"], get)
        title = _title(folder["name"])
        doc = _details_doc(inside, ("detail", "info", "description"))
        fields: dict = {}
        if doc:
            pause()
            text = read_text(doc, get)
            if text is None:
                problems.append(f"{title}: its \"{doc['name']}\" could not be read (save it as a Google Doc or .txt)")
            fields = parse_fields(text or "", PRODUCT_KEYS, rest_key="description")
        else:
            problems.append(f"{title}: no Details doc (price, sizes, description)")
        product, found = product_from(title, fields, name)
        problems += found
        base, n = product["handle"], 2
        while product["handle"] in handles:
            product["handle"] = f"{base}-{n}"
            n += 1
        handles.add(product["handle"])
        pictures = sorted((e for e in inside if e["kind"] == "file" and PICTURE.search(e["name"])), key=lambda e: _natural(e["name"]))
        if len(pictures) > MAX_PICTURES:
            problems.append(f"{product['title']}: {len(pictures)} pictures, the first {MAX_PICTURES} are used")
        for pic in pictures[:MAX_PICTURES]:
            pause()
            got = files.fetch(pic, [root_title or "folder", products_dir["name"], folder["name"]])
            if got is None:
                problems.append(f"{product['title']}: the picture {pic['name']} could not be downloaded")
            else:
                product["images"].append({"path": str(got), "alt": product["title"]})
        if not product["images"]:
            problems.append(f"{product['title']}: no pictures (put 1.jpg, 2.jpg ... in its folder)")
        product["videos"] = [{"name": e["name"], "link": e["link"], "id": e["id"]} for e in inside
                             if e["kind"] == "file" and VIDEO.search(e["name"])]
        product["source"] = folder["link"]
        for c in [x.strip() for x in re.split(r"[,\n]", fields.get("collection", "")) if x.strip()]:
            col = collections.setdefault(slug(c), {"handle": slug(c), "title": c[:255], "description_html": "", "products": []})
            if product["handle"] not in col["products"]:
                col["products"].append(product["handle"])
        products.append(product)

    banners = []
    if banners_dir:
        pause()
        _, inside = list_folder(banners_dir["id"], get)
        for pic in sorted((e for e in inside if e["kind"] == "file" and PICTURE.search(e["name"])), key=lambda e: _natural(e["name"])):
            pause()
            got = files.fetch(pic, [root_title or "folder", banners_dir["name"]])
            if got is None:
                problems.append(f"the banner {pic['name']} could not be downloaded")
            else:
                banners.append(str(got))

    policies = {}
    if policies_dir:
        pause()
        _, inside = list_folder(policies_dir["id"], get)
        for doc in inside:
            if not (doc["kind"] == "doc" or (doc["kind"] == "file" and TEXT.search(doc["name"]))):
                continue
            ptype = next((t for t, words in POLICY_WORDS if any(w in _plain(doc["name"]) for w in words)), None)
            if not ptype or ptype in policies:
                continue
            pause()
            text = read_text(doc, get)
            if not text or len(text.strip()) < 40:
                problems.append(f"the policy \"{doc['name']}\" is empty or could not be read")
                continue
            policies[ptype] = {"body": _paragraphs(text), "source": doc["link"]}

    data = {"source": "drive", "platform": "drive", "link": link, "folder_id": fid, "base": link, "name": name,
            "myshopify_domain": None, "currency": None, "brand": brand, "products": products,
            "collections": list(collections.values()), "more_collections": 0, "unreadable_pages": [],
            "banners": banners, "policies": policies, "product_count": len(products), "more_products": False,
            "collection_count": len(collections),
            "best_sellers": [{"handle": p["handle"], "title": p["title"], "url": p["source"]} for p in products],
            "best_sellers_from": "the Drive folder's order", "problems": problems}
    out.mkdir(parents=True, exist_ok=True)
    (out / "drive.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    return data


def summary(data: dict) -> str:
    unpriced = sum(1 for p in data["products"] if p.get("price_needed"))
    pictures = sum(len(p["images"]) for p in data["products"])
    return (f"{data['name']}: {len(data['products'])} products ({pictures} pictures"
            + (f", {unpriced} without a price" if unpriced else "") + f"), {len(data['collections'])} collections, "
            f"{len(data['banners'])} banners, {len(data['policies'])} policy pages, logo: {'yes' if data['brand'].get('logo') else 'no'}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m provision.drive_assets", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read", help="download a public Drive folder and read its brand, products, banners and policies")
    r.add_argument("link")
    r.add_argument("--out", required=True, type=Path)
    a = ap.parse_args(argv)
    try:
        data = read_folder(a.link, a.out)
    except DriveError as exc:
        print(f"could not read the folder: {exc}")
        return 1
    print(summary(data))
    for p in data["problems"]:
        print(f"  - {p}")
    print(f"written: {a.out / 'drive.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
