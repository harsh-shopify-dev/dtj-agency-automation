# AG1 (supplements): home page study, 19 Oct 2026
Source: https://drinkag1.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 88 ("long but ordered: trust, products, compare table, reviews, guarantee, FAQ"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 19 / 19 |
| Page length px (desktop / phone) | 16294 / 16268 |
| Pad median, p25-p75 (desktop / phone) | 100, 80-108 (min 0, max 256, n 31) / 40, 40-52 (min 0, max 391, n 29) |
| H1 / hero heading px | H1 not measured desktop, not measured phone / hero heading not measured desktop, not measured phone |
| Section headings px (median, min-max; desktop / phone) | 56, 18-96 / 32, 16-40 |
| Button (radius, colour) | 32px, rgb(2, 61, 61) |
| Body font | diatype |
| Colour share between header and footer | ground 0.65 (white 0.53 + offwhite 0.12), tint 0.15, solid 0.04, dark 0.03, picture 0.13 |
| Colour bands of 150 px or more, in order | tint #EFEBE2 797, white #FFFFFF 523, picture 164, tint #EDEBE4 513, white #FFFFFF 1821, offwhite #F6F5F1 700, white #FFFFFF 1093, solid #0C3D3D 328, picture 560, white #FFFFFF 1907, offwhite #F6F5F1 412, dark #000000 292, picture 440, dark #000000 204, offwhite #F6F5F1 622, white #FFFFFF 1462, picture 626, white #FFFFFF 964, tint #EDEBE4 960 |

Other measured values: 18 colour changes, 0 gradient bands, longest white run 1907 px, longest off-white run 700 px; bands of 150 px or more: white 6, offwhite 3, tint 3, solid 1, dark 2, picture 4.
Corrected 19 Oct 2026 after the reader fixes: the FAQ's impossible gaps (-34, -158) are left out, and the 1471 px footer is no longer counted as content.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Star line with review count, serif headline, one line, green pill button, product box photo on the right; a four-point trust strip (icons) under the fill | tint #EFEBE2, trust strip on white | 203 / 40 (full-width picture, left out of the median) |
| 2 | best-sellers | Heading only: mono caps label, a large serif heading and one line introducing the range | white | 132 / 60 |
| 3 | best-sellers | Three product cards side by side: photo, name, monthly and per-serving price, button, flavour dots, benefit ticks; middle card dark green with a "most popular" tag | white (cards greige and dark green) | 5 / 62 (the top value is the card tag) |
| 4 | compare | Full product compare table: rows of ticks and crosses, price per month and per serving, one dark button | white | 100 / 100 |
| 5 | benefits | "Who it is for" checklist of five lines and a wide dark button, four lifestyle photos in a grid on the right half | off-white #F6F5F1 (right half photo) | 80 / 80 |
| 6 | ugc | Customer count as the heading, outline button, three customer video tiles with name and short title | white | 116 / 42 |
| 7 | press | Three media logos in one row, no quote | white | not measured (logos only, no text) |
| 8 | ingredients | Heading, one line, two outline buttons, then a swipe row of ingredient photo cards with a short note each | solid #0C3D3D | 100 / 124 |
| 9 | ingredients | Quality standards: certification photo on the left, mono label, heading, paragraph and button on the right | white | 256 / 216 (short text beside a tall photo) |
| 10 | compare | Cost table: ticks per ingredient group against the price of buying each separately, product photo beside it | white | 100 / 148 |
| 11 | other | Chooser prompt: "not sure which one" heading, one line, one button to the compare page | off-white #F6F5F1 | 100 / 100 |
| 12 | reviews | Well-known users in a swipe row: photo card, quote, name and role; star line and button above | dark #000000 | 100 / 100 |
| 13 | reviews | Three written reviews: stars, bold title, quote, name, date and product | off-white #F6F5F1 | 100 / 84 |
| 14 | best-sellers | Heading only for the two blocks below | white | 108 / 0 |
| 15 | other | New-product spotlight in a bright green rounded card: "new" tag, heading, price with strike price, button, pack photo | white (green card inside) | 101 / 96 |
| 16 | best-sellers | Four product cards: tag, name, one line, price with strike price, colour dots | white | 16 / 144 |
| 17 | guarantee | Full-width dark green texture photo: shield icon, mono label, heading, paragraph, green button | photo | 196 / 100 (full-width photo) |
| 18 | faq | Heading on the left, eight questions in an accordion on the right, first one open | white | 100 / -34 |
| 19 | editorial | Blog posts in a swipe row with a "view all" button | tint #EDEBE4 | 100 / 100 |

