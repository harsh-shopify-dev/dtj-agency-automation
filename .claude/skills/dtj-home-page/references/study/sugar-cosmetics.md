# Sugar Cosmetics (home): home page study, 19 Oct 2026
Source: https://www.sugarcosmetics.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 66 ("black and purples, dense promotion rows"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 13 / 13 |
| Page length px (desktop / phone) | 7521 / 7541 |
| Pad median, p25-p75 (desktop / phone) | 86, 30-168 (min 24, max 314, n 18) / 39, 36-105 (min 20, max 537, n 20) |
| H1 / hero heading px | H1 28 desktop, 28 phone / hero heading not measured |
| Section headings px (median, min-max; desktop / phone) | 28, 28-28 / 20, 20-20 |
| Button (radius, colour) | 6px, rgb(0, 0, 0) (#000000) |
| Body font | Poppins |
| Colour share between header and footer | ground 0.65 (white 0.59 + offwhite 0.06), tint 0.12, solid 0.14, dark 0.03, picture 0.07 |
| Colour bands of 150 px or more, in order | tint #CFCFCF 518, tint #EFEFEF 294, white 535, white 535, white 626, picture 157, white 544, white 652, white 279, dark #0A060A 197, solid #9A5FFA 935, white 535, offwhite #F2F2F2 261, white 192 |

Other measured values: 9 colour changes, 0 gradient bands, longest white run 652 px, longest off-white run 261 px; bands of 150 px or more: white 8, offwhite 1, tint 2, solid 1, dark 1, picture 1.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Full-width video slideshow of models with dots and a mute icon; no headline and no button on the slide | photo (video) | 468 / 48 (full-width, left out of the median) |
| 2 | categories | Row of square category tiles (product photo on a coloured gradient, a white label tab on top), the last tile cut off at the edge | light grey #EFEFEF | 24 / 151 |
| 3 | best-sellers | New-arrivals product row: 4 cards with a badge, name, stars and count, price with strike price and % off, and a full-width black add-to-cart bar | white | 117 / 33 |
| 4 | best-sellers | Bestseller row, same card plus shade dots and a shade count | white | 118 / 33 |
| 5 | ugc | Row of 6 portrait video tiles with a play icon, each with a product thumbnail, name and price at the foot; its heading repeats section 4's | white | 110 / 63 |
| 6 | offer | Full-width app-download banner image with a discount code and store badges, all text inside the picture | picture | not measured (no live text) |
| 7 | bundle | Gift-kit row: 4 kit cards with save % badges (prices also printed inside the photos), add-to-cart bars, a black "view all" button | white | 314 / 30 |
| 8 | bundle | Combo row, same card and "view all" button | white | 310 / 30 |
| 9 | offer | Full-width offer slideshow (a multi-buy price with a code), text inside the picture | picture (read as dark) | 288 / 48 (full-width) |
| 10 | editorial | One-product spotlight: tall close-up photo on the left, underlined uppercase product name and two long paragraphs on the right, no button | violet-to-pink gradient (read as solid #9A5FFA) | 218 / 217 |
| 11 | offer | Price-capped product row (every item under one low price), same card | white | 118 / 30 |
| 12 | story | Founder portrait on the left half, heading and two bold paragraphs on grey on the right | off-white #F2F2F2 (half photo) | not measured |
| 13 | other | Plain text notice warning shoppers about fake payment calls and links | white | 31 / 30 |

`order: hero, categories, best-sellers, best-sellers, ugc, offer, bundle, bundle, offer, editorial, offer, story, other`

- A blank 60 px white strip between sections 9 and 10 is its own theme section (empty rich text); desktop-metrics.json lists 14 sections, the spacing files skip it.
- Measured data vs the picture: the hero video has a flat grey studio wall at both edges, so the reader classed it as tint #CFCFCF 518; the real picture share is above 0.07 and the tint share below 0.12. Section 9's slideshow was captured dark mid-fade (dark #0A060A 197). Section 10 is a horizontal gradient (violet, pink, a green corner top right) read as one solid #9A5FFA 935.
- The large pad tops in product rows (117, 118, 314, 310) are the heading plus the card pictures above the first card text, not empty space. desktop-metrics.json gives 30-31 px above the heading (gap_top) and 30-33 px below the last button (gap_bottom): the real rhythm is tight.

## Colour pacing
- Bands of 150 px or more: 8 white, 1 off-white, 2 tint, 1 solid, 1 dark, 1 picture. White is the ground for every product row (sections 3-5, 7-8, 11); the colour lives in product photos, category tiles and banner images, not in section fills.
- Black is a working colour, not a band: announcement bar, every add-to-cart bar, the "view all" buttons, badges and the footer.
- One loud fill: the violet-pink spotlight, 10th of 13, after the second offer banner. The only other fills are pale greys (#EFEFEF under categories, #F2F2F2 beside the founder).
- Neighbouring white sections are split by thin grey lines, so long runs read as one white sheet broken only by banner images.

## Type, buttons and spacing
- H1 28 px and every measured section heading 28 px (n 7, no variation); the hero carries no text. Headings are centred, uppercase and widely letter-spaced at weight 400; the category heading alone is weight 700 with no letter-spacing (desktop-metrics.json). Body copy in the founder note is bold.
- Buttons: 6px corners, solid black. Full-width "add to cart" bars under each card; a short black "view all" under the kit, combo and price rows. No outline or secondary style.
- Spacing: product rows sit 30-31 px below the section edge and end 30-33 px after the last button (desktop-metrics.json), so the page reads as a dense catalogue. Only the spotlight (218 / 217, text centred beside a tall photo) breathes. Desktop pad median 86 (p25 30, p75 168).

## Proof
- #3, #4, #7, #8, #11 product cards: star rating with a count on most cards, including counts of 1 to 3; bestseller and save % badges; strike prices with % off.
- Claims printed inside product images (a units-sold figure, a "sold every few minutes" line), not as page text.
- #12 story: a founder note is the only trust section; no review section, press row, certification or guarantee.
- #13 other: a fraud warning about payment requests, plain text at the foot.

## Phone
- Same 13 sections in the same order; nothing is dropped.
- Hero is a tighter crop on one model, same dots and mute icon; H1 28 px.
- A web-push pop-up covers the category row in the capture; the category labels sit under the tiles.
- Product rows show about one and a half cards per screen as a swipe hint, the add-to-cart bars stay full width; the video row shows two tiles and dots.
- Section 9 caught a different slide (a spend-and-save banner): the offer slideshow rotates promotions.
- The spotlight stacks photo over text and uses a different product photo (phone height 1025 px); the founder photo goes on top and the text centres under it.
- Section headings 20 px (n 7). Pad median 39 (p25 36, p75 105, min 20, max 537, n 20): most sections end 36-39 px after the last button.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- Product cards: name, star rating with count, price, strike price and % off, one full-width add-to-cart button on desktop and phone.
- On the phone, show about one and a half cards per screen in every product row, so the swipe is obvious.
- One short plain-text notice near the foot about how the store does and does not ask for payment; Indian shoppers face payment scams, and plain text is readable and translatable.
- A founder note (photo plus two short paragraphs) near the end as the human trust section, only with the client's real words.
- Section headings at one size (28 px desktop / 20 px phone here); keep one heading style for every section.

Avoid:
- More than one offer banner and five product rows in one page: here three promotions and five rows bury the one spotlight.
- Two sections with the same heading, and a blank spacer section between bands.
- Prices, codes and claims printed inside banner and product images: unreadable on the phone, untranslatable, and they go stale; put them in live text.
- Star counts of 1 to 3 reviews on a card: they read as weak proof; show ratings only above a minimum count.
- A hero video with no headline and no button: the first screen never says what the store sells.
