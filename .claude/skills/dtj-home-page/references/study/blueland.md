# Blueland (home): home page study, 19 Oct 2026
Source: https://www.blueland.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 90 ("one blue in 3 jobs (white, soft tint, ONE solid band), clear order, calm"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 11 / 11 |
| Page length px (desktop / phone) | 7808 / 7731 |
| Pad median, p25-p75 (desktop / phone) | 112, 72-140 (min 72, max 542, n 18) / 64, 64-64 (min 48, max 427, n 16) |
| H1 / hero heading px | H1 48 desktop, 30 phone / hero heading 48 desktop, 30 phone |
| Section headings px (median, min-max; desktop / phone) | 40, 40-40 / 26, 24-26 |
| Button (radius, colour) | 9999px (pill), rgb(19, 60, 209) (#133CD1) |
| Body font | Sailec |
| Colour share between header and footer | ground 0.55 (white 0.39 + offwhite 0.16), tint 0.09, solid 0.11, dark 0.0, picture 0.25 |
| Colour bands of 150 px or more, in order | picture 729, white 693, tint #E1F2FF 507, white 765, offwhite #F0F7FF 480, picture 795, solid #133CD1 804, white 363, picture 257, offwhite #EFF5FF 625, white 908 |

Other measured values: 10 colour changes, 0 gradient bands, longest white run 908 px, longest off-white run 625 px; bands of 150 px or more: white 4, offwhite 2, tint 1, solid 1, dark 0, picture 3.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | One wide lifestyle photo with a centred headline, one line of support and one pill button over the lower part of the photo | photo | 515 / 64 (full-width photo, left out of the median) |
| 2 | categories | Product-family cards in a swipe row, each with a small uppercase label, an arrow and one line; a pale pill button under it to build a kit | white | 72 / 72 |
| 3 | benefits | Line icons with short uppercase reasons; the section heading itself is a household count | tint #E1F2FF | 72 / 72 |
| 4 | best-sellers | Product row (swipe) with badges, star rating and review count, price and strike price on each card; outline pill button under it | white | 72 / 72 |
| 5 | press | Small uppercase label, one short media quote as the heading, then a row of pale media and certification logos | off-white #F0F7FF | 112 / 261 |
| 6 | story | Full-width family photo with a white rounded card on the right: mission line, one sentence, outline button | photo | 275 / 280 (full-width photo) |
| 7 | reviews | Review carousel: one outlined card in the centre with stars, quote and the product name, the next and previous cards faded at the sides; the heading carries a review count | solid #133CD1 | 112 / 112 |
| 8 | how-it-works | Half-width product photo on the left, short heading, paragraph and outline button on the right | white (half photo) | 224 / 224 |
| 9 | ingredients | Certification and award badges in one row with names under each, and a text link to learn more (standards, not a recipe list) | off-white #EFF5FF | 112 / 112 |
| 10 | social | Left-aligned heading with a follow link and a row of square brand and customer photos | white | 112 / 542 |
| 11 | other | Closing call to action: one heading and one solid pill button to shop everything | photo (pale blue sky photo) | 72 / 72 |

`order: hero, categories, benefits, best-sellers, press, story, reviews, how-it-works, ingredients, social, other`

- Under the header (not counted) sits a pale strip of category text links, so the shopper can browse before the hero even starts.
- Measured data vs the picture: the closing sky photo (section 11) is not in the band list as a picture; the reader folded its top into the last white band (908) and read its foot as a short tint strip (#C7E7FD, 104 px). The 804 px solid band also runs a little into the top of section 8's sky photo; the blue fill itself ends sooner. Section 8 shows as "white 363, picture 257" because its photo touches only the left edge.
- The large bottom pads (261 in press, 542 in social) are logo and photo rows under the last text, not empty space.
- In the desktop capture the product pictures in section 4 are blank tiles (they did load on the phone capture).

## Colour pacing
- Bands of 150 px or more: 4 white, 2 off-white, 1 tint, 1 solid, 3 picture. One hue does every job: white ground, a near-white with a blue cast (#F0F7FF, #EFF5FF), one pale blue tint (#E1F2FF) and one strong blue (#133CD1), which is also the button, the announcement bar and the footer.
- The one strong band is the reviews section, 7th of 11, just after the story photo, so the loudest colour lands on customer proof in the middle of the page.
- No two neighbouring sections share a fill: white and blue-tinted grounds alternate (white, tint, white, off-white, photo, solid, white, off-white, white). Where white meets off-white the change is very soft; the colour step alone separates them, with no lines or dividers.
- Colour is carried by bands and photos, not by cards. Cards are white or pale grey-blue tiles inside the bands; the reviews card is only an outline on the solid blue.

## Type, buttons and spacing
- H1 48 px, every section heading 40 px (n 10, no variation), weight 500 for both (desktop-metrics.json). Headings are dark navy, a few are in the brand blue. Small bold uppercase labels sit above some headings and on category and benefit titles.
- Buttons are pills (9999px): solid blue (hero, closing call), outline blue on white (product row, story card, how-it-works) and a pale-blue filled pill (under the categories).
- Spacing: shopping strips (categories, benefits, product row, closing call) use 72 px top and bottom; the proof and story sections step up to 112 px; how-it-works has 224 px because its short text sits centred beside a tall photo. So browsing sections feel compact and the "read me" sections breathe. Desktop pad median 112 (p25 72, p75 140).

## Proof
- #3 benefits: the heading itself is a household count; one benefit line repeats the review count.
- #4 best-sellers: star rating and review count on every product card, plus "bestseller" and savings badges.
- #5 press: one media quote as a heading over a row of pale logos on off-white, high on the page, right after the products.
- #7 reviews: one customer quote at a time in a carousel on the solid band, heading with a review count.
- #9 ingredients: a row of certification badges with names, on off-white.
- Proof is spread over several sections rather than stacked in one block, and each type has its own look.

## Phone
- Same 11 sections in the same order; nothing is dropped.
- Hero uses a different, taller photo, with the headline, two lines and the pill button stacked over its lower part (H1 30 px).
- Categories, product cards, the press logos, reviews, the certification badges and the social photos all become swipe rows with the next card cut off at the edge as a hint. The benefits become a two-column grid.
- The story card drops below the photo's lower edge and overlaps it; how-it-works puts the photo on top and the text under it.
- Section headings 26 px (min 24). Pad median 64 (p25 64, p75 64, min 48, max 427, n 16): almost every section uses exactly 64 top and bottom, the closing call 48. The large values are photo and logo rows again.
- The closing call sits on plain white on the phone (the sky photo is a desktop-only background in this capture).

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- One brand blue in three strengths: white ground, a near-white with a blue cast for alternate sections, one pale tint, and one solid band. Keep the ground (white + off-white) near half the page or more (here 0.55), with tint 0.09 and solid 0.11.
- Exactly one solid band, on reviews or another proof section in the middle of the page (here 7th of 11). Green belongs in icons, badges and small accents, not in a second solid band.
- Two spacing steps on desktop: 72 px for browsing strips (categories, product row, closing call), 112 px for proof and story sections; on the phone one value, 64 px, everywhere.
- One heading size for every section (40 px desktop / 26 px phone) and one weight (500); H1 48 px desktop / 30 px phone.
- Pill buttons (9999px): solid brand blue for the main action, outline for secondary ones.
- Browse first: categories directly under the hero, then the product row, then proof; spread proof over several sections, each with its own format.

Avoid:
- Counts, review totals, media quotes or certification badges the client cannot prove: every figure and logo must come from the client's real records.
- A review carousel that shows one review at a time on desktop; it hides most of the proof.
- Product images that wait for a scroll to load: the desktop capture shows the product row as blank tiles.
- A sky or photo background behind the closing call that only some screens get; plain fills read the same everywhere.
