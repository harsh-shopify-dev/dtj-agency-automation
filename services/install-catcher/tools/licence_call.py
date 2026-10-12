"""Ask the install catcher for a licence's status, or switch it (the kill switch). Signed with DTJ_CATCHER_CONTROL_KEY (never printed).

    python services/install-catcher/tools/licence_call.py test-store-harsh-dtj-sections status
    python services/install-catcher/tools/licence_call.py test-store-harsh-dtj-sections inactive --approved-by Harsh --reason "unpaid invoice"

status is read-only. active / inactive change what the client's shoppers see: Tier 2, a person approves each change and is named
with --approved-by (the catcher refuses a change without it and writes an audit row). Retries 429/5xx up to 3 times.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy import read_var  # noqa: E402

WORKER = "https://dtj-install-catcher.ultimateecomwithharsh.workers.dev"


def signed_request(worker: str, key: str, body: dict) -> urllib.request.Request:
    raw = json.dumps(body).encode()
    return urllib.request.Request(f"{worker}/licence", data=raw, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "dtj-licence-call/1",  # Cloudflare answers 403 to Python's default agent
        "X-DTJ-Signature": hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()})


def call(app: str, state: str, approved_by: str | None = None, reason: str = "", worker: str = WORKER,
         key: str | None = None, opener: Callable = urllib.request.urlopen, sleep: Callable = time.sleep) -> tuple[int, dict]:
    if state not in ("status", "active", "inactive"):
        raise SystemExit("state must be status, active or inactive")
    if state != "status" and not (approved_by or "").strip():
        raise SystemExit("a licence change needs --approved-by (who said yes to this exact change)")
    key = key or read_var("DTJ_CATCHER_CONTROL_KEY")
    if not key:
        raise SystemExit("DTJ_CATCHER_CONTROL_KEY is not set (Windows user variable written by deploy.py)")
    for attempt in range(4):
        body = {"app": app, "state": state, "ts": int(time.time())}  # a fresh timestamp each try: the catcher refuses old ones
        if state != "status":
            body.update({"approved_by": approved_by, "reason": reason})
        try:
            with opener(signed_request(worker, key, body), timeout=60) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            data = e.read().decode(errors="replace")
            if (e.code == 429 or e.code >= 500) and attempt < 3:
                sleep(2 ** attempt)
                continue
            try:
                return e.code, json.loads(data)
            except ValueError:
                return e.code, {"error": data[:300]}
    raise AssertionError("unreachable")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("app", help="the app key, e.g. test-store-harsh-dtj-blocks")
    ap.add_argument("state", choices=("status", "active", "inactive"))
    ap.add_argument("--approved-by")
    ap.add_argument("--reason", default="")
    ap.add_argument("--worker", default=WORKER)
    args = ap.parse_args(argv)
    code, data = call(args.app, args.state, args.approved_by, args.reason, args.worker)
    print(json.dumps({"http": code, **data}))
    return 0 if code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
