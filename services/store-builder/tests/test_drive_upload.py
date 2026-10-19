"""Google Drive upload (Harsh, 19 Oct 2026: "Google OAuth", DTJ's Gmail, run from GitHub Actions). A Drive held in memory: nothing here
reaches Google."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from page_builder import drive_upload  # noqa: E402
from page_builder.drive_upload import API, FOLDER, TOKEN_URL, UPLOAD, Drive, DriveError  # noqa: E402

KEYS = {"DTJ_GDRIVE_CLIENT_ID": "id-123", "DTJ_GDRIVE_CLIENT_SECRET": "secret-456", "DTJ_GDRIVE_REFRESH_TOKEN": "refresh-789"}


class FakeDrive:
    """Answers the few Drive API calls drive_upload makes."""

    def __init__(self, refuse_token=False, busy=0):
        self.files = {"root": {"id": "root", "name": "My Drive", "mimeType": FOLDER, "parents": []}}
        self.calls, self.sessions, self.refuse_token, self.busy = [], {}, refuse_token, busy
        self.content = {}  # file id -> bytes (for downloads)

    def _new(self, name, parent, mime, size=0):
        fid = f"f{len(self.files)}"
        self.files[fid] = {"id": fid, "name": name, "mimeType": mime, "parents": [parent], "size": size,
                           "webViewLink": f"https://drive.google.com/drive/folders/{fid}"}
        return self.files[fid]

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url.split("?")[0]))
        if url == TOKEN_URL:
            if self.refuse_token:
                return 400, {}, b'{"error": "invalid_grant"}'
            return 200, {}, b'{"access_token": "access-1", "expires_in": 3599}'
        assert headers.get("Authorization") == "Bearer access-1"
        if self.busy:
            self.busy -= 1
            return 429, {}, b"{}"
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if method == "GET" and url.startswith(API + "?"):
            parent = q["q"][0].split("'")[1]
            only = FOLDER in q["q"][0]
            found = [f for f in self.files.values() if parent in f["parents"] and (not only or f["mimeType"] == FOLDER)]
            return 200, {}, json.dumps({"files": found}).encode()
        if method == "GET" and url.startswith(API + "/") and "alt=media" in url:
            return 200, {}, self.content[url.split("/")[-1].split("?")[0]]
        if method == "GET" and url.startswith(API + "/"):
            return 200, {}, json.dumps({"webViewLink": self.files[url.split("/")[-1].split("?")[0]]["webViewLink"]}).encode()
        if method == "POST" and url.startswith(API + "?"):
            meta = json.loads(body)
            return 200, {}, json.dumps(self._new(meta["name"], meta["parents"][0], meta["mimeType"])).encode()
        if method == "POST" and url.startswith(UPLOAD) and q["uploadType"] == ["multipart"]:
            meta = json.loads(body.split(b"\r\n\r\n", 1)[1].split(b"\r\n--", 1)[0])
            data = body.rsplit(b"\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0]
            made = self._new(meta["name"], meta["parents"][0], "file", len(data))
            self.content[made["id"]] = data
            return 200, {}, json.dumps(made).encode()
        if method == "POST" and q["uploadType"] == ["resumable"]:
            sid = f"https://upload.example/session/{len(self.sessions)}"
            self.sessions[sid] = {"meta": json.loads(body), "got": 0, "size": int(headers["X-Upload-Content-Length"])}
            return 200, {"Location": sid}, b""
        if method == "PUT" and url in self.sessions:
            s = self.sessions[url]
            s["got"] += len(body)
            s["data"] = s.get("data", b"") + body
            assert headers["Content-Range"].endswith(f"/{s['size']}")
            if s["got"] < s["size"]:
                return 308, {}, b""
            made = self._new(s["meta"]["name"], s["meta"]["parents"][0], "file", s["size"])
            self.content[made["id"]] = s["data"]
            return 200, {}, json.dumps(made).encode()
        raise AssertionError(f"unexpected call {method} {url}")

    def named(self, name):
        return [f for f in self.files.values() if f["name"] == name]


class DriveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "images" / "products" / "foam").mkdir(parents=True)
        (self.tmp / "BRAND.md").write_text("# Brand", encoding="utf-8")
        (self.tmp / "images" / "products" / "foam" / "a.png").write_bytes(b"png" * 10)
        (self.tmp / "images" / "products" / "foam" / "b.png").write_bytes(b"png" * 10)

    def test_the_path_is_made_the_folder_mirrored_and_a_rerun_sends_only_what_is_new(self):
        fake = FakeDrive()
        res = Drive(KEYS, fake).upload_tree(self.tmp, "DTJ Clients/Free Soul/Brand intake 2026-10-19", out=lambda *_: None)
        self.assertEqual((res["uploaded"], res["skipped"]), (3, 0))
        self.assertTrue(res["link"].startswith("https://drive.google.com/drive/folders/"))
        for name in ("DTJ Clients", "Free Soul", "Brand intake 2026-10-19", "images", "products", "foam", "a.png", "BRAND.md"):
            self.assertEqual(len(fake.named(name)), 1, name)
        again = Drive(KEYS, fake).upload_tree(self.tmp, "DTJ Clients/Free Soul/Brand intake 2026-10-19", out=lambda *_: None)
        self.assertEqual((again["uploaded"], again["skipped"]), (0, 3))
        self.assertEqual(len(fake.named("DTJ Clients")), 1)  # folders are found again, never doubled

    def test_a_folder_comes_back_from_drive_and_a_second_copy_keeps_what_is_there(self):
        (self.tmp / "clip.mp4").write_bytes(b"v" * 2500)
        fake = FakeDrive()
        with mock.patch.object(drive_upload, "SMALL", 1000), mock.patch.object(drive_upload, "CHUNK", 1000):
            Drive(KEYS, fake).upload_tree(self.tmp, "DTJ Clients/Senso Foods/Brand intake 2026-10-19", out=lambda *_: None)
        back = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, back, ignore_errors=True)
        folders = len(fake.named("DTJ Clients"))
        res = Drive(KEYS, fake).download_tree("DTJ Clients/Senso Foods/Brand intake 2026-10-19", back, out=lambda *_: None)
        self.assertEqual((res["downloaded"], res["kept"]), (4, 0))
        for f in ("BRAND.md", "clip.mp4", "images/products/foam/a.png", "images/products/foam/b.png"):
            self.assertEqual((back / f).read_bytes(), (self.tmp / f).read_bytes(), f)
        again = Drive(KEYS, fake).download_tree("DTJ Clients/Senso Foods/Brand intake 2026-10-19", back, out=lambda *_: None)
        self.assertEqual((again["downloaded"], again["kept"]), (0, 4))
        with self.assertRaises(DriveError):
            Drive(KEYS, fake).download_tree("DTJ Clients/Nobody/Brand intake", back, out=lambda *_: None)
        self.assertEqual(len(fake.named("DTJ Clients")), folders)  # looking never makes a folder
        self.assertFalse(fake.named("Nobody"))

    def test_a_big_video_goes_up_in_pieces(self):
        (self.tmp / "clip.mp4").write_bytes(b"v" * 2500)
        fake = FakeDrive()
        with mock.patch.object(drive_upload, "SMALL", 1000), mock.patch.object(drive_upload, "CHUNK", 1024):
            Drive(KEYS, fake).upload_tree(self.tmp, "DTJ Clients/X", out=lambda *_: None)
        self.assertEqual(fake.named("clip.mp4")[0]["size"], 2500)
        self.assertEqual(sum(1 for m, _ in fake.calls if m == "PUT"), 3)

    def test_missing_keys_or_a_refused_login_say_what_to_do_and_never_show_a_secret(self):
        with self.assertRaises(DriveError) as missing:
            Drive({"DTJ_GDRIVE_CLIENT_ID": "id-123"}, FakeDrive())
        self.assertIn("DTJ_GDRIVE_REFRESH_TOKEN", str(missing.exception))
        with self.assertRaises(DriveError) as refused:
            Drive(KEYS, FakeDrive(refuse_token=True)).path("DTJ Clients")
        self.assertIn("--authorize", str(refused.exception))
        for value in KEYS.values():
            self.assertNotIn(value, str(missing.exception) + str(refused.exception))

    def test_a_busy_drive_is_retried(self):
        fake = FakeDrive(busy=2)
        self.assertTrue(Drive(KEYS, fake).path("DTJ Clients")["id"])

    def test_the_one_time_sign_in_saves_the_three_keys_without_printing_them(self):
        client = self.tmp / "client_secret.json"
        client.write_text(json.dumps({"installed": {"client_id": "id-123", "client_secret": "secret-456"}}), encoding="utf-8")
        saved = {}

        def browser(url):  # Google sends the browser back to our one-off local page with a code
            q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            self.assertEqual(q["scope"], [drive_upload.SCOPE])  # only the files the app creates
            back = f"{q['redirect_uri'][0]}/?code=abc&state={q['state'][0]}"
            threading.Thread(target=lambda: urllib.request.urlopen(back, timeout=10).read(), daemon=True).start()

        def http(method, url, headers, body):
            form = urllib.parse.parse_qs(body.decode())
            self.assertEqual((form["code"], form["grant_type"]), (["abc"], ["authorization_code"]))
            self.assertTrue(form["code_verifier"][0])
            return 200, {}, json.dumps({"access_token": "a", "refresh_token": "refresh-789"}).encode()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            drive_upload.authorize(client, http=http, open_browser=browser, save=lambda k, v: saved.__setitem__(k, v))
        self.assertEqual(saved, KEYS)
        self.assertNotIn("refresh-789", out.getvalue())
        self.assertNotIn("secret-456", out.getvalue())
        with self.assertRaises(DriveError):
            bad = self.tmp / "bad.json"
            bad.write_text("{}", encoding="utf-8")
            drive_upload.authorize(bad, http=http, open_browser=browser, save=lambda k, v: None)


class IntakeToDriveTests(unittest.TestCase):
    def test_the_intake_lands_in_dtj_clients_brand_brand_intake_date_and_github_gets_the_link(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_brand_intake import BASE, store  # noqa: PLC0415
        from page_builder import brand_intake  # noqa: PLC0415
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        get, _ = store(n_products=2)
        fake = FakeDrive()
        gh_out, gh_sum = tmp / "out.txt", tmp / "summary.md"
        printed = io.StringIO()
        with mock.patch.object(brand_intake, "POLITE_DELAY", 0), mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(gh_out), "GITHUB_STEP_SUMMARY": str(gh_sum)}), \
                contextlib.redirect_stdout(printed):
            code = brand_intake.main([BASE, "--client", str(tmp / "c"), "--drive", "DTJ Clients"], get=get, drive=Drive(KEYS, fake))
        self.assertEqual(code, 0)
        self.assertEqual(len(fake.named("Toilova")), 1)
        self.assertTrue(any(f["name"].startswith("Brand intake ") for f in fake.files.values()))
        self.assertIn("DRIVE_LINK=https://drive.google.com/drive/folders/", printed.getvalue())
        self.assertIn("link=https://drive.google.com/drive/folders/", gh_out.read_text(encoding="utf-8"))
        self.assertIn("Brand intake: Toilova", gh_sum.read_text(encoding="utf-8"))
        saved = json.loads((tmp / "c" / "intake" / "brand-intake.json").read_text(encoding="utf-8"))
        self.assertTrue(saved["drive"]["link"])


if __name__ == "__main__":
    unittest.main()
