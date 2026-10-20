# Grove (home care): home page study, 19 Oct 2026
Source: https://www.grove.co/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 70 ("marketplace density, cramped"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 10 / 10 |
| Page length px (desktop / phone) | 8057 / 7443 |
| Pad median, p25-p75 (desktop / phone) | 32, 0-70 (min 0, max 120, n 18) / 15, 0-24 (min 0, max 41, n 16) |
| H1 / hero heading px | H1 not measured (desktop and phone) / hero heading 40 desktop, 24 phone |
| Section headings px (median, min-max; desktop / phone) | 32, 12-40 (n 9) / 20, 10-24 (n 9) |
| Button (radius, colour) | not measured |
| Body font | Value Sans Pro (phone-metrics.json names ABC Diatype on the phone) |
| Colour share between header and footer | ground 0.55 (white 0.48 + offwhite 0.07), tint 0.0, solid 0.39, dark 0.0, picture 0.06 |
| Colour bands of 150 px or more, in order | picture 381, white 658, offwhite #F5F2EC 515, white 1017, white 174, solid #203C4E 1004, white 1016, white 175, solid #203C4E 912, white 632, solid #033B4C 1096 |

Other measured values: 8 colour changes, 0 gradient bands, longest white run 1017 px, longest off-white run 515 px; bands of 150 px or more: white 6, offwhite 1, tint 0, solid 3, dark 0, picture 1.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Carousel of wide kitchen photos with a left-aligned headline, two lines and an outline pill button; slide dashes and a pause control | photo | 0 / 0 (full-width photo, left out of the median) |
| 2 | categories | Shop-by grid with five text tabs (room, routine, category, family member, own brand) and four photo tiles with white labels | white | 0 / 16 |
| 3 | other | Expert panel: small uppercase label, heading, one line, then four cards with a grey photo, role, name and credentials, in a swipe row | off-white #F5F2EC | 48 / 64 |
| 4 | categories | Second shop-by grid with three tabs (health goal, exposure, wellness) and four photo tiles | white | 0 / 16 |
| 5 | best-sellers | Personal product row with three tabs (routine, subscribe, recently viewed); five cards with heart, brand, name and price | white | 0 / 32 |
| 6 | editorial | Shopping guide: heading on the left, a numbered accordion (01-04) on the right, the open item showing a photo, label, title, two lines and a shop link | solid navy #203C4E | 64 / 89 |
| 7 | categories | Shop by brand: eight photo tiles in two rows, brand name on each | white | 0 / 16 |
| 8 | best-sellers | Product row with four tabs (featured, bestsellers, top rated, new); badges, strike price and a save figure on some cards | white | 0 / 32 |
| 9 | editorial | Second numbered accordion guide (01-03), same layout | solid navy #203C4E | 64 / 89 |
| 10 | other | Closing collection card: product photo on the left, label, heading, one line and an outline pill button on a cream panel | white (cream panel inside) | 120 / 120 |

`order: hero, categories, other, categories, best-sellers, editorial, categories, best-sellers, editorial, other`

- Section 3 is an expert panel; the vocabulary has no word for it, so it is "other". Section 10 promotes one collection and closes the page.
- Measured data vs the picture: the last solid band (#033B4C, 1096) is the footer (newsletter and link columns), not content. The reader left out only the 245 px legal strip at the very bottom as the footer, so solid 0.39 and the 3 solid bands include it; the content has two navy bands (sections 6 and 9).
- "white 1017, white 174" and "white 1016, white 175" are one white stretch each: a carousel arrow touching the page edge cuts a 46 px "picture" strip into the product rows.
- Most sections measure 0 above the heading because the heading sits at the very top of its box; the visible gap between sections lies outside the boxes and is not measured. The page still looks tight.
- The hero is a carousel: the screenshot shows one slide, the measured hero heading comes from another slide.

## Colour pacing
- Bands of 150 px or more: 6 white, 1 off-white, 3 solid (one of them the footer), 1 picture. Colours: white ground, a warm off-white #F5F2EC (expert panel, closing panel), a deep navy #203C4E for the two guides, a darker teal-navy #033B4C in the header bar and footer.
- The only strong colour is the two navy guide bands, 6th and 9th of 10, each with white product sections on both sides. They carry shopping guides, not proof.
- Most colour lives in the photo tiles of the three shop-by grids, not in bands. With white between every tile grid and product row, the page reads like a marketplace listing.

## Type, buttons and spacing
- One sans for everything, weight 500, sentence case; section headings 32-40 px on desktop (the 12 px minimum is the small uppercase label over the expert panel, read as a heading). Hero heading 40.
- Buttons: outline pills with a dark outline and dark text (hero, closing panel); underlined text links inside the guides; a small green rewards button in the header. No solid main button in the page body (the button reader found none).
- Spacing: tile grids 0 / 16, product rows 0 / 32, guides 64 / 89, closing panel 120 / 120. Desktop pad median 32 (p25 0, p75 70): the lowest of the four home-care rows in ratings.md.

## Proof
- #1 hero: the visible slide states the brand's ingredient screening standard as the headline (a claim, not shown proof).
- #3 other: four named experts with roles and credentials, third on the page, as proof for that standard.
- #5 and #8 best-sellers: "new", "limited edition" and "running low" badges, a strike price with a save figure; no stars or review counts on any card.
- There is no reviews, press, numbers or guarantee section on the home page; certification badges appear only in the footer.

## Phone
- Same 10 sections in the same order; page 7443 px against 8057 on desktop.
- Hero: the photo on top, then the headline, two lines and the outline pill on the photo's pale wall, slide dashes under them.
- Tile grids become 2 x 2 (the brand grid 2 x 4); the tab rows scroll sideways with the last tab cut; expert cards and product rows become swipe rows with the next card cut at the edge.
- The guides stack the heading over the accordion; the closing panel puts the photo on top.
- Section headings 20 px (min 10, max 24), hero 24. Pad median 15 (p25 0, p75 24, min 0, max 41, n 16): very tight.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- Shop-by tiles with tabs (by room, by need, by concern): one heading, four photo tiles per tab, the label on the tile.
- An expert panel high on the page only with real people who work with the client: photo, role, name, one credential line.
- A numbered shopping guide (01-04 accordion with a photo and a shop link per item) works on one solid band; use at most two solid bands and keep at least two sections between them (here 6th and 9th of 10).
- Tabs on a product row (featured, bestsellers, new) so one row serves several lists.

Avoid:
- Headings glued to the section top (pad median 32 desktop, 15 phone): give every section real top and bottom space.
- Three tile grids and two product rows on one page with no customer proof between them.
- A home page with no reviews or ratings at all, even on product cards.
- A hero carousel: most visitors see one slide only.
- Outline-only buttons: keep one solid main button.
