---
name: dtj-collection-page
description: Design a client store's COLLECTION page (the page that lists a collection's products, one template for every collection) with DTJ Product List, the exact replica of Proeffex's product list, so every card shows the store's real ratings, shade swatches, offer and Add to cart; hide the theme's default product grid; check every card against the store's own data; and prepare the draft write for a person's yes. Use it whenever someone says "collection page", "shop all page", "category page", "product listing page", "PLP", "the grid of products", "add the product list section to the collection page", "ratings not showing on the collection page", or "make the collection page look like Proeffex", even if they don't name the skill. Not for the home page (dtj-home-page), a product page (dtj-pdp-factory) or a single product row on another page (place DTJ Product List directly).
---

# DTJ collection page: the Proeffex product list on every collection

Harsh, 20 Oct 2026:
- "for the collection we will create the exact app of this collection nothing should be changed and it should look exact as it is" (the
  block: DTJ Collection app, block "DTJ Product List", `services/block-library-collection/`)
- "design the collection page adding that section and ensure all the ratings and everything appears perfectly"

What that means here:
- **The card is the original, untouched.** Every card style setting keeps the replica's default (the Proeffex look: frame, star row,
  title, % OFF, price, swatches, Add to cart). The page decides only what is AROUND the cards: the title band, columns, gaps, count and Sort.
- **Real data only.** Stars come only from the store's `reviews.rating` / `reviews.rating_count` metafields (a review app writes them);
  a rating with 0 reviews behind it is never shown (`pf_hide_no_reviews`, on by default). Badges only from whole product tags
  (`best-seller`, `new`). % OFF only from a real compare-at price. Never add a rating, badge or offer to make a page look fuller
  (CLAUDE.md rule 5): a card without reviews simply shows no stars.
- **One template, every collection.** The title band reads `{{ closest.collection.title }}` / `.description`; the list's Collection
  setting is left EMPTY, and on a collection page the block then shows that page's own collection (Shopify refused `autofill` on a
  collection setting on 20 Oct 2026; library rule 23 now stops it locally).
- **Tier 2 every time.** Harsh's standing draft rule covers product and home pages only. A collection page is written only after a
  person's yes for that exact page (the approval code), through `push_page`, to a DRAFT theme. Never the live theme.

## The page (`services/store-builder/page_builder/assemble_collection.py`)
| Section | Made of | Notes |
|---|---|---|
| header | the theme's own `section` + 2 text blocks | H1 = collection title (theme h3 size), the description under it, centred, on the page colour; padding 40 / 28, or 32 / 12 when the links row follows (the theme makes it 0.7 on phones) |
| nav | DTJ Commerce circle-menu | the store's own collections from `home-facts.json` "categories" (3-8; their own pictures, names, links), no heading, framed squares / circles / rings by niche, 88 px tiles (64 on phones, one row to swipe), on the page colour; left out with the reason when the facts have fewer than 3 |
| products | `_blocks` wrapper + DTJ Product List | the page's collection, up to 50 products, 4 laptop / 2 phone columns, 16 px gaps (12 on phones, the block's cap), "N products" + Sort above, no block heading (the H1 is the heading); on the palette's soft `panel` tint so the white framed cards stand out (Proeffex: white cards on #F5F5F5) |
| trust (optional) | DTJ Commerce marquee-band, line style | only with 3-6 STORE-WIDE points in `collection-page.json` (shipping, payment, returns), each with its source; product claims never |
| faq (optional) | DTJ Sections faq | the client's own FAQ from `home-facts.json` |

The theme's `main-collection` grid, its old title section, the earlier Proeffex test copies and any DTJ Product List placed by hand are
kept in the file but **switched off** (`assemble_collection.merge`): undo = switch them on in the editor. Other sections stay as they are.

