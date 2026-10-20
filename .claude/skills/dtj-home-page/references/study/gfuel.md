# G FUEL (supplements): home page study, 19 Oct 2026
Source: https://gfuel.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 72 ("brand-specific purple/orange, loud promotions"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 7 / 7 |
| Page length px (desktop / phone) | 4594 / 6692 |
| Pad median, p25-p75 (desktop / phone) | 42, 18-79 (min 16, max 200, n 10) / 40, 20-91 (min 20, max 289, n 10) |
| H1 / hero heading px | H1 43 desktop, 22 phone / hero heading 43 desktop, 22 phone |
| Section headings px (median, min-max; desktop / phone) | 59, 16-78 / 31, 16-44 |
| Button (radius, colour) | 9999px, rgb(70, 26, 162) |
| Body font | Acumin VF |
| Colour share between header and footer | ground 0.28 (white 0.28 + offwhite 0.0), tint 0.0, solid 0.1, dark 0.12, picture 0.49 |
| Colour bands of 150 px or more, in order | solid #423758 249, picture 248, solid #413954 199, picture 810, white #FFFFFF 671, picture 398, white #FFFFFF 156, picture 368, dark #170634 310, picture 235, dark #0C0024 219, white #FFFFFF 377 |

Other measured values: 11 colour changes, 1 gradient bands, longest white run 671 px, longest off-white run 0 px; bands of 150 px or more: white 3, offwhite 0, tint 0, solid 2, dark 2, picture 5.
Corrected 19 Oct 2026 after the reader fixes: the capture's blank right side (1440-1800 px) is no longer read: the colour figures changed. Figures in the text below that differ from this table are the earlier reading.

The colour numbers for this page are wrong: the saved desktop.png is 1800 x 5743 px, but the page fills only its left 1440 px; every row from 1440 px to the right edge is blank white (checked on the file), and the picture runs on in white below the footer. The reader's right-edge sample therefore always reads white, so the dark purple hero, BOGO row and last-call block come out as "white 776", "solid" or "picture". Band heights are in that file's pixels. Use the screenshots, not the share, for this brand.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Slide 1 of 3: sale chip with event name, two-line offer heading, one line, two buttons, sale end line, large promo artwork on the right, slider dots, small legal line | photo (dark purple artwork) | 232 / 14 (full-width picture) |
| 2 | offer | BOGO product row after a scrolling promo strip: label with end date, heading, button and text link, an "add 2 tubs" progress bar, five product cards with a sale tag, "new formula" badge, price and a full-width orange add button, fine print | dark purple | 51 / 45 |
| 3 | categories | One tall tile for the main range and two wide tiles for the others, each with a 2-3 word sub-line and an arrow; one stars-and-review-count line under them | white | 143 / 32 (tile labels sit low in tall tiles) |
| 4 | best-sellers | "New formula" product row with arrows and a see-all link: purple cards, "new" tags, white name-and-price pill with a round add button | white | 38 / 58 |
| 5 | other | Limited editions: one large tile plus a 2x2 grid of collector-box tiles, each with a small label, name and "view" link, one "sold out" tag | white | 16 / 16 |
| 6 | offer | Last call: event logo, heading, countdown timer, button, fine print, four product picks with a "+1 free" tag; a four-icon benefit strip runs along its foot | dark purple | 200 / 18 |

`order: hero, offer, categories, best-sellers, other, offer`

- Measured section 2 (777 px, pad 232 / 11) is the hidden second hero slide; it is left out of the table, which is why the measured section heights add up to more than the page.
- The scrolling promo strip between the hero and the BOGO row is not a measured section. The benefit strip is inside section 6, not its own section.

## Colour pacing
- Read from the screenshots (the measured share is not usable here): three dark purple promo areas (hero, BOGO row, last call, 1st, 2nd and 6th of 6) and three white browsing sections in the middle. The two dark areas at the top run back to back, joined by the promo strip.
- On the white sections the colour sits in cards: purple product cards, a dark tile, a pale blue tile, one hot-pink card. Orange is the sale colour (sale chips, BOGO buttons, add buttons, "+1 free" tags); the measured button colour is purple.
- The page is loud from start to finish: purple, orange, lime and pink appear together on the first screen.

## Type, buttons and spacing
- Headings use a heavy all-caps display face; the measured weight is 400 for all of them (desktop-metrics.json), the face itself is heavy. Sizes jump: hero 43 px, tile label 63, product row 58, limited editions 60, last call 78 (median 59, p25 36, p75 67). The H1 is smaller than four later headings.
- Buttons are pills (9999px): purple measured; on screen orange solid with a dark outline (sale buttons), orange solid on every product card, round purple "+" add buttons, white pills on dark tiles.
- Spacing is tight: pad median 42 (p25 18, p75 79); the limited-editions grid has 16 / 16. The large values (232, 200, 143) are text sitting low in a tall picture or tile, not white space.

## Proof
- #3: one line with stars and a review count under the category tiles; it is the only review proof on the page body.
- No reviews section, press, story, how-it-works, FAQ or guarantee. Trust badges (accessibility, a shop rating, an accredited-business badge) appear only in the footer.
- #6: a four-icon benefit strip (energy, antioxidants, zero sugar, free tub) closes the last section.
- The one sale is repeated five times: announcement bar, hero, promo strip, BOGO row and last call, with a countdown timer.

## Phone
- Same order; 7 measured sections. Page 6692 px against 4594 on desktop: the cards stack.
- In the phone capture an open cart panel (empty cart, four category shortcuts, two upsell products, a "shop all" button) sits over the lower hero and the top of the BOGO row, and a grey overlay dims the hero. The capture does not show whether it opens on its own for shoppers.
- Hero text stacks above the promo artwork. Category tiles: the main tile full width, the two others side by side. Both product rows swipe with the next card cut off. Limited editions: one large tile, then a 2x2 grid. Last call: picks in a 2x2 grid, benefits as a stacked list.
- H1 22 px; section headings 31 px (min 16, max 44). Pad median 40 (p25 20, p75 91, n 10).

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- When a sale is running: one offer block with a real end date near the top and at most one reminder near the end (here positions 2 and 6 of 6), not in every section.
- Category tiles right after the first product block: one large tile for the main range, smaller tiles for the rest, each with a 2-3 word sub-line.
- An add button on every product card, so a shopper can buy from the home page without opening the product page.
- A four-icon benefit strip just above the footer, one short phrase per icon.
- Keep the page short: 6 visible sections and 4594 px on desktop is enough for a store with few ranges.

Avoid:
- This spacing: pad median 42 px on desktop and 16 / 16 on a tile grid reads cramped; ratings.md puts the clean, high-scoring pages at 84-112.
- One sale in five places plus a countdown timer; a timer only with a real, approved end date.
- Heading sizes that jump from section to section (43 to 78 px here) and an H1 smaller than later headings.
- Any panel or overlay over the first phone screen.
- Review proof reduced to one line: the only body proof here is a stars-and-count line; trust badges hidden in the footer.
