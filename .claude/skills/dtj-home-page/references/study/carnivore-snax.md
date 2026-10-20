# Carnivore Snax (food): home page study, 19 Oct 2026
Source: https://www.carnivoresnax.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 83 ("loud brand, but consistent bands and spacing"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 8 / 8 |
| Page length px (desktop / phone) | 7235 / 7086 |
| Pad median, p25-p75 (desktop / phone) | 84, 72-148 (min 57, max 196, n 12) / 57, 56-100 (min 24, max 265, n 12) |
| H1 / hero heading px | H1 72 desktop, 38 phone / hero heading 72 desktop, 38 phone |
| Section headings px (median, min-max; desktop / phone) | 56, 18-56 / 34, 18-40 |
| Button (radius, colour) | 8px, rgb(168, 37, 46) (#A8252E) |
| Body font | Roboto |
| Colour share between header and footer | ground 0.25 (white 0.25 + offwhite 0.0), tint 0.32, solid 0.12, dark 0.16, picture 0.15 |
| Colour bands of 150 px or more, in order | picture 700, tint #F9F2DE 1515, dark #270C0C 278, tint #FCF6E5 485, tint #F9F0D8 193, picture 287, dark #240F0F 835, solid #255B8E 797, white 1656 |

Other measured values: 8 colour changes, 0 gradient bands, longest white run 1656 px, longest off-white run 0 px; bands of 150 px or more: white 1, offwhite 0, tint 3, solid 1, dark 2, picture 2.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Dark product photo with a centred 2-line headline, 2 lines of support, a short quote pill with a face photo, one solid red button, stars with a customer count under it | photo (dark) | 70 / 187 (full-width photo, left out of the median) |
| 2 | best-sellers | Heading, one line on pack size, 4 product cards (pack on a white tile, stars with review count, name, price, outline add-to-cart, "view product" link) with arrows, a solid "shop all" button and a free-shipping line | cream #F9F2DE (faint texture) | 80 / 57 |
| 3 | offer | Membership programme: small label, big name, one line and a solid button on the left, the membership card image on the right | dark maroon (fine texture) | 166 / 196 |
| 4 | compare | Check-and-cross table, the brand against a common alternative, 4 rows with icons; a round stamp badge top left; outline "story" and solid "shop all" buttons under it | cream #FCF6E5 / #F9F0D8 | 72 / 96 |
| 5 | ingredients | Full-width photo strip of the product with one label stating the two ingredients | photo | not measured (no live text read) |
| 6 | ugc | Heading with stars and a review count, 2 customer taste-test videos, each with a big quote and a verified name under it | dark #240F0F | 72 / 194 |
| 7 | reviews | Heading with stars and a customer count, 3 customer photos, each with a quote and its own outline "shop this product" button | solid blue #255B8E | 72 / 88 |
| 8 | faq | Heading, a long accordion (15 questions on taste, shipping, guarantee, subscription), a solid "shop all" button at the end | white | 88 / 64 |

`order: hero, best-sellers, offer, compare, ingredients, ugc, reviews, faq`

- Torn-paper edges join the dark ugc band to the blue reviews band and the FAQ to the dark footer; a red announcement bar sits on top.
- Measured data vs the picture: the cream band (1515) runs on into the dark membership section, whose textured fill the reader does not see as flat; the dark band (278) starts lower than the section and ends inside the comparison heading. The fills are in the right order, their edges are shifted.
- The two cream values (#FCF6E5 485, #F9F0D8 193) are one section; the shift is the faint paper texture, not a new band.
- The 18 px "section heading" is the small label above the membership name, which pulls the desktop min to 18 and the p25 to 46; the real section headings are 56 px.

## Colour pacing
- Bands of 150 px or more: 1 white, 0 off-white, 3 tint, 1 solid, 2 dark, 2 picture. Light and dark alternate almost every section: dark photo, cream, dark, cream, photo, dark, blue, white, dark footer.
- Four jobs, four colours: cream is the ground, deep maroon-brown the heavy band (and the footer), brand red the buttons and announcement bar, and one blue band (#255B8E), 7th of 8, for customer quotes.
- White appears only once, under the FAQ (1656 px, the longest run): the quiet end of a loud page.
- Ground (white + off-white) is only 0.25; cream tint 0.32 does the ground's job. Dark plus picture is 0.31.

## Type, buttons and spacing
- H1 72 px and section headings 56 px (n 6 including the 18 px label; weight 400 in a heavy all-caps display face, the FAQ heading weight 600; desktop-metrics.json). Body copy and FAQ questions in Roboto.
- Buttons have 8px corners: solid red for every "shop all" and the membership button; outline red for add-to-cart and "story"; outline white on the blue band; underlined text for "view product".
- Spacing: one top value, 72 px, for the compare, ugc and reviews sections (80 and 88 for the product row and FAQ); bottoms vary from 57 to 196 with what sits under the last text. Desktop pad median 84 (p25 72, p75 148).

## Proof
- #1 hero: a known person's short quote with a face photo, and a star row with a customer count, both inside the first screen.
- #2 best-sellers: stars with a review count on every card; a free-shipping threshold under the row.
- #4 compare: four plain facts against a common alternative, checks and crosses.
- #6 ugc: taste-test videos; each quote is set as a big heading, the names carry a verified tick, the heading carries a review count.
- #7 reviews: customer photos with quotes, each tied to the product with its own shop button; heading with a customer count.
- #8 faq: the guarantee and shipping answers sit in the FAQ, not in a section of their own.

## Phone
- Same 8 sections in the same order (phone page 7086).
- Hero: centred H1 38 px, quote pill, full-width red button and stars, then the product photo below.
- Product row shows two cards with a third peeking; the membership block stacks text and button over the card image.
- The comparison table keeps its two columns; its two buttons stack full width, solid on top.
- The two taste-test videos stack; the customer quotes become a one-at-a-time carousel with dots.
- Section headings 34 px median (28-40). Pad median 57 (p25 56, p75 100): almost every section starts 56 px below its top edge.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- One top pad for every section (72 px desktop, 56 px phone here); let the bottom grow with buttons and notes under the last text.
- A short comparison table high on the page: the client's product against the usual alternative, 4 plain facts with check and cross, a solid "shop" and an outline "learn more" button under it. Facts only from the client.
- Star row with the real customer or review count directly under the hero button.
- Each customer quote tied to the product it praises, with its own outline "shop this" button.
- A free-shipping line under the product row's main button, only with the client's real threshold.
- End on the FAQ with the main buy button under it.

Avoid:
- Light and dark alternating on every section, torn edges and textured grounds: right for a loud snack brand, too heavy for calm home care (here dark plus picture is 0.31).
- A famous person's quote unless the client has it in writing and the right to use it.
- A 15-question FAQ on the home page: keep the few questions that stop a purchase and link the rest.
- A membership or loyalty block third on the page, before the shopper knows why the product is good.
