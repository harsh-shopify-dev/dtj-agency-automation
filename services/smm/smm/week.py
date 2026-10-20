"""One week of posts: a folder `weeks/<YYYY-Www>/` in the content store holding week.json and media/.

The fingerprint of a post covers its whole entry in week.json and the bytes of every file it uses. An approval stores it, and the
daily run posts only when the post still has the same fingerprint (a changed word or picture needs a new yes).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from jsonschema import Draft202012Validator

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "smm-week.schema.json"
LINK = "{link}"


class WeekError(Exception):
    pass


@dataclass
class Week:
    folder: Path
    data: dict

    @property
    def name(self) -> str:
        return self.data["week"]

    @property
    def posts(self) -> list[dict]:
        return self.data["posts"]

    def post(self, post_id: str) -> dict:
        for p in self.posts:
            if p["id"] == post_id:
                return p
        raise WeekError(f"{self.name} has no post {post_id}")

    def media_path(self, item: dict) -> Path:
        return self.folder / item["file"]

    def fingerprint(self, post: dict) -> str:
        h = hashlib.sha256(json.dumps(post, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        for item in post["media"]:
            path = self.media_path(item)
            h.update(item["file"].encode())
            h.update(path.read_bytes() if path.exists() else b"<missing>")
        return h.hexdigest()


def schema_errors(data: dict) -> list[str]:
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    return [f"{'/'.join(str(x) for x in e.absolute_path) or 'week'}: {e.message}" for e in validator.iter_errors(data)]


def load(folder: str | Path) -> Week:
    folder = Path(folder)
    path = folder / "week.json"
    if not path.exists():
        raise WeekError(f"no week.json in {folder}")
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = schema_errors(data)
    if errors:
        raise WeekError("week.json does not match the format:\n  " + "\n  ".join(errors[:20]))
    if folder.name != data["week"]:
        raise WeekError(f"folder {folder.name} holds week {data['week']}")
    return Week(folder, data)


def publish_time(post: dict) -> datetime:
    return datetime.fromisoformat(post["publish_at"])


def tracked_link(audit_url: str, platform: str, post_id: str) -> str:
    return f"{audit_url}?{urlencode({'utm_source': platform, 'utm_medium': 'social', 'utm_campaign': 'dtj-organic', 'utm_content': post_id})}"


def final_text(post: dict, platform: str, audit_url: str) -> dict[str, str]:
    """The exact words that go out on this platform: {link} becomes the tracked audit link, hashtags go on the end."""
    spec = post["platforms"][platform]
    link = tracked_link(audit_url, platform, post["id"])
    out = {}
    for key, value in spec.items():
        if isinstance(value, str):
            out[key] = value.replace(LINK, link)
    tags = spec.get("hashtags") or []
    if tags and "caption" in out:
        out["caption"] = out["caption"].rstrip() + "\n\n" + " ".join(tags)
    return out
