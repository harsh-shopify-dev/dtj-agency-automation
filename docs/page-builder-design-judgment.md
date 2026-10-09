# Page builder: the design judgment, written down

Code: `services/store-builder/page_builder/`. Tests: `services/store-builder/tests/test_page_builder.py` (37). Written 9 Oct 2026 from the hand-built TOILOVA page and
Harsh's corrections while building it. The goal: for ANY client, the automation designs a product page that looks like that brand and is built to convert,
using only our blocks, with every word traceable to a fact.

## How a brand becomes a page

```
brand profile (name, category, price tier, voice, colours, fonts)  +  product facts (each with a source)
        |                                                                  |
   direction.py: palette roles, shape, type, density, motion, signature     sections.py: facts -> block settings (missing facts = section omitted)
        \________________________________________________________________/
                                   assemble.py: recipe order, bands, buy box, template JSON
                                                   |
                                  rules.py (L01-L12)  +  catalog.py (settings exist in the real blocks)
                                                   |
                           report: every choice with its reason, what was omitted and why, what needs replacing
```
Same input, same page (deterministic). A model is used for exactly one thing: rewriting structural signposts inside `copy_contract.py`, validated by code.

Since 9 Oct 2026 the page then goes through two more steps (run all of it with `python -m page_builder.run_page`, see below):
```
built page -> copy_step.py (Claude API: signposts only, every line checked, any failure keeps the template wording)
           -> review.py (render the real blocks, measure on a 390 px phone and a 1280 px desktop, revert failing Claude lines, re-check)
           -> template.json + build-report.json + copy.json + review.json + preview.html + page-390.png + page-1280.png  -> a person approves
```

## The Claude copy step (copy_step.py)
- **One API call per page**, model `claude-opus-5-5`, effort `medium`, structured output (a JSON schema built per page: one required text per
  signpost, because structured outputs accept only closed objects and no length limits; the 48-character limit and every other rule are enforced
  afterwards by `copy_contract.validate_response`, the real gate). Anthropic's server-side fallback is on (`fallbacks: "default"`).
- Only signposts are sent (never fact text). A line that is unchanged is not recorded as a rewrite. Refusal, cut-off answer, API error, bad JSON or a
  rewritten page that fails lint all leave the template wording in place; the report says which happened.
- The key: `ANTHROPIC_API_KEY` in the environment (from the vault), read by the SDK only; never passed, printed or logged. Default is a **dry run**
  (the exact request is written to `copy.json`, nothing is called, nothing is spent). Every live run records model, prompt fingerprint, tokens and
  the cost worked out from the listed prices.

## The screenshot review loop (review.py, render.py, browser.py)
`render.py` draws the whole page from the REAL generated block files (python-liquid), their CSS/JS and Horizon's `base.css` review copy; the theme's
own product-section parts (gallery, title, picker, buy buttons) are marked stand-ins and pictures are labelled placeholders unless `--media` points
at the real files. Headless Edge measures it (an iframe gives a true 390 px phone). Checks, all measured, none left to a model's eye:
R01 page wider than the screen | R02 element past the edge | R03 rendered text contrast (4.5:1, 3:1 for large text and for symbol-only text such as
stars, WCAG 1.4.11) against what is really behind it | R04 text on a picture/gradient or an unmeasured colour space (warn: a person looks) |
R05 cut-off text (warn) | R06 empty block | R07 tap target under 24 px on the phone (warn) | R08 picture fails to load.
**The loop may fix only one thing by itself:** Claude-written lines in a section that fails an error check go back to the template wording and the
page is checked again. Everything else is "needs human", with the screenshots. The real store preview after an approved push stays the final check.

What the first runs found and fixed (9 Oct 2026), proof that rendering catches what planned colours cannot:
- the struck-through compare-at price used the block's default "softer shade": 3.57:1 on white. The page builder now sets it to the direction's
  muted colour (checked 4.5:1 on the page).
- on a dark brand the review slider's cards defaulted to white under light text (1.12:1); now the direction's card pair is set for every brand.
- the rating stars' plain gold was 2.2:1 on light pages; `direction.rating_star` darkens it only as far as 3:1 needs (light brands #BA8500, dark
  brands keep #E0A100) and the pair is in the contrast checks.
- on a dark brand the slider's star tiles took the light text colour behind a white star (invisible, seen in the screenshot; SVG icons are not
  measured yet). Dark brands now get `direction.rating_tile` (white star 3.26:1).
