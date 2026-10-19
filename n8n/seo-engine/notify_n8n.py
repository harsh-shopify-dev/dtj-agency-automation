"""Send the Monday SEO report and its fixes batch to DTJ's n8n, signed, so the Telegram bot can show it and ask for one yes.

Runs as the last step of .github/workflows/seo-weekly.yml (after the report artifact is uploaded), or by hand:

    python n8n/seo-engine/notify_n8n.py --run-id 123 --dry-run            print what would be sent (no secret needed), send nothing
    python n8n/seo-engine/notify_n8n.py --run-id 123 --save sample.json   also keep the signed request body (for the n8n tests)
    python n8n/seo-engine/notify_n8n.py --run-id 123                      send it

What is sent: the newest .work/seo/<date>/ folder's report.md, its fixes batch (id, counts, the changes a yes would apply and those
the checks stopped, the tasks for a person) and the website check's counts and coverage, as JSON (schemas/seo-weekly-report.schema.json)
inside {"content": "<that JSON as text>"}. The request carries a JWT (HS256) signed with the secret N8N_SEO_REPORT_KEY (a GitHub
secret; the same value is the n8n credential "DTJ SEO Report Key"). Its claims hold the run, the batch id and the SHA-256 of the
content text and expire after 10 minutes, so n8n can prove the report came from this workflow and was not changed.
The address: N8N_SEO_WEBHOOK_URL when set, else DTJ's n8n webhook below. Without the secret nothing is sent (exit 0, says so):
the weekly run's own job is done either way. A send that fails after 3 tries exits 1 so the run shows it.
The secret is read from the environment only; it is never printed, logged or written.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / ".work" / "seo"
DEFAULT_URL = "https://n8n.srv2048145.hstgr.cloud/webhook/dtj-seo-weekly"
REPO = "harsh-shopify-dev/dtj-agency-automation"
SCHEMA = "dtj-seo-weekly/1"
LIFETIME = 600  # seconds the signature stays valid
TRIES = 3
TEXT_MAX = 300
REPORT_MAX = 60000
KIND = {"meta_description": "Google description", "seo_title": "Google title", "noindex": "Hide from Google", "alt_text": "Image alt text",
        "site_jsonld": "Business details for Google and AI"}


def _short(value, n: int = TEXT_MAX) -> str | None:
    if value is None:
        return None
    s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def latest_folder(out_root: Path) -> Path:
    """The newest dated folder with both a report and a fixes batch (the one this run just wrote)."""
    found = sorted(p for p in out_root.glob("????-??-??") if (p / "report.md").exists() and (p / "fixes.json").exists())
    if not found:
        raise SystemExit(f"no report: no {out_root}/<date>/ folder has report.md and fixes.json")
    return found[-1]


def _offices(after) -> list[str]:
    """Town names in the business details (site_jsonld): what a person reads instead of the raw data."""
    graph = after.get("@graph", []) if isinstance(after, dict) else []
    towns = [((g.get("address") or {}).get("addressLocality") or "").strip() for g in graph if isinstance(g, dict)]
    return [t for t in dict.fromkeys(towns) if t]


def change_view(c: dict) -> dict:
    after = c.get("after")
    if c.get("kind") == "site_jsonld":
        towns = _offices(after)
        after = "business details for Google and AI" + (f": offices in {', '.join(towns)}" if towns else "")
    out = {"cid": c["cid"], "kind": c["kind"], "url": _short(c.get("url"), 500) or "", "before": _short(c.get("before")),
           "after": _short(after) or "", "how": c["how"]}
    if c.get("how") == "blocked" and c.get("blocks"):
        out["why"] = _short("; ".join(map(str, c["blocks"])))
    return out


def coverage_text(cov: dict) -> str | None:
    if cov.get("complete", True):
        return None
    parts = []
    bad = cov.get("unreadable_sitemaps") or []
    if bad:
        parts.append(f"{len(bad)} sitemap(s) could not be read, so their pages were not checked")
    if cov.get("fewer_than_before"):
        parts.append(f"only {cov.get('pages_read')} pages were read; the last complete check read {cov.get('previous_pages')}")
    return _short("; ".join(parts) or "the check did not read the whole site", 2000)


def build_content(folder: Path, *, run_id: str, repo: str = REPO, ref: str = "chore/initial-import", mode: str | None = None) -> dict:
    batch = json.loads((folder / "fixes.json").read_text(encoding="utf-8"))
    scan = json.loads((folder / "scan.json").read_text(encoding="utf-8")) if (folder / "scan.json").exists() else {}
    cov = scan.get("coverage") or {}
    counts = scan.get("counts") or {}
    changes = [change_view(c) for c in batch.get("changes", []) if c.get("how") in ("auto", "blocked")]
    report = (folder / "report.md").read_text(encoding="utf-8")
    if len(report) > REPORT_MAX:
        report = report[: REPORT_MAX - 80] + "\n\n(cut here: the full report is in the GitHub run's seo-report artifact)\n"
    scan_part = {"pages": int(scan.get("pages_in_sitemap") or 0), "high": int(counts.get("high") or 0),
                 "medium": int(counts.get("medium") or 0), "low": int(counts.get("low") or 0), "complete": bool(cov.get("complete", True))}
    warning = coverage_text(cov)
    if warning:
        scan_part["warning"] = warning
    content = {
        "schema": SCHEMA, "repo": repo, "run_id": str(run_id), "run_url": f"https://github.com/{repo}/actions/runs/{run_id}", "ref": ref,
        "made_at": batch.get("made_at") or scan.get("scanned_at"), "site": batch.get("site") or scan.get("site", ""),
        "scan": scan_part,
        "batch": {"id": batch["id"], "counts": {k: int(batch.get("counts", {}).get(k) or 0) for k in ("auto", "blocked", "manual")},
                  "changes": changes[:200],
                  "manual": [_short(c.get("reason"), 600) or "" for c in batch.get("changes", []) if c.get("how") == "manual"][:50],
                  "notes": [_short(n, 600) or "" for n in batch.get("notes", [])][:50]},
        "report_md": report,
    }
    if mode in ("shadow", "approve", "auto"):
        content["mode"] = mode
    return content


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def sign(content_text: str, secret: str, *, run_id: str, batch_id: str, now: int | None = None) -> str:
    """A JWT (HS256) whose claims cover the content's SHA-256."""
    now = int(time.time()) if now is None else now
    claims = {"iss": "dtj-seo-weekly", "aud": "dtj-n8n", "iat": now, "exp": now + LIFETIME, "run_id": str(run_id), "batch_id": batch_id,
              "sha256": hashlib.sha256(content_text.encode("utf-8")).hexdigest()}
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    mac = hmac.new(secret.encode("utf-8"), f"{head}.{body}".encode("ascii"), hashlib.sha256).digest()
    return f"{head}.{body}.{_b64(mac)}"


