# Building a missing block (a wireframe gap G1-G9)

Harsh's decision (10 Oct 2026): when the wireframe needs a section no DTJ block can build, BUILD the block instead of settling for
the nearest one. This is engineering work on a feature branch with tests; releasing it is Tier 2 (Harsh's yes, then
`shopify app deploy` for our own app and for every client copy that should get it).

## Before writing anything
1. Read `services/<app>/README.md` (layout, commands) and the library rules in `services/block-library/tools/check_library.py`
   (each rule cites the Shopify refusal that created it). Read `docs/block-library-design.md` for the licence gate.
2. Choose the app by size budget: each app may hold at most **100 KB of Liquid and 30 blocks** (Shopify's cap). Check with
   `python tools/check_library.py` in each app folder; put the block where it fits.
3. Write the block's contract in the PR description first: which wireframe slot(s), settings (ids, types, limits), mobile
   behaviour, what the builder will set, what stays empty without facts.

## The rules that Shopify or Harsh enforced (all checked by code)
- Blocks are GENERATED: edit `manifests/<id>.json` and `src/<id>.liquid|.css|.js`, then `python tools/build_blocks.py`. Never edit
  `extensions/.../blocks/*.liquid` by hand (`build_blocks.py --check` fails on stale files).
- Every output is wrapped in the licence gate (fail closed: nothing renders unless the licence is `active`); with no copy the block
  renders nothing for shoppers and a dashed note in the theme editor.
- No default copy, no hard-coded colours (settings or theme variables only).
- An app block cannot contain child blocks: lists are numbered slots (`item_1..item_6`).
- Schema name at most 25 characters; one resource picker per type; at most 75 interactive settings (keep under 40 where possible:
  Theme Check warns above 40); at most 6 header settings.
- Never put a literal `{` or `}` inside `{{ }}`; read `*_list` settings by looping, never by position.
- Every `<img>` has an explicit size in CSS; scripts under 10,000 bytes; respect `prefers-reduced-motion`.
- New setting ids only: never rename or remove an existing setting id (live templates use them).

## Tests (in the same commit)
- Generic per-block tests run automatically from the manifest; add block-specific tests for its logic (render with python-liquid
  in `.work/.venv`: empty settings render nothing for shoppers, licence off ships no markup, text is escaped, mobile classes exist).
- `shopify theme check --path extensions/<ext>`: 0 errors.
- Then teach the page builder: a builder in `sections.py` (facts -> settings, omit rule), the slot in the recipe, catalog and lint
  tests, and a fixture that exercises it. A block the builder cannot fill is not finished.

## Release (Tier 2)
1. Harsh's yes for our app, then `shopify app deploy --path services/<app> --allow-updates --message "<what>" --no-color`.
2. Each client copy that should get it: `--config <client>` the same way, one at a time, then rerun `client_registry.py`
   (the uuid does not change on a new version, but run it anyway: it proves the record is current).
3. Verify in a real theme editor (Harsh) or on a draft page before using it on a client page.
