# Glossier (beauty): home page study, 19 Oct 2026
Source: https://www.glossier.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture, round 2). Harsh's rating in ratings.md: 68 ("giant sale type, sparse"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 7 / 5 |
| Page length px (desktop / phone) | 4268 / 3914 |
| Pad median, p25-p75 (desktop / phone) | 39, 0-279 (min 0, max 363, n 8) / 29, 0-76 (min 0, max 192, n 6) |
| H1 / hero heading px | H1 not measured / hero heading 20 desktop, 18 phone |
| Section headings px (median, min-max; desktop / phone) | 12, 12-12 / 12, 12-12 |
| Button (radius, colour) | 0px (square), rgb(6, 0, 255) (#0600FF) |
| Body font | Apercu |
| Colour share between header and footer | ground 0.45 (white 0.21 + offwhite 0.24), tint 0.05, solid 0.1, dark 0.0, picture 0.4 |
| Colour bands of 150 px or more, in order | solid #0600FF 355, picture 215, offwhite #F7F7F7 496, white 307, picture 522, picture 361, tint #D4D4D2 183, picture 276, white 377, offwhite #FAF2F4 488 |

Other measured values: 9 colour changes, 0 gradient bands, longest white run 377 px, longest off-white run 496 px; bands of 150 px or more: white 2, offwhite 2, tint 1, solid 1, dark 0, picture 4.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Sale hero: the whole band filled with giant repeated white "sale" lettering and doodles; the actual offer sits in a small white card at the top left (label, offer line, one line, blue button) | solid #0600FF | 100 / 438 (full-width, left out of the median) |
| 2 | best-sellers | Small uppercase "shop sale" label with an outline button on the right, then a product carousel: grey tiles with a blue discount tag and a pink "best seller" tag, name, type, price, size chips, outline add-to-bag | white | 0 / 33 |
| 3 | bundle | Two large half-width photos of gift sets and holiday kits, each with a small white label chip in the centre | white (photos) | 283 / 267 |
| 4 | categories | Five photo tiles in one row with a small uppercase category name under each | white (photos) | 363 / 45 |
| 5 | ugc | "Get the look": three lifestyle and creator-style photos of different heights with a one-line caption each | white (photos) | 0 / 0 |

`order: hero, best-sellers, bundle, categories, ugc`

- The pink area after section 5 (brand statement, email sign-up, links, doodles) is the footer.
- Measured data vs the picture: the reader leaves out the top 140 px as the header, but this header is shorter, so the top of the blue hero is cut off. The hero shows as solid #0600FF 355, then its lower part (giant letters touching the edges) as picture 215. All of solid 0.1 is the hero.
- Off-white #F7F7F7 496 is the grey product tiles touching the page's left edge; the section itself is white. Tint #D4D4D2 183 is a grey wall inside a "get the look" photo, not a fill.
- Off-white #FAF2F4 488 is the top of the pink footer: footer_top is 4163, so most of the footer is counted as content.
- The 7 desktop sections include two 80 px spacer blocks; the gaps between sections come from spacer blocks (30, 80, 48 and 80 px in desktop-metrics.json), which is why the product row and "get the look" show pads of 0. The large pads in sections 3 and 4 (283 / 267, 363) are photos above and below the labels.

## Colour pacing
- Bands of 150 px or more: 2 white, 2 off-white, 1 tint, 1 solid, 4 picture. One loud electric blue does every strong job: the hero band, the hero button, the discount tags and the announcement bar. A pale pink appears in the "best seller" tags and the footer.
- The one solid band is the first section, so the page opens at full volume and then drops to white with photos for the rest (picture 0.4).
- After the hero there is no colour step between sections; photos carry all the colour, and the pink in the photos (wrapping paper, product caps) echoes the footer.

## Type, buttons and spacing
- The hero's giant letters are artwork; the real offer text is a 20 px line in the card (18 on the phone). Every section heading is a 12 px uppercase label (n 3); no section has a large heading. H1 not measured.
- Buttons: 0px corners. The hero's main button is solid blue; "shop now" and "add to bag" are outline buttons drawn with thin lines; product sizes are grey square chips, the chosen one outlined.
- Spacing comes from spacer blocks, not from section padding: a 30 px block under the hero, 80 + 48 px under the product row, 80 px before the footer. Desktop pad median 39 (p25 0, p75 279), mostly photo height.

## Proof
- #2 best-sellers: "best seller" tags and a discount tag on every card. No star ratings or review counts on the cards.
- #5 ugc: real-life and creator-style photos with a caption, no names or quotes.
- No reviews section, no press, no numbers, no guarantee, no FAQ. The footer holds a short brand statement.

## Phone
- 5 sections in the same order (the spacer blocks are not counted).
- Hero: the white offer card sits near the top of a tall blue block (707 px in phone-metrics.json) filled with the repeated lettering; offer line 18 px.
- Product row shows one and a half cards; price moves beside the name; size chips wrap to two lines.
- The two gift photos stack; categories and "get the look" become swipe rows with the next tile cut off.
- Footer: brand statement, email sign-up and accordion links on pink.
- Section headings 12 px (n 3). Pad median 29 (p25 0, p75 76, min 0, max 192, n 6).

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- During a sale, show the offer as live text in a card on the hero (label, one offer line, one support line, one button), and repeat it as a tag on each product card in the brand blue.
- Two tags at most per card, top left: the offer tag in solid blue, the best-seller tag in a pale tint (green for us).
- Seasonal collections (festive gift sets, kits) as two equal half-width photos with a short label chip on each.
- A row of five category tiles with a short uppercase name under each on desktop; a swipe row on the phone.
- A "see it at home" row of real customer photos with one caption line each, only with the customer's permission.

Avoid:
- A hero that is mostly artwork, with the offer in a 20 px line: the offer is the smallest thing on the first screen.
- 12 px labels as the only section headings; give each section a real heading.
- Product cards with no rating or review count, and no reviews section anywhere.
- Spacing built from spacer blocks of different heights (30, 80, 48, 80 px); use one padding rule per section.
- Only 5 sections (4268 px) for a store with several categories: no proof, story or FAQ.
