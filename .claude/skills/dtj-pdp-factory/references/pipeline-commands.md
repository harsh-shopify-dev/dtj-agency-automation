# Pipeline commands (exact, tested 9-10 Oct 2026)

Run from the repo root unless a `cd` is shown. Secrets are NEVER typed into a command or printed: every tool reads them from
Windows user variables (env first, then the registry `HKCU\Environment`). Check a variable by its shape only (name exists, length,
prefix), never by printing it.

## A. New client: app copies, catcher, install (once per store)

1. Harsh creates 3 empty apps in the Dev Dashboard (org 141167028): "DTJ Blocks - <Label>", "DTJ Sections - <Label>",
   "DTJ Sections 2 - <Label>", and saves each client secret as `DTJ_SECRET_<NAME>_BLOCKS / _SECTIONS / _SECTIONS2`
   (NAME = the `--name` below in capitals, dashes as underscores). He sends the 3 client IDs.
2. Register them (writes `shopify.app.<name>.toml` in each app folder and the catcher's APPS):
   ```
   python services/install-catcher/tools/add_client.py --shop <ORIGINAL>.myshopify.com --name <name> --label "<Label>" \
     --worker https://dtj-install-catcher.ultimateecomwithharsh.workers.dev --blocks-id <id> --sections-id <id> --sections2-id <id>
   ```
   `--shop` must be the store's ORIGINAL address: the handle in `admin.shopify.com/store/<handle>` (a renamed store still installs
   under its original name; seen with qaxv3r-8g -> test-store-harsh-dtj).
3. Check each secret matches its app without printing it: compare `shopify app env show --path services/<folder> --config <name>`
   (SHOPIFY_API_SECRET) with the Windows variable inside a script that prints only "match" / "no match".
