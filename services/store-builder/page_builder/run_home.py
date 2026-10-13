"""Build a client's HOME page from a brand profile and home facts. Design only: nothing is pushed to any store.

    cd services/store-builder
    python -m page_builder.run_home --brand brand.json --facts home-facts.json --out ../../.work/home-run [--client-registry page_builder/clients/<store>.json]

Writes <out>/templates/index.json (the home template), <out>/home-report.json (niche, order, sections built and omitted with reasons, provenance, lint)
and prints a short summary. Exit code: 0 = built and clean, 2 = built but a lint error or a build problem needs a person's look, 1 = could not build.
Putting the template on a store is a separate, approved step (an UNPUBLISHED theme only): shopify theme push --only templates/index.json --nodelete."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import catalog
from .assemble import InputError
from .assemble_home import build_home


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--facts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--client-registry", help="a client's own app copies (handles and extension ids); without it the page uses DTJ's original apps")
    args = ap.parse_args(argv)
    try:
        brand = json.loads(Path(args.brand).read_text(encoding="utf-8"))
        facts = json.loads(Path(args.facts).read_text(encoding="utf-8"))
        result = build_home(brand, facts)
        template = result.template
        if args.client_registry:
            template = catalog.to_client(template, catalog.load_client_registry(args.client_registry))
    except (InputError, ValueError, KeyError, OSError) as e:
        print(f"could not build the home page: {e}", file=sys.stderr)
        return 1
    out = Path(args.out)
    (out / "templates").mkdir(parents=True, exist_ok=True)
    (out / "templates" / "index.json").write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "home-report.json").write_text(json.dumps(result.report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rep = result.report
    errors = [f for f in rep["lint"] if f["severity"] == "error"]
    print(f"niche: {rep['niche']} | order: {' > '.join(rep['page_order'])}")
    for s in rep["sections_built"]:
        print(f"  built   {s['id']:14} {s['block']:32} {s['niche_fit']}")
    for o in rep["sections_omitted"]:
        print(f"  omitted {o['section']:22} {o['reason']}")
    print(f"lint errors: {len(errors)} | build problems: {len(rep['problems'])} | samples to replace: {len(rep['needs_replacement'])}")
    return 0 if not errors and not rep["problems"] else 2


if __name__ == "__main__":
    sys.exit(main())
