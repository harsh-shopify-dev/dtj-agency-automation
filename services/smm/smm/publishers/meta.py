"""Instagram and the Facebook Page through Meta's Graph API (Facebook Login set-up: the Instagram account is linked to DTJ's Page).

Env: META_PAGE_TOKEN (a long-lived Page access token with pages_manage_posts, pages_read_engagement, instagram_basic,
instagram_content_publish, instagram_manage_insights), META_PAGE_ID, META_IG_USER_ID, META_GRAPH_VERSION (default v26.0).
"""
from __future__ import annotations

import json
import time
from typing import Callable, Mapping

from ..config import secret
from ..http import Http, PublishError
from . import Job

DEFAULT_VERSION = "v26.0"


def graph(env: Mapping[str, str]) -> str:
    return f"https://graph.facebook.com/{(env.get('META_GRAPH_VERSION') or DEFAULT_VERSION).strip()}"


def _wait_container(http: Http, base: str, cid: str, token: str, sleep: Callable[[float], None], polls: int = 30) -> None:
    """Meta: check status_code before publishing (FINISHED); a video can take minutes."""
    for _ in range(polls):
        status = http.json("GET", f"{base}/{cid}", params={"fields": "status_code,status", "access_token": token}).get("status_code")
        if status in ("FINISHED", "PUBLISHED"):
            return
        if status in ("ERROR", "EXPIRED"):
            raise PublishError(f"Instagram could not process the file (status {status})")
        sleep(10)
    raise PublishError("Instagram was still processing the file after 5 minutes")


def instagram(job: Job, http: Http, env: Mapping[str, str], sleep: Callable[[float], None] = time.sleep) -> dict:
    token, ig = secret("META_PAGE_TOKEN", env), secret("META_IG_USER_ID", env)
    base = graph(env)
    urls = job.public_urls()
    fmt = job.post["format"]
    common = {"access_token": token}
    if job.ai_label:
        common["is_ai_generated"] = "true"
    if fmt == "image":
        body = {"image_url": urls[0], "caption": job.texts["caption"], "alt_text": job.alts[0][:1000], **common}
    elif fmt == "carousel":
        children = []
        for url, alt in zip(urls, job.alts):
            child = http.json("POST", f"{base}/{ig}/media", data={"image_url": url, "is_carousel_item": "true",
                                                                   "alt_text": alt[:1000], "access_token": token})["id"]
            _wait_container(http, base, child, token, sleep)
            children.append(child)
        body = {"media_type": "CAROUSEL", "children": ",".join(children), "caption": job.texts["caption"], **common}
    elif fmt == "video":
        body = {"media_type": "REELS", "video_url": urls[0], "caption": job.texts["caption"], "share_to_feed": "true", **common}
    else:
        raise PublishError("Instagram does not take text-only posts")
    container = http.json("POST", f"{base}/{ig}/media", data=body)["id"]
    _wait_container(http, base, container, token, sleep)
    media_id = http.json("POST", f"{base}/{ig}/media_publish", data={"creation_id": container, "access_token": token})["id"]
    link = http.json("GET", f"{base}/{media_id}", params={"fields": "permalink", "access_token": token}).get("permalink", "")
    return {"id": media_id, "url": link}


def facebook(job: Job, http: Http, env: Mapping[str, str], sleep: Callable[[float], None] = time.sleep) -> dict:
    token, page = secret("META_PAGE_TOKEN", env), secret("META_PAGE_ID", env)
    base = graph(env)
    fmt = job.post["format"]
    caption = job.texts["caption"]
    if fmt == "text":
        post_id = http.json("POST", f"{base}/{page}/feed", data={"message": caption, "access_token": token})["id"]
    elif fmt == "image":
        post_id = http.json("POST", f"{base}/{page}/photos", data={"url": job.public_urls()[0], "caption": caption,
                                                                   "access_token": token})["post_id"]
    elif fmt == "carousel":
        ids = [http.json("POST", f"{base}/{page}/photos", data={"url": u, "published": "false", "access_token": token})["id"]
               for u in job.public_urls()]
        data = {"message": caption, "access_token": token}
        data.update({f"attached_media[{i}]": json.dumps({"media_fbid": fid}) for i, fid in enumerate(ids)})
        post_id = http.json("POST", f"{base}/{page}/feed", data=data)["id"]
    else:  # a reel: start, upload from the public link, wait, finish
        start = http.json("POST", f"{base}/{page}/video_reels", data={"upload_phase": "start", "access_token": token})
        vid = start["video_id"]
        version = base.rsplit("/", 1)[1]
        http.call("POST", f"https://rupload.facebook.com/video-upload/{version}/{vid}",
                  headers={"Authorization": f"OAuth {token}", "file_url": job.public_urls()[0]})
        for _ in range(30):
            status = http.json("GET", f"{base}/{vid}", params={"fields": "status", "access_token": token}).get("status", {})
            if status.get("video_status") in ("ready", "upload_complete") or status.get("uploading_phase", {}).get("status") == "complete":
                break
            if status.get("video_status") == "error":
                raise PublishError("Facebook could not process the video")
            sleep(10)
        finish = {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": caption, "access_token": token}
        if job.ai_label:
            finish["is_ai_generated"] = "true"
        http.json("POST", f"{base}/{page}/video_reels", data=finish)
        post_id = vid
    link = http.json("GET", f"{base}/{post_id}", params={"fields": "permalink_url", "access_token": token}).get("permalink_url", "")
    return {"id": post_id, "url": link}
