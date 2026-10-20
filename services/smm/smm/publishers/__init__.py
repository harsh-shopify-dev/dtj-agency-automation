"""One publisher per platform. Each takes the approved post, its final words and its files, posts it, and returns
{"id": ..., "url": ...}. Tokens are read from the environment at call time and never logged.

Every publisher follows the platform's official API (facts and doc links in docs/smm/README.md, "Platform facts", checked
20 Oct 2026). Instagram and Facebook fetch pictures and videos from a public link, so those files go to DTJ's WordPress
media library first (media_host.py), only after approval and only at posting time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping


@dataclass
class Job:
    post: dict                    # the post from week.json
    texts: dict[str, str]         # final words for this platform (link and hashtags in)
    files: list[Path]             # local files, in order
    alts: list[str]               # alt text per file
    public_urls: Callable[[], list[str]] = field(default=lambda: [])   # uploads the files and returns their public links

    @property
    def ai_label(self) -> bool:
        ai = self.post.get("ai_media") or {}
        return bool(ai.get("label_on") or ai.get("realistic_person"))


def publisher(platform: str) -> Callable[[Job, object, Mapping[str, str]], dict]:
    from . import linkedin, meta, x, youtube
    return {"instagram": meta.instagram, "facebook": meta.facebook, "linkedin": linkedin.publish,
            "youtube": youtube.publish, "x": x.publish}[platform]


NEEDS = {
    "instagram": ["META_PAGE_TOKEN", "META_IG_USER_ID", "WP_USER", "WP_APP_PASSWORD"],
    "facebook": ["META_PAGE_TOKEN", "META_PAGE_ID", "WP_USER", "WP_APP_PASSWORD"],
    "linkedin": ["LINKEDIN_TOKEN", "LINKEDIN_ORG_ID"],
    "youtube": ["YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"],
    "x": ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"],
}


def missing(platform: str, env: Mapping[str, str]) -> list[str]:
    return [name for name in NEEDS[platform] if not (env.get(name) or "").strip()]