def request_body(content: dict) -> tuple[str, bytes]:
    text = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    return text, json.dumps({"content": text}, ensure_ascii=False).encode("utf-8")


def post(url: str, body: bytes, token: str, *, opener=urllib.request.urlopen, wait: float = 2.0) -> int:
    """POST with up to 3 tries on 429, 5xx or a network error (2 s, then 4 s). Returns the final HTTP status (0 = no answer)."""
    status = 0
    for attempt in range(TRIES):
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {token}", "User-Agent": "dtj-seo-weekly/1"})
        try:
            with opener(req, timeout=30) as r:
                return r.status
        except urllib.error.HTTPError as exc:
            status = exc.code
            if status != 429 and status < 500:
                return status
        except (urllib.error.URLError, TimeoutError, OSError):
            status = 0
        if attempt < TRIES - 1 and wait:
            time.sleep(wait * (2 ** attempt))
    return status


def main(argv: list[str] | None = None, env=None) -> int:
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True, help="the GitHub run number of this 'SEO weekly' run (github.run_id)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--repo", default=env.get("GITHUB_REPOSITORY") or REPO)
    ap.add_argument("--ref", default="chore/initial-import", help="the branch 'SEO apply fixes' runs from")
    ap.add_argument("--dry-run", action="store_true", help="print what would be sent; send nothing")
    ap.add_argument("--save", type=Path, help="also write the signed request (body + its JWT claims, no secret) to this file")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    folder = latest_folder(a.out)
    content = build_content(folder, run_id=a.run_id, repo=a.repo, ref=a.ref, mode=env.get("SEO_MODE") or None)
    text, body = request_body(content)
    b = content["batch"]
    print(f"Report {folder.name}: batch {b['id']}, {b['counts']['auto']} change(s) ready, {b['counts']['blocked']} stopped, "
          f"{b['counts']['manual']} for a person; check complete: {content['scan']['complete']}; {len(body)} bytes.")
    secret = (env.get("N8N_SEO_REPORT_KEY") or "").strip()
    if a.save:
        a.save.write_text(json.dumps({"body": json.loads(body), "note": "signed with a test key in the tests; the live key is never saved"},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Saved the request body to {a.save}.")
    if a.dry_run:
        print("Dry run: nothing sent.")
        return 0
    if not secret:
        print("Not sent: the GitHub secret N8N_SEO_REPORT_KEY is not set (n8n/seo-engine/README.md, 'Setting it up').")
        return 0
    url = (env.get("N8N_SEO_WEBHOOK_URL") or "").strip() or DEFAULT_URL
    if not url.startswith("https://"):
        print("Not sent: N8N_SEO_WEBHOOK_URL must start with https://")
        return 1
    token = sign(text, secret, run_id=content["run_id"], batch_id=b["id"])
    status = post(url, body, token)
    if 200 <= status < 300:
        print(f"Sent to n8n (HTTP {status}): the bot shows the report and asks for one yes.")
        return 0
    print(f"Not delivered to n8n (HTTP {status or 'no answer'} after {TRIES} tries). 403 = the key in n8n's credential "
          "'DTJ SEO Report Key' differs from N8N_SEO_REPORT_KEY; 404 = the workflow 'SEO Engine: Weekly Report' is not published.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
