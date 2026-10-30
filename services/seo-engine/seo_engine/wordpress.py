"""WordPress: (1) saves a new article or city page as a DRAFT; (2) for an APPROVED fixes batch only, reads and writes a page's Yoast
title / description / "hide from Google" setting (through the DTJ SEO Bridge plugin), an image's alt text, and the site's business
details.

Drafts are Tier 1 (reversible, nobody sees them): the request always sends status "draft", never updates an existing post, and refuses
a slug that is already taken. Publishing is deliberately not here: a person reviews the draft and presses Publish. The fix writes are
Tier 2 and are called only by apply_batch.py after a named person approved the batch. Credentials come from WP_USER / WP_APP_PASSWORD at call time (a WordPress
"application password" for an Editor), never from a file, and are never logged.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from .config import Config

Opener = Callable[[urllib.request.Request], tuple[int, dict | list]]


class WordPressError(Exception):
    pass


def _open(req: urllib.request.Request) -> tuple[int, dict | list]:
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8") or "null")
        except ValueError:
            body = {}
        return exc.code, body


def _request(cfg: Config, method: str, path: str, body: dict | None = None, base: str = "wp/v2") -> urllib.request.Request:
    user, password = cfg.wp_credentials()
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{cfg.site}/wp-json/{base}/{path}", data=data, method=method,
                                 headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json",
                                          "User-Agent": "dtj-seo-engine/1.0"})
    return req


def slug_taken(cfg: Config, slug: str, opener: Opener = _open, kind: str = "posts") -> bool:
    status, body = opener(_request(cfg, "GET", f"{kind}?" + urllib.parse.urlencode({"slug": slug, "status": "publish,draft,pending,future,private", "_fields": "id"})))
    if status != 200:
        raise WordPressError(f"could not check the slug (HTTP {status}: {str(body)[:200]})")
    return bool(body)


def create_draft(cfg: Config, *, title: str, slug: str, html: str, excerpt: str = "", opener: Opener = _open, kind: str = "posts") -> dict:
    """kind: posts (a blog article) or pages (a city page)."""
    if kind not in ("posts", "pages"):
        raise WordPressError(f"unknown kind {kind!r}")
    if slug_taken(cfg, slug, opener, kind):
        raise WordPressError(f"a {kind[:-1]} with the slug {slug!r} already exists; nothing was changed")
    payload = {"title": title, "slug": slug, "content": html, "status": "draft", "comment_status": "closed"}
    if kind == "posts":
        payload["excerpt"] = excerpt
    assert payload["status"] == "draft"  # the only status this service ever sends
    status, body = opener(_request(cfg, "POST", kind, payload))
    if status not in (200, 201) or not isinstance(body, dict) or body.get("status") != "draft":
        raise WordPressError(f"WordPress did not save a draft (HTTP {status}: {str(body)[:200]})")
    return {"id": body.get("id"), "status": body.get("status"), "edit_url": f"{cfg.site}/wp-admin/post.php?post={body.get('id')}&action=edit"}


# --- Approved fixes only (apply_batch.py) ---------------------------------------------------------------------------------------
BRIDGE = "dtj-seo/v1"


def _ok(status: int, body, what: str):
    if status == 404 and isinstance(body, dict) and body.get("code") == "rest_no_route":
        raise WordPressError("the DTJ SEO Bridge plugin is not active on the site (services/seo-engine/wordpress-plugin)")
    if status not in (200, 201):
        raise WordPressError(f"{what}: HTTP {status}: {str(body)[:200]}")
    return body


def resolve(cfg: Config, url: str, opener: Opener = _open) -> dict:
    """The post behind a public URL and its current Yoast fields: {post_id, post_type, status, metadesc, title, noindex}."""
    return _ok(*opener(_request(cfg, "GET", "resolve?" + urllib.parse.urlencode({"url": url}), base=BRIDGE)), f"resolve {url}")


def set_field(cfg: Config, post_id: int, field: str, value: str, opener: Opener = _open) -> dict:
    if field not in ("metadesc", "title", "noindex"):
        raise WordPressError(f"field {field!r} is not one the bridge may change")
    return _ok(*opener(_request(cfg, "POST", "meta", {"post_id": post_id, "field": field, "value": value}, base=BRIDGE)), f"set {field}")


def get_alt(cfg: Config, media_id: int, opener: Opener = _open) -> str:
    body = _ok(*opener(_request(cfg, "GET", f"media/{int(media_id)}?context=edit&_fields=id,alt_text")), f"media {media_id}")
    return body.get("alt_text", "") if isinstance(body, dict) else ""


def set_alt(cfg: Config, media_id: int, alt: str, opener: Opener = _open) -> dict:
    return _ok(*opener(_request(cfg, "POST", f"media/{int(media_id)}", {"alt_text": alt})), f"media {media_id}")


def get_jsonld(cfg: Config, opener: Opener = _open):
    return (_ok(*opener(_request(cfg, "GET", "jsonld", base=BRIDGE)), "business details") or {}).get("jsonld")


def set_jsonld(cfg: Config, data, opener: Opener = _open) -> dict:
    return _ok(*opener(_request(cfg, "POST", "jsonld", {"jsonld": data}, base=BRIDGE)), "business details")
