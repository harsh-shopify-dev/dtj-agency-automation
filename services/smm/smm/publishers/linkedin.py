"""LinkedIn company page through the Posts API (needs the Community Management API product, scope w_organization_social).

Env: LINKEDIN_TOKEN (60-day member token of a page admin), LINKEDIN_ORG_ID (the number in urn:li:organization:<id>),
LINKEDIN_VERSION (default 202610). The daily run warns 10 days before the token's end date in LINKEDIN_TOKEN_EXPIRES (YYYY-MM-DD).
"""
from __future__ import annotations

import re
import time
from typing import Callable, Mapping

from ..config import secret
from ..http import Http, PublishError
from . import Job

API = "https://api.linkedin.com/rest"
DEFAULT_VERSION = "202610"
_RESERVED = re.compile(r"([|{}@\[\]()<>#\\*_~])")


def little_text(text: str) -> str:
    """LinkedIn's 'little' text format: these characters must be escaped even in plain text."""
    return _RESERVED.sub(r"\\\1", text)


def _headers(env: Mapping[str, str]) -> dict:
    return {"Authorization": f"Bearer {secret('LINKEDIN_TOKEN', env)}", "LinkedIn-Version": (env.get("LINKEDIN_VERSION") or DEFAULT_VERSION).strip(),
            "X-Restli-Protocol-Version": "2.0.0", "Content-Type": "application/json"}


def _image(http: Http, env, owner: str, path) -> str:
    init = http.json("POST", f"{API}/images?action=initializeUpload", headers=_headers(env),
                     json={"initializeUploadRequest": {"owner": owner}})["value"]
    http.call("PUT", init["uploadUrl"], data=path.read_bytes(), headers={"Authorization": _headers(env)["Authorization"]})
    return init["image"]


def _video(http: Http, env, owner: str, path, sleep) -> str:
    data = path.read_bytes()
    init = http.json("POST", f"{API}/videos?action=initializeUpload", headers=_headers(env),
                     json={"initializeUploadRequest": {"owner": owner, "fileSizeBytes": len(data), "uploadCaptions": False,
                                                       "uploadThumbnail": False}})["value"]
    etags = []
    for part in init["uploadInstructions"]:
        r = http.call("PUT", part["uploadUrl"], data=data[part["firstByte"]:part["lastByte"] + 1],
                      headers={"Content-Type": "application/octet-stream"})
        etags.append(r.headers.get("ETag", "").strip('"'))
    http.call("POST", f"{API}/videos?action=finalizeUpload", headers=_headers(env),
              json={"finalizeUploadRequest": {"video": init["video"], "uploadToken": init.get("uploadToken", ""), "uploadedPartIds": etags}})
    from urllib.parse import quote
    for _ in range(30):
        status = http.json("GET", f"{API}/videos/{quote(init['video'], safe='')}", headers=_headers(env)).get("status")
        if status == "AVAILABLE":
            return init["video"]
        if status == "PROCESSING_FAILED":
            raise PublishError("LinkedIn could not process the video")
        sleep(10)
    raise PublishError("LinkedIn was still processing the video after 5 minutes")


def publish(job: Job, http: Http, env: Mapping[str, str], sleep: Callable[[float], None] = time.sleep) -> dict:
    owner = f"urn:li:organization:{secret('LINKEDIN_ORG_ID', env)}"
    body = {"author": owner, "commentary": little_text(job.texts["caption"]), "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
            "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
    fmt = job.post["format"]
    if fmt == "image":
        body["content"] = {"media": {"id": _image(http, env, owner, job.files[0]), "altText": job.alts[0][:4000]}}
    elif fmt == "carousel":
        body["content"] = {"multiImage": {"images": [{"id": _image(http, env, owner, f), "altText": a[:4000]}
                                                     for f, a in zip(job.files, job.alts)]}}
    elif fmt == "video":
        body["content"] = {"media": {"id": _video(http, env, owner, job.files[0], sleep), "title": job.post["id"]}}
    r = http.call("POST", f"{API}/posts", headers=_headers(env), json=body)
    urn = r.headers.get("x-restli-id", "")
    return {"id": urn, "url": f"https://www.linkedin.com/feed/update/{urn}" if urn else ""}