**Not built (say so plainly when asked):** filters (Availability, Price...) and pages beyond 50 products. Shopify gives one page of a
collection 50 products; a bigger collection shows its first 50 in the chosen sort order. Filters need a decision from Harsh (they matter
from about 20 products; DTJ clients usually have fewer). Sort uses Shopify's own `?sort_by=`; the live check proves it reorders.

## Design rules (measured on 12 public collection pages, 20 Oct 2026; `references/study.md`)
| Rule | Measured | What the builder does | Checked by |
|---|---|---|---|
| First products inside the first screen | first picture 282-413 px down a phone (median 361); 375-617 on a laptop | compact title band | `COLLECTION_TARGETS`: at most 420 / 620 px; live check L5, preview |
| Ratings on every card that has reviews | 8 of 8 pages | the replica's star row from the metafields | live check L6 (every card against the store) |
| Count and Sort above the grid | every page has Sort, most show the count | `show_sort` | template CC5, live check L11 |
| Grid | 2 phone columns everywhere; 3-4 on laptops; 10-16 px phone gaps | 4 / 2, 16 px (12 on phones) | CC5, live L4 |
| Title | 24-50 px laptop, 20-34 phone | the theme's h3 preset | live L2 (exactly one H1, the collection's title) |
| Collection links above the grid | 4 of 8 pages | the nav row (real collections only) | look at the preview |
| Colour | per brand (Harsh, 19 Oct: "every brand has their own color palette"); Proeffex's grid sits on #F5F5F5 with white framed cards | `COLLECTION_COLOURS`: title and links on the page colour, products on the palette's soft `panel` tint | look at the preview |

## Steps
### C0. Orient
Read `CLAUDE.md` and the latest `docs/HANDOFF.md` collection entry. Confirm: the store's ORIGINAL `.myshopify.com` address, the DRAFT
theme id (role unpublished), the client folder (`.work/clients/<client>/` with `brand.json` and `home-facts.json`), and a collection to
check with. Pick one whose products have real reviews and shade swatches if the store has one: on a collection without them the rating
and swatch checks (L6, L7) pass with nothing to test, so also run C2/C3 on such a collection (or a test collection) and say which you
used. **Gate:** all four known, or one precise question.

Commands below are for Git Bash from the repo root (forward slashes). Two Pythons: `.work/.venv/Scripts/python.exe` (has python-liquid:
the builder, the checks, the preview) and the system `python` (has Playwright: `check_collection_live.py`). Any command with `--store`
and `--theme` reads the theme with the store's Theme Access password, kept in the Windows variable `DTJ_THEME_ACCESS_<STORE HANDLE>`
(e.g. `DTJ_THEME_ACCESS_ELEVATE_WITH_HARSH`); check it exists by NAME only, never print it. Missing: ask the person to set it
(`docs/ACCESS-AND-KEYS.md`), never to paste it in chat. The read-only store queries use the CLI's own sign-in instead.

