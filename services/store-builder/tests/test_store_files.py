"""Pictures into a store's Files (Harsh, 19 Oct 2026: "upload the assets ... to the store" after a yes in Telegram). A stand-in
Shopify CLI: nothing here reaches a store."""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from page_builder import store_files  # noqa: E402
from provision.gql import OperationNotAllowed  # noqa: E402

STORE = "elevate-with-harsh.myshopify.com"


class FakeCli:
    """Answers `shopify store execute` from memory: Files the store already has, staged uploads, fileCreate, the READY check."""

    def __init__(self, have=(), fail=()):
        self.have, self.fail, self.calls, self.made = {h.lower() for h in have}, set(fail), [], {}

    def __call__(self, cmd):
        self.calls.append(list(cmd))
        if cmd[1:3] == ["store", "auth"]:
            return subprocess.CompletedProcess(cmd, 0, "", "")
        query = Path(cmd[cmd.index("--query-file") + 1]).read_text(encoding="utf-8")
        variables = json.loads(Path(cmd[cmd.index("--variable-file") + 1]).read_text(encoding="utf-8"))
        if "files(first" in query:
            name = variables["q"].split(":", 1)[1].lower()
            nodes = [{"id": "gid://shopify/MediaImage/1", "fileStatus": "READY",
                      "image": {"url": f"https://cdn.shopify.com/s/files/1/x/files/{name}?v=1"}}] if name in self.have else []
            data = {"files": {"nodes": nodes}}
        elif "stagedUploadsCreate" in query:
            data = {"stagedUploadsCreate": {"userErrors": [], "stagedTargets": [
                {"url": "https://shopify-staged-uploads.storage.googleapis.com/", "resourceUrl": f"https://staged/{i['filename']}",
                 "parameters": [{"name": "key", "value": i["filename"]}]} for i in variables["input"]]}}
        elif "fileCreate" in query:
            files = []
            for f in variables["files"]:
                gid = f"gid://shopify/MediaImage/{100 + len(self.made)}"
                self.made[gid] = f["originalSource"].rsplit("/", 1)[1]
                files.append({"id": gid, "fileStatus": "UPLOADED"})
            data = {"fileCreate": {"userErrors": [], "files": files}}
        elif "nodes(ids" in query:
            data = {"nodes": [{"id": g, "fileStatus": "FAILED" if self.made[g] in self.fail else "READY",
                               "image": {"url": f"https://cdn.shopify.com/s/files/1/x/files/{self.made[g]}?v=2"}} for g in variables["ids"]]}
        else:
            raise AssertionError(f"unexpected query {query[:80]}")
        Path(cmd[cmd.index("--output-file") + 1]).write_text(json.dumps({"data": data}), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def mutations(self):
        return [c for c in self.calls if "--allow-mutations" in c]


class StoreFiles(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        for rel in ("turmeric-latte/TURMERIC LATTEE SAFRON.jpg", "turmeric-latte/box.png", "unsweetened/box.png", "notes.txt"):
            (self.folder / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.folder / rel).write_bytes(b"picture")
        self.posted = []
        patcher = mock.patch.object(store_files, "upload_staged", lambda target, path: self.posted.append((target["url"], path.name)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_main(self, *args, cli=None):
        cli = cli or FakeCli()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = store_files.main(["--store", STORE, "--folder", str(self.folder), *args], runner=cli, cli="shopify", sleep=lambda s: None)
        return code, out.getvalue() + err.getvalue(), cli

    def test_new_pictures_are_uploaded_once_under_clean_unique_names_and_logged(self):
        code, text, cli = self.run_main("--approved-by", "Harsh (Telegram, brief 5)")
        self.assertEqual(code, 0, text)
        rows = json.loads((self.folder / "store-files.json").read_text(encoding="utf-8"))
        self.assertEqual([(r["file"], r["status"]) for r in rows],
                         [("box.png", "uploaded"), ("TURMERIC-LATTEE-SAFRON.jpg", "uploaded"), ("unsweetened-box.png", "uploaded")])
        self.assertEqual(sorted(name for _, name in self.posted), ["TURMERIC-LATTEE-SAFRON.jpg", "box.png", "unsweetened-box.png"])
        self.assertEqual(len(cli.mutations()), 2)  # stagedUploadsCreate + fileCreate, nothing else changes the store
        for call in cli.calls:
            if "--allow-mutations" not in call:
                self.assertNotIn("Create", Path(call[call.index("--query-file") + 1]).read_text(encoding="utf-8"))
        log = [json.loads(line) for line in (self.folder / "action-log.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(log), 3)
        self.assertEqual({r["approved_by"] for r in log}, {"Harsh (Telegram, brief 5)"})
        self.assertEqual({r["result"] for r in log}, {"success"})

    def test_pictures_the_store_already_has_are_not_uploaded_again(self):
        code, text, cli = self.run_main("--approved-by", "Harsh", cli=FakeCli(have={"box.png", "unsweetened-box.png"}))
        self.assertEqual(code, 0, text)
        self.assertEqual(sorted(name for _, name in self.posted), ["TURMERIC-LATTEE-SAFRON.jpg"])
        rows = {r["file"]: r["status"] for r in json.loads((self.folder / "store-files.json").read_text(encoding="utf-8"))}
        self.assertEqual(rows["box.png"], "already there")
        everything = FakeCli(have={"turmeric-lattee-safron.jpg", "box.png", "unsweetened-box.png"})
        code, _, cli = self.run_main("--approved-by", "Harsh", cli=everything)
        self.assertEqual((code, cli.mutations()), (0, []))  # an old store with the pictures: no change at all

    def test_a_dry_run_or_a_missing_approval_changes_nothing(self):
        code, text, cli = self.run_main("--dry-run")
        self.assertEqual((code, cli.mutations(), self.posted), (0, [], []))
        self.assertIn("dry run: nothing uploaded", text)
        code, text, cli = self.run_main()
        self.assertEqual((code, cli.calls), (1, []))
        self.assertIn("needs the person who said yes", text)

    def test_only_and_max_pick_the_pictures_and_a_failed_one_is_reported(self):
        code, text, _ = self.run_main("--approved-by", "Harsh", "--only", "box.png", "--max", "1")
        self.assertEqual(code, 0, text)
        self.assertEqual([n for _, n in self.posted], ["box.png"])
        self.posted.clear()
        code, text, _ = self.run_main("--approved-by", "Harsh", cli=FakeCli(fail={"box.png"}))
        self.assertEqual(code, 1)
        self.assertIn("box.png: failed: the store could not process it", text)

    def test_only_the_allowlisted_mutations_can_be_sent(self):
        store = store_files.Store(STORE, FakeCli(), cli="shopify")
        with self.assertRaises(OperationNotAllowed):
            store.run("mutation { fileDelete(fileIds: [\"x\"]) { deletedFileIds } }", {})
        with self.assertRaises(OperationNotAllowed):
            store.run("mutation { productDelete(input: {id: \"x\"}) { deletedProductId } }", {})


if __name__ == "__main__":
    unittest.main()