- an overflow on phones came from the preview's own stand-in grid, not from the theme: Horizon caps its product columns (`minmax(0, ...)` subgrid);
  the stand-in now does the same.
**Still open (block library, needs a release you approve):** the Testimonials block draws the avatar initial and the slider draws its star in the
browser colour `Canvas` (white in a light theme, dark in a dark one), so on a light accent (Nocturne's gold: 2.4:1) the initial is unreadable and
the result depends on the theme's colour scheme. Fix: an explicit "avatar text colour" (and "star colour") setting, or pick black/white by contrast.

## Adapting to the brand (direction.py)
| Decision | How it adapts | Why |
|---|---|---|
| Colours | Page = the brand's background and text. Band = a very light tint of the brand colour. Dark band = the brand colour darkened. Accent = the brand's accent (or primary), pushed toward black or white until it reaches 4.5:1 on what it sits on. | A brand colour that fails contrast loses sales and is reported, never shipped. |
| Dark brands | Bands lighten the page background; the dark band darkens it; text keeps 7:1+. | A dark brand must not get a white template. |
| Shape | sharp, soft or round from the brand (or category): ONE radius family for cards, buttons and chips. | One radius everywhere reads as a template; mixed radii read as sloppy. A family reads as a brand. |
| Type | Heading class (theme / sans / serif) from the brand's fonts or category; the accent-word treatment follows the voice (serif italic for luxe and warm, bold for clinical and playful, plain otherwise). | Brands must not share a type treatment. |
| Accent words | At most 2 accent headlines per page (1 for premium). | Accenting a word in every heading is the commonest tell of a generated page. |
| Eyebrow labels | At most 2, only when a real fact exists. | A label above every heading decorates instead of informing. |
| Density and motion | Value 28/32 px, mid 32/36, premium 36/40; premium and warm brands fade, others slide; nothing animates on its own except the slideshow timer. | Premium reads as air; motion is spent in one place. |
| Signature | One emphasised section per category (story card, proof panel, free-from band, hero slideshow). | "Spend boldness in one place": one memorable element, everything else quiet. |

## The page recipe (recipes/pdp.json)
Below the first screen (the theme's gallery and buy box): trust strip, why this product (4 or 6 reasons), the numbers (or a dark proof panel), one photo-led story,
how to use it, what is in the box, what is NOT in it, an approved comparison, REAL reviews, last questions. Categories reorder it (beauty leads with the story, supplements
with proof, home-care puts "what is not inside" after the steps). The buy box: rating above the title (only a real one), title, live price with the real compare-at and a
worked-out badge, bullets, option picker and add-ons only with real products, the buy buttons, then reviews directly under them.

## Never invented
A section whose facts are missing is OMITTED with a reason (for example "needs at least 3 REAL reviews"). Every text has an origin: `fact` (with its source), `structure`
(a signpost template), `copy` (a validated model rewrite of a signpost) or `demo` (allowed only when `demo: true`, always listed for replacement). Numbers in structural text must exist in
the facts. A comparison with other products needs the owner's approval flag.

## Lint rules (rules.py)
L01 contrast 4.5:1 | L02 side space at least 12 px | L03 padding within 56 px, neighbours within 80 | L04 neighbours never share a background | L05 at most 2 dark bands |
L06 reviews directly under the buy buttons | L07 every text has an origin | L08 numbers traceable | L09 demo gating | L10 accent budget | L11 monotony (warning) | L12 the live price block
replaces the theme's price line. The first run of the tests caught a real mistake in this document's own defaults (premium neighbours added up to 88 px): rules are checked, not decorative.

## Not built yet
(Built 9 Oct 2026: the Claude API call `copy_step.py`, the screenshot review loop `review.py`, the end-to-end command `run_page.py`; first LIVE API
call still waits for Harsh's yes and a key.) Still to do: measuring SVG icon contrast in the review loop, an optional Claude vision critique of the
screenshots (advisory only),
the push of the template to an unpublished theme (Tier 2, a person approves), a home-page recipe, a per-client app registry (uuids differ per duplicated app), theme-level
settings (fonts and palette in `config/settings_data.json` already have code in `provision/style.py`), and real client pilots. Fonts: blocks use theme heading font or a generic
sans/serif; a brand's exact typeface comes through the theme's font setting, not through our blocks.
