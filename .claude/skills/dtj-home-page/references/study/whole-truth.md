# The Whole Truth (food, India): home page study, 19 Oct 2026
Source: https://thewholetruthfoods.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 74 ("strong personality, very airy, products sit far down"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 1 / 1 |
| Page length px (desktop / phone) | 7729 / 8405 |
| Pad median, p25-p75 (desktop / phone) | 152, 50-254 (min 50, max 254, n 2) / 129, 48-210 (min 48, max 210, n 2) |
| H1 / hero heading px | H1 90 desktop, 65 phone / hero heading 90 desktop, 65 phone |
| Section headings px (median, min-max; desktop / phone) | not measured / not measured |
| Button (radius, colour) | not measured, not measured |
| Body font | obviously |
| Colour share between header and footer | ground 1.00 (white 1.0 + offwhite 0.0), tint 0.0, solid 0.0, dark 0.0, picture 0.0 |
| Colour bands of 150 px or more, in order | white #FFFFFF 6846 |

Other measured values: 0 colour changes, 0 gradient bands, longest white run 6846 px, longest off-white run 0 px; bands of 150 px or more: white 1, offwhite 0, tint 0, solid 0, dark 0, picture 0.
Corrected 19 Oct 2026 after the reader fixes: the quartiles of its two values are kept inside the data.

The pad numbers come from ONE measured block: its top gap (50 desktop / 48 phone, block top to the hero heading) and its bottom gap (254 / 210, last text to the end of the block; on desktop the last text is the press cards and the media-logo row fills most of that gap). They say nothing about the space between sections, which is not measured. With only two values the quartiles say nothing (they are now kept inside the data); do not use them. Ratings.md's "152 / 129" for this brand is the same single measurement.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Very large heading with one underlined phrase, a one-line "who we are" in a mono font, a hand-lettered outline button to the brand story, an illustrated product bar on the right | white | not measured (block top gap 50) |
| 2 | categories | Large heading and two mono lines on the left, a swipe row of three range cards (pack photo over a coloured label bar) with arrows | white | not measured |
| 3 | story | Heading with a hand-written aside, mono paragraph, a swipe row of tall people videos | white | not measured |
| 4 | editorial | Heading and mono paragraph, three cards for the brand's newsletter, course and ingredient dictionary (with a search box) | white | not measured |
| 5 | other | One-range spotlight: violet rounded banner with heading, age line, pack photo and a white pill button | white (violet banner inside) | not measured |
| 6 | ingredients | Where it is made: large heading and mono lines on the left, a pale pink card with a factory video tour and two tabs on the right, a certified-facility note; a hand-drawn video button under it | white (pink card inside) | not measured |
| 7 | reviews | Heading with a like-counter badge, four outlined review cards (quote, photo, name, job title), a hand-drawn heart icon and a button to all reviews | white | not measured |
| 8 | reviews | Famous fans: hand-lettered title, a swipe row of round portraits with names | white | not measured |
| 9 | social | Community call: heading, three outline buttons (Instagram, YouTube, LinkedIn), one customer photo | white | not measured |
| 10 | press | Hand-lettered title, swipe row of press article cards (source, read time), then a scrolling row of media logos | white | not measured (block bottom gap 254 ends here, logo row included) |
| 11 | other | Payment strip: card, wallet and UPI logos and a cash-on-delivery note | white | not measured (outside the measured block) |

`order: hero, categories, story, editorial, other, ingredients, reviews, reviews, social, press, other`

- Section 11 lies outside the measured block (the block's last text is the press cards), but shows as a white strip above the dark footer, so it is listed.
- There is no product row with prices anywhere on the home page: the only shopping blocks are the range cards (2) and the one-range spotlight (5).
- The like counter on section 7 shows different values in the two captures (it animates while the page loads).

## Colour pacing
- Measured and visible: one white ground from the header to the footer (6846 px, 0 colour changes). The only dark areas are the black announcement strip and the dark footer.
- Colour sits only in small inset pieces: the three range cards' label bars (plum, violet, green), the violet spotlight banner, the pale pink factory card, plum outlines on review cards and buttons, pink and yellow press cards. One plum accent repeats in every section (underline, hand-lettering, outlines).
- Sections are told apart only by large white gaps and very large headings; no band, line or tint between them.

## Type, buttons and spacing
- H1 90 px desktop (weight 600 in desktop-metrics.json); every section opens with a heading in the same heavy condensed face, which on screen looks close to the H1 size (not measured). Three faces work together: heavy condensed headings, a typewriter-style mono for body lines, and a hand-lettered script for buttons, asides and two section titles.
- Buttons (not measured): outline pills in plum with hand-lettered text; a white pill inside the violet banner; round arrow buttons on cards and carousels.
- Spacing: not measured between sections. On screen the gaps between sections are large (ratings.md: "very airy"), and the first product price never appears on the page.

## Proof
- #2: the range intro promises a declared-ingredient label. #4: a reader count on the newsletter card.
- #6: a factory video tour and a certified-facility note, plus a video on one ingredient: proof by showing how it is made.
- #7: like counter, four review cards with the customer's photo, name and job, and a link to all reviews. #8: famous fans with a note that they were not paid.
- #10: press article cards with links, then a row of Indian media logos. #11: payment logos with cash on delivery, a trust signal for Indian shoppers.
- No stars, review counts, prices, guarantee or FAQ on the home page.

## Phone
- Same 11 sections in the same order; page 8405 px. The hero heading (65 px) runs over five lines; the mono line and button follow under it.
- A bottom tab bar (home, shop, search, reorder, kids' range) is fixed to the screen; the capture draws it once, part-way down the page.
- Range cards, people videos, journalism cards, the spotlight (now a two-slide carousel), review cards, famous fans and press cards become swipe rows with the next card cut off. The factory card moves under its heading. The journalism section gains a hand-drawn diagram that the desktop does not show.
- Pad (one block): 48 top, 210 bottom; median 129 from those two values only.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- A one-line "who we are" under the hero heading, with a link to the brand story.
- A "how and where it is made" section (factory photos or video, real certification names only), one section on its own, not mixed with product cards.
- Review cards with the customer's real photo, name and occupation, and a link to all reviews.
- A payment strip right above the footer: UPI, cards, wallets and cash on delivery, for Indian shoppers.
- Press: link each logo or card to the real article; Indian media the client was actually featured in.
- One accent colour for outlines, underlines and small notes on a pure white ground (here white 1.0); keep the dark colour for text and the footer.

Avoid:
- A home page with no product row and no prices: shoppers must open a range card before they see a single price.
- Celebrity portrait rows unless the client has written permission and the endorsement is real.
- Counters that animate on load: the value differs between the two captures, so a shopper may read a half-counted number.
- Three type faces (condensed, mono, hand-lettered) on a store whose buyers need to read fast; one family plus one accent is enough.
- Section gaps so large that the first product sits far down (ratings.md verdict).