4. Deploy the catcher (Tier 2: Harsh's yes):
   `CLOUDFLARE_ACCOUNT_ID=530794c3825d1c37ba7f8af33b6415df python services/install-catcher/tools/deploy.py`
   Expect `/health -> 200 {"ok":true,"apps":N}`.
5. Release the 3 copies, ONE at a time, output to a file (Tier 2: Harsh's yes):
   `shopify app deploy --path services/<folder> --config <name> --allow-updates --message "<why>" --no-color > release.log 2>&1`
   folders: `block-library`, `block-library-sections`, `block-library-sections-2`.
6. Record the block addresses IMMEDIATELY after step 5 (the next release overwrites the record):
   `python services/install-catcher/tools/client_registry.py --client <name>` (exit 2 = handles pending until the install).
7. Harsh (store OWNER, not a collaborator login) on each app: Distribution -> Custom distribution -> `<store>.myshopify.com` ->
   "Allow multi-store install" UNTICKED -> Generate link -> open it logged into that store -> Install -> "... is connected".
8. Check: `python services/install-catcher/tools/licence_call.py <name>-blocks status` (and -sections, -sections2): `"licence":"active"`.
   Then run step 6 again to fill the handles.

## B0. Build, check and write the draft in ONE command (the standard since 10 Oct 2026)

First, for a product already on the store, read it and its pictures (read-only):
```
python -m page_builder.fetch_product --store <ORIGINAL>.myshopify.com --handle <handle> --client <C>
```
It writes `<C>/store-product.json` (title, prices in rupees, variants, description as text, every picture's STORE file name) and
saves the pictures in `<C>/media/` under those names. Use exactly those names in `facts.media[].file` (they become
`shopify://shop_images/<name>`). Videos are listed only: `facts.ugc[].video` needs the Content > Files name (ask Harsh).

```
cd services/store-builder
python -m page_builder.ship_draft --client <C> --store <ORIGINAL>.myshopify.com --theme <draft id>   --template-suffix dtj-<product> --client-registry page_builder/clients/<name>.json      [--design-only]
```
- Reads `<C>/brand.json`, `facts.json`, `copy-answer.json` and, when present, `media/` and `kept-edits.json`; the run goes to `<C>/run`.
- Gates in order, any failure stops BEFORE the store is touched: run_client (fixed sections, `--plan off`; a headless-browser start
  failure is retried, max 3 runs) -> review pass, lint errors 0, build problems 0 -> `design_checks.py` all pass -> `push_page`
  with the build's own approve code (draft only, backup, read-back, action-log row; `--allow-samples` / `--allow-demo` added only
  because it is a draft preview). An approval.json from an earlier run is deleted first, so an old page can never be pushed.
- Writes `<C>/run/ship-result.json` (page_status, approve_code, preview_url, design_checks, samples, dtj_copy, note) = the body for
  `python n8n/store-factory/reply.py --resume-url <url> --body <C>/run/ship-result.json` when n8n is waiting for the page.
- Exit 0 written (or designed with `--design-only`), 2 needs a look (the note says which gate), 1 could not build.
- Section B below is what it runs; use B directly only to debug one step.

## B. Design a page (read-only for the store)

```
cd services/store-builder
python -m page_builder.run_client --brand <C>/brand.json --facts <C>/facts.json --store <ORIGINAL>.myshopify.com --theme <id> \
  --out <C>/run --media <C>/media --plan answer --plan-answer <C>/plan-answer.json --copy answer --copy-answer <C>/copy-answer.json \
  --client-registry page_builder/clients/<name>.json --template-suffix dtj-<product>
```
- `<C>` = `../../.work/clients/<client>-<product>` (git-ignored).
- Editor edits to keep: `--keep-edits <C>/kept-edits.json` (a list of {section, block, setting, value, why}; the build stops if a
  block or setting no longer exists). Reader videos: in `facts.ugc[]` add `"video": "<name in Content > Files>"` (the picture
  stays as fallback).
- First run with `--plan dry --copy dry` (or `off`): it writes `plan-request.json` / `copy-request.json`; answer them (you are the AI
  step while Harsh is in the loop; unattended runs use the API key: `--plan live --copy live`), then run with `answer`.
- `--no-theme-check` designs without reading the store (nothing can be pushed from it). The theme check refuses a LIVE theme by design.
- Exit 0 = ready for approval, 2 = needs a person's look, 1 = could not run. Outputs: `template.json`, `approval.json` (approve_code),
  `build-report.json`, `page-390.png`, `page-1280.png`, `graphics-todo.json`, `plan.json`, `copy.json`.

## C. Review (the `dtj-pdp-design-review` skill)
Run it on `page-390.png` + `page-1280.png` before asking for approval, and on the real storefront after writing.

## D. Write (drafts: Harsh's standing rule, no code needed, normally done by `ship_draft`; live: his yes, every time)
- Draft theme: `python -m page_builder.push_page --out <C>/run --approve <code> --approved-by Harsh [--allow-samples] [--allow-demo]`
  (`--allow-samples` only for a draft preview that still holds SAMPLE values; Harsh's yes covers it)
  (refuses a live theme, backs up, writes only the named template file, reads it back, logs).
- Live theme: no tool does this. `.claude/settings.json` blocks `--allow-live` on the command line on purpose. Ask Harsh: either he
  duplicates the theme (Online Store > Themes > ... > Duplicate) and the page goes to that draft, or he publishes it himself.
  (On 9-10 Oct a session-only script wrote to two live themes after Harsh's explicit yes; that sidestepped the block and is
  NOT the process. See the errors playbook, "live theme".)

## E. Verify on the real store
- Alternate template preview: `https://<store>/products/<handle>?view=<suffix>` (works before the product is assigned). For a DRAFT theme open
  `https://<store>/?preview_theme_id=<id>` first (it sets a cookie), then the product URL in the same browser / cookie jar.
- Blocks present: the page HTML contains `cdn.shopify.com/extensions/<id>/<app-handle>-<version>/assets/dtj-...` for each app.
- Kill switch: `licence_call.py <name>-sections inactive --approved-by Harsh --reason "test"` -> that app's blocks vanish at once
  (only their CSS/JS still load) -> `active` again. Both changes are audited by the catcher.
- Assign the template: Products > <product> > Theme template > `<suffix>` (Harsh, or a product write with his yes).
