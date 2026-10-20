# Sullen (fashion): home page study, 19 Oct 2026
Source: https://www.sullenclothing.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 66 ("all dark: niche, not transferable"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 9 / 9 |
| Page length px (desktop / phone) | 4567 / 6292 |
| Pad median, p25-p75 (desktop / phone) | 52, 34-77 (min 16, max 177, n 14) / 38, 27-62 (min 12, max 152, n 14) |
| H1 / hero heading px | H1 28 desktop, 28 phone / hero heading not measured (null) |
| Section headings px (median, min-max; desktop / phone) | 30, 20-48 (n 5) / 30, 20-30 (n 5) |
| Button (radius, colour) | 4px, rgb(0, 0, 0) (#000000) |
| Body font | Oswald |
| Colour share between header and footer | ground 0.0 (white 0.0 + offwhite 0.0), tint 0.0, solid 0.0, dark 0.68, picture 0.32 |
| Colour bands of 150 px or more, in order | picture 510, dark #0D0D0D 961, picture 164, dark #000000 265, dark #0D0D0D 1230, picture 415 |

Other measured values: 5 colour changes, 0 gradient bands, longest white run 0 px, longest off-white run 0 px; bands of 150 px or more: white 0, offwhite 0, tint 0, solid 0, dark 3, picture 3.

One reader error: "dark #000000 265" is not its own band. It is the black middle of the featured-collection background photo (section 4), whose edges go flat black; that photo is the run picture 164 + dark 265 + picture 118 in all_bands (1841 to 2388). So the page really has two near-black runs (#0D0D0D 961 and 1230) split by three photo sections.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Full-width photo carousel: small spaced eyebrow, a large uppercase headline at lower left, one outline button, dots at the lower right | photo | 338 / 48 (full-width photo, left out of the median) |
| 2 | categories | "Explore our collections": six photo tiles with the category name at the foot, arrows beside the heading | dark #0D0D0D | 48 / 58 |
| 3 | best-sellers | Product row behind five tabs (new, best sellers, product types; the active tab is a filled amber chip), name, "from" price and stars per card, one filled "view all" button under it | dark #0D0D0D | 38 / 20 |
| 4 | best-sellers | A seasonal featured collection: eyebrow, the largest heading on the page, four product cards, one filled button, all on a dark artwork photo | photo | 39 / 20 |
| 5 | categories | Six round pictures with names, one per design series | dark #0D0D0D | 177 / 56 |
| 6 | social | "The Community": heading, an invite to tag the brand, a follow link and a row of six square customer and team photos | dark #0D0D0D | 16 / 119 |
| 7 | reviews | Star rating and review count above the heading, then a carousel of short quotes with five stars and a first name, cards cut off at both sides | dark #0D0D0D | 47 / 69 |
| 8 | guarantee | Three service promises in a row, each an amber line icon, a short title and one line | dark #0D0D0D | 100 / 56 |
| 9 | newsletter | Centred heading, one offer line, email field with a light button, optional phone field and the legal line, over a dim studio photo | photo | 114 / 114 (full-width photo, left out of the median) |

`order: hero, categories, best-sellers, best-sellers, categories, social, reviews, guarantee, newsletter`

- The large pads are pictures, not empty space: 177 above section 5 holds the round pictures over their names, 100 above section 8 the icons over the titles, 119 under section 6 the photo row under its text.
- The H1 of 28 px is not the hero headline: the headline on the photo is much larger (its size is not measured, hero heading is null).
- Sections that share the dark ground are split by thin grey hairlines, not by colour; the reader cannot see these lines (they are under 40 px).

## Colour pacing
- One near-black ground (#0D0D0D) from the header to the footer, dark 0.68 of the page; photos take the other 0.32. No white, off-white, tint or solid band at all.
- The only rhythm comes from three photo sections: the hero (1st of 9), the featured collection (4th of 9) and the sign-up (9th of 9). Between them sit two and then four dark sections in a row.
- One amber accent does every small job: filled buttons, the active tab, review stars, the promise icons, eyebrow labels and the tag handle. Everything else is white or grey text on black.
- The announcement bar is the only light strip (tint #EFECE7, inside the cut-off header area).

## Type, buttons and spacing
- Headings are a condensed uppercase face with wide letter spacing (Oswald is also the measured body font); review quotes and small print use a plain sans. Heading sizes jump: 20 px (collections, community), 30 px (reviews, sign-up) and 48 px (the featured collection), median 30, weight 400 for all five (desktop-metrics.json). Some headings set the first word brighter than the rest.
- The measured button is black with 4px corners. On screen the actions are amber filled rectangles with an arrow, a white outline button on the hero and a light grey button in the sign-up, all with small square corners.
- Spacing: pad median 52 px desktop (p25 34, p75 77), between the cramped and the airy pages in ratings.md. Product sections are tight at the bottom (20 px under the cards before the next hairline).

## Proof
- #3 and #4: a star rating with a decimal score under every product card (no review count).
- #6 social: real customer and team photos with an invite to tag the brand, so shoppers see people wearing the products.
- #7 reviews: a total review count and average rating above the heading, then short quotes with first names in a carousel.
- #8 guarantee: three service promises (returns, support, quality) just before the sign-up.
- No press, no numbers section, no founder story.

## Phone
- Same 9 sections in the same order; the page grows from 4567 to 6292 px.
- The hero shows another slide, with the headline centred and the outline button under it.
- Collection tiles and the product row become swipe rows (two tiles and the edge of a third; one product card and part of the next). Only two product tabs show, the rest scroll sideways.
- The featured collection becomes a 2 x 2 product grid, the round series pictures a 3 x 2 grid, the community photos a three-column grid; the reviews stay a carousel with one card and the edges of its neighbours; the three promises stack.
- Section headings median 30 px, min 20, max 30: the 48 px heading drops to 30. Pad median 38 (p25 27, p75 62, min 12, max 152, n 14).
- Floating accessibility and chat buttons sit over the right edge of the content.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- One accent colour reserved for actions and ratings: every filled button, the active tab and the stars; nothing decorative in it.
- Put the overall rating and the total review count directly above the review heading, then short quotes with first names (only the client's real reviews).
- A row of three service promises (icon, short title, one line) just before the sign-up section.
- A product row with tabs (new, best sellers, by type) directly after the categories, with one "view all" button under it.
- Where two neighbouring sections share a ground, a thin hairline between them instead of a colour change.

Avoid:
- An all-dark page (dark 0.68, no white): home care needs a light, clean ground.
- Three heading sizes on one page (20, 30, 48 px); keep one size for every section heading.
- Grey small text on near-black (review quotes, sign-up legal line): hard to read on a phone in daylight.
- Floating chat or accessibility buttons that cover product cards on the phone.
