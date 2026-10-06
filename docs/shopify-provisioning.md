# Shopify provisioning (Phase 4 core) - decisions and how to run

Status 6 Oct 2026: **Stages 1 to 3 done on the test store `elevate-with-harsh`** (theme pushed unpublished as 188893495469; 6 DRAFT products with 42 images created). **Stage 4 partly done** (app blocks and `templates.add_app_block()` built; brand style, collection, Active products and installer not done). Stages 5 to 8 not started. Full state, IDs and open items: `docs/HANDOFF.md`.
Plan: `D:\Extra Data\DTJ\claude-terminal\plans\pasted-content-id-0ea7-system-instructi-starry-fox.md`

## Decisions
- Master theme: `harsh-shopify-dev/dtj-master-theme` (private), a fork of Shopify Horizon 4.2.0. Pin a commit SHA in the brand config, never a branch.
- First test target: a new dedicated dev store (created by hand; Partner-API creation still **[VERIFY]**).
- Inputs: brand config + product sheet + image folder, schema-checked (`schemas/`). No scraping of a prospect's content in this phase.
- Products are always created as DRAFT. One variant per product for now.
- Only these mutations can be sent: `productCreate`, `productVariantsBulkUpdate`, `stagedUploadsCreate`, `fileCreate`. Anything with "delete" in it is refused in code.
- Apps are a checklist for a person; the Admin API cannot install apps.
- Self-healing (Stage 7) will be recommend-only until Harsh moves it up.

## Findings from reading the master theme
- `templates/product.json` is dynamic, so no product handles go into it.
- `templates/index.json` shows products through the `product-list` section's `collection` setting (currently `all`). The hero image setting is assumed to be `image_1` **[VERIFY]**.
- The GOMINT `cg-` blocks belong to the Tattva Soul theme and do not carry over to Horizon directly.

## How to run (dry run only)
```
cd services/store-builder
pip install -r requirements.txt
python -m unittest discover -s tests -t .
python -m provision.run --brand brand.json --products products.json --images ./images --out ./out [--theme-dir ./theme]
```
Writes `out/dry-run-plan.json`, `out/app-checklist.md` and `out/action-log.jsonl`. Sends nothing; there is no live mode yet.
Defaults: `AUTOMATION_ENABLED` off, `DRY_RUN` on, `AUTOMATION_MODE=shadow`. `SHOPIFY_API_VERSION` has no default and must be pinned before any live call.

## Verified on 5 Oct 2026
- 52 unit tests pass (allowlist, retry and backoff, 401 halt, throttle wait, dry-run, config gate, live-theme refusal, schemas, template binding, action-log secret scrubbing, CLI dry run).
- The four GraphQL operations plus the variant `sku` and `compareAtPrice` shape passed Shopify's schema validator (current schema, not a pinned version).
- `shopify theme push --unpublished --theme <name> --json` behaviour read from the CLI's own help (v4.8.4).

## Not verified
- Nothing has run against a real store. Real cost/throttle numbers, staged-upload POST details and the `--json` output on a real push are untested.
- The pinned API version, the hero `image_1` setting and `shopify://shop_images/` references.
- Lighthouse, Playwright checkout test and self-healing (Stages 6 and 7) are not written.
- This folder is not a git repository yet, so nothing is committed and no branch or PR exists.
