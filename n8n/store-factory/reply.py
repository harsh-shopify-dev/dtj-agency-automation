"""Claude Code's answer to a paused "Store Factory: Page Design" run: POST a JSON body to the run's resume URL.

    python n8n/store-factory/reply.py --resume-url "<resume_url from the Request for Claude Code node>" --body answer.json

Since 10 Oct 2026 the page step is ONE command (services/store-builder: python -m page_builder.ship_draft ...) that designs, checks and,
when every gate passes, writes the page into the DRAFT theme (Harsh's standing rule for drafts); its <client>/run/ship-result.json is
the body to send here.

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
    # "ready for approval" belongs to the older two-step flow (design, then a yes code before the draft write); kept for runs still waiting
    "page_design": {"page_status": ("written to draft", "designed (not written)", "needs a look", "could not build", "ready for approval")},
    "write_to_draft": {"result": ("written to draft", "not written")},
}


N8N_HOST = "n8n.srv2048145.hstgr.cloud"  # DTJ's n8n since 10 Oct 2026 (moved from n8n.srv1969859.hstgr.cloud)
RESUME = re.compile(r"^https://" + re.escape(N8N_HOST) + r"/webhook-waiting/\d+(/[\w-]+)?(\?signature=[0-9a-f]+)?$")
PREVIEW = re.compile(r"^https://[a-z0-9-]+\.myshopify\.com/\S*preview_theme_id=\d+")


def check(body: dict) -> str:
    """Returns the stage the body answers, or raises ValueError saying what is wrong."""
    for stage, fields in STAGES.items():
        for key, allowed in fields.items():
            if key in body:
                if body[key] not in allowed:
                    raise ValueError(f"{key} must be one of {allowed}, not {body[key]!r}")
                code_ok = re.fullmatch(r"[0-9a-f]{12}", str(body.get("approve_code", "")))
                if stage == "page_design" and body[key] in ("ready for approval", "written to draft") and not code_ok:
                    raise ValueError(f"a page that is {body[key]} needs its 12-character approve_code from the build")
                if stage == "page_design" and body[key] == "written to draft" and not PREVIEW.match(str(body.get("preview_url", ""))):
                    raise ValueError("a page written to the draft needs its preview_url (https://<store>.myshopify.com/...preview_theme_id=...)")
                if stage == "write_to_draft" and body[key] == "written to draft" and not body.get("approved_by"):
                    raise ValueError("a write to the draft theme needs approved_by (who said yes)")
                return stage
    raise ValueError("the body answers no stage: give page_status (page design) or result (write to draft)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--resume-url", required=True)
    ap.add_argument("--body", required=True, help="JSON file with the answer")
    args = ap.parse_args(argv)
    if not RESUME.match(args.resume_url):
        print(f"not a resume URL of DTJ's n8n (https://{N8N_HOST}/webhook-waiting/<run>?signature=...)", file=sys.stderr)
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
