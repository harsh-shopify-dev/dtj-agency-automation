# DTJ Sections 2 (third theme app extension)

Why it exists: one app holds at most 100 KB of Liquid and one extension. DTJ Blocks (7 blocks, 70.9 KB) and DTJ Sections (8 blocks, 94.8 KB) are
nearly full, so the next full-width sections go here. Design and limits: `docs/block-library-design.md`; state and history: `docs/HANDOFF.md`.

**Status (8 Oct 2026): app created (app id 432980918273, Custom distribution, org Harsh), linked, active release `dtj-sections-2-6` (Feature Showcase, Split Story Card, Stat Cards, Measured Results; confirmed with the version list). Installed on the test store with the licence flag active.**

## Blocks (4; 52.9 KB of 100 KB)
| Block (file `dtj-<id>`) | Editor name | Notes |
|---|---|---|
| `feature-showcase` | DTJ Feature Showcase | heading, a centre image, up to 3 features each side (icon, title, text); 12 built-in icons or the merchant's own; desktop = three columns, phones = image then a 1 or 2 column grid. Built from Harsh's "Why ROSEE sinks in" screenshot (no original code existed) |
| `split-story` | DTJ Split Story Card | one rounded card: photo on one side (left or right, cropped to fit, focus setting), tinted panel with a two-tone heading, a paragraph, up to 5 round check points and a white review card (avatar, quote, stars, name); phones = photo on top, compact panel. Built from Harsh's "Another cream? We hear you." screenshot |
| `stat-cards` | DTJ Stat Cards | a centred heading whose accent part has a brush underline, then up to 6 soft cards (big figure, bold line, small footnote); desktop = one row (1-4 per row, automatic), phones = stacked or a swipe row. Built from Harsh's "From greasy, to gone, to still there" screenshot |
| `measured-results` | DTJ Measured Results | a dark rounded panel: left a picture card (two-tone heading with an italic part, a line, one big figure; the picture sits below the text, or under it with the overlay option), right a heading with an accent word, a subheading, up to 5 rows (big figure, title, text) and a dashed footnote box. Built from Harsh's "Measured, not promised" screenshot |

Standard controls: top/bottom padding (`spacing_v`), side space (`gutter`, default 16 px, keeps a full-width section off the screen edges) and text/background colour. No default copy, no hard-coded colours, every block runs the licence gate.
A theme app extension can only deliver app blocks (never a standalone theme section): the merchant adds it from the Apps list. Put it in a FULL-WIDTH section for the edge-to-edge look.

## First-time setup (Harsh, once; each step is his or needs his approval)
1. DONE: the app was created in the Dev Dashboard (Custom distribution). When generating the install link, type the store as `elevate-with-harsh.myshopify.com` only (no https://, no trailing slash) and untick multi-store install.
2. DONE (verified: its client id differs from the other two apps): in PowerShell, `cd "D:\CODE CONTAINERR\WEB DEV\dtj-agency-automation\services\block-library-sections-2"`, then `shopify app config link` and pick that app.
   CHECK that the prompt path ends in `block-library-sections-2` before answering (the command rewrites that folder's `shopify.app.toml`; the wrong folder would overwrite another app's file).
3. Deploy (Tier 2, approve the exact command each time): `shopify app deploy --path "services\block-library-sections-2" --allow-updates --message "<what>" --no-color`, then confirm with `shopify app versions list --path services\block-library-sections-2` (the star = active). Expect Shopify to refuse something the local checks cannot see; each refusal becomes a library rule.
4. Install on the test store through the app's custom-distribution install link.
5. Set the licence flag `active` (a fresh install has none, so blocks show nothing, by design). In your own terminal: `$env:DTJ_SECTIONS2_CLIENT_SECRET = Read-Host "Sections 2 client secret"` (type ONLY the secret), then from `services\block-library`:
   `python tools\licence.py --shop elevate-with-harsh.myshopify.com --set active --approved-by Harsh --app sections2`
6. In the theme editor add the block from the Apps list. Block references use the new app's handle: `shopify://apps/<handle>/blocks/feature-showcase/<extension uuid>`.

## Daily commands (from `services/block-library-sections-2`, venv python)
```
python ../block-library/tools/build_blocks.py --root .            # write generated files (add --check to only verify)
DTJ_APP_ROOT=$PWD python ../block-library/tools/check_library.py   # library rules + size budget (PowerShell: $env:DTJ_APP_ROOT=(Get-Location).Path)
../../.work/.venv/Scripts/python -m unittest discover -s tests -t .
shopify theme check --path extensions/dtj-sections-2
```
Preview (from `services/block-library`, `DTJ_APP_ROOT` pointing at this folder): `python tools/preview_block.py feature-showcase ../../.work/previews/fs.png "heading=Sample" "f1_title=Sample"`; `PREVIEW_THEME=1` renders inside the real Horizon wrapper; `tools/preview_overflow.py` stress-tests long words in 9 layouts.
The shared tools live in `services/block-library/tools`. Do not copy them here.

## Known limits / things not verified
Look and feel is verified only in headless-browser renders (desktop, 800 px tablet, 390 px phone), never in Harsh's real editor, and never with a real transparent product photo.