### C1. The app on the store (in this order)
1. **Released?** `shopify app versions list --path services/block-library-collection` (read-only): the ACTIVE version's message must
   mention the collection page (first release with it: 20 Oct 2026, "DTJ Product List: collection page ..."). If not, the release is
   Tier 2 and the person's command (the classifier blocks Claude): `shopify app deploy --path "services\block-library-collection"
   --allow-updates --message "<what changed>"` in their PowerShell after the PATH line in `services/block-library-collection/README.md`.
   Before asking, run `check_library.py` for the app (Shopify refuses some schema attributes the docs suggest, e.g. `autofill` on a
   collection setting: library rule 23).
2. **Address known?** The app's address (extension uuid) is only known from a placed block. If `page_builder/registry.json` says
   `"uuid": "pending"` (or the client registry has no `dtj-collection`): AFTER the release, ask the person to add DTJ Product List once in
   the DRAFT theme's editor (Collections template > Add section > Apps > DTJ Product List > Save), then, read-only:
   `cd services/store-builder && ../../.work/.venv/Scripts/python.exe -m page_builder.run_collection --learn-uuid --store <store> --theme <id>`.
   With its Collection setting left empty, that placed block should already show the page's products on the draft's collection pages:
   the first proof that the fallback works. The merge switches that placed block off later.
**Gate:** the active version has the collection-page settings; the address is known; `run_collection` no longer reports PENDING ADDRESS.

### C2. Store data (comes with the preview)
`preview_collection.py` (C3) prints, from the store's own data, what EACH card will show: stars and review count (or "no stars (no
reviews)"), swatches, badge, offer, Add to cart or Sold out; `preview.json` keeps it. C2 and C3 can run before C1 is finished. Report
what will look empty and why (no reviews yet, no swatches set in Admin, sold out), never fill it. **Gate:** the person knows what the
cards will and will not show.

### C3. Build and preview
```bash
cd services/store-builder
../../.work/.venv/Scripts/python.exe -m page_builder.run_collection --client ../../.work/clients/<client> [--sections header,products,trust,faq]
../../.work/.venv/Scripts/python.exe -m page_builder.collection_checks --run ../../.work/clients/<client>/collection-run
cd ../..
.work/.venv/Scripts/python.exe .claude/skills/dtj-collection-page/scripts/preview_collection.py --client .work/clients/<client> --store <store> --collection <handle> [--theme-css <a pulled theme's assets/base.css>]
python .claude/skills/dtj-collection-page/scripts/check_collection_live.py --store <store> --collection <handle> --preview .work/clients/<client> --out .work/clients/<client>/collection-live-preview
```
Look at `collection-preview/phone-390.png` and `desktop-1280.png` yourself. **Gate:** before C1 is done, the ONLY build problem is
PENDING ADDRESS and the ONLY failing template check is CC6; after C1, none. The preview passes the card checks; the first picture is
within the targets.

### C4. Approval (Tier 2)
Run `run_collection` again with `--store` and `--theme` (read-only: it checks the theme is a draft Horizon theme, backs up
`templates/collection.json` and merges); then `collection_checks` must pass with no finding at all. Show the person: the two screenshots, what changes (sections added, sections switched off), what
the cards will not show and why, the target (store, draft theme id, `templates/collection.json`) and the approve code. **Gate:** their
"yes" with the code, in this session, by name.

### C5. Write and verify
The person (or Claude when allowed) runs
`python -m page_builder.push_page --out ../../.work/clients/<client>/collection-run --approve <code> --approved-by <name>` (draft only,
backup, read-back, action-log row). Then `check_collection_live.py --store <store> --theme <id> --collection <handle> --out ...` on the
real draft: every check L1-L12 must pass, including Sort really reordering. Update `docs/HANDOFF.md`. **Gate:** live check PASS, or
each finding explained with its fix.

## Talking to the person
Lead with the result in one line, then what they must do (numbered, exact clicks or one command each), then detail. Say what the cards
show and why some show less (no reviews yet, no swatches, sold out). Never ask anyone to paste a secret; the CLI holds its own sign-in.

## Files
| File | What |
|---|---|
| `services/block-library-collection/` | the app and the block (src, manifest, tests; README for releases) |
| `services/store-builder/page_builder/assemble_collection.py` | the page: sections, numbers, merge |
| `services/store-builder/page_builder/run_collection.py` | build, theme check, approval file, `--learn-uuid` |
| `services/store-builder/page_builder/collection_checks.py` | template checks CC1-CC6 |
| `services/store-builder/page_builder/base/horizon-collection-parts.json` | Horizon 4.2.0's own settings the page writes, for validation |
| `scripts/preview_collection.py`, `scripts/store_read.py` | local preview with the store's real products (read-only) |
| `scripts/check_collection_live.py` | the page as shoppers see it, against the store's data (L1-L12) |
| `scripts/study_capture.py`, `references/study.md` | the 12-page study and its numbers |
