"""Put pictures from this laptop into a store through Shopify's own staged upload, so a product can show them (22 Oct 2026, the
new-store branch: a client's pictures from their Google Drive folder, and the pictures ChatGPT makes for sample products and banners).

The store's key never comes here. The install service (POST /copy, op "uploads", src/copy.js) asks Shopify with DTJ Store Builder's
key for one-time upload addresses; this module sends each picture's bytes straight to that address (Shopify's storage, not the store)
and gives back its resourceUrl. A copy plan names that resourceUrl as the product picture's originalSource, and the picture becomes
part of the product only when the copy runs after its Approve tap. An upload by itself changes nothing in the store.

    from provision.staged_upload import upload
    urls = upload([Path("1.jpg"), Path("2.png")], call=store_job._catcher, shop="dtj-testing.myshopify.com")
        {"<local path>": "https://shopify-staged-uploads.storage.googleapis.com/...", ...}

Only jpg, png, webp and gif (at most 20 MB each, the install service's own limits); 50 addresses per call to the install service; a
send that fails on a dropped connection or a 5xx is tried again (3 tries, growing pause), anything else stops with the reason.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Callable

TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
MAX_BYTES = 20 * 1024 * 1024
PER_CALL = 50
TRIES = 3

Poster = Callable[[str, list, str, bytes, str], int]  # url, [(name, value)], file name, bytes, mime -> HTTP status


class UploadError(RuntimeError):
    pass


def mime_type(path: Path) -> str:
    mime = TYPES.get(path.suffix.lower())
    if not mime:
        raise ValueError(f"{path.name}: only jpg, png, webp or gif pictures can go to a product")
    return mime


def multipart_body(fields: list, filename: str, data: bytes, mime: str) -> tuple[bytes, str]:
    """multipart/form-data: every parameter Shopify gave first, the file last (its storage reads the fields before the file)."""
    boundary = f"dtj{uuid.uuid4().hex}"
    parts = []
    for name, value in fields:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8"))
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                 f"Content-Type: {mime}\r\n\r\n".encode("utf-8") + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def multipart_post(url: str, fields: list, filename: str, data: bytes, mime: str) -> int:
    body, ctype = multipart_body(fields, filename, data, mime)
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": ctype, "User-Agent": "dtj-store-factory"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _send(post: Poster, target: dict, path: Path, data: bytes, mime: str, sleep) -> None:
    fields = [(p["name"], p["value"]) for p in target.get("parameters") or []]
    for attempt in range(1, TRIES + 1):
        try:
            status = post(target["url"], fields, target.get("filename") or path.name, data, mime)
        except (urllib.error.URLError, OSError) as exc:  # a dropped connection: tried again
            if attempt >= TRIES:
                raise UploadError(f"{path.name}: Shopify's upload address did not answer ({exc})") from exc
            sleep(2 * attempt)
            continue
        if 200 <= status < 300:
            return
        if status >= 500 and attempt < TRIES:
            sleep(2 * attempt)
            continue
        raise UploadError(f"{path.name}: Shopify's upload address refused it (HTTP {status})")


def upload(paths: list, call: Callable[[dict], dict], shop: str, post: Poster = multipart_post, sleep=time.sleep) -> dict[str, str]:
    """Every picture's local path (str) -> its resourceUrl. A picture already sent in this run is sent once."""
    files = []
    for p in dict.fromkeys(Path(x) for x in paths):
        size = p.stat().st_size
        if not 0 < size <= MAX_BYTES:
            raise ValueError(f"{p.name}: {size} bytes; a product picture must be between 1 byte and 20 MB")
        files.append((p, mime_type(p), size))
    out: dict[str, str] = {}
    for i in range(0, len(files), PER_CALL):
        batch = files[i:i + PER_CALL]
        got = call({"op": "uploads", "shop": shop, "files": [{"filename": p.name, "mimeType": m, "fileSize": n} for p, m, n in batch]})
        targets = got.get("targets") or []
        if len(targets) != len(batch):
            raise UploadError(f"the install service gave {len(targets)} upload addresses for {len(batch)} pictures "
                              f"({got.get('userErrors') or 'no reason given'})")
        for (p, mime, _), target in zip(batch, targets):
            if not target.get("url") or not target.get("resourceUrl"):
                raise UploadError(f"{p.name}: Shopify gave no upload address ({got.get('userErrors') or 'no reason given'})")
            _send(post, target, p, p.read_bytes(), mime, sleep)
            out[str(p)] = target["resourceUrl"]
    return out
