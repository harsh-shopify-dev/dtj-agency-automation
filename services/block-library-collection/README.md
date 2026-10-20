# DTJ Collection (sixth theme app extension)

Why it exists: collection and home product rows that look and behave EXACTLY like a client's own section. First block: **DTJ Product List**, an exact app-block replica of Proeffex's
"Proeffex product list" section (`proeffex-producttab-collection.liquid`, Horizon 1.0.2 product cards with the Proeffex compact look). Harsh, 20 Oct 2026: build it as a new app
("it will be a collection page section"). The other apps are 87-97 KB full, this one holds 27 KB.

**Status (20 Oct 2026):** linked (client_id in `shopify.app.toml`), released (`dtj-collection-3` active with the cart fix) and installed on
elevate-with-harsh. The collection-page settings below (`show_heading`, `show_sort`, `pf_hide_no_reviews`, autofill, 50 products) are
built and tested locally and NOT released yet.

## What the block is (and is not)
- The original is a THEME section made of Horizon's own blocks and snippets (product-card, gallery slideshow, review, price, swatches, buy-buttons, carousel, editorial grid). An app block
  cannot call those, so the block rebuilds the same OUTPUT: its own markup, css and a 9 KB script that reproduce the numbers measured on the original
  (Proeffex Dev theme 193583382709, page `iconic-cover-concealer`, first product list, at 390 and 1280 px). The font comes from the store's theme, as in the original.
- Settings: the original's 34 (same ids, labels, ranges, defaults, `visible_if`), plus `heading`, `show_view_all`, `view_all_label` (the header was a theme block), `pf_badge_source`,
  and the standard Text / Background colours (an app block has no `color_scheme`). 39 settings.
- Tag badges use WHOLE product tags (`new`, `best-seller`, any capitals); the original matched any tag containing "new". `pf_badge_source = sample` shows sample badges in the theme editor only.
- The original's script that deletes the page's confetti / click-through canvases is NOT included (it can break another app).
- The original colours are written as `rgb()` in the css (frame, button, offer green, badges, star gold): they are the original's fixed colours, the merchant's colours still win. Library rule 4 is about hex; this is a documented exception.
- Ratings come only from the store's `reviews.rating` / `reviews.rating_count` metafields. Nothing is ever invented.
- **Collection page (added 20 Oct 2026, skill `dtj-collection-page`):** an EMPTY collection setting on a collection page shows that page's own
  collection (Shopify refused `autofill` on a collection setting: "'autofill' is not a valid attribute"), up to 50 products (one Shopify page),
  `show_heading` (off on a collection page: the page's H1 is the heading), `show_sort` (the product count and a Sort menu using Shopify's own
  `?sort_by=`), and `pf_hide_no_reviews` (on by default: a placeholder rating with 0 reviews behind it is never shown; the original would show
  "1.0 | 0 reviews"). All four are off or unchanged by default where the original had a setting, so the replica still measures 41 of 42 parts
  exact and passes 33 of 33 behaviour checks. 42 settings.
- Not exact by nature: the "non-compact" card (the original shows the theme's own default card there) is a plain card; the Sale / Sold out pills (hidden by default) are generic.

## First-time setup (Harsh; each step is his or needs his yes)
1. Dev Dashboard: create the app `DTJ Collection` (Custom distribution, organization Harsh).
2. In a normal PowerShell:
   ```
   $env:Path += ";C:\Users\harsh\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\npm"
   cd "D:\CODE CONTAINERR\WEB DEV\dtj-agency-automation\services\block-library-collection"
   shopify app config link
   ```
   pick `DTJ Collection`; CHECK that the path in the prompt ends in `block-library-collection`.
3. Deploy (Tier 2): from the repo root `shopify app deploy --path "services\block-library-collection" --allow-updates --message "DTJ Product List: replica of the Proeffex product list"`.
4. Install on the test store (a fresh link; Incognito if "installation link is invalid"), then set the licence flag.
5. Register the app AFTER step 2: `services/block-library/tools/licence.py` (`APPS`, env var `DTJ_COLLECTION_CLIENT_SECRET`) and its tests, `tools/dtj-licence.ps1`,
   `page_builder/registry.json`, `page_builder/block_tags.json`, `clients/<store>.json`, the vault, the install catcher and the Telegram bot's licence calls.

## Daily commands (from `services/block-library-collection`, venv python)
```
python ../block-library/tools/build_blocks.py --root .            # write generated files (add --check to only verify)
DTJ_APP_ROOT=$PWD python ../block-library/tools/check_library.py   # library rules + size budget
DTJ_APP_ROOT=$PWD ../../.work/.venv/Scripts/python -m unittest discover -s tests -t .
```

## Proof (private, in `.work/proeffex-product-list/`, not committed)
`replica/render_local.py` renders the block with the original product's real data inside Horizon's own base.css and theme variables; `replica/compare.py` compares each part with the
original page (computed styles, 390 and 1280 px): 41 of 42 parts exact (the heading's width differs: the original's heading has italic words and a trailing space);
`replica/behaviour.py` runs 32 checks in a real browser (swatch pick, price and % OFF, sold-out shade, add to cart, gallery arrows, carousel, editorial, phone variants, dark scheme, setting changes).
`original/` holds the measurements and the style dump of the original; `make_test_product.py` creates the test product on elevate-with-harsh.
