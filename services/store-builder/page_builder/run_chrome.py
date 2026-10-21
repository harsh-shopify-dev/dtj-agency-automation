"""Design a store's HEADER and FOOTER from the brand's palette, for a DRAFT theme. Nothing is written to any store here.

    cd services/store-builder
    python -m page_builder.run_chrome --client ../../.work/clients/<client> --store X.myshopify.com --theme 123
        read-only on the store: checks the theme is a DRAFT Horizon theme, backs up sections/header-group.json and sections/footer-group.json,
        builds the new ones FROM them (every section, block and id kept; only colours, words, social links and a few switches change) and
        writes <client>/chrome-run/header/ and <client>/chrome-run/footer/ (template.json + approval.json each) and chrome-report.json.
    python -m page_builder.run_chrome --client ... --from <a pulled theme folder>     design only, from files already on disk

The client folder holds brand.json, home-facts.json (its announcements are used when chrome.json has none) and, optionally, chrome.json:
    {"announcements": [{"text": "Free shipping above Rs. 499", "source": "shipping policy page, 21 Oct 2026", "link": "/policies/shipping-policy"}],
     "social": {"instagram": {"url": "https://www.instagram.com/<brand>/", "source": "the brand's own site footer, 21 Oct 2026"}},
     "newsletter": {"text": "...", "source": "..."}}
Writing is Tier 2 (these two files are on EVERY page; not covered by the standing draft rule): a person approves each file's code, then
    python -m page_builder.push_page --out ../../.work/clients/<client>/chrome-run/header --approve <code> --approved-by <name> [--allow-samples]
    python -m page_builder.push_page --out ../../.work/clients/<client>/chrome-run/footer --approve <code> --approved-by <name>
Exit code: 0 = built and clean, 2 = built but a problem needs a person's look, 1 = could not build.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from provision import templates
from provision.theme import ThemeError

from . import theme_target as tt
from .assemble import InputError
from .assemble_chrome import FOOTER_FILE, HEADER_FILE, build_chrome


def _load(path: Path) -> dict:
    return templates.load(path.read_text(encoding="utf-8"))[1]


def main(argv: list[str] | None = None, *, access=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--client", required=True, help="the client folder (brand.json, home-facts.json, optional chrome.json)")
    ap.add_argument("--store", help="the store's ORIGINAL .myshopify.com address (read-only check and backup)")
    ap.add_argument("--theme", help="the DRAFT theme's id")
    ap.add_argument("--from", dest="source", help="design only: a folder holding sections/header-group.json and sections/footer-group.json")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if bool(args.store) != bool(args.theme):
        ap.error("--store and --theme go together")
    if not args.store and not args.source:
        ap.error("give --store and --theme (read the draft) or --from <a pulled theme folder> (design only)")
    client = Path(args.client)
    out = client / "chrome-run"
    base, checks = {}, {}
    try:
        brand = json.loads((client / "brand.json").read_text(encoding="utf-8"))
        facts_file = client / "home-facts.json"
        facts = json.loads(facts_file.read_text(encoding="utf-8")) if facts_file.exists() else {}
        chrome_file = client / "chrome.json"
        chrome = json.loads(chrome_file.read_text(encoding="utf-8")) if chrome_file.exists() else {}
        if args.store:
            if access is None:
                access = tt.open_access(args.store)  # the Theme Access password, else the CLI's own (collaborator) login
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            for file in (HEADER_FILE, FOOTER_FILE):
                checks[file] = tt.check_target(access, args.theme, out / f"backup-{stamp}", file)
                if checks[file]["base_theme"] != "Horizon":
                    raise ThemeError(f"the header and footer builder knows Horizon only; theme {args.theme} is built on {checks[file]['base_theme']}")
                if not checks[file]["backup"]:
                    raise ThemeError(f"the theme has no {file}")
                base[file] = _load(Path(checks[file]["backup"]))
        else:
            for file in (HEADER_FILE, FOOTER_FILE):
                base[file] = _load(Path(args.source) / file)
        res = build_chrome(brand, facts, chrome, base[HEADER_FILE], base[FOOTER_FILE])
    except (InputError, ThemeError, ValueError, KeyError, OSError) as e:
        print(f"could not build the header and footer: {e}", file=sys.stderr)
        return 1

    rep = res.report
    ready = not rep["problems"]
    for name, file, body_dict in (("header", HEADER_FILE, res.header), ("footer", FOOTER_FILE, res.footer)):
        folder = out / name
        folder.mkdir(parents=True, exist_ok=True)
        body = tt.template_bytes(body_dict)
        (folder / "template.json").write_bytes(body)
        digest = tt.sha256(body)
        samples = [k for k in rep["samples"] if k.split(".")[0] in body_dict.get("sections", {})]
        check = checks.get(file)
        approval = {
            "client": brand.get("brand_name", ""), "store": tt.normalise_store(args.store) if args.store else "", "theme_id": str(args.theme or ""),
            "file": file, "template_sha256": digest, "approve_code": digest[:12], "pushable": bool(args.store),
            "base_sha256": check["current_product_template_sha256"] if check else None, "samples": len(samples), "demo": False, "ready": ready,
            "review": "pass" if ready else f"{len(rep['problems'])} problems", "standing_rule": False,
            "theme": {k: check[k] for k in ("theme_name", "role", "base_theme", "base_version")} if check else None,
        }
        (folder / "approval.json").write_text(json.dumps(approval, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{name}: {file}" + (f" | approve code {digest[:12]}" if args.store else " | design only") + (f" | {len(samples)} SAMPLE line(s)" if samples else ""))
    (out / "chrome-report.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in rep["changes"]:
        print(f"  {c['part']}: {c['change']}")
    if rep["removed_placeholders"]:
        print("  theme placeholders removed: " + "; ".join(rep["removed_placeholders"]))
    print("  contrast: " + ", ".join(f"{k} {v}:1" for k, v in rep["contrast"].items()))
    for p in rep["problems"]:
        print(f"  PROBLEM {p}")
    return 0 if ready else 2


if __name__ == "__main__":
    sys.exit(main())
