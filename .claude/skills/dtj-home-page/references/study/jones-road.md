# Jones Road (beauty): home page study, 19 Oct 2026
Source: https://www.jonesroadbeauty.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 83 ("refined serif, black/cream; one weak orphan-image section"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 8 / 7 |
| Page length px (desktop / phone) | 4546 / 4665 |
| Pad median, p25-p75 (desktop / phone) | 52, 18-111 (min 0, max 326, n 10) / 34, 18-100 (min 0, max 359, n 10) |
| H1 / hero heading px | H1 32 desktop, 30 phone / hero heading 42 desktop, 28 phone |
| Section headings px (median, min-max; desktop / phone) | 16, 16-48 / 16, 13-28 |
| Button (radius, colour) | 2px, rgb(0, 0, 0) (#000000) |
| Body font | RingsideWideWeb |
| Colour share between header and footer | ground 0.62 (white 0.42 + offwhite 0.2), tint 0.27, solid 0.0, dark 0.07, picture 0.04 |
| Colour bands of 150 px or more, in order | tint #EFEFEF 530, white 644, dark #000000 274, white 575, offwhite #F5F2EC 298, tint #EBEBEB 336, tint #E5E5E5 200, offwhite #F8F8F8 493, white 452 |

Other measured values: 8 colour changes, 0 gradient bands, longest white run 644 px, longest off-white run 493 px; bands of 150 px or more: white 3, offwhite 2, tint 3, solid 0, dark 1, picture 0.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Wide product photo on a pale grey backdrop; serif headline, one support line and one black button on the left, a signature under it | photo | 200 / 200 (full-width photo, left out of the median) |
| 2 | best-sellers | Product row with tabs (bestsellers, new, kits, face, eyes, lips) under a large serif heading; pink "bestseller" labels, award seals on two photos, the price sits inside the black buy button | white | 0 / 20 |
| 3 | press | One centred brand line in white serif, then a sliding row of magazine logos with a progress line | dark #000000 | not measured |
| 4 | categories | Small bold uppercase label, then a swipe row of square collection photos with a grey name strip under each and arrows at the sides | white | 36 / 263 |
| 5 | story | Founder quote: three centred serif lines and the founder's name and title, nothing else | off-white #F5F2EC | 60 / 60 |
| 6 | bundle | Second full-width photo banner with headline, line and black button, pushing one product of the same kit as the hero | photo | 72 / 234 (full-width photo) |
| 7 | benefits | Value cards in a slider; on desktop only one shows: a small product cut-out, a label, one line and a text link | off-white #F8F8F8 | 326 / 60 |
| 8 | editorial | "Get the look" row of four model portraits, each with the look's name and a white button | white | 43 / 10 |

`order: hero, best-sellers, press, categories, story, bundle, benefits, editorial`

- Measured data vs the picture: the hero and the section 6 banner are photos, but their backdrop at the page edges is a flat light grey, so the reader classed them as tint (#EFEFEF 530; #EBEBEB 336 + #E5E5E5 200). Picture 0.04 undercounts the photos, and most of tint 0.27 is photo backdrop. The real colour fills are only the black press band, the cream quote and the light-grey value band.
- Section 2's top pad of 0 is not a real gap of 0: the white space above its heading belongs to the hero's box. The press band has no measured text gap because the reader found no text items in it.
- The large pads (263 under the collection label, 326 above the value text, 234 in the banner) are photo rows and the product cut-out, not empty space.
- The newsletter sign-up sits in the cream footer (#F6F2EB, left out), not as a section.

## Colour pacing
- Bands of 150 px or more: 3 white, 2 off-white, 3 tint, 1 dark, 0 picture. The page is neutral only: white, a warm cream (#F5F2EC) for the quote, light greys, and black for the press band, the buttons and the announcement bar. The only hue is a small pink on the "bestseller" labels and the active tab line.
- The one strong band is the black press bar, 3rd of 8, right after the product row, so the loudest fill carries media proof high on the page.
- No two neighbouring sections share a fill (grey photo, white, black, white, cream, grey photo, light grey, white). White to cream and white to light grey are soft steps with no dividers.
- Cards add no colour: product tiles are pale grey squares, collection tiles have grey name strips.

## Type, buttons and spacing
- Two heading roles: a light serif (weight 300) at 38-48 px for the hero (42), the product-row heading (48) and the banner (38); and a 16 px bold uppercase sans label (weight 700) for the browse rows (collections, values, looks). That split is why the section heading median is 16. H1 32 px is not the hero headline (the files do not say which element it is).
- Buttons: 2px corners, solid black with white letters in a typewriter-style face; product buttons are split, "shop now" plus the price in its own cell; white buttons sit on the portrait photos. Secondary actions are underlined text links.
- Spacing is tight: desktop pad median 52 (p25 18, p75 111). The only text-only section (the quote) uses 60 / 60; browse rows sit at 0-43 at the top and 10-20 at the bottom.

## Proof
- #1 hero: the support line is a sales claim (sold-out history), not a figure in a proof block.
- #2 best-sellers: pink "bestseller" labels on three cards and award seals printed on two product photos; on the phone each card also shows a star rating and review count (not seen in the desktop capture).
- #3 press: magazine logos on the black band, directly under the products.
- #5 story: the founder's own quote with name and title, centred on cream.
- No reviews section, no numbers strip, no customer photos, no guarantee and no FAQ.

## Phone
- Same order. The desktop press bar is replaced by a 74 px logo-only strip on black (no brand line, partly different logos); it holds no text, so the phone counts 7 sections.
- Hero: photo on top, then a white card overlapping the photo's foot with the headline (H1 30 px, hero heading 28), line and button.
- Product row, collections, value cards and looks all become swipe rows with the next card cut off at the edge; the tabs scroll sideways. The value cards now read as a row (two visible), so the desktop gap goes away.
- The banner (section 6) puts its text above the photo on the grey backdrop.
- Section headings 16 px median (min 13, max 28). Pad median 34 (p25 18, p75 100, min 0, max 359, n 10); the quote uses 40 / 40, the browse rows 0-28 at the top and 10-20 at the bottom.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- Put a tabbed product row directly under the hero (best sellers, new, kits, one tab per room or category) with the price inside the buy button, so the first scroll is shopping.
- Exactly one strong band, short (here 274 px, 3rd of 8), for press or certification logos; for us solid brand blue instead of black.
- A text-only founder or brand quote as its own section on an off-white band with a blue cast, centred, 60 px top and bottom on desktop and 40 on the phone.
- Two heading roles only: one large display size (38-48 px desktop, 26-28 phone) for hero and main sections, one small 16 px bold uppercase label for browse rows.
- Keep it short when almost every section sells: here 8 sections and 4546 px on desktop.

Avoid:
- A slider that shows a single card on desktop: here one small picture and one line sit in a 493 px band (the orphan section Harsh marked).
- A second full-width banner that repeats the hero's product (section 6 repeats the hero's kit).
- Proof that only one screen size sees: ratings show on the phone cards but not in the desktop capture.
- Text gaps of 10-20 px at a section's edge (product row bottom 20, looks bottom 10); they look cramped next to 60 px sections.
- Award seals, sold-out lines or media logos the client cannot prove.