`order: hero, best-sellers, best-sellers, compare, benefits, ugc, press, ingredients, ingredients, compare, other, reviews, reviews, best-sellers, other, best-sellers, guarantee, faq, editorial`

- Sections 2 and 14 are only headings for the product blocks under them; the reader counts them as their own sections. The trust strip is inside section 1.
- Measured data vs the picture: "picture 164" and "tint #EDEBE4 513" are the product cards of section 3 reaching into the side margins, not a band; that section is white. The ingredients section (8) shows as "solid #0C3D3D 328, picture 560" plus a 100 px strip because its card row touches both edges. The athletes section (12) is one black area split into "dark 292, picture 440, dark 204" by its card row.
- The negative pads (-34 desktop, -158 phone) are the FAQ list running past the measured section box, not overlap on screen.

## Colour pacing
- Bands of 150 px or more (footer left out): 6 white, 3 off-white, 3 tint, 1 solid, 2 dark, 4 picture. Ground is white with a warm off-white (#F6F5F1) and warm greige tints (#EFEBE2 hero, #EDEBE4 blog). Every tint is warm and grey; no coloured pastel band.
- Three loud areas, four to five sections apart: dark green ingredients (8th of 19), black famous-user reviews (12th), dark green guarantee photo (17th). Bright green is kept for the hero, product-card and guarantee buttons and one spotlight card.
- Neighbours often share white (2-4, 6-7, 9-10, 14-16); spacing and the 56 px headings separate them. The longest white run is 1907 px (sections 9-10).
- A lot of colour sits in cards, not bands: greige and dark green product cards, the bright green spotlight card.

## Type, buttons and spacing
- Section headings 56 px on desktop (p25 and p75 both 56), weight 400 on every section heading (desktop-metrics.json); product names 18 px at 700. The hero headline and the range heading (96 px) use a serif; everything else is the sans body font. Small monospaced uppercase labels sit above headings and on cards.
- Buttons: radius 32px, measured colour rgb(2, 61, 61) (deep green). On screen there are four kinds: deep green solid, bright green solid (hero, cards, guarantee), an olive-brown solid (chooser) and outline (reviews, ingredients).
- Spacing: one value does most of the work: 100 px top and bottom on sections 4, 11, 12 and 19, and 100 on the top of 8, 10, 13 and 18. Only text beside a tall photo goes larger (256 / 216). Desktop pad median 100 (p25 80, p75 108).

## Proof
- #1 hero: star line with a review count, a "#1 recommended" badge on the photo, trust strip (certification, research, scientists and athletes, 90-day guarantee).
- #4 and #10: two tables, one product against product, one against the price of buying separately.
- #6 ugc: customer count heading over three customer videos. #7 press: three media logos, no quote.
- #9: certification shown on a photo. #12: well-known users with quotes and roles. #13: three dated written reviews.
- #17 guarantee as its own section, and two FAQ questions repeat it. The same review-count line appears three times (sections 1, 6 and 12).

## Phone
- Same 19 sections in the same order. Page 16268 px. Hero puts the product photo on top, then star line, headline, one line, full-width green button; the trust strip becomes a stacked list.
- The three product cards stack vertically (section 3 is 1505 px tall on the phone); the compare table keeps three columns at full width; the goals photo grid moves above its text.
- Video reviews, ingredients, famous users, written reviews and blog become swipe rows with the next card cut off. Press logos stack one per row. The four-product row becomes a list: image left, text right.
- Section headings 32 px (min 16, max 40). Pad median 40 (p25 40, p75 52, n 29): most sections use exactly 40 top and bottom. Main buttons go full width.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- A trust strip of 3-4 icon points directly under the hero (testing, certification, guarantee), only points the client can prove.
- When the store sells three or more versions of one product, one side-by-side compare table (ticks, crosses, price per unit), and a short "not sure which one" prompt that links to it.
- One heading size and one weight for every section (here 56 px desktop / 32 px phone, weight 400); product names smaller and bold.
- One pad value for most sections: 100 px top and bottom on desktop, 40 on phone; only text beside a tall photo gets more.
- The guarantee as its own section right above the FAQ, and answered again inside the FAQ.
- Loud bands (here 3 of 19) spaced four to five sections apart; the bright accent colour only on buttons and one spotlight card.

Avoid:
- This length: 19 sections and 16294 px, with two compare blocks, two review blocks and three product blocks.
- The same review-count line in three places.
- Endorsements by famous people, "#1 recommended" badges or price-against-buying-separately tables the client cannot prove.
- Product cards stacked one under another on the phone (1505 px for three cards); use a swipe row.
- A heading-only strip split from its product block (sections 14-16).
