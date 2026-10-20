# Cooking Guild (home): home page study, 19 Oct 2026
Source: https://thecookingguild.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 80 ("dark premium, sale hero, risk-free guarantee band"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 6 / 6 |
| Page length px (desktop / phone) | 5579 / 7735 |
| Pad median, p25-p75 (desktop / phone) | 56, 32-101 (min 22, max 176, n 10) / 57, 24-97 (min 24, max 148, n 6) |
| H1 / hero heading px | H1 84 desktop, 33 phone / hero heading 84 desktop, 33 phone |
| Section headings px (median, min-max; desktop / phone) | 24, 24-32 / 22, 22-24 |
| Button (radius, colour) | 8px, rgb(2, 6, 23) |
| Body font | Montserrat |
| Colour share between header and footer | ground 0.38 (white 0.38 + offwhite 0.0), tint 0.0, solid 0.0, dark 0.62, picture 0.01 |
| Colour bands of 150 px or more, in order | dark #010000 831, white #FFFFFF 507, dark #000000 1618, white #FFFFFF 1388, dark #0E0E0E 873 |

Other measured values: 4 colour changes, 1 gradient bands, longest white run 1388 px, longest off-white run 0 px; bands of 150 px or more: white 2, offwhite 0, tint 0, solid 0, dark 3, picture 0.
Corrected 19 Oct 2026 after the reader fixes: the desktop list started with the nav bar (28 / 29 px), now left out; the desktop pad median is 56, as in ratings.md.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Dark photo of a knife in an open gift box; on the left a small sale label, a spaced uppercase discount line, a very large uppercase headline in white and gold, a paragraph, a gold pill and a white outline pill, two tick lines (trial, guarantee) | dark photo | 80 / 80 (full-width photo, left out of the median) |
| 2 | other | Ticker strip of trust lines with small icons: guarantee, steel, a units-sold count, hand finishing | black | not measured (strip not in the spacing file; 41 px tall in desktop-metrics.json) |
| 3 | offer | Sale product row: uppercase heading with the discount, one line, a view-all link; five cards with top tags, a "save" tag, a small uppercase spec line, name, strike and sale price, a black add-to-cart button; arrows, counter and progress bar | white | 32 / 84 |
| 4 | categories | Knife series: six tiles on black, each a hanging knife photo with a grey name bar and item count | black | 32 / 32 |
| 5 | guarantee | Centred logo, two-line uppercase heading with the second line in dark green, one paragraph, a dark green button, a small reassurance line | black | 176 / 80 |
| 6 | ugc | Unboxing videos: uppercase heading, a subline with the units-sold count, five vertical clips with play buttons, each with a product card (strike and sale price, one with stars and count) | white | 32 / 101 |
| 7 | faq | Large warranty badge graphic on the left, heading and a four-question accordion on the right, the first one open | white | 102 / 22 |

`order: hero, other, offer, categories, guarantee, ugc, faq`

- Section 2 mixes guarantee, material and a sales count, so it is "other" (a trust ticker), not one proof type.
- Measured data vs the picture: the desktop spacing list starts with the navigation bar (28 / 29). The first reading's desktop pad median of 32 included the nav bar (now left out: 56), numbers.json takes the nav bar as the hero (hero heading "not measured"), and the hero's 84 px is counted among the section headings (max 84). The real section headings in desktop-spacing.json are 24 and 32 px. ratings.md lists this page at 56 / 57, which the corrected reading matches.
- The last dark band (#0E0E0E, 873, the one "gradient" band) is the footer (newsletter, links, payment icons): the reader left out only a 53 px strip at the very bottom. So dark 0.62 and the 3 dark bands include the footer.
- The hero photo is dark at both edges and reads as a flat dark band (#010000, 831, which also takes in the ticker), not as picture; that is why picture is only 0.01.
- The series grid and the guarantee band share one black and merge into "dark #000000 1618"; the video row and the FAQ merge into "white 1388".

## Colour pacing
- Bands of 150 px or more: 2 white, 3 dark (one of them the footer). Big blocks alternate: dark hero, white sale row, black series plus guarantee, white videos plus FAQ, dark footer. 4 colour changes.
- Accents: a gold gradient on the hero's main button and half of its headline, dark olive green on the guarantee line and its button, blue for sale prices and the open FAQ question.
- The strongest moment is the guarantee band, 5th of 7, on black right after the series grid, given the most space on the page (176 above).

## Type, buttons and spacing
- Montserrat throughout. The hero headline is 84 px, uppercase, weight 700, two-tone. Section headings are uppercase at weight 400 and only 24-32 px, a very big step down from the hero. Small spaced uppercase labels sit over the hero headline.
- Buttons: the measured one is the black add-to-cart (#020617, 8px corners) on every product card; the hero has a gold gradient pill and a white outline pill; the guarantee band has a dark green rounded button.
- Spacing is compact: desktop pad median 56 (p25 32, p75 101). Sale row 32 / 84, series 32 / 32, videos 32 / 101; only the guarantee (176 / 80) and the FAQ top (102) get more room.

## Proof
- #1 hero: two tick lines (home trial, lifetime guarantee) right under the buttons.
- #2 other: the ticker repeats guarantee, material and a units-sold count.
- #3 offer: strike price and a save tag on every card; no stars on these cards.
- #5 guarantee: a whole band on the trial and the guarantee, with a shop button.
- #6 ugc: customer unboxing clips, each linked to its product and price; the subline repeats the units-sold count.
- #7 faq: buying questions (delivery, returns, guarantee, material) beside a warranty badge.
- The guarantee shows up in the hero, the ticker, its own band and the FAQ, and the sales count twice: strong, but repetitive.

## Phone
- Same order with 6 measured sections (no nav bar in this list). The page is 7735 px against 5579 on desktop, mostly because the five unboxing clips stack one under another (that section is 3426 px on the phone, phone-metrics.json).
- The announcement bar switches to the guarantee message. Hero: labels and headline above the photo, then the paragraph, two full-width pill buttons and the tick lines on black.
- The sale row becomes a swipe row with the third card cut; the series grid shows one tile at a time with a counter; the guarantee band keeps its layout with a full-width button; the FAQ puts the badge on top of the accordion.
- H1 33; section headings 22-24 (median 22). Pad median 57 (p25 24, p75 97, min 24, max 148, n 6); the FAQ's bottom pad reads -94, a measuring artefact (that section is flagged full-width and left out).

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- One guarantee band, only for a real policy: centred heading, one paragraph, one button and a short reassurance line, placed after the browsing sections and given the most space on the page.
- Two short tick lines under the hero buttons for the client's real trial, returns or delivery promise.
- A sale row only for a real, dated offer: strike price, sale price and a save tag on every card.
- A closing FAQ with four buying questions (delivery, returns, guarantee, what it is made of), the first one open.
- Customer unboxing or usage clips, each linked to its product and price.

Avoid:
- Black as the main ground (dark 0.62 here, footer included): keep a light ground and at most one dark band.
- Gold accents and gold buttons: they read yellow-brown.
- The same guarantee and sales-count message in four places; say it once in the hero and once in its own band.
- Section headings far smaller than the hero (84 against 24-32 px on desktop).
- Stacking every video under the last on the phone (a 3426 px section): use one swipe row.
