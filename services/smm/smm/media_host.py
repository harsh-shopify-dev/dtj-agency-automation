"""Public links for Instagram and Facebook: they fetch the picture or video from a URL. The approved file is uploaded to DTJ's
WordPress media library (the same Editor login the SEO engine uses) at posting time, never before approval.

Env: WP_USER, WP_APP_PASSWORD, SMM_SITE (default https://digitaltusharjoshi.com).
"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Mapping

from .config import secret
from .http import Http

DEFAULT_SITE = "https://digitaltusharjoshi.com"


def upload(http: Http, env: Mapping[str, str], path: Path, name: str, alt: str = "") -> str:
    site = (env.get("SMM_SITE") or DEFAULT_SITE).rstrip("/")
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    auth = (secret("WP_USER", env), secret("WP_APP_PASSWORD", env))
    body = http.json("POST", f"{site}/wp-json/wp/v2/media", data=path.read_bytes(), auth=auth,
                     headers={"Content-Type": ctype, "Content-Disposition": f'attachment; filename="{name}"'})
    if alt:
        http.json("POST", f"{site}/wp-json/wp/v2/media/{body['id']}", json={"alt_text": alt[:500]}, auth=auth)
    return body["source_url"]
