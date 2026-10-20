"""X through the v2 API: media upload (api.x.com/2/media/upload) and POST /2/tweets.

Auth: OAuth 1.0a user context (an app key and secret plus DTJ's own access token and secret from the developer portal). These
do not expire, so no rotating refresh token has to be saved back after every run. [VERIFY on the first real post: X's v2 pages
show a generic user-token scheme; if OAuth 1.0a is refused, switch to OAuth 2.0 with offline.access.]
Env: X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET.
Cost (X's pricing page, 20 Oct 2026): pay per use, about $0.015 a post and $0.20 a post with a link. DTJ's posts carry the
audit link, so each X post costs about $0.20.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Callable, Mapping
from urllib.parse import quote

from ..config import secret
from ..http import Http, PublishError
from . import Job

API = "https://api.x.com/2"


def _pct(s: str) -> str:
    return quote(str(s), safe="~-._")


def oauth1_header(method: str, url: str, env: Mapping[str, str], params: dict | None = None,
                  nonce: str | None = None, timestamp: str | None = None) -> str:
    """OAuth 1.0a HMAC-SHA1 header. Only query and form params are signed (not JSON or multipart bodies)."""
    oauth = {"oauth_consumer_key": secret("X_API_KEY", env), "oauth_nonce": nonce or secrets.token_hex(16),
             "oauth_signature_method": "HMAC-SHA1", "oauth_timestamp": timestamp or str(int(time.time())),
             "oauth_token": secret("X_ACCESS_TOKEN", env), "oauth_version": "1.0"}
    allp = {**(params or {}), **oauth}
    base_params = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted(allp.items()))
    base = "&".join([method.upper(), _pct(url.split("?")[0]), _pct(base_params)])
    key = f"{_pct(secret('X_API_SECRET', env))}&{_pct(secret('X_ACCESS_SECRET', env))}"
    oauth["oauth_signature"] = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))


def _upload(http: Http, env, path, sleep) -> str:
    data = path.read_bytes()
    if path.suffix.lower() != ".mp4":
        url = f"{API}/media/upload"
        r = http.json("POST", url, headers={"Authorization": oauth1_header("POST", url, env)},
                      files={"media": (path.name, data)}, data={"media_category": "tweet_image"})
        return r["data"]["id"]
    url = f"{API}/media/upload/initialize"
    init = http.json("POST", url, headers={"Authorization": oauth1_header("POST", url, env)},
                     json={"media_type": "video/mp4", "total_bytes": len(data), "media_category": "tweet_video"})
    mid = init["data"]["id"]
    step = 4 * 1024 * 1024
    for i in range(0, len(data), step):
        url = f"{API}/media/upload/{mid}/append"
        http.call("POST", url, headers={"Authorization": oauth1_header("POST", url, env)},
                  files={"media": ("part", data[i:i + step])}, data={"segment_index": str(i // step)})
    url = f"{API}/media/upload/{mid}/finalize"
    info = http.json("POST", url, headers={"Authorization": oauth1_header("POST", url, env)}).get("data", {}).get("processing_info")
    for _ in range(30):
        if not info or info.get("state") == "succeeded":
            return mid
        if info.get("state") == "failed":
            raise PublishError("X could not process the video")
        sleep(info.get("check_after_secs", 5))
        url = f"{API}/media/upload"
        params = {"command": "STATUS", "media_id": mid}
        info = http.json("GET", url, params=params,
                         headers={"Authorization": oauth1_header("GET", url, env, params)}).get("data", {}).get("processing_info")
    raise PublishError("X was still processing the video")


def publish(job: Job, http: Http, env: Mapping[str, str], sleep: Callable[[float], None] = time.sleep) -> dict:
    body: dict = {"text": job.texts["text"]}
    if job.post["format"] != "text":
        body["media"] = {"media_ids": [_upload(http, env, f, sleep) for f in job.files[:4]]}
    if job.ai_label:
        body["made_with_ai"] = True
    url = f"{API}/tweets"
    tid = http.json("POST", url, headers={"Authorization": oauth1_header("POST", url, env)}, json=body)["data"]["id"]
    return {"id": tid, "url": f"https://x.com/i/web/status/{tid}"}
