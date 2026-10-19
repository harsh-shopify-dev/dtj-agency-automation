"""Put pictures into a store's Files (Shopify admin: Content > Files), so a DTJ page can use them by file name.

Harsh, 19 Oct 2026: the brand intake's pictures go to the store when the requester says so in Telegram ("Upload the brand's
pictures to the shop?": a new store needs them, an old store already has them). The tap is the named approval for that one upload.

    python -m page_builder.store_files --store elevate-with-harsh.myshopify.com --folder <pictures> \
        --approved-by "Harsh (Telegram, brief 5)" [--only a.jpg,b.jpg] [--max 12] [--dry-run]

Every picture (jpg, png, webp) in the folder and its sub-folders, at most --max (12): a picture whose file name the store already
has is not uploaded again. It goes through the Shopify CLI (`shopify store execute`: the store's sign-in stays inside the CLI, no
token in this repo), with the GraphQL allowlist of provision/gql.py: only stagedUploadsCreate and fileCreate can change the store,
never a delete. Writes <folder>/store-files.json ([{"local", "file", "status"}]: "file" is the name for facts.media[].file) and one
action-log row per upload (<folder>/action-log.jsonl). Exit 0 = every picture is in the store, 1 = some are not (why is printed).
"""
from __future__ import annotations

import argparse
import glob
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provision.actionlog import ActionLog  # noqa: E402
from provision.gql import check_operation  # noqa: E402
from provision.stage3 import UploadError, upload_staged  # noqa: E402

PICTURES = (".jpg", ".jpeg", ".png", ".webp")
MAX_PICTURES = 12
SCOPES = "write_files,read_files"
EXISTING = "query Existing($q: String!) { files(first: 10, query: $q) { nodes { ... on MediaImage { id fileStatus image { url } } } } }"
STAGE = """mutation Stage($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) { stagedTargets { url resourceUrl parameters { name value } } userErrors { field message } }
}"""
CREATE = """mutation Create($files: [FileCreateInput!]!) {
  fileCreate(files: $files) { files { id fileStatus } userErrors { field message } }
}"""
STATUS = "query Status($ids: [ID!]!) { nodes(ids: $ids) { ... on MediaImage { id fileStatus image { url } } } }"
Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


class StoreError(Exception):
    pass


def find_shopify() -> str:
    """The Shopify CLI: on PATH, or inside the Claude desktop app's own npm folder (a normal PowerShell does not see that one)."""
    for name in ("shopify.cmd", "shopify"):
        if shutil.which(name):
            return shutil.which(name)
    local = os.environ.get("LOCALAPPDATA", "")
    for p in glob.glob(os.path.join(local, "Packages", "Claude_*", "LocalCache", "Roaming", "npm", "shopify.cmd")):
        return p
    raise StoreError("the Shopify CLI is not installed: npm install -g @shopify/cli, then run this again")


