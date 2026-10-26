"""Download one file for a reel job (a reference video, a Flow clip, a product picture, music): fetch.py <https url> <out file>

The VPS session has no curl (CLAUDE.md: network tools stay denied); this is the one download it may run. https only, at most
300 MB, and the answer must be a picture, video or audio file (an HTML page, e.g. a sign-in wall or a Drive preview, is refused,
not saved as .mp4). Prints one JSON line {"ok": true, "path", "bytes", "type"} or {"ok": false, "error"}; exit 0 / 1.
"""
import json
import sys
import urllib.request
from pathlib import Path

MAX = 300 * 1024 * 1024
KINDS = ("video/", "image/", "audio/", "application/octet-stream", "binary/octet-stream")


def fetch(url: str, out: Path, opener=urllib.request.urlopen) -> dict:
    if not url.startswith("https://"):
        return {"ok": False, "error": "https links only"}
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (DTJ reel factory)"})
    try:
        with opener(req, timeout=120) as r:
            kind = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if not kind.startswith(KINDS):
                return {"ok": False, "error": f"not a media file ({kind or 'no type'}): a sign-in page or a preview page?"}
            out.parent.mkdir(parents=True, exist_ok=True)
            n = 0
            with out.open("wb") as fh:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    n += len(chunk)
                    if n > MAX:
                        fh.close()
                        out.unlink(missing_ok=True)
                        return {"ok": False, "error": "larger than 300 MB"}
                    fh.write(chunk)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:300]}
    return {"ok": True, "path": str(out), "bytes": n, "type": kind}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(json.dumps({"ok": False, "error": "usage: fetch.py <https url> <out file>"}))
        raise SystemExit(1)
    res = fetch(sys.argv[1], Path(sys.argv[2]))
    print(json.dumps(res))
    raise SystemExit(0 if res["ok"] else 1)
