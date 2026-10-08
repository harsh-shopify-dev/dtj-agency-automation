# DTJ block library (theme app extension)

Design: `docs/block-library-design.md`. Status 5 Oct 2026: app "DTJ Blocks" (Dev Dashboard) is installed on the dev store `elevate-with-harsh`. The licence kill switch is proven there (editor). Blocks are GENERATED from manifests.

Current blocks (7, live release `dtj-blocks-23`, 70.9 KB of 100 KB): **Hero Points**, **Rotating Text**, **Social Proof Line**, **Testimonials**, **Shoppable Reels**, **Option Picker**, **Add-ons**. Full-width sections live in the other apps (`services/block-library-sections`, `services/block-library-sections-2`). Full details, rules and errors: `docs/HANDOFF.md`. (The seven first-built blocks, Trust Row, Highlighted Text, Offer Pill, Offer Callout, Urgency Line, Bullet Points and Secure Checkout, were removed at Harsh's request on 5 Oct 2026 to free size budget for the priority pack blocks; their files were deleted.)

## Layout
```
manifests/<id>.json           settings, slots, standard controls, tests: the single source of truth
src/<id>.liquid / .css / .js  body (no schema, no licence gate), styles, optional script
src/_check-item.css           shared styles for the round tick bullet design
tools/build_blocks.py         generates the files below from the three sources above
extensions/dtj-blocks/        the theme app extension (what Shopify serves). DO NOT EDIT generated files by hand
  blocks/dtj-<id>.liquid        generated: prelude + body wrapped in the licence gate + compact schema
  assets/dtj-<id>.css|.js       generated
  snippets/dtj-licence.liquid   the licence gate (wraps the content; prints it only when app.metafields.dtj.licence == "active")
  snippets/dtj-check-icon.liquid  the master theme's bullet icon: one solid circle with a tick
tools/check_library.py        library rules + size budget; tools/licence.py flips the licence flag (tier 2)
tests/                        rule tests, generic per-block tests, block-specific tests
```

## Run the checks (no store contact)
From `services/block-library`:
```
python tools/build_blocks.py            # regenerate (add --check to verify nothing is stale)
python tools/check_library.py           # rules + size budget (Shopify caps one app at 100 KB of Liquid and 30 blocks)
../../.work/.venv/Scripts/python -m unittest discover -s tests -t .      # Liquid tests need python-liquid in .work/.venv
shopify theme check --path extensions/dtj-blocks
```

## What the local tests prove and do not prove
Proves: our logic (fail closed, kill switch hides the block and ships no markup, nothing renders without copy, text is escaped, no copy or colours baked in, rules below).
Does not prove: how it looks (no browser here), and Shopify's server-side rules, which have each refused a deploy at least once (6-header cap, `{`/`}` inside `{{ }}`, blank range unit) and are now library rules. Always expect a retry on a new kind of block.
