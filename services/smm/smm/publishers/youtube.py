"""YouTube Shorts through the YouTube Data API (resumable videos.insert, scope youtube.upload).

Env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (made once by a person signing in to DTJ's channel; the Google Cloud app must
be "In production", or Google drops the refresh token after 7 days).
A vertical video of 3 minutes or less becomes a Short. Google's own pages disagree on whether uploads from an unaudited API
project are forced to private (20 Oct 2026); the result's privacy is read back and reported, so the first real upload settles it.
"""
from __future__ import annotations

import json
from typing import Mapping

from ..config import secret
from ..http import Http, PublishError
from . import Job


def access_token(http: Http, env: Mapping[str, str]) -> str:
    return http.json("POST", "https://oauth2.googleapis.com/token",
                     data={"client_id": secret("YT_CLIENT_ID", env), "client_secret": secret("YT_CLIENT_SECRET", env),
                           "refresh_token": secret("YT_REFRESH_TOKEN", env), "grant_type": "refresh_token"})["access_token"]


def publish(job: Job, http: Http, env: Mapping[str, str]) -> dict:
    if job.post["format"] != "video":
        raise PublishError("YouTube takes only video posts")
    token = access_token(http, env)
    data = job.files[0].read_bytes()
    meta = {"snippet": {"title": job.texts["title"].replace("<", "").replace(">", ""),
                        "description": job.texts.get("description", "").replace("<", "").replace(">", ""),
                        "tags": job.post["platforms"]["youtube"].get("tags", []), "categoryId": "22"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": job.ai_label}}
    start = http.call("POST", "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Length": str(len(data)), "X-Upload-Content-Type": "video/mp4"},
                      data=json.dumps(meta))
    upload_url = start.headers.get("Location")
    if not upload_url:
        raise PublishError("YouTube did not give an upload link")
    video = http.call("PUT", upload_url, data=data, headers={"Content-Type": "video/mp4"}, ok=(200, 201)).json()
    privacy = video.get("status", {}).get("privacyStatus", "")
    out = {"id": video["id"], "url": f"https://www.youtube.com/shorts/{video['id']}"}
    if privacy and privacy != "public":
        out["warning"] = f"YouTube saved it as {privacy}: the API project may need Google's audit before uploads can be public"
    return out
