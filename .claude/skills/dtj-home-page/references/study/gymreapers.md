# Gymreapers (fitness): home page study, 19 Oct 2026
Source: https://gymreapers.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 76 ("black/white/grey, clean product rows, little colour"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 11 / 11 |
| Page length px (desktop / phone) | 7225 / 7115 |
| Pad median, p25-p75 (desktop / phone) | 64, 28-67 (min 2, max 84, n 16) / 58, 46-69 (min 42, max 101, n 14) |
| H1 / hero heading px | H1 13 desktop, 14 phone / hero heading not measured (null) |
| Section headings px (median, min-max; desktop / phone) | 40, 40-40 (n 5) / 24, 24-24 (n 5) |
| Button (radius, colour) | 4px, rgb(0, 0, 0) (#000000) |
| Body font | Arimo |
| Colour share between header and footer | ground 0.67 (white 0.67 + offwhite 0.0), tint 0.02, solid 0.06, dark 0.21, picture 0.05 |
| Colour bands of 150 px or more, in order | dark #020202 498, white 1657, solid #959693 225, white 1494, dark #000000 640, white 1100 |

Other measured values: 5 colour changes, 0 gradient bands, longest white run 1657 px, longest off-white run 0 px; bands of 150 px or more: white 3, offwhite 0, tint 0, solid 1, dark 2, picture 0.

The band reader read all three full-width photos as colour bands. "dark #020202 498" is the hero photo (a dark gym shot whose edges are flat black); "solid #959693 225", with the strips solid #A4A6A5 141 (gradient) and tint #B9BBBA 133 under it, is the grey studio backdrop of the second photo banner; "dark #000000 640" is the third photo banner. The only real CSS colour between header and footer is a dark trust strip (dark #111111, 79 px, under 150 so not in the list). So the dark 0.21 and solid 0.06 shares are photos, and every content section sits on white.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Full-width dark lifestyle photo, uppercase headline and one line at the left, one white rectangular button | photo | 378 / 240 (full-width photo, left out of the median) |
| 2 | proof-numbers | Three trust lines with line icons, split by thin dividers: a customer count with founding year, a review count, a warranty | dark #111111 strip, then white | 22 / 70 |
| 3 | best-sellers | "New Releases": slider of large square product pictures on light grey, badge, stars with score and count, name, price, colour swatches; progress line and arrows under it | white | 20 / 64 |
| 4 | best-sellers | "Best-selling lifting gear": same slider, some cards with a red saving badge and a red sale price | white | 64 / 64 |
| 5 | other | Full-width photo banner for a seasonal clothing line: headline, one line, white button | photo (grey studio) | 570 / 48 (full-width photo) |
| 6 | best-sellers | "Men's best sellers": same slider | white | 84 / 64 |
| 7 | best-sellers | "Women's best sellers": same slider | white | 20 / 64 |
| 8 | other | Full-width dark gym photo banner: small eyebrow, headline, white button | photo | 406 / 48 (full-width photo) |
| 9 | best-sellers | "Best-selling accessories": same slider | white | 84 / 64 |
| 10 | other | A single centred, underlined "shop all products" text link | white | 2 / 68 |
| 11 | guarantee | Four service promises: line icon, uppercase title, one or two lines (support hours, free-shipping threshold, returns, secure payment) | white | 44 / 64 |

`order: hero, proof-numbers, best-sellers, best-sellers, other, best-sellers, best-sellers, other, best-sellers, other, guarantee`

- Section 2 is 128 px in the spacing file but its dark strip is only 79 px; the rest of the section is white space under the strip.
- The H1 (13 px desktop, 14 px phone) is not the hero headline; the headline on the photo is far larger (its size is not measured).
- The product sliders cut the last card at the right edge on purpose, as a hint to scroll.

## Colour pacing
- One white ground for every content section; the only CSS colour is the dark trust strip under the hero, the grey announcement bar and the black footer. No tint or solid brand band anywhere.
- Rhythm comes from photos: two product sliders, then a full-width photo banner, twice (sections 5 and 8), so the page reads as hero, white, white, photo, white, white, photo, white. Each photo breaks a long white run (1657 and 1494 px).
- Colour inside the white sections comes only from product pictures (light grey backdrops), black stars, black swatches and the red saving badges and sale prices.

## Type, buttons and spacing
- Section headings are 40 px, weight 400, uppercase with wide letter spacing, all five the same (desktop-metrics.json). The same uppercase light style is used for the photo-banner headlines. A "View all" text link with a small round arrow sits at the right of each heading.
- The measured button is black with 4px corners. On the photos the buttons are white rectangles with black uppercase text; slider arrows are small round outline buttons.
- Spacing: pad median 64 px desktop (p25 28, p75 67). Every product section ends exactly 64 px below its slider; the top is 84 px after a photo banner and 20 or 64 px after another white section.

## Proof
- #2 proof-numbers: a customer count, a review count and a warranty in one dark strip directly under the hero, the first thing after the photo.
- #3, 4, 6, 7, 9: stars, decimal score and review count above the name on every product card; a few "new release", "bundle" or approval badges.
- #11 guarantee: four service promises as the last section, with a phone number and live-chat link in the support item.
- No customer quotes, photos from buyers, press or founder story on the page.

## Phone
- 11 sections. A black band with four round category pictures and two-line labels sits between the header and the hero (first phone section, 156 px, no gap data); the "shop all products" link is in phone-metrics.json (54 px) but not in the phone spacing file.
- The hero keeps the same photo, cropped to the narrow frame, with the headline in two lines, one line of text and the white button at the lower left.
- The trust strip stays three across with dividers, each line wrapped to two or three short lines.
- Sliders show one card and the edge of the next; each card gets an outline "add to cart" button, dots under the picture, and "View all" moves under the heading.
- The photo banners stay full width (450 and 560 px tall); the four service promises become a one-at-a-time carousel with dots.
- Section headings 24 px (n 5). Pad median 58 (p25 46, p75 69, min 42, max 101, n 14).

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- A strip of three short trust lines (a customer count, a review count, a guarantee) directly under the hero, only with the client's real, provable numbers.
- On every product card: stars, score and review count, name, price, variant choice; on the phone, an add-to-cart button on the card.
- Two product rows, then one full-width picture banner with a short headline and one button, then product rows again; never more than two rows in a row.
- One heading style for every section (here 40 px desktop / 24 px phone, weight 400), with a "View all" link beside it.
- End every product section with the same bottom space (here 64 px on desktop).
- Service promises (support, delivery, returns, safe payment) as the last section before the footer.

Avoid:
- Five product sliders on one page: by the fourth the cards blur together.
- An H1 that is not the visible headline (here 13 px).
- White headline text on a pale grey photo (the second banner): weak contrast.
- A page with no brand colour band at all: add one soft tint and one solid band in blue or green between the white sections.
