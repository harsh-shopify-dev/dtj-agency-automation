# Boom Beauty (beauty): home page study, 19 Oct 2026
Source: https://boombeauty.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 74 ("cohesive pink, but cramped and price-heavy"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 9 / 9 |
| Page length px (desktop / phone) | 5136 / 5761 |
| Pad median, p25-p75 (desktop / phone) | 38, 24-80 (min 0, max 169, n 12) / 28, 21-58 (min 0, max 78, n 9) |
| H1 / hero heading px | H1 40 desktop, 28 phone / hero heading 64 desktop, 30 phone |
| Section headings px (median, min-max; desktop / phone) | 40, 40-64 / 28, 28-36 |
| Button (radius, colour) | 0px, rgb(219, 78, 116) |
| Body font | Helvetica |
| Colour share between header and footer | ground 0.73 (white 0.57 + offwhite 0.16), tint 0.26, solid 0.0, dark 0.0, picture 0.02 |
| Colour bands of 150 px or more, in order | offwhite #FAF4F0 703, white #FFFFFF 1022, tint #F9E0D7 562, white #FFFFFF 1475, tint #C1C1C0 582 |

Other measured values: 4 colour changes, 0 gradient bands, longest white run 1475 px, longest off-white run 703 px; bands of 150 px or more: white 2, offwhite 1, tint 2, solid 0, dark 0, picture 0.
Corrected 19 Oct 2026 after the reader fixes: a leading nav bar is no longer counted as a section.

Reader errors: the 1022 px "white" band holds a cream texture photo behind the quiz banner (about 375 px); the "tint #C1C1C0 582" band is the flat grey backdrop of a video/photo, not a CSS colour band.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | categories | A row of small round product icons with labels right under the menu, for one-tap browsing (sits in the header group, above the hero) | white | 78 / 10 (first row of pad_by_section_desktop, no heading; matched by position) |
| 2 | hero | Split screen: headline, one line for whom it is, outlined button on the left, lifestyle photo on the right | off-white #FAF4F0 panel + photo | 232 / 88 (photo section, left out of the median) |
| 3 | best-sellers | Four product cards with badges, stars, review counts, prices and a button each | white | 20 / 24 |
| 4 | other | Quiz invitation: short question, one line, one pink button, to route unsure shoppers | photo (cream fabric texture; the reader counted it as white) | 81 / 75 |
| 5 | categories | Four large category cards (photo, name, one line, a filled button each) | tint #F9E0D7 | 54 / 36 (no heading in the row; matched by position) |
| 6 | other | One-product spotlight (back-in-stock product): small eyebrow, heading, two lines, button; the picture half did not load on the desktop capture | white, with a light grey card | 168 / 169 |
| 7 | benefits | Four line icons with a short title and one line each | white | 0 / 36 |
| 8 | reviews | A review count as the heading, a row of product thumbnails to pick from, stars and one quote | white | 40 / 26 |
| 9 | story | Closing brand message: brand name, short mission lines and a button over a video | photo (grey video backdrop, read as tint #C1C1C0) | 118 / 150 (photo section, left out of the median) |

`order: categories, hero, best-sellers, other, categories, other, benefits, reviews, story`

## Colour pacing
- Bands: off-white hero, then white, one blush tint band (the category cards, #F9E0D7, 562 px), a long white run (1475 px: spotlight, benefits, reviews), and a grey video band. No solid and no dark band.
- There is no strong colour band at all. The strong colour is the pink of the buttons (rgb(219, 78, 116)); it repeats on the quiz button, the four category buttons and the spotlight button. The footer reuses the blush tint of the category band.
- Neighbours often share white: best sellers, the spotlight, benefits and reviews all sit on white. The page separates them only by spacing, plus the spotlight's own grey card. The quiz banner is separated from the best sellers by its texture photo, not a flat colour.
- Colour is carried mostly by product photos and buttons, one tint band, and photo bands (hero right half, quiz texture, closing video).

## Type, buttons and spacing
- Headings are a classic serif at weight 400 (desktop-metrics.json); body text is Helvetica. Most section headings are 40 px desktop; the hero heading is 64 and the closing brand line 60 (desktop-spacing.json). The hero headline is left-aligned; section headings are centred.
- Buttons mix three shapes: square pink filled (0px, the measured button), square black outline in the hero, and black pill buttons on the product cards (seen, radius of those not measured). Labels are upper case and letter-spaced.
- Spacing is uneven: the product row is tight (20 / 24), the benefits heading touches the section top (0 / 36), reviews 40 / 26, while the spotlight gets 168 / 169. The page median is 38, in the cramped group of the study (best pages 84-112).
- The quiz banner (81 / 75) and the category band (54 / 36) sit in between.

## Proof
- Stars and review counts on every product card in section 3 (best sellers), plus small claim badges on the product photos.
- Section 8 of 9 is the reviews block: the total review count is the heading, then stars and a single customer quote with first name and age, switched by product thumbnails.
- No press logos, no stat band, no customer photo wall, no guarantee.

## Phone
- Same order. Page length 5761 px (desktop 5136).
- Hero stacks: the off-white text panel comes first (heading centred), the photo sits below it.
- The icon strip, the best-seller row and the category cards all become sideways swipes (the last card is cut at the right edge to hint at more).
- The spotlight's product picture loads on the phone and sits above the text. Benefits stack one per row, so that section grows from 345 to 980 px.
- The closing section changes from text over a video to a photo above left-aligned text, and its button turns pink filled.
- H1 28, section headings median 28 (28-36). Pad phone median 28, p25-p75 21-58, min 0, max 78 (a leading bar and the reviews quote's impossible -32 left out).

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- Give a multi-product store a one-tap browse row directly under the menu (here a 112 px strip on desktop), before or beside the hero.
- Put stars and the review count on every product card in the first product row.
- Keep the ground (white + off-white) at about 0.73 of the page and allow one soft tint band (here 0.26) for the category cards; the footer may reuse that same tint.
- Reserve one accent colour for buttons only (for us a blue or a green), so every action reads the same.
- Add a short "not sure what you need?" helper right after the first product row (for home care: pick by problem or room), with one button.

Avoid:
- A desktop pad median near 38 px; aim for the 84-112 px range of the top-rated pages.
- Three button shapes on one page (square filled, square outline, pill); pick one shape.
- A long white run (here 1475 px) where three sections differ only by spacing; give one of them a tint or a card.
- Texture photos behind a text band; use a flat tint so the band reads clean.
- Price text that repeats the currency twice on a card; keep prices short.
