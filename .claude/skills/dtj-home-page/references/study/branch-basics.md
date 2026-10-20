# Branch Basics (home care): home page study, 19 Oct 2026
Source: https://branchbasics.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 88 ("warm cream/earth palette, press logos right under the hero"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 7 / 7 (the press strip under the hero is not in the spacing files) |
| Page length px (desktop / phone) | 5595 / 6171 |
| Pad median, p25-p75 (desktop / phone) | 106, 59-147 (min 50, max 276, n 10) / 44, 36-65 (min 25, max 77, n 6) |
| H1 / hero heading px | H1 52 desktop, 40 phone / hero heading 42 desktop, 29 phone |
| Section headings px (median, min-max; desktop / phone) | 32, 32-44 (n 5) / 32, 22-32 (n 5) |
| Button (radius, colour) | 2px (square), rgb(221, 238, 157) (#DDEE9D, pale lime) |
| Body font | TT Norms |
| Colour share between header and footer | ground 0.88 (white 0.88 + offwhite 0.0), tint 0.0, solid 0.0, dark 0.0, picture 0.12 |
| Colour bands of 150 px or more, in order | white 1614, picture 578, white #FDFAF4 2741 |

Other measured values: 2 colour changes, 0 gradient bands, longest white run 2741 px, longest off-white run 0 px; bands of 150 px or more: white 2, offwhite 0, tint 0, solid 0, dark 0, picture 1.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Wide warm studio photo of the range; on the left a small uppercase "from" price line, a light serif headline, one line of support and one square lime button | photo | 197 / 166 (full-width photo, left out of the median) |
| 2 | press | A tiny "featured in" label and five media logos in one row | white | not measured (strip not in the spacing file; 70 px tall in desktop-metrics.json) |
| 3 | best-sellers | Kit row with three pill tabs (kits, refills, accessories), a shop-all link and arrows; four cards with chip badges, small uppercase label, name, two-line description and price | cream #FDFAF4 | 60 / 94 |
| 4 | ugc | Shoppable video row: creator clips and one TV segment, the centre clip larger and playing, each with a small product card and an add-to-cart pill | cream (videos touch both edges) | not measured (the file found no text in it) |
| 5 | how-it-works | Heading and a numbered step card (01, next) on the left explaining the one concentrate and its uses; a large photo on the right with numbered points 01-07 | cream (half photo) | 110 / 276 |
| 6 | reviews | Heading and arrows; two review cards in view, each a customer photo, five stars, a review title and a long quote; dots underneath | cream | 50 / 102 |
| 7 | story | Rounded founders' photo on the left; three text tabs on the right (story, blog, a cause page) with a founders' quote, signatures and a beige button | cream | 56 / 139 |
| 8 | press | One media quote in a carousel with arrows, five pale media logos under it | cream | 128 / 172 |

`order: hero, press, best-sellers, ugc, how-it-works, reviews, story, press`

- Under the header (not counted) sits a second row of category text links, so browsing starts before the hero.
- Measured data vs the picture: the first band, "white 1614", is not white. It runs from the header through the hero photo, the white press strip and the cream product row; the hero's smooth brown wall reads as flat at the page edge and was chained into the band. So the hero is not counted as picture; the only picture band (578) is the video row.
- The cream ground #FDFAF4 is classed as white (it passes the white test), so the share reads white 0.88 although almost every section is cream on screen; only the header and the press strip are pure white.
- The large bottom pads (276 in how-it-works, 172 in the closing press block) are the photo and the logo row under the last text, not empty space.
- desktop-metrics.json gives an H1 of 52 px but does not name it; the visible hero headline is 42 px. By eye the largest heading is section 5's.

## Colour pacing
- Bands of 150 px or more: 2 white-class (really white plus cream), 1 picture; 2 colour changes in the whole page. From the product row to the footer it is one cream ground: the longest run is 2741 px, and no section has a fill of its own.
- Colour comes from photos (warm beige studio shots, bright creator videos), small peach and beige chip badges, the pale lime button, and the brown footer #9A6A47 (outside the measured area). The add-to-cart pills in the video row are brown on desktop.
- Sections are separated only by space and photos, with no lines or fill changes. It reads calm, but in the long cream run the reviews, story and closing press blocks run into each other.

## Type, buttons and spacing
- Headings are a light serif at weight 300 (desktop-metrics.json), dark brown-black; section headings 32-44 px (median 32). Body text is a plain sans (TT Norms). Small bold uppercase labels sit over product names and on the story tabs.
- Buttons: the main one is a square (2px) pale-lime fill with a dark outline and dark text. Others: pill-shaped outline tabs (the active one filled beige), brown add-to-cart pills in the video row, a square beige "learn more".
- Spacing is uneven: desktop pad median 106 (p25 59, p75 147), from 50 above the reviews heading to 128 above the closing quote. The product row is tight (60 / 94); story and press get more room.

## Proof
- #2 press: five media logos directly under the hero, the first thing after it.
- #3 best-sellers: chip badges on cards ("top rated", "most loved", material), but no stars or review counts on the product cards.
- #4 ugc: creator clips and a TV segment, each tied to a product with price and add to cart.
- #6 reviews: long written reviews with five stars and a customer photo, two at a time, seven pages of dots.
- #7 story: the founders' photo, quote and signatures.
- #8 press: a rotating media quote plus five logos; one outlet appears in both logo strips. Press opens and closes the page.

## Phone
- Same sections in the same order; nothing is dropped. Page 6171 px against 5595 on desktop.
- In the phone capture an email pop-up with a shipping offer covers the hero and the press strip, so the first phone screen shows the pop-up, not the hero.
- Under the logo bar: three outlined category buttons. The product row and the video row become swipe rows with the next card cut at the edge; the product row gets a full-width outline "shop all" button under it.
- How-it-works puts the photo first and the step card under it; reviews show one card with a large customer photo on top; the story tabs become an accordion with the first one open; the closing press block shows the quote and three logos.
- Section headings 32 px (min 22); H1 40, hero heading 29. Pad median 44 (p25 36, p75 65, min 25, max 77, n 6); the how-it-works and story photos run full width on the phone and are left out.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- A short logo strip right under the hero (one row, a small label, up to five logos; here 70 px tall), only with press or certifications the client really has.
- One product row with type tabs (for example kits, refills, accessories) so a single block serves the whole range; price and a two-line description on every card.
- One how-it-works section that shows how the products fit together, with numbered steps tied to a product photo.
- A shoppable video row: every clip linked to its product with price and add to cart; real customer or creator clips only.
- Proof at the top and at the end of the page, each block in its own format.

Avoid:
- One ground colour for the whole page (here a 2741 px cream run): in blue and green, step to a pale tint between proof sections so they do not blur.
- An email or offer pop-up over the first phone screen.
- The same media logo in two strips; use each logo once.
- Product cards without any rating when the client has real reviews.
- Cream, brown and lime accents: they pull the page towards the yellow and brown we never use.
