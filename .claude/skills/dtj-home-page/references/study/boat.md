# boAt (electronics, India): home page study, 19 Oct 2026
Source: https://www.boat-lifestyle.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 62 ("information density, not a design model"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 8 / 10 |
| Page length px (desktop / phone) | 6449 / 5046 |
| Pad median, p25-p75 (desktop / phone) | 5, 0-15 (min 0, max 168, n 14) / 2, 0-16 (min 0, max 104, n 16) |
| H1 / hero heading px | H1 38 desktop, 35 phone / hero heading not measured desktop, not measured phone |
| Section headings px (median, min-max; desktop / phone) | 24, 24-24 / 24, 24-24 |
| Button (radius, colour) | 17px, rgb(236, 240, 244) |
| Body font | -apple-system |
| Colour share between header and footer | ground 0.85 (white 0.62 + offwhite 0.23), tint 0.12, solid 0.0, dark 0.0, picture 0.03 |
| Colour bands of 150 px or more, in order | tint #E0D2C9 218, tint #E0D1C9 179, white #FFFFFF 3739, tint #E7F0F5 321, offwhite #EFF4F7 1279 |

Other measured values: 3 colour changes, 0 gradient bands, longest white run 3739 px, longest off-white run 1279 px; bands of 150 px or more: white 1, offwhite 1, tint 3, solid 0, dark 0, picture 0.
Corrected 19 Oct 2026 after the reader fixes: the phone list started with a bar, now left out; the phone pad median is 2, as in ratings.md.

