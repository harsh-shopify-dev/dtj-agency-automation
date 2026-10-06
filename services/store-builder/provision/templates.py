"""Fill Horizon template JSON from the brand config.

Findings from reading harsh-shopify-dev/dtj-master-theme (Horizon 4.2.0):
- templates/product.json is dynamic ("{{ closest.product }}"): it needs no product handles.
- templates/index.json shows products through a collection setting on the `product-list` section.
- The hero section's image setting is assumed to be `image_1` and to take `shopify://shop_images/<file>`.
  [VERIFY] with `shopify theme check` and a preview before relying on it.
Section ids change between theme versions, so bindings find sections by TYPE, not by id.
The files start with an auto-generated /* ... */ comment which is kept as it is.
"""
from __future__ import annotations

import json
import re
from typing import Iterable

_HANDLE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_FILENAME = re.compile(r"^[^/\\]+\.(jpg|jpeg|png|webp)$")


class TemplateError(Exception):
    pass


def load(text: str) -> tuple[str, dict]:
    """Returns (leading comment header, parsed JSON)."""
    start = text.find("{")
    if start < 0:
        raise TemplateError("no JSON object found")
    try:
        return text[:start], json.loads(text[start:])
    except ValueError as exc:
        raise TemplateError(f"invalid JSON: {exc}") from exc


def dump(header: str, data: dict) -> str:
    return header + json.dumps(data, indent=2, ensure_ascii=False) + "\n"


_APP_PART = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_ALNUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"


def app_block_type(app_handle: str, block_handle: str, ext_uuid: str) -> str:
    """The block type Shopify saves for a theme app extension block (learned from a real theme, 5 Oct 2026):
    shopify://apps/dtj-blocks/blocks/dtj-trust-row/01a10b7e-02ff-7b68-95a3-bbcdcb562875"""
    if not (_APP_PART.match(app_handle) and _APP_PART.match(block_handle) and _UUID.match(ext_uuid)):
        raise TemplateError("bad app handle, block handle or extension uuid")
    return f"shopify://apps/{app_handle}/blocks/{block_handle}/{ext_uuid}"


def add_app_block(text: str, *, section_type: str, app_handle: str, block_handle: str, ext_uuid: str,
                  settings: dict, index: int | None = None, rng=None) -> tuple[str, str, bool]:
    """Place an app block as a top-level block of the first section of `section_type` in a template.
    Returns (new text, block key, added). Idempotent: if that block is already there, its settings are updated
    in place and nothing is duplicated. `index` is the position in block_order (None = end)."""
    import random

    rng = rng or random.SystemRandom()
    block_type = app_block_type(app_handle, block_handle, ext_uuid)
    header, data = load(text)
    hits = [(sid, s) for sid, s in data.get("sections", {}).items() if s.get("type") == section_type]
    if not hits:
        raise TemplateError(f"no section of type {section_type!r}")
    _, section = hits[0]
    blocks = section.setdefault("blocks", {})
    for key, block in blocks.items():
        if block.get("type") == block_type:
            block["settings"] = dict(settings)
            return dump(header, data), key, False
    stem = f"{app_handle}_{block_handle}".replace("-", "_")
    key = f"{stem}_{''.join(rng.choice(_ALNUM) for _ in range(6))}"
    while key in blocks:
        key = f"{stem}_{''.join(rng.choice(_ALNUM) for _ in range(6))}"
    blocks[key] = {"type": block_type, "settings": dict(settings)}
    order = section.setdefault("block_order", [k for k in blocks if k != key])
    order.insert(len(order) if index is None else max(0, min(index, len(order))), key)
    return dump(header, data), key, True


def bindings_from_brand(brand: dict) -> list[dict]:
    home = brand.get("home") or {}
    out = []
    collection = home.get("product_list_collection")
    if collection:
        if not _HANDLE.match(collection):
            raise TemplateError(f"bad collection handle: {collection!r}")
        out.append({"file": "templates/index.json", "section_type": "product-list",
                    "setting": "collection", "value": collection})
    hero = home.get("hero_image")
    if hero:
        if not _FILENAME.match(hero):
            raise TemplateError(f"bad hero image file name: {hero!r}")
        out.append({"file": "templates/index.json", "section_type": "hero",
                    "setting": "image_1", "value": f"shopify://shop_images/{hero}"})
    return out


def apply_bindings(files: dict[str, str], bindings: Iterable[dict]) -> tuple[dict[str, str], list[dict]]:
    """files: {theme-relative path: file text}. Returns (new texts for changed files, change list).
    Raises if a binding finds no section of that type, so a theme change cannot fail silently."""
    parsed: dict[str, tuple[str, dict]] = {}
    changes: list[dict] = []
    for b in bindings:
        path = b["file"]
        if path not in files:
            raise TemplateError(f"{path} is not in the theme")
        if path not in parsed:
            parsed[path] = load(files[path])
        sections = parsed[path][1].get("sections", {})
        hits = [(sid, s) for sid, s in sections.items() if s.get("type") == b["section_type"]]
        if not hits:
            raise TemplateError(f"{path}: no section of type {b['section_type']!r}")
        for sid, section in hits[:1]:  # first matching section only
            settings = section.setdefault("settings", {})
            before = settings.get(b["setting"])
            if before != b["value"]:
                settings[b["setting"]] = b["value"]
                changes.append({"file": path, "section": sid, "setting": b["setting"],
                                "before": before, "after": b["value"]})
    changed_files = {c["file"] for c in changes}
    return {p: dump(h, d) for p, (h, d) in parsed.items() if p in changed_files}, changes
