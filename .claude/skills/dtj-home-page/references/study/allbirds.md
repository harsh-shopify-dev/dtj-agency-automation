# Allbirds (fashion): home page study, 19 Oct 2026
Source: https://www.allbirds.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 78 ("muted earth tones, short and simple; shipping pop-up"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 5 / 5 |
| Page length px (desktop / phone) | 3662 / 4635 |
| Pad median, p25-p75 (desktop / phone) | 60, 18-196 / 47, 32-96 |
| H1 / hero heading px | 24 / 24 (desktop); 24 / 24 (phone) |
| Section headings px (median, min-max; desktop / phone) | 26, 12-40 / 21, 12-30 (2 headings each) |
| Button (radius, colour) | 3.35544e+07px (pill), rgb(33, 33, 33) |
| Body font | Geograph |
| Colour share between header and footer | ground 0.15 (white 0.15 + offwhite 0.0), tint 0.07, solid 0.12, dark 0.0, picture 0.65 |
| Colour bands of 150 px or more, in order | picture 760, solid #80887E 154, solid #80887E 169, white #FFFFFF 150, white #FFFFFF 152, picture 667 |

The band reader misread this page: the two "solid #80887E" bands are the row of coloured category cards (it read the right-hand card), and the two "white" bands are white product cards. The real page ground is cream #ECE9E2 (in the band data only as strips under 150 px, class tint). There is no full-width colour band on the page.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Lifestyle photo of the newest shoe with a short line and two shop buttons (men, women) | photo | 595 / 64 (full-width photo; text sits low on the photo) |
| 2 | categories | Four tall tiles, one per shopping path (new, men, women, best sellers), each with one product shot | cream #ECE9E2 ground, each card its own muted colour (blue-grey, brown, rose, sage) | 213 / 144 (the label sits mid-tile, so this is not empty space) |
| 3 | best-sellers | Swipeable row of product cards: name, colour, price, swatch, a "new" chip | white cards on cream #ECE9E2 | 0 / 18 (data section has no heading; matched by position) |
| 4 | categories | Three photo tiles for seasonal edits, each with shop buttons | photo tiles on cream #ECE9E2 | 273 / 20 (text is on the photos) |
| 5 | benefits | Three short text cards: comfort, everyday wear, natural materials | white cards on cream #ECE9E2 | 42 / 78 (data section has no heading; matched by position) |

`order: hero, categories, best-sellers, categories, benefits`

A shipping-country pop-up and a floating "shop best sellers" chip cover the first screen on both sizes. The middle seasonal tile's photo had not fully loaded on desktop.

## Colour pacing
- Zero full-width tinted or solid bands. One cream ground (#ECE9E2) runs from the hero to the footer; the only dark areas are the announcement bar and the footer (dark #212121).
- Colour is carried by cards and photos, not bands: four muted category cards (position 2), white product and text cards, and photo tiles. The most colourful spot is the category row right under the hero.
- Every neighbouring section shares the same cream ground. They are told apart by rounded card edges and short cream gutters, never by a line or a colour change. The measured colour changes (3) are card edges, not section changes.

## Type, buttons and spacing
- The hero line is small and light: H1 24 px. Section labels are tiny underlined caps (12 px, "Best Sellers"); the seasonal tiles use a light serif at 40 px on the photo. Text cards use a small monospaced caps label over body text.
- Buttons are pills (radius 3.35544e+07px). The measured button is dark rgb(33, 33, 33); the hero buttons on the photo are light grey pills and the tile buttons are outline pills.
- Spacing: pad median 60 px desktop, p25-p75 18-196. The high values come from text placed in the middle of tiles and photos, not from white space; the cream gutters between sections look narrow (gutter size not measured). Related strips sit tight: the category row starts almost straight under the hero.

## Proof
No press, review, rating or number section anywhere on the page. The only trust content is the materials card in the last section (position 5). Product cards show no star ratings.

## Phone
- Same five sections in the same order.
- The category tiles become a horizontal swipe of tall rounded cards (about one card per screen); the first tile was caught in a hover or animation state (oval shape with extra buttons).
- Best sellers show about 1.2 cards per screen. The three seasonal tiles stack full width, so that section grows from 667 px to 1650 px. The text cards stack.
- Hero heading stays 24 px; section headings median 21 px (12-30). Pad phone median 47, p25-p75 32-96, min 0, max 122.
- The shipping pop-up again covers most of the first screen.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- Put a browse-by-category row at position 2, directly under the hero: 4 tiles across on desktop, a swipe row on phone.
- Product row at position 3 with name, variant and price visible on every card.
- One quiet ground for the whole page and let cards carry the colour: for us white or a very pale blue ground with soft blue and green card tints.
- A short page is acceptable for a small catalogue: 5 sections, 3662 px desktop.
- Pill buttons throughout.

Avoid:
- Any pop-up over the first screen (here a shipping-country modal on both sizes).
- A 24 px hero line: too quiet to say what the store sells (ratings.md: the best pages use an H1 of 48-60 px).
- A page with no proof at all: we need reviews and press or numbers before the footer.
- Muted earthy card colours (brown, rose): outside our blue and green rule.
