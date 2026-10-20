"""Step 9: read each posted item's numbers from the platform at 24 hours and at 7 days, and write the Monday report.

Numbers come only from the platform's API response, saved with the endpoint they came from (CLAUDE.md rule 4). What we cannot
read yet is written as "not available" with the reason, never estimated.

    Instagram: GET /{media-id}/insights   views, reach, likes, comments, saved, shares, total_interactions (Meta, v26.0)
    Facebook:  GET /{post-id}/insights    post_media_view, post_total_media_view_unique, post_clicks, post_reactions_by_type_total
    YouTube:   videos.list part=statistics   viewCount, likeCount, commentCount
    LinkedIn, X: not read yet (LinkedIn needs the page-statistics permission; X charges per read)
    Audit-form leads from social (utm_medium=social): not available until the leads sheet is connected

    python -m smm results [--store DIR] [--report]
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Mapping

from .config import IST
from .http import Http, PublishError
from .publishers import meta, youtube
from .store import Store

MARKS = {"24h": timedelta(hours=24), "7d": timedelta(days=7)}
IG_METRICS = ["views", "reach", "likes", "comments", "saved", "shares", "total_interactions"]
FB_METRICS = ["post_media_view", "post_total_media_view_unique", "post_clicks", "post_reactions_by_type_total"]
WORDS = {"views": "views", "reach": "people reached", "likes": "likes", "comments": "comments", "saved": "saves", "shares": "shares",
         "total_interactions": "total interactions", "post_media_view": "views", "post_total_media_view_unique": "people reached",
         "post_clicks": "clicks", "post_reactions_by_type_total": "reactions", "viewCount": "views", "likeCount": "likes",
         "commentCount": "comments"}
NOT_READ = {"linkedin": "not available: LinkedIn page statistics need an extra permission (r_organization_social)",
            "x": "not available: X charges per read; switched off to keep costs down"}


def fetch(platform: str, item_id: str, http: Http, env: Mapping[str, str]) -> tuple[dict, str]:
    if platform == "instagram":
        url = f"{meta.graph(env)}/{item_id}/insights"
        body = http.json("GET", url, params={"metric": ",".join(IG_METRICS), "access_token": env["META_PAGE_TOKEN"]})
    elif platform == "facebook":
        url = f"{meta.graph(env)}/{item_id}/insights"
        body = http.json("GET", url, params={"metric": ",".join(FB_METRICS), "access_token": env["META_PAGE_TOKEN"]})
    elif platform == "youtube":
        url = "https://www.googleapis.com/youtube/v3/videos"
        token = youtube.access_token(http, env)
        items = http.json("GET", url, params={"part": "statistics", "id": item_id}, headers={"Authorization": f"Bearer {token}"})["items"]
        return ({k: int(v) for k, v in items[0]["statistics"].items() if k in WORDS} if items else {}), f"GET {url} part=statistics"
    else:
        raise PublishError(NOT_READ[platform])
    numbers = {}
    for row in body.get("data", []):
        value = (row.get("values") or [{}])[0].get("value", row.get("total_value", {}).get("value"))
        if isinstance(value, dict):
            value = sum(v for v in value.values() if isinstance(v, (int, float)))
        if isinstance(value, (int, float)):
            numbers[row["name"]] = value
    return numbers, f"GET {url} metric={','.join(IG_METRICS if platform == 'instagram' else FB_METRICS)}"


def pull(store: Store, env: Mapping[str, str], http: Http | None = None, now: datetime | None = None, out=print) -> int:
    http, now = http or Http(), now or datetime.now(timezone.utc)
    pulled = 0
    for week in store.week_names():
        folder = store.week_folder(week) / "published"
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.json")):
            pid, platform = path.stem.rsplit(".", 1)
            rec = store.read(path)
            age = now - datetime.fromisoformat(rec["at"])
            for mark, wait in MARKS.items():
                target = store.path(week, "results", pid, platform, mark)
                if age < wait or target.exists() or age > wait + timedelta(days=3):
                    continue
                if platform in NOT_READ:
                    store.write(target, {"post_id": pid, "platform": platform, "mark": mark, "numbers": {}, "note": NOT_READ[platform]})
                    continue
                try:
                    numbers, source = fetch(platform, rec["id"], http, env)
                except (PublishError, KeyError) as e:
                    out(f"{pid} {platform} {mark}: could not read the numbers: {str(e)[:200]}")
                    continue
                store.write(target, {"post_id": pid, "platform": platform, "mark": mark, "numbers": numbers, "source": source,
                                     "fetched_at": now.isoformat(), "url": rec.get("url", "")})
                pulled += 1
    return pulled


def report(store: Store, week: str) -> str:
    """The Monday report for one week, in plain words. Every number names where it came from."""
    lines = [f"DTJ social media: results for {week}", ""]
    folder = store.week_folder(week) / "results"
    rows = [store.read(p) for p in sorted(folder.glob("*.json"))] if folder.exists() else []
    if not rows:
        return "\n".join(lines + ["No results yet: nothing from this week has been posted by code for 24 hours or more."])
    best: dict[str, tuple[int, str]] = {}
    for r in rows:
        name = f"{r['post_id']} on {r['platform'].capitalize()} after {r['mark']}"
        if not r["numbers"]:
            lines.append(f"- {name}: {r.get('note', 'no numbers returned')}")
            continue
        parts = ", ".join(f"{v:,} {WORDS.get(k, k)}" for k, v in r["numbers"].items())
        lines.append(f"- {name}: {parts}. Source: {r['platform'].capitalize()} API ({r['source'].split(' metric')[0]}), "
                     f"read {r['fetched_at'][:16].replace('T', ' ')} UTC.")
        views = r["numbers"].get("views") or r["numbers"].get("post_media_view") or r["numbers"].get("viewCount")
        if r["mark"] == "7d" and views is not None and views > best.get(r["platform"], (-1, ""))[0]:
            best[r["platform"]] = (views, r["post_id"])
    lines.append("")
    for platform, (views, pid) in best.items():
        lines.append(f"Most viewed on {platform.capitalize()} after 7 days: {pid} ({views:,} views).")
    lines += ["", "Leads from social (audit forms with utm_medium=social): not available until the leads sheet is connected.",
              "Next: the content session reads this report and suggests keep / change / stop for next week's posts."]
    return "\n".join(lines)


def last_week(now: datetime | None = None) -> str:
    now = now or datetime.now(IST)
    return (now - timedelta(weeks=1)).strftime("%G-W%V")
