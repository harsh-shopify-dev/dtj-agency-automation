# DTJ Sections (second theme app extension)

The second app of the block library. Why it exists: one app can hold only 100 KB of Liquid and one extension, and the first app
(`services/block-library`, "DTJ Blocks") is at ~73 KB. This app takes the full-width section blocks. Design and limits:
`docs/block-library-design.md`, state and history: `docs/HANDOFF.md`.

**Status (8 Oct 2026): app id 432103260161, installed on the test store (elevate-with-harsh), licence flag `active`. Active release `dtj-sections-9` (faithful FAQ / Comparison Table / Stories, light spacing controls).** When running `shopify app config link`, check that the prompt path ends in `block-library-sections`: it rewrites that folder's `shopify.app.toml`.

## Blocks (8; 94.8 KB of 100 KB, so the next faithful ports need a third app)
| Block (file `dtj-<id>`) | Editor name | Notes |
|---|---|---|
| `faq` | DTJ FAQ | port of the pack's `dtj-beauty-faq`: two-line heading, category pills, round toggle accordion; 12 questions, 6 categories |
| `comparison-table` | DTJ Comparison Table | port of `dtj-comparison-table`: two tall columns, picture rows, sticky heading beside the table (or above it); 10 rows |
| `stories` | DTJ Stories | port of `dtj-beauty-customer-stories`: rating strip, swipe row of photo cards with tags, CTA, trust line; 8 cards, tags comma-separated |
| `science-stats` | DTJ Science Stats Grid | port of `dtj-science-stats`, with an "Adapt to each image" option |
| `testimonials-slider` | DTJ Testimonials Slider | redesigned to match the pack section |
| `whats-inside` | DTJ Whats Inside | still designed from the settings list, NOT yet compared with its original |
| `whats-not-inside` | DTJ Not Inside | same: not yet compared with its original |
| `marquee` | DTJ Marquee | same: not yet compared with its original |

Lists use fixed numbered slots (no child blocks in app blocks). No default copy, no hard-coded colours. Every block runs the licence gate. Standard controls: top/bottom padding (`spacing_v`) and text/background colour. To port a block faithfully: render the ORIGINAL first (`tools/render_pack_section.py`), read all of its markup and CSS, port it line by line, then compare phone and desktop renders. The removed block `root-science` is in git history (commit 13532d9).

## Daily commands (from `services/block-library-sections`, venv python)
```
python ../block-library/tools/build_blocks.py --root .            # write generated files (add --check to only verify)
DTJ_APP_ROOT=$PWD python ../block-library/tools/check_library.py   # library rules + size budget (PowerShell: $env:DTJ_APP_ROOT=(Get-Location).Path)
../../.work/.venv/Scripts/python -m unittest discover -s tests -t .   # generic tests + tests/test_sections.py (77 tests)
shopify theme check --path extensions/dtj-sections
```
Preview a block in a real browser (from `services/block-library`, `DTJ_APP_ROOT` pointing at this folder; `PREVIEW_WIDTH`/`PREVIEW_HEIGHT` optional):
`python tools/preview_block.py faq ../../.work/previews/faq.png "question_1=Sample?" "answer_1=<p>Sample</p>"`

The shared tools live in `services/block-library/tools` (builder, rules, licence tool, preview tools). Do not copy them here.

## First-time setup (Harsh, once; each step is his or needs his approval)
1. In the Dev Dashboard (org Harsh, 141167028) create an app named **DTJ Sections** (the handle must come out as `dtj-sections`), distribution **Custom**.
2. In this folder run `shopify app config link` and pick that app. It writes `shopify.app.toml` here (client id is not a secret).
3. Deploy (Tier 2, approve the exact command): `shopify app deploy --path "services\block-library-sections" --allow-updates --message "<what>" --no-color`. Expect Shopify to refuse something the local checks cannot see (it has happened for every new block family); each refusal becomes a library rule.
4. Install on the test store through the app's custom-distribution install link.
5. Set the licence flag `active` (the install starts without one, so blocks show nothing, by design): in your own terminal
   `$env:DTJ_SECTIONS_CLIENT_SECRET = Read-Host "Sections client secret"` then
   `python tools\licence.py --shop elevate-with-harsh.myshopify.com --set active --approved-by Harsh --app sections`
   (run from `services/block-library`). Each app has its OWN client secret and its own flag.
6. In the theme editor add the blocks from the Apps list. Block references use the new app's handle: `shopify://apps/dtj-sections/blocks/<block>/<extension uuid>`.

## Known limits / things not verified
Look and feel is verified only in a headless-browser render (not in Horizon). Never deployed. The Whats Inside phone row has no dots or arrows (swipe only).
