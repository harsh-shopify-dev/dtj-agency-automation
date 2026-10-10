"""Claude Code's answer to a paused "Store Factory: Page Design" run: POST a JSON body to the run's resume URL.

    python n8n/store-factory/reply.py --resume-url "<resume_url from the Request for Claude Code node>" --body answer.json

The resume URL carries n8n's own signature; it is passed on the command line only and never stored in git. The body is checked here
against what the workflow's reply node accepts, so a typo cannot silently record "reply not understood".
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

STAGES = {
    "page_design": {"page_status": ("ready for approval", "needs a look", "could not build")},
    "write_to_draft": {"result": ("written to draft", "not written")},
}


def check(body: dict) -> str:
    """Returns the stage the body answers, or raises ValueError saying what is wrong."""
    for stage, fields in STAGES.items():
        for key, allowed in fields.items():
            if key in body:
                if body[key] not in allowed:
                    raise ValueError(f"{key} must be one of {allowed}, not {body[key]!r}")
                if stage == "page_design" and body[key] == "ready for approval" and not re.fullmatch(r"[0-9a-f]{12}", str(body.get("approve_code", ""))):
                    raise ValueError("a page that is ready for approval needs its 12-character approve_code from run_client")
                if stage == "write_to_draft" and body[key] == "written to draft" and not body.get("approved_by"):
                    raise ValueError("a write to the draft theme needs approved_by (who said yes)")
                return stage
    raise ValueError("the body answers no stage: give page_status (page design) or result (write to draft)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resume-url", required=True)
    ap.add_argument("--body", required=True, help="JSON file with the answer")
    args = ap.parse_args(argv)
    if not re.match(r"^https://n8n\.srv1969859\.hstgr\.cloud/webhook-waiting/\d+(\?signature=[0-9a-f]+)?$", args.resume_url):
        print("not a resume URL of DTJ's n8n (https://n8n.srv1969859.hstgr.cloud/webhook-waiting/<run>?signature=...)", file=sys.stderr)
        return 1
    body = json.loads(Path(args.body).read_text(encoding="utf-8"))
    try:
        stage = check(body)
    except ValueError as exc:
        print(f"not sent: {exc}", file=sys.stderr)
        return 1
    req = urllib.request.Request(args.resume_url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"sent the {stage} answer: n8n replied HTTP {r.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
