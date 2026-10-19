"""Put a folder into Google Drive (Harsh's Gmail Drive, 19 Oct 2026: "Google OAuth") with DTJ's own Google app. The app has the
`drive.file` permission only: it sees and changes nothing in the Drive except the folders and files it created itself.

One-time, by Harsh in his OWN PowerShell, after making the Google app (steps: .claude/skills/dtj-brand-intake/SKILL.md, "Setup"):
    cd services/store-builder
    python -m page_builder.drive_upload --authorize --client-file <the client_secret_....json Google gave you>
        opens Google's consent page in the browser (sign in with the Gmail that owns the Drive); saves DTJ_GDRIVE_CLIENT_ID,
        DTJ_GDRIVE_CLIENT_SECRET and DTJ_GDRIVE_REFRESH_TOKEN in the Windows user settings. The values are never shown.
        Back them up for the team: python tools/team-setup/vault.py push DTJ_GDRIVE_CLIENT_ID DTJ_GDRIVE_CLIENT_SECRET DTJ_GDRIVE_REFRESH_TOKEN
Every upload:
    python -m page_builder.drive_upload <local folder> --to "DTJ Clients/Free Soul/Brand intake 2026-10-19"
        makes the folders that are missing, uploads every file (sub-folders mirrored), skips a file the Drive folder already has
        (a re-run sends only what is new), sends big videos in 8 MB pieces, and prints the folder's link.
Exit 0 = uploaded, 1 = could not (the reason is printed; a secret never is).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import http.server as httpserver
import json
import mimetypes
import os
import secrets as pysecrets
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser
from pathlib import Path
from typing import Callable

SCOPE = "https://www.googleapis.com/auth/drive.file"  # only what this app creates: non-sensitive, so the app can be "in production"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
API = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"
VARS = ("DTJ_GDRIVE_CLIENT_ID", "DTJ_GDRIVE_CLIENT_SECRET", "DTJ_GDRIVE_REFRESH_TOKEN")
SMALL = 5 * 1024 * 1024  # up to this a file goes in one request; bigger ones (videos) in pieces
CHUNK = 8 * 1024 * 1024  # a multiple of 256 KB, as Drive asks

# (method, url, headers, body) -> (status, response headers, body). Swappable so the tests never reach Google.
Http = Callable[[str, str, dict, "bytes | None"], tuple[int, dict, bytes]]


class DriveError(Exception):
    pass


def _http(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as exc:  # Drive's error body explains what went wrong; keep it
        return exc.code, dict(exc.headers or {}), exc.read()


def _env() -> dict:
    """The three keys: from this process, else from the Windows user settings (a key saved a minute ago counts)."""
    out = {k: os.environ.get(k, "") for k in VARS}
    if os.name == "nt" and not all(out.values()):
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                for k in VARS:
                    if not out[k]:
                        try:
                            out[k] = str(winreg.QueryValueEx(key, k)[0])
                        except OSError:
                            pass
        except OSError:
            pass
    return out


class Drive:
    def __init__(self, keys: dict | None = None, http: Http = _http):
        self.keys = keys if keys is not None else _env()
        missing = [k for k in VARS if not self.keys.get(k)]
        if missing:
            raise DriveError(f"not set up on this laptop: {', '.join(missing)} missing (run --authorize once, or vault.py pull)")
        self.http = http
        self._token = ""

    # ---- the access token (an hour long), from the stored refresh token
    def token(self) -> str:
        if not self._token:
            body = urllib.parse.urlencode({"client_id": self.keys["DTJ_GDRIVE_CLIENT_ID"], "client_secret": self.keys["DTJ_GDRIVE_CLIENT_SECRET"],
                                           "refresh_token": self.keys["DTJ_GDRIVE_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
            status, _, data = self.http("POST", TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"}, body)
            if status != 200:
                reason = json.loads(data or b"{}").get("error", status) if data[:1] == b"{" else status
                raise DriveError(f"Google refused the stored login ({reason}): run --authorize again")
            self._token = json.loads(data)["access_token"]
        return self._token

    def call(self, method: str, url: str, body: bytes | None = None, headers: dict | None = None) -> tuple[int, dict, bytes]:
        h = {"Authorization": f"Bearer {self.token()}", **(headers or {})}
        for attempt in range(3):  # CLAUDE.md self-healing: 429 / 5xx retried, at most 3 tries
            status, rh, data = self.http(method, url, h, body)
            if status not in (429, 500, 502, 503, 504):
                return status, rh, data
        return status, rh, data

    def _json(self, method: str, url: str, payload: dict | None = None) -> dict:
        status, _, data = self.call(method, url, json.dumps(payload).encode() if payload is not None else None,
                                    {"Content-Type": "application/json; charset=UTF-8"} if payload is not None else None)
        if status not in (200, 201):
            raise DriveError(f"Drive answered {status}: {data[:300].decode('utf-8', 'replace')}")
        return json.loads(data or b"{}")

    # ---- folders
    def children(self, parent: str, folders_only: bool = False) -> dict[str, dict]:
        q = f"'{parent}' in parents and trashed = false" + (f" and mimeType = '{FOLDER}'" if folders_only else "")
        out, page = {}, ""
        while True:
            url = f"{API}?" + urllib.parse.urlencode({"q": q, "fields": "nextPageToken,files(id,name,mimeType,webViewLink)", "pageSize": 1000,
                                                      **({"pageToken": page} if page else {})})
            res = self._json("GET", url)
            out.update({f["name"]: f for f in res.get("files", [])})
            page = res.get("nextPageToken", "")
            if not page:
                return out

    def folder(self, name: str, parent: str) -> dict:
        found = self.children(parent, folders_only=True).get(name)
        if found:
            return found
        return self._json("POST", f"{API}?fields=id,name,webViewLink", {"name": name, "mimeType": FOLDER, "parents": [parent]})

    def path(self, drive_path: str) -> dict:
        """'DTJ Clients/Free Soul/Brand intake 2026-10-19' -> that folder (made where missing), from the top of My Drive."""
        node = {"id": "root"}
        for part in [p.strip() for p in drive_path.replace("\\", "/").split("/") if p.strip()]:
            node = self.folder(part, node["id"])
        return node

    # ---- files
    def upload(self, local: Path, parent: str) -> dict:
        mime = mimetypes.guess_type(local.name)[0] or "application/octet-stream"
        meta = json.dumps({"name": local.name, "parents": [parent]}).encode()
        size = local.stat().st_size
        if size <= SMALL:
            boundary = "dtj" + uuid.uuid4().hex
            body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode() + meta
                    + f"\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n".encode() + local.read_bytes() + f"\r\n--{boundary}--".encode())
            status, _, data = self.call("POST", f"{UPLOAD}?uploadType=multipart&fields=id,name",
                                        body, {"Content-Type": f"multipart/related; boundary={boundary}"})
            if status not in (200, 201):
                raise DriveError(f"{local.name}: Drive answered {status}: {data[:200].decode('utf-8', 'replace')}")
            return json.loads(data)
        status, headers, data = self.call("POST", f"{UPLOAD}?uploadType=resumable&fields=id,name", meta,
                                          {"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": mime,
                                           "X-Upload-Content-Length": str(size)})
        where = {k.lower(): v for k, v in headers.items()}.get("location")
        if status != 200 or not where:
            raise DriveError(f"{local.name}: Drive would not start the upload ({status})")
        with local.open("rb") as fh:
            sent = 0
            while sent < size:
                piece = fh.read(CHUNK)
                end = sent + len(piece) - 1
                status, _, data = self.call("PUT", where, piece, {"Content-Range": f"bytes {sent}-{end}/{size}"})
                if status not in (200, 201, 308):
                    raise DriveError(f"{local.name}: a piece failed ({status})")
                sent = end + 1
        return json.loads(data or b"{}")

    def upload_tree(self, local_dir: Path, drive_path: str, out=print, tick=None) -> dict:
        """Mirror a local folder into the Drive path. Files the Drive folder already has (same name) are skipped.
        tick(done, total), when given, hears each file (sent or skipped): the brand intake's progress bar."""
        top = self.path(drive_path)
        sent = skipped = 0
        total = sum(1 for f in local_dir.rglob("*") if f.is_file())

        def walk(directory: Path, parent: str) -> None:
            nonlocal sent, skipped
            have = self.children(parent)
            for item in sorted(directory.iterdir()):
                if item.is_dir():
                    existing = have.get(item.name)
                    sub = existing if existing and existing.get("mimeType") == FOLDER else self.folder(item.name, parent)
                    walk(item, sub["id"])
                elif item.name in have:
                    skipped += 1
                else:
                    self.upload(item, parent)
                    sent += 1
                    if sent % 25 == 0:
                        out(f"  {sent} files uploaded...")
                if tick and not item.is_dir():
                    tick(sent + skipped, total)
        walk(local_dir, top["id"])
        link = top.get("webViewLink") or self._json("GET", f"{API}/{top['id']}?fields=webViewLink").get("webViewLink", "")
        return {"folder_id": top["id"], "link": link, "uploaded": sent, "skipped": skipped}