def _run(cmd: Sequence[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(list(cmd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False)


class Store:
    """GraphQL through `shopify store execute`, the way make_collections.py ran on 19 Oct 2026 (no pinned version, JSON to a file)."""

    def __init__(self, store: str, runner: Runner = _run, cli: str | None = None, sign_in: bool = True):
        self.store, self.runner, self.cli, self.sign_in = store, runner, cli, sign_in
        self.tmp = Path(tempfile.mkdtemp())

    def run(self, query: str, variables: dict, signed_in: bool = False) -> dict:
        kind = check_operation(query)  # only the allowlisted mutations, never a delete
        cli = self.cli or find_shopify()
        q, v, out = self.tmp / "q.graphql", self.tmp / "v.json", self.tmp / "out.json"
        q.write_text(query, encoding="utf-8")
        v.write_text(json.dumps(variables), encoding="utf-8")
        out.unlink(missing_ok=True)
        cmd = [cli, "store", "execute", "-s", self.store, "--no-input", "-j", "--query-file", str(q), "--variable-file", str(v),
               "--output-file", str(out)]
        if kind == "mutation":
            cmd.append("--allow-mutations")
        done = self.runner(cmd)
        if done.returncode != 0 or not out.exists():
            said = ((done.stdout or "") + (done.stderr or "")).lower()
            if self.sign_in and not signed_in and ("auth" in said or "scope" in said or "access denied" in said):
                print("Signing the Shopify CLI in to the store: approve the page that opens in the browser...")
                self.runner([cli, "store", "auth", "-s", self.store, "--scopes", SCOPES])
                return self.run(query, variables, signed_in=True)
            raise StoreError(f"the store did not answer: {(done.stdout or '')[-300:]} {(done.stderr or '')[-300:]}".strip())
        data = json.loads(out.read_text(encoding="utf-8"))
        return data.get("data", data)


def pictures(folder: Path, only: list[str] | None = None, limit: int = MAX_PICTURES) -> list[Path]:
    found = sorted((p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in PICTURES), key=lambda p: str(p.relative_to(folder)).lower())
    if only:
        wanted = {o.strip().lower() for o in only if o.strip()}
        found = [p for p in found if p.name.lower() in wanted]
    return found[:limit]


def store_name(path: Path, taken: set[str]) -> str:
    """The file name in the store: letters, digits, dot, dash and underscore only; unique (the folder's name in front when needed)."""
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", path.stem).strip("-") or "picture"
    name = f"{stem}{path.suffix.lower()}"
    if name.lower() in taken:
        parent = re.sub(r"[^A-Za-z0-9_-]+", "-", path.parent.name).strip("-")[:30] or "folder"
        name = f"{parent}-{name}"
    taken.add(name.lower())
    return name


def _url_name(url: str) -> str:
    """The file name in a store URL, exactly as the store spells it (compare it lower-cased)."""
    return urlparse(url or "").path.rsplit("/", 1)[-1]


def upload(store: Store, folder: Path, approved_by: str, only: list[str] | None = None, limit: int = MAX_PICTURES,
           dry_run: bool = False, sleep: Callable[[float], None] = time.sleep, out=print) -> list[dict]:
    files = pictures(folder, only, limit)
    if not files:
        raise StoreError(f"no pictures (jpg, png, webp) in {folder}")
    taken: set[str] = set()
    plan = [{"local": str(p.relative_to(folder)), "path": p, "file": store_name(p, taken)} for p in files]
    log = ActionLog(folder / "action-log.jsonl", client_id=store.store, automation="store-files")
    for item in plan:  # already in the store? (a re-run, or an old store that has the pictures)
        nodes = store.run(EXISTING, {"q": f"filename:{item['file']}"}).get("files", {}).get("nodes", [])
        item["status"] = "already there" if any(_url_name((n.get("image") or {}).get("url", "")).lower() == item["file"].lower() for n in nodes) else "to upload"
    todo = [i for i in plan if i["status"] == "to upload"]
    if dry_run or not todo:
        for i in todo:
            i["status"] = "would upload"
        return plan
    staged = store.run(STAGE, {"input": [{"filename": i["file"], "mimeType": mimetypes.guess_type(i["file"])[0] or "image/jpeg",
                                           "httpMethod": "POST", "resource": "IMAGE", "fileSize": str(i["path"].stat().st_size)}
                                          for i in todo]})["stagedUploadsCreate"]
    if staged.get("userErrors"):
        raise StoreError(f"the store refused the upload: {staged['userErrors']}")
    for i, target in zip(todo, staged["stagedTargets"]):
        try:
            src = i["path"]
            if src.name != i["file"]:  # the uploaded file carries the store name
                src = store.tmp / i["file"]
                shutil.copyfile(i["path"], src)
            upload_staged(target, src)
            i["resource"] = target["resourceUrl"]
        except (UploadError, OSError) as exc:
            i["status"] = f"failed: {exc}"[:200]
    sent = [i for i in todo if i.get("resource")]
    if sent:
        made = store.run(CREATE, {"files": [{"originalSource": i["resource"], "contentType": "IMAGE",
                                             "alt": re.sub(r"[-_]+", " ", Path(i["file"]).stem)[:120]} for i in sent]})["fileCreate"]
        if made.get("userErrors"):
            raise StoreError(f"the store refused the files: {made['userErrors']}")
        for i, f in zip(sent, made["files"]):
            i["id"] = f["id"]
        waiting = {i["id"]: i for i in sent}
        for _ in range(15):  # the store makes each picture ready within seconds
            for node in store.run(STATUS, {"ids": list(waiting)}).get("nodes", []):
                if node and node.get("fileStatus") in ("READY", "FAILED"):
                    item = waiting.pop(node["id"])
                    item["status"] = "uploaded" if node["fileStatus"] == "READY" else "failed: the store could not process it"
                    if node["fileStatus"] == "READY" and (node.get("image") or {}).get("url"):
                        item["file"] = _url_name(node["image"]["url"]) or item["file"]
            if not waiting:
                break
            sleep(2)
        for i in waiting.values():
            i["status"] = "failed: still processing after 30 s (run again: it is skipped once ready)"
    for i in todo:
        ok = i["status"] == "uploaded"
        log.record(tier=2, mode="approve", target=f"{store.store} Files: {i['file']}", action="upload a picture to the store's Files",
                   reason="brand intake pictures for a DTJ page (Telegram: upload the brand's pictures)", result="success" if ok else "failed",
                   approved_by=approved_by, after={"file": i["file"]} if ok else None, error=None if ok else i["status"][:300])
        out(f"  {i['file']}: {i['status']}")
    return plan


def main(argv: list[str] | None = None, *, runner: Runner = _run, cli: str | None = None, sleep=time.sleep) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store", required=True, help="the store's ORIGINAL .myshopify.com address")
    ap.add_argument("--folder", required=True, help="the pictures (sub-folders included), e.g. <client>/intake/images/products")
    ap.add_argument("--approved-by", default="", help="who said yes to this upload, e.g. 'Harsh (Telegram, brief 5)'")
    ap.add_argument("--only", default="", help="only these file names, comma-separated")
    ap.add_argument("--max", type=int, default=MAX_PICTURES)
    ap.add_argument("--dry-run", action="store_true", help="say what would be uploaded; change nothing")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", args.store):
        ap.error("--store must be the store's .myshopify.com address")
    if not args.dry_run and not args.approved_by.strip():
        print("not uploaded: a store change needs the person who said yes (--approved-by), e.g. the Telegram tap", file=sys.stderr)
        return 1
    folder = Path(args.folder)
    try:
        plan = upload(Store(args.store, runner, cli), folder, args.approved_by.strip(), [o for o in args.only.split(",") if o],
                      min(args.max, MAX_PICTURES), args.dry_run, sleep=sleep)
    except StoreError as exc:
        print(f"not uploaded: {exc}", file=sys.stderr)
        return 1
    rows = [{"local": i["local"], "file": i["file"], "status": i["status"]} for i in plan]
    (folder / "store-files.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    ready = sum(1 for r in rows if r["status"] in ("uploaded", "already there"))
    print(f"{ready} of {len(rows)} pictures are in the store's Files{' (dry run: nothing uploaded)' if args.dry_run else ''}; "
          f"names for facts.media: {folder / 'store-files.json'}")
    return 0 if args.dry_run or ready == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
