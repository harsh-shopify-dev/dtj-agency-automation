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
The Claude API call (the contract and prompt exist), a screenshot review loop (render on phone and desktop, check against the rules a model cannot be trusted with),
the push of the template to an unpublished theme (Tier 2, a person approves), a home-page recipe, a per-client app registry (uuids differ per duplicated app), theme-level
settings (fonts and palette in `config/settings_data.json` already have code in `provision/style.py`), and real client pilots. Fonts: blocks use theme heading font or a generic
sans/serif; a brand's exact typeface comes through the theme's font setting, not through our blocks.