# ------------------------------------------------------------------------------------------------ the one-time consent
def authorize(client_file: Path, http: Http = _http, open_browser=webbrowser.open, save=None) -> None:
    """Google's consent page in the browser (the 'installed app' flow with PKCE, a one-off local page catches the answer), then the
    three keys go into the Windows user settings. Nothing is printed except what to do next."""
    info = json.loads(client_file.read_text(encoding="utf-8"))
    app = info.get("installed") or info.get("web") or {}
    if not app.get("client_id") or not app.get("client_secret"):
        raise DriveError("that file is not a Google OAuth client file (Credentials > OAuth client ID > Desktop app > Download JSON)")
    verifier = pysecrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = pysecrets.token_urlsafe(16)
    got: dict = {}

    class Catch(httpserver.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h2>Done. You can close this tab and go back to PowerShell.</h2>".encode())

        def log_message(self, *a):  # keep the console clean
            pass

    server = httpserver.HTTPServer(("127.0.0.1", 0), Catch)
    redirect = f"http://127.0.0.1:{server.server_address[1]}"
    url = AUTH_URL + "?" + urllib.parse.urlencode({"client_id": app["client_id"], "redirect_uri": redirect, "response_type": "code",
                                                   "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
                                                   "code_challenge": challenge, "code_challenge_method": "S256"})
    print("Opening Google's sign-in page. Sign in with the Gmail that owns the Drive and allow access.")
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    open_browser(url)
    thread.join(timeout=300)
    server.server_close()
    if got.get("state") != state or not got.get("code"):
        raise DriveError(f"no answer from Google ({got.get('error', 'timed out after 5 minutes')}): run it again")
    body = urllib.parse.urlencode({"code": got["code"], "client_id": app["client_id"], "client_secret": app["client_secret"],
                                   "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier}).encode()
    status, _, data = http("POST", TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"}, body)
    tokens = json.loads(data or b"{}")
    if status != 200 or not tokens.get("refresh_token"):
        raise DriveError(f"Google did not give a lasting login ({tokens.get('error', status)}): remove the app's access at "
                         "myaccount.google.com/permissions and run it again")
    save = save or _save_user_var
    save("DTJ_GDRIVE_CLIENT_ID", app["client_id"])
    save("DTJ_GDRIVE_CLIENT_SECRET", app["client_secret"])
    save("DTJ_GDRIVE_REFRESH_TOKEN", tokens["refresh_token"])
    print("Saved on this laptop: DTJ_GDRIVE_CLIENT_ID, DTJ_GDRIVE_CLIENT_SECRET, DTJ_GDRIVE_REFRESH_TOKEN (values not shown).")
    print("Back them up for the team: python tools/team-setup/vault.py push DTJ_GDRIVE_CLIENT_ID DTJ_GDRIVE_CLIENT_SECRET DTJ_GDRIVE_REFRESH_TOKEN")
    print("Then delete the downloaded client_secret file.")


def _save_user_var(name: str, value: str) -> None:
    if os.name != "nt":
        raise DriveError(f"saving {name} only works on Windows")
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)


def main(argv: list[str] | None = None, *, http: Http = _http, keys: dict | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?", help="the local folder to upload")
    ap.add_argument("--to", help="the Drive path, e.g. 'DTJ Clients/Free Soul/Brand intake 2026-10-19'")
    ap.add_argument("--authorize", action="store_true", help="one-time: sign in with Google and save the login on this laptop")
    ap.add_argument("--client-file", help="with --authorize: the OAuth client JSON downloaded from Google Cloud")
    args = ap.parse_args(argv)
    try:
        if args.authorize:
            if not args.client_file:
                ap.error("--authorize needs --client-file")
            authorize(Path(args.client_file), http=http)
            return 0
        if not (args.folder and args.to):
            ap.error("give the local folder and --to '<Drive path>'")
        res = Drive(keys, http).upload_tree(Path(args.folder), args.to)
    except DriveError as exc:
        print(f"could not upload: {exc}", file=sys.stderr)
        return 1
    print(f"uploaded {res['uploaded']} files ({res['skipped']} already there): {res['link']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