The band reader misread this page twice. The two beige "tint" bands (218, 179) are the hero banner picture: its left edge and the next slide peeking in at the right edge are both flat beige. The footer really starts at 4613 (the top of the tint #E7F0F5 band in all_bands), not at 6213, so "tint #E7F0F5 321" (email sign-up) and "offwhite #EFF4F7 1279" (long link lists) are footer, and the shares above include them. Between the hero and the footer the page is one white ground (the single 3739 px band).

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Carousel of wide sale banners; the offer text, product shots and a square black "shop now" block are all inside the picture; arrows, dots, next slide peeking at the right | photo (beige and red banner) | not measured (full-width picture) |
| 2 | guarantee | A thin yellow strip of payment-partner logos, then four icon-and-label service promises (warranty, billing, delivery, replacement) | yellow strip, then pale blue-grey #F6FAFF (126 px strip) | not measured (not in the spacing file) |
| 3 | offer | "Exclusive Offers": six product cards in one row (badge, picture, yellow feature-and-rating label, name, price, strike price, % off, colour dots) | white | 0 / 5 |
| 4 | other | "Explore Nirvana": one wide banner for a sub-brand line, its text inside the picture | white (lavender gradient banner) | 0 / 168 |
| 5 | offer | "Top Deals": the same product row with category tabs as pale pills above it | white | 0 / 5 |
| 6 | categories | "Shop by Categories": ten product cut-outs on small grey circles with names, one row | white | 15 / 15 |
| 7 | best-sellers | "Hot Picks": the same product row, tabs for new launches and personalisation | white | 0 / 5 |
| 8 | categories | "Shop by Lifestyle": four tall cards, a person in an arch-shaped frame, a use-case label and a view-all link | white (pale grey-blue cards) | 0 / 20 |
| 9 | best-sellers | "Best Of boAt": the same product row, first tab best sellers | white | 0 / 5 |
| 10 | editorial | "Blogs": four dated article cards with picture, title, two lines and an outline "read more" pill; popular / latest tabs | white | not measured |
| 11 | press | "In the Press": carousel, one media logo on a grey panel at the left and one quote at the right | white (grey panels) | not measured |

`order: hero, guarantee, offer, other, offer, categories, best-sellers, categories, best-sellers, editorial, press`

- The desktop spacing file stops at section 9: the guarantee strip, Blogs and In the Press have no gap data (desktop-metrics.json lists Blogs at 461 px and In the Press at 324 px tall). So "8 sections measured" undercounts the 11 visible ones.
- Pad 0 at the top means the heading sits on the section's top edge; the white gap a shopper sees between sections lies outside the measured sections (not measured). The 168 bottom in section 4 is the banner under its heading, not empty space.
- Four product rows (3, 5, 7, 9) use one identical card; two are framed as deals, two as picks.
- ratings.md lists the pad as 5 / 2; numbers.json gives 5 / 5 for phone. This note uses numbers.json.
- The footer holds the email sign-up and long "under a price" link lists; it is not counted as a section.

## Colour pacing
- No colour bands at all between the hero and the footer: one white ground carries 9 sections in a row (3739 px). Sections are told apart only by their 24 px headings and the gap above them.
- Colour comes from small, repeated parts: the yellow feature-and-rating label on every product card, the yellow partner-logo strip, the beige-and-red hero banner, a lavender sub-brand banner, pale grey-blue lifestyle cards and grey press panels. Card pictures each have their own backdrop colour, so a product row reads as a row of mixed colours.
- The pale blue-grey of the trust strip (#F6FAFF) comes back only in the footer (#E7F0F5, #EFF4F7).

## Type, buttons and spacing
- H1 38 px desktop / 35 px phone is in the page code, but no headline of that size is visible: the hero words are part of the banner picture. Every section heading is 24 px, weight 500 (desktop-metrics.json), with the second word in bold and a short red underline under part of it.
- The measured button (17px corners, pale grey #ECF0F4) matches the selected tab pills above the product rows. Other actions: "View All" text links with a circled arrow at the right of each heading, outline pills under the blog cards, and the black block inside the hero picture.
- Spacing: pad median 5 px desktop (p25 0, p75 15). Headings sit flush on the section top and product cards end 5 px above the section bottom: the lowest pad in ratings.md (the cramped group there is 32-42).

## Proof
- #3, 5, 7, 9 product rows: a star rating number on every card inside the yellow label (no review count), plus badges (new launch, extra discount, engraving, trending) and a green "% off" line.
- #2 guarantee: four service promises with icons directly under the hero, and partner bank and pay-later logos in the yellow strip.
- #11 press: one media logo and one quote at a time, last on the page.
- No customer reviews, photos or videos from buyers anywhere on the page.

## Phone
- 11 sections measured on the phone. A swipe row of round category icons sits right under the black header, above the hero; the desktop "Shop by Categories" section is dropped.
- The hero shows a different slide: a rounded banner card with a product picture, one line and a small black pill button.
- The partner strip and the four service promises stay under the hero (four across, icon over two short lines).
- Product rows become three-column grids of six cards (two rows); the lifestyle cards become a 2 x 2 grid.
- A sticky bottom bar with five icons (home, categories, rewards, personalisation, chat) covers part of the product grid in the capture.
- Blogs and In the Press are in phone-spacing.json (440 and 501 px) but the screenshot shows a loading logo in their place: they did not render.
- Section headings 24 px (n 8), same as desktop. Pad median 2 (p25 0, p75 16, min 0, max 104, n 16; a leading bar left out).

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- A strip of up to four service promises with icons (delivery, returns, payment options, support) directly under the hero, only with the client's real policies.
- On the phone, a swipe row of round category icons at the top of the page, so the shopper can browse in one tap.
- One product card used everywhere: name, price, strike price, saving, rating; the same card in every product row.
- Put several product groups behind tabs (pale pills) in one product section instead of stacking separate rows.
- A "View All" link at the right of every product and category heading.

Avoid:
- Headings flush on the section edge (pad median 5 px): use the steps in blueland.md (72 / 112 px desktop, 64 px phone).
- Four product rows of the same card on one page; two at most, with a different section between them.
- 3739 px of plain white with no band: give the page at least one tint and one solid band.
- Offer text and headlines inside the hero picture: it cannot be read, translated or measured, and the visible page has no real headline.
- Yellow labels on product cards (outside our blue and green rule), and sections that load late and miss on the phone.
