# KittySpout (pets): home page study, 19 Oct 2026
Source: https://www.kittyspout.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 80 ("orange/cream rhythm, hero busy with sale text"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 9 / 9 |
| Page length px (desktop / phone) | 8659 / 9605 |
| Pad median, p25-p75 (desktop / phone) | 98, 63-292 (min 41, max 750, n 12) / 50, 32-314 (min 32, max 1228, n 8) |
| H1 / hero heading px | H1 63 desktop, 41 phone / hero heading 63 desktop, 41 phone |
| Section headings px (median, min-max; desktop / phone) | 42, 22-46 / 32, 22-32 |
| Button (radius, colour) | 500px, rgb(221, 153, 51) |
| Body font | Poppins |
| Colour share between header and footer | ground 0.65 (white 0.28 + offwhite 0.37), tint 0.22, solid 0.0, dark 0.0, picture 0.13 |
| Colour bands of 150 px or more, in order | picture 978, offwhite #F8FAFC 869, white #FFFFFF 807, offwhite #F8FAFC 1691, white #FFFFFF 976, offwhite #F5F0E8 310, white #FFFFFF 374, tint #F2E9D7 889, tint #E1E1E1 854 |

Other measured values: 8 colour changes, 1 gradient bands, longest white run 976 px, longest off-white run 1691 px; bands of 150 px or more: white 3, offwhite 3, tint 2, solid 0, dark 0, picture 1.
Corrected 19 Oct 2026 after the reader fixes: the review widget's impossible gaps (-5113 / -3642 desktop, -5501 / -3330 phone) are now left out.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Seasonal sale photo: review-platform rating line, a 4-line sale headline, one line of urgency, a solid and an outline pill button, an icon row, a vet quote card and slide dots | photo | 150 / 187 (full-width photo, left out of the median) |
| 2 | best-sellers | 4 product cards: photo with benefit icons printed down its side, sale badge, stars and review count, name, one line, strike price, green save pill, orange add-to-cart pill | off-white #F8FAFC | 502 / 96 |
| 3 | ugc | Heading, one line, then a swipe row of portrait customer videos with play buttons and a progress bar | white | not measured (no text read) |
| 4 | benefits | Two photo-and-text rows: a "why us" paragraph with check bullets, then a vet-health block citing a journal, with check bullets | off-white #F8FAFC | 105 / 73 |
| 5 | categories | Heading, one line, 4 round photos with pale pill labels and arrows | off-white #F8FAFC | 41 / 50 |
| 6 | benefits | Heading with a customer count, product cut-out in the centre, 3 round orange icons with a title and line on each side | white | 60 / 750 |
| 7 | reviews | Rating summary, topic filter tabs, then a 4-column wall of dated, named review cards with star rows and verified tags | cream #F5F0E8 (cards reach the edges) | -5113 / -3642 (broken, see below) |
| 8 | faq | Heading and one line on the left, accordion on the right with the first answer open, outline "view more" button | cream tint #F2E9D7 (vertical gradient) | 107 / 99 |
| 9 | newsletter | Closing photo: headline, one paragraph, orange pill button, then a white email card with customer avatars across the foot | photo (read as tint #E1E1E1) | 354 / 97 |

`order: hero, best-sellers, ugc, benefits, categories, benefits, reviews, faq, newsletter`

- Under the header (not counted) sits a thin white strip of 5 icon facts (customer count, money-back guarantee, vet backing, free shipping, quick cleaning).
- Measured data vs the picture: the reviews widget holds hidden text far outside its box, so section 7 reads -5113 / -3642 desktop and -5501 / -3330 phone. study_numbers.py now leaves these impossible values out (see the table).
- The closing photo (section 9) has a flat grey wall at both edges, so it reads as tint #E1E1E1 854; the true tint share is below 0.22 and the picture share above 0.13. The 750 bottom pad in section 6 is the product photo and icon columns under the heading, not empty space.
- The section-heading minimum of 22 px is a review card title, not a section heading; the reviews heading itself is not measured.

## Colour pacing
- Bands of 150 px or more: 3 white, 3 off-white, 2 tint, 0 solid, 0 dark, 1 picture. The ground alternates white with a cool near-white (#F8FAFC) for the first half, then warms to cream (#F5F0E8, #F2E9D7) for reviews and FAQ.
- No solid band between header and footer. The brand orange (#DD9933) does the work in small pieces: every button, the small uppercase labels, the round icons, the category rings, and then the whole footer as the one big orange block.
- Green is a second accent only for money: sale badges, sale prices and the save pills on product cards.
- Sections 4 and 5 share one off-white fill (one 1691 px run); elsewhere neighbours change fill, softly, with no lines.

## Type, buttons and spacing
- H1 63 px (weight 600) is far larger than the section headings (32 to 46 px, weight 700; desktop-metrics.json): the sale headline dominates the first screen. Headings are bold black, with one orange word in the reviews heading.
- Buttons are pills (500px), solid orange with dark text for every buy action; outline pills for the second hero button and the FAQ "view more".
- Spacing: section 5 is tight (41 / 50), the text sections 4 and 8 use 105 and 107 on top and 73 and 99 below. Desktop pad median 98 (p25 63, p75 292), the broken review values left out.

## Proof
- Header strip and #1 hero: a review-platform rating with count above the headline, a named vet quote card with credentials, an icon row.
- #2 best-sellers: stars with review count on every card, sale badges, strike prices and save amounts.
- #3 ugc: customer videos high on the page, straight after the products.
- #4 benefits: an owner survey percentage and a cited journal for the health claim.
- #7 reviews: a rating summary with count, filter tabs by topic, a wall of dated, named, verified cards.
- The same customer count appears 6 times (strip, section 4 label, section 6 heading, reviews heading, closing headline, signup card), and the hero and reviews show two different review totals.

## Phone
- Same 9 sections in the same order; the phone page is longer (9605 against 8659).
- Hero: centred H1 41 px, only the solid pill button (the outline one is dropped), 3 icons, the vet card under the photo. The header strip becomes a sideways strip cut at the edges.
- Product cards and videos become swipe rows with one card or video and the next one peeking; benefits stack photo over text; categories become a 2 x 2 grid; section 6 puts the icons in two columns above the product photo.
- Reviews become one column with a topic drop-down; the FAQ heading moves above the accordion; the closing section puts text and button first, photo next, signup card last.
- Section headings 32 px (p25 26). Pad median 50 (p25 32, p75 314), the broken review values left out.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- A thin strip under the header with short icon facts the client can prove (here 5: guarantee, delivery, backing and the like).
- Product cards with stars and review count, strike price and a save amount in a small green pill, separate from the one solid brand-blue buy button.
- Pill buttons (500px here): one solid colour for every buy action, outline for "view more" type links.
- A review wall with topic filters (for home care: cleaning, smell, delivery, value) after the benefits, then the FAQ as an accordion with the first answer open.
- Put the source next to any health or safety claim (a lab report or certificate, named), as section 4 does with its journal.
- Ground near two thirds of the page (here 0.65): white alternating with a cool near-white such as #F8FAFC, no solid band in the body.

Avoid:
- A hero carrying a long sale headline, two buttons, an icon row, a rating line and a quote card at once.
- The same customer count six times on one page, and two different review totals.
- Benefit icons printed inside every product photo: the cards look alike and the text is too small to read.
- Two separate benefit sections; merge them into one.
- Review widgets that load hidden text off-screen; they break the page's own spacing and any measurement of it.
