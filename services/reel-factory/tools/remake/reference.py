"""Get the reference reel's video for a remake: reference.py <link> <out.mp4>

- A direct video link (.mp4, a CDN link): downloaded as it is (fetch.py rules: https, media only).
- An Instagram reel / post link: one Apify run of apify/instagram-scraper (directUrls, 1 result, $0.05 cap), then its
  videoUrl is downloaded. The token comes only from the environment (APIFY_TOKEN, set on the VPS with tools/vps/set_key.py);
  it is never printed. Same actor family as n8n "Reel Factory: Find References" (PR #84).
Prints one JSON line {"ok": true, "path", "source", "caption", "owner"} or {"ok": false, "error"}; exit 0 / 1.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch  # noqa: E402

ACTOR = "apify~instagram-scraper"
CAP_USD = "0.05"


def instagram(link: str, token: str, opener=urllib.request.urlopen) -> dict:
    url = (f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items?"
           + urllib.parse.urlencode({"maxItems": 1, "maxTotalChargeUsd": CAP_USD, "timeout": 240}))
    body = json.dumps({"directUrls": [link], "resultsType": "posts", "resultsLimit": 1, "addParentData": False}).encode()
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    with opener(req, timeout=300) as r:
        items = json.loads(r.read() or b"[]")
    item = items[0] if items else {}
    return {"video": item.get("videoUrl") or "", "caption": (item.get("caption") or "")[:300], "owner": item.get("ownerUsername") or ""}


def main(link: str, out: Path) -> dict:
    if "instagram.com/" not in link:
        res = fetch(link, out)
        return dict(res, source="direct") if res["ok"] else res
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        return {"ok": False, "error": "APIFY_TOKEN is not set on this machine (Harsh: python tools/vps/set_key.py APIFY_TOKEN)"}
    try:
        got = instagram(link, token)
    except Exception as exc:  # noqa: BLE001 - never echo the request (it carries the token)
        return {"ok": False, "error": f"Apify did not answer ({type(exc).__name__})"}
    if not got["video"]:
        return {"ok": False, "error": "Apify found no video for that link (private, removed, or not a reel)"}
    res = fetch(got["video"], out)
    return dict(res, source="apify instagram", caption=got["caption"], owner=got["owner"]) if res["ok"] else res


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({"ok": False, "error": "usage: reference.py <link> <out.mp4>"}))
        raise SystemExit(1)
    r = main(sys.argv[1], Path(sys.argv[2]))
    print(json.dumps(r, ensure_ascii=False))
    raise SystemExit(0 if r["ok"] else 1)
