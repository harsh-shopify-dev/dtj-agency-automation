"""Dry-run planner for the provisioning pipeline (Stage 1).

    python -m provision.run --brand brand.json --products products.json --images ./images --out ./out [--theme-dir ./theme]

It validates the inputs, then prints and logs everything the pipeline WOULD do. It never contacts a
store: there is no live mode in this file yet. Live stages are added one at a time, each behind approval.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from . import apps, config, products, templates, theme
from .actionlog import ActionLog

SCHEMAS = Path(__file__).resolve().parents[3] / "schemas"


class InputError(Exception):
    pass


class CircuitBreaker:
    """After 3 consecutive failures of the same step: stop (CLAUDE.md self-healing rule)."""

    def __init__(self, limit: int = 3):
        self.limit = limit
        self.failures: dict[str, int] = {}

    def failed(self, step: str) -> bool:
        self.failures[step] = self.failures.get(step, 0) + 1
        return self.failures[step] >= self.limit

    def ok(self, step: str) -> None:
        self.failures[step] = 0


def validate(instance: dict, schema_name: str) -> None:
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        raise InputError(schema_name + ": " + "; ".join(f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors))


def plan(brand: dict, sheet: dict, image_dir: Path, theme_dir: Path | None = None) -> dict:
    validate(brand, "brand-config.schema.json")
    validate(sheet, "product-sheet.schema.json")
    handles = [p["handle"] for p in sheet["products"]]
    if len(handles) != len(set(handles)):
        raise InputError("duplicate product handles in the sheet")
    todo = [p["handle"] for p in sheet["products"] if "[[TODO]]" in json.dumps(p, ensure_ascii=False)]

    wanted = sorted({i["file"] for p in sheet["products"] for i in p.get("images", [])})
    hero = (brand.get("home") or {}).get("hero_image")
    uploads = products.staged_upload_variables(image_dir, wanted + ([hero] if hero and hero not in wanted else []))
    fake_urls = {f: f"<staged:{f}>" for f in wanted}

    out = {
        "stage_2_theme": theme.push_new_unpublished_cmd(
            brand["store_domain"], str(theme_dir or "<cloned master theme>"), brand.get("theme_name") or f"{brand['brand_name']} - draft"),
        "stage_3_uploads": uploads,
        "stage_3_products": [{"handle": p["handle"], "create": products.product_variables(p, fake_urls),
                              "variant": products.variant_variables("<product id>", "<variant id>", p)} for p in sheet["products"]],
        "stage_4_bindings": templates.bindings_from_brand(brand),
        "needs_human_input": todo,
    }
    if theme_dir is not None:
        files = {}
        for b in out["stage_4_bindings"]:
            f = theme_dir / b["file"]
            if f.is_file():
                files[b["file"]] = f.read_text(encoding="utf-8")
        _, out["stage_4_changes"] = templates.apply_bindings(files, out["stage_4_bindings"])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--brand", required=True)
    ap.add_argument("--products", required=True)
    ap.add_argument("--images", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--theme-dir")
    args = ap.parse_args(argv)

    cfg = config.load()
    brand = json.loads(Path(args.brand).read_text(encoding="utf-8"))
    sheet = json.loads(Path(args.products).read_text(encoding="utf-8"))
    log = ActionLog(Path(args.out) / "action-log.jsonl", brand.get("client_id", "unknown"))
    try:
        result = plan(brand, sheet, Path(args.images), Path(args.theme_dir) if args.theme_dir else None)
    except (InputError, templates.TemplateError, FileNotFoundError, ValueError, KeyError) as exc:
        log.record(tier=0, mode=cfg.mode, target="inputs", action="validate", reason="check supplied files",
                   result="blocked", error=str(exc))
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "dry-run-plan.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "app-checklist.md").write_text(apps.checklist_markdown(brand), encoding="utf-8")
    for stage, tier, what in (("stage_2_theme", 2, "push new unpublished theme"), ("stage_3_products", 2, "create draft products"),
                              ("stage_4_bindings", 2, "push filled templates")):
        log.record(tier=tier, mode=cfg.mode, target=brand["store_domain"], action=what,
                   reason="dry run of the provisioning plan", result="dry_run", evidence={"stage": stage})
    print(f"Dry run OK. Nothing was sent. Plan: {out / 'dry-run-plan.json'}")
    if result["needs_human_input"]:
        print("Needs human input ([[TODO]]):", ", ".join(result["needs_human_input"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
