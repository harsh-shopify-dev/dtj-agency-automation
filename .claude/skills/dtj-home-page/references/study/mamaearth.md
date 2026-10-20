# Mamaearth (beauty, India): home page study, 19 Oct 2026
Source: https://mamaearth.in/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 60 ("12,000 px, dense, SEO text at the bottom"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 13 / 13 |
| Page length px (desktop / phone) | 12033 / 15345 |
| Pad median, p25-p75 (desktop / phone) | 32, 23-73 (min 16, max 168, n 24) / 24, 23-35 (min 0, max 140, n 26) |
| H1 / hero heading px | H1 24 desktop, 24 phone / hero heading not measured |
| Section headings px (median, min-max; desktop / phone) | 40, 40-40 / 22, 22-22 |
| Button (radius, colour) | 8px, rgb(0, 174, 239) (#00AEEF) |
| Body font | Open Sans |
| Colour share between header and footer | ground 0.76 (white 0.36 + offwhite 0.4), tint 0.2, solid 0.0, dark 0.0, picture 0.04 |
| Colour bands of 150 px or more, in order | tint #FADDBE 162, picture 222, white 272, white 432, tint #F3EDE3 655, white 2319, tint #FFF8EC 564, white 244, offwhite #F5F5F5 738, white 182, tint #EDFAFF 572, tint #C8E1D0 313, white 627, offwhite #F5F5F5 179, offwhite #F2F2F2 3863 |

Other measured values: 12 colour changes, 0 gradient bands, longest white run 2319 px, longest off-white run 3863 px; bands of 150 px or more: white 6, offwhite 3, tint 5, solid 0, dark 0, picture 1.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Banner slider: model and product photo with a large percentage claim, a green button and a footnote in tiny type | photo | 0 / 29 (full-width banner, left out of the median) |
| 2 | best-sellers | "Most-loved" product carousel under a row of icon tabs (best sellers, an offer tab, hair, face, baby...) | white | 16 / 23 |
| 3 | best-sellers | Seasonal product carousel in a rounded beige panel | tint #F3EDE3 | 32 / 31 |
| 4 | best-sellers | Face best sellers: icon tabs per product type, a photo promo card on the left, product carousel | white | 32 / 23 |
| 5 | best-sellers | Hair best sellers, same layout without the photo card | white | 32 / 23 |
| 6 | best-sellers | Baby best sellers, same layout with a photo card | white | 32 / 23 |
| 7 | ingredients | Shop by ingredient: one icon tab per ingredient over a product carousel with a photo card | white heading, tint #FFF8EC row | 32 / 23 |
| 8 | benefits | "Why us" row: four line icons with a two-word label each, no copy | white | 168 / 32 |
| 9 | best-sellers | New launches carousel in a rounded grey panel | off-white #F5F5F5 | 32 / 31 |
| 10 | best-sellers | Makeup best sellers: icon tabs, a video card on the left, product carousel | white heading, tint #EDFAFF row | 32 / 23 |
| 11 | story | Tree-planting programme: logo, one bold line, and a card with a live counter of trees planted over a forest photo | tint #C8E1D0 fading lighter | 112 / 131 |

`order: hero, best-sellers, best-sellers, best-sellers, best-sellers, best-sellers, ingredients, benefits, best-sellers, best-sellers, story`

- Under the footer sits a long block of SEO text (category write-ups, link lists, a price list) on #F2F2F2, 3863 px on desktop; it is below the footer, so it is not in the order line.
- Measured data vs the picture: the page has no detected footer (footer_top not measured), so the footer (white 627), its badge strip (#F5F5F5 179) and the SEO block (3863) are all counted as content: 4669 px of the 11893 px measured. The ground share 0.76 and the off-white 0.4 mostly come from that.
- The saved section list is nested: a 5947 px wrapper holds sections 3-10, and the footer is listed as a 13th section, so the pad numbers (n 24) include the wrapper's 32 / 131 and the footer's 87 / 123. Only 3 section headings were read (one twice, through the wrapper), all 40 px; the other headings are not measured.
- Floating widgets broke bands: the "ask AI" bubble and a second round bubble at the left edge turn product rows into short "picture" strips (75 and 98 px), which is why white 272 and white 432 sit side by side. The hero reads as tint #FADDBE 162 + picture 222 because the banner's top edge is a flat peach.
- Sections 7 and 10 change colour mid-section: heading and tabs on white, product row on the tint.

## Colour pacing
- Bands of 150 px or more: 6 white, 3 off-white, 5 tint, 0 solid, 0 dark, 1 picture. The band tints come from five different hues: beige #F3EDE3, cream #FFF8EC, grey #F5F5F5, light blue #EDFAFF and green #C8E1D0, with no fixed order.
- The brand blue #00AEEF is never a band: it is the announcement bar, the app button and every add-to-cart button. Green shows in the hero button, offer badges and the tree section; red and purple appear only in card badges.
- Three white product rows in a row (face, hair, baby) make the longest white run, 2319 px, with no change of fill.
- No solid or dark band anywhere; the strongest colour on the page is the stack of blue buttons.

## Type, buttons and spacing
- Headings are centred, regular weight with one word in bold, and a small grey line under each. The three measured ones are 40 px (weight 500); the hero's words seem to be part of the banner picture (the reader found no hero heading). H1 24 px.
- Buttons: 8px corners, solid #00AEEF, full card width on every product card ("add to cart"); the hero's button is green. "View all products" is a text link with an arrow under each row.
- Spacing is dense and almost uniform: the product rows sit at 32 px top and 23-31 px bottom. Only the icon row (168 top) and the tree section (112 / 131) get more. Desktop pad median 32 (p25 23, p75 73).

## Proof
- Every product card (#2-#10): star rating with review count, a badge (best seller, number-one claims, "selling fast", buy-one-get-one), price with strike price and percent off; many product photos carry printed result claims.
- #1 hero: an "up to" percentage claim with an asterisk and a test footnote in tiny type.
- #8 benefits: four claim icons (natural, toxin-free, tree planting, safety).
- #11 story: a live counter of trees planted, credited to shoppers.
- Footer: certification icons, service icons (free shipping, easy return, COD available) and payment logos.
- No review section, no press, no customer photos, no FAQ.

## Phone
- Same sections, but the order starts differently: the first product carousel comes first (under a "discover" search header) and the banner slider (202 px) moves below it. The phone shows no announcement bar.
- Product rows stay carousels with the second card cut off; icon tabs scroll sideways; the photo promo cards become a large card at the start of the row.
- The footer links fold into one accordion line, then the SEO text runs on; the phone page is 15345 px.
- A free-delivery progress bar, a bottom app bar (home, category, offer, profile, app, cart) and the "ask AI" bubble float over the content (captured mid-page in the full-page shot).
- Section headings 22 px (n 3). Pad median 24 (p25 23, p75 35, min 0, max 140, n 26): the rows use 24-30 top and 23-29 bottom.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- Every product card carries: star rating with review count, price with strike price and percent off, one short benefit line, and a full-width add-to-cart button, so shoppers buy from the home page.
- Icon tabs over a product row (one small line icon per sub-category: room, surface or need) let one section cover a whole category.
- Brand blue on every add-to-cart button (here #00AEEF, 8px corners); green only in badges and icons.
- Show the service promises Indian shoppers check (COD available, free-shipping threshold, easy returns) as an icon row near the products, not only in the footer.
- A four-icon "why us" row with two-word labels, placed between product rows, as a short pause.

Avoid:
- Eight product rows (seven plus the ingredient row): here they push the page to 12033 px desktop and 15345 px phone, and three white rows in a row give a 2319 px run with no change.
- Band tints from five unrelated hues; keep one hue family.
- An SEO text dump under the footer (3863 px here).
- "Up to" percentage claims with an asterisk and tiny-print footnotes, or number-one badges, unless the client holds the test report or the ranking source.
- Floating chat bubbles and app bars over the content.
