# Prompt: build "Proeffex product list" as a DTJ app block, an exact replica (20 Oct 2026)

Paste everything below the line into the Claude Code session that builds DTJ's theme app extensions (repo
`D:\CODE CONTAINERR\WEB DEV\dtj-agency-automation`, folders `services/block-library-*`).

---

Read `CLAUDE.md` and the newest entry of `docs/HANDOFF.md` first, then
`.claude/skills/dtj-pdp-factory/references/building-a-missing-block.md` and `services/block-library-commerce/README.md` (how our app
blocks are built, checked, licensed and released).

## The job
Build a new DTJ app block that is an EXACT replica of the Proeffex collection section "Proeffex product list". It must look and behave
exactly like the original: same layout, same sizes, spacing, colours, borders, radius, font sizes and weights, same breakpoints, same
settings with the same names, labels, ranges and defaults, same behaviour. Nothing redesigned, nothing "improved", nothing left out.

- The original code (the only source of truth): `D:\CODE CONTAINERR\WEB DEV\PROEFFEX-junior-collection-backup-2026-09-25\sections\proeffex-producttab-collection.liquid`
  (1,230 lines, 34 settings: collection, layout grid / carousel / editorial, carousel on mobile, product count, columns, mobile columns,
  gaps, width, alignment, padding, plus every `pf_` setting: phone layout, compact cards, compact rating, card frame, card padding,
  Best Seller / New Launches tag badges, hide the sale badge, "% OFF" text, image ratio and fit, title lines, button height, compare and
  review colours, swatch size, gap, alignment and show-all). Do NOT use our ported copy in `.work/push-proeffex-producttab/`: it was
  adapted for Horizon 4.2.0 and is not the reference.
- How it looks (the visual reference): Proeffex's Dev theme, READ-ONLY. Store `1sq0y0-3c.myshopify.com`, theme "Proeffex Dev"
  `193583382709`, the page `iconic-cover-concealer` (page template `iconic-cover-concealer`):
  https://1sq0y0-3c.myshopify.com/pages/iconic-cover-concealer?preview_theme_id=193583382709
  The reference is the FIRST product list on that page (section id ending `proeffex_product_list_3wEipx`, collection "Iconic Cover
  Concealer"); the second one (`product_list_UAVWw6`) is Horizon's own product list, not the reference. Its card: framed white card,
  product picture, "★ 4.5 | 252 reviews", bold 2-line title, price, shade swatches (all shown, wrapping), one black "Add to cart" button.
  Never touch Proeffex's live theme `191887081653`, never write anything to that store.
- Confirm the source first: on the Dev theme that section's file is `sections/proeffex-product-list.liquid` (the section id says so).
  If you can read it (read-only pull), compare it with Harsh's file above; if they differ, show Harsh the differences and ask which one
  to replicate before building.

## What cannot be copied as code, and how to handle it
The original is a THEME section built on Horizon 1.0.2's own pieces: theme blocks (`_product-list-content` with the collection title
and View all button; `product-card` with gallery, review, price, title, swatches and buy buttons) and theme snippets
(`resource-list-carousel`, `editorial-product-grid`, `gap-style`, `spacing-style`). An app block cannot call theme blocks or theme
snippets, and our blocks must work on any theme (Horizon of any version, Dawn). So rebuild the SAME OUTPUT inside the app block: the
same markup structure the CSS expects, the original CSS rules and numbers, and the scripts (carousel, swatch picks that change the picture
and the variant in the Add to cart form, the "% OFF" text, the variant sync), with the data read from Liquid objects (product, variants,
images, `reviews.rating` / `reviews.rating_count` metafields, compare-at price). The font family comes from the store's theme, as in the
original; every other visual number comes from the original file.

## Two behaviours to confirm with Harsh BEFORE you build (do not decide them yourself)
1. Tag badges match by substring: any tag that merely contains "new" (`new-deal`, `renewal`) shows "New Launches". On a client store
   that is a false claim (CLAUDE.md rule 5). Ask: copy exactly, or match whole tags (`new`, `best-seller`)?
2. The original has a script that disables `window.confetti` and removes every fixed, click-through `<canvas>` on the page (a Proeffex
   store fix). In an app used on other stores it can break another app's animation. Ask: copy, or leave out?

## How to prove it is exact
- Before building: measure the original on the Proeffex Dev preview in the built-in browser at 390 and 1280 px (computed styles, not
  guesses): card width and height, frame border, radius, padding, gap between image and text, font size and weight of title, price,
  compare price, "% OFF", rating, button height, radius and colours, swatch size and gap, columns and gaps. Save the numbers.
- After building: put the block on the test store's DRAFT theme (elevate-with-harsh, `188893495469`, never a live theme) with the same
  settings, measure the same numbers at 390 and 1280 px, and show a side-by-side table original vs app plus screenshots. Every number
  must match; list any that cannot, with the reason. Check no sideways scroll, no console errors, add to cart works, a swatch changes the
  picture and the cart variant, the carousel works on phones.
- The test store's products (Toilova) have no reviews and no shade variants, so the rating row and the swatches cannot be compared on
  them. Ask Harsh for a test product with shade variants and review metafields (creating a product is Tier 2: his yes), and never put a
  made-up rating on a real product.
- Our checks: `check_library.py`, the block tests, the licence gate, the extension size limit (Shopify allows 100 KB of Liquid per
  theme app extension; DTJ Commerce is at 94 KB, and the original alone is about 45 KB, so it will need its own app or one with room:
  say which and why before creating anything).

## Rules
- Work on a feature branch; never commit to main.
- Releasing an app version, creating an app and installing it are Tier 2: Harsh's yes each time, with the exact command.
- No invented reviews, ratings, prices or badges: show only what the store's data has.
- No secrets in files or chat.
- Report in plain words at the end: what was built, the numbers table, what was verified and what was not. Update `docs/HANDOFF.md`.
