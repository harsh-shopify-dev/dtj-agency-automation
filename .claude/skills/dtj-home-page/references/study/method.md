# Method (home care): home page study, 19 Oct 2026
Source: https://methodhome.com/ (redirects to methodproducts.com), captured 19 Oct 2026 at 1440 and 390 px (private capture, round 2). Harsh's rating in ratings.md: 85 ("bold gradients: distinctive, hard to copy"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 8 / 7 |
| Page length px (desktop / phone) | 6830 / 9854 |
| Pad median, p25-p75 (desktop / phone) | 88, 41-166 (min 24, max 281, n 12) / 64, 64-64 (min 64, max 64, n 2) |
| H1 / hero heading px | H1 64 desktop, 32 phone / hero heading 64 desktop, 32 phone |
| Section headings px (median, min-max; desktop / phone) | 44, 36-54 / 32, 24-40 |
| Button (radius, colour) | 999px, rgb(77, 0, 132) |
| Body font | Haffer |
| Colour share between header and footer | ground 0.66 (white 0.63 + offwhite 0.03), tint 0.0, solid 0.14, dark 0.0, picture 0.21 |
| Colour bands of 150 px or more, in order | white #FFFFFF 319, white #FFFFFF 1913, picture 956, white #FFFFFF 820, solid #D80E80 911, white #FFFFFF 957, offwhite #F5F5F5 166 |

Other measured values: 5 colour changes, 0 gradient bands, longest white run 1913 px, longest off-white run 166 px; bands of 150 px or more: white 4, offwhite 1, tint 0, solid 1, dark 0, picture 1.
Corrected 19 Oct 2026 after the reader fixes: the phone list started with the nav bar, now left out; the phone pad median is 64, as in ratings.md.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Product bottles and water splashes on white; on the left a small gradient "new" label, a bold lowercase headline with its last line in gradient colour, one solid purple pill | photo on white | 425 / 155 (full-width photo, left out of the median) |
| 2 | editorial | Two large rounded launch cards (one illustrated, one photo), each with a "new" chip, heading, short copy and a white outline pill | white | 259 / 183 |
| 3 | bundle | Heading and one line, then three bundle cards: two bottles joined by a plus sign, bundle name, a "for which skin" line, outline pill | white | 56 / 24 |
| 4 | best-sellers | Product row on a full-width gradient band (blue, pink, green): small label, heading, round arrows; white cards with stars and review count, a "best seller" or "new" label, name, price, outline add-to-cart pill | gradient | 64 / 104 (flagged full-width picture, left out of the median) |
| 5 | categories | Collections by mood: small label, heading and outline pill on the left; tall photo cards with a name and a white pill each in a sideways row with a scroll bar | white | 281 / 84 |
| 6 | reviews | Centred line and heading on a pink-to-purple gradient band; four cards, each a product photo, five stars, a one-word title, a short quote with a user name and a shop-now pill | gradient | 92 / 116 |
| 7 | other | Product finder: heading and line over a large colour wheel on the left, a product row (stars, count, price, add to cart) on the right that follows the chosen colour | white | 64 / 104 |
| 8 | other | Slogan ticker on a purple-to-teal gradient strip | gradient | 36 / 36 |

`order: hero, editorial, bundle, best-sellers, categories, reviews, other, other`

- Measured data vs the picture: the page has three horizontal gradient bands (sections 4, 6, 8) but the reader counts 0 gradient bands. Section 4 is read as "picture 956", section 6 as "solid #D80E80 911" (the pink at its left edge; the right edge is purple), section 8 as a 107 px picture strip.
- The hero is read as white ("white 319" plus short picture strips where splashes touch the edge); sections 2 and 3 then sit inside "white 1913".
- "offwhite #F5F5F5 166" is the top of the grey footer, not content: the social-icon row (a 70 px picture strip) splits the footer and only the part below it was left out.
- Phone pads: the phone list starts with the navigation bar (0 / 0) and flags most sections as full-width pictures, so the phone median 32 (n 4) is the nav bar plus the reviews section. The phone hero heading is "not measured" for the same reason (phone-spacing.json gives the hero 32 px), and the hero is counted among the phone section headings. ratings.md lists this page at 98 / 64; numbers.json gives 88 / 32.
- The large top pads (259, 281) are not empty bands: section 2's heading sits just under the hero's white fade, and section 5's text is centred beside tall cards.

## Colour pacing
- Bands of 150 px or more: 4 white, 1 off-white (footer top), 1 solid and 1 picture (both really gradients). 5 colour changes.
- A white page with two loud full-width gradient bands, the bestseller row (4th of 8) and the reviews (6th of 8), with one white section between them; a thin gradient strip closes the page. Each gradient crosses several hues (blue, pink, purple, green).
- The white sections are not calm either: bright launch cards, pastel bundle photos, mood-photo collection cards and the colour wheel fill them. Only the grey footer is quiet.
- Colour also sits in the buttons: white pills with a purple-to-teal gradient outline everywhere, one solid deep purple in the hero.

## Type, buttons and spacing
- All headings lowercase, bold geometric sans (Haffer), weight 500 (hero 400, desktop-metrics.json); H1 64, section headings 36-54 (median 44). Short lowercase label lines sit over some headings.
- Buttons: pills (999px). The solid deep purple #4D0084 only in the hero; every other button (add to cart, shop the bundle, view products, shop now) is a white pill with a gradient outline.
- Spacing is uneven: desktop pad median 88 (p25 41, p75 166); bundles 56 / 24, reviews 92 / 116, colour finder 64 / 104, slogan strip 36 / 36.

## Proof
- #1 hero: the headline carries a performance figure (a claim, not shown proof).
- #4 best-sellers: stars and review count on every product card, plus "best seller" and "new" labels.
- #6 reviews: four short quotes at once, each with five stars, a one-word title, the product photo and a shop-now button, so every review sells its product.
- #7 other: stars and counts again on the finder's products.
- No press, numbers strip, guarantee or founder story on the home page.

## Phone
- Same sections in the same order, but the page grows to 9854 px (6830 on desktop): launch cards and bundle cards stack one per row, each very tall (the bundle section is 2140 px on the phone, phone-metrics.json).
- Hero: headline centred above the bottles, the solid pill over the photo's lower edge.
- Product row and reviews become one-card swipe rows with the next card's edge showing (arrows under the products, dots under the reviews); the collections become a stacked card deck with a full-width outline button; the colour wheel sits above its product row.
- H1 32; section headings 32 (min 24, max 40, n 7). Pad median 64 (p25 64, p75 64, n 2; the nav bar left out).

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- Bundles as their own section: three cards, each with who it is for in one line and one button, placed before the bestseller row.
- Stars and review count on every product card, taken only from the client's review app.
- Reviews as several short quotes in view at once (a one-word title and one or two sentences), each linked to its product with a button.
- One solid brand colour for the main button only; every other button outlined, all pills (999px).
- A simple product finder late on the page when the range has many variants (scent, size, use).

Avoid:
- Multi-hue gradient bands (here three): they bring in pink, purple and yellow-green; use flat blue or green fills.
- A page where every section is loud: keep a calm ground between colour blocks.
- Stacking big cards one under another on the phone (the page grows from 6830 to 9854 px): use swipe rows.
- A performance percentage in the hero headline without the client's test report.
