"""Send pictures and videos to Telegram (the store factory only sends text; a reel's pictures and the finished reel must be seen
in Telegram before anyone approves them, Harsh 25 Oct 2026).

    upload(token, "sendPhoto", {"chat_id": c, "caption": "..."}, {"photo": Path("p01.png")})
    album(token, chat, [Path(...), ...], captions)      up to 10 per message group (Telegram's limit), several groups if more
    video(token, chat, Path("reel.mp4"), caption)       sendVideo; a file over 48 MB is sent as a smaller copy (ffmpeg), the
                                                        full file stays on the VPS

Plain multipart/form-data with urllib (no extra package). Best effort with one retry; returns Telegram's "result" ({} or [] when it
failed). The token is only ever part of the request URL and is never printed or logged.
"""
from __future__ import annotations

import json
import mimetypes
import subprocess
import uuid
import urllib.error
import urllib.request
from pathlib import Path

MAX_BYTES = 48 * 1024 * 1024     # Telegram bots may upload 50 MB; keep a margin
TIMEOUT = 180


def _form(fields: dict, files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = "dtj" + uuid.uuid4().hex
    out = bytearray()
    for name, value in fields.items():
        if value is None:
            continue
        if not isinstance(value, str):
            value = json.dumps(value)
        out += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
    for name, path in files.items():
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{path.name}\"\r\n"
                f"Content-Type: {kind}\r\n\r\n").encode()
        out += path.read_bytes() + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def _post(url: str, body: bytes, kind: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=body, headers={"Content-Type": kind}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {}
    except (urllib.error.URLError, OSError, ValueError):
        return 0, {}


def upload(token: str, method: str, fields: dict, files: dict[str, Path], post=_post):
    if not token:
        return {}
    body, kind = _form(fields, files)
    for _ in range(2):                       # one retry (CLAUDE.md self-healing)
        status, got = post(f"https://api.telegram.org/bot{token}/{method}", body, kind)
        if status == 200 and got.get("ok"):
            return got.get("result") or {}
        if status == 400:                    # a bad request does not get better on a retry
            break
    return {}


def album(token: str, chat: str, pictures: list[Path], captions: list[str] | None = None, post=_post) -> list:
    """Pictures in groups of 10, each with its caption (its number and name); returns the sent messages."""
    sent = []
    captions = captions or [p.stem for p in pictures]
    for start in range(0, len(pictures), 10):
        group = pictures[start:start + 10]
        media = [{"type": "photo", "media": f"attach://f{i}", "caption": captions[start + i][:1000]} for i in range(len(group))]
        if len(group) == 1:
            got = upload(token, "sendPhoto", {"chat_id": chat, "caption": media[0]["caption"]}, {"photo": group[0]}, post)
            sent += [got] if got else []
            continue
        got = upload(token, "sendMediaGroup", {"chat_id": chat, "media": media},
                     {f"f{i}": p for i, p in enumerate(group)}, post)
        sent += got if isinstance(got, list) else []
    return sent


def smaller(path: Path, run=subprocess.run) -> Path:
    """A copy under 48 MB for review in Telegram (the full file stays as it is)."""
    if path.stat().st_size <= MAX_BYTES:
        return path
    out = path.with_name(path.stem + "_telegram.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-c:v", "libx264", "-crf", "28", "-preset", "veryfast",
         "-vf", "scale=720:-2", "-c:a", "aac", "-b:a", "128k", str(out)], check=False)
    return out if out.exists() and out.stat().st_size <= MAX_BYTES else path


def download(token: str, file_id: str, out_dir: Path, opener=urllib.request.urlopen) -> Path | None:
    """A photo someone sent to the bot (its file_id, "tg:<id>" in the request) saved into out_dir; None when Telegram refuses."""
    if not token:
        return None
    try:
        with opener(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}", timeout=30) as r:
            info = json.loads(r.read() or b"{}")
        path = (info.get("result") or {}).get("file_path") or ""
        if not info.get("ok") or not path:
            return None
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"tg_{file_id[-12:]}{Path(path).suffix or '.jpg'}"
        with opener(f"https://api.telegram.org/file/bot{token}/{path}", timeout=60) as r:
            dest.write_bytes(r.read())
        return dest
    except (urllib.error.URLError, OSError, ValueError):
        return None                          # never repeat the URL: it carries the token


def video(token: str, chat: str, path: Path, caption: str = "", post=_post, run=subprocess.run) -> dict:
    f = smaller(path, run)
    return upload(token, "sendVideo", {"chat_id": chat, "caption": caption[:1000], "supports_streaming": "true"},
                  {"video": f}, post)
