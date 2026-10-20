# Grubbly Farms (pets): home page study, 19 Oct 2026
Source: https://grubblyfarms.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 86 ("four soft colours in a fixed rhythm, playful but tidy"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 12 / 12 |
| Page length px (desktop / phone) | 8907 / 10891 |
| Pad median, p25-p75 (desktop / phone) | 102, 60-124 (min 60, max 220, n 24) / 66, 45-86 (min 36, max 93, n 16) |
| H1 / hero heading px | desktop 60 / 60; phone 40 / 40 |
| Section headings px (median, min-max; desktop / phone) | 54, 54-60 (n 11) / 35, 35-44 (n 11) |
| Button (radius, colour) | 4px, rgb(30, 226, 113) |
| Body font | Centra |
| Colour share between header and footer | ground 0.72 (white 0.72 + offwhite 0.0), tint 0.19, solid 0.0, dark 0.0, picture 0.09 |
| Colour bands of 150 px or more, in order | picture 596, white #FFFBF3 908, tint #8CD1FF 592, white #FFFFFF 2304, tint #8CD1FF 571, tint #FFBF99 395, white #FFFFFF 1001, white #FFFFFF 1696 |

Also measured: 6 colour changes, longest ground run 2304 px (white), 0 gradient bands; bands of 150 px or more: white 4, tint 3, picture 1.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Product bag and birds in a full-width photo; short headline and one button in a see-through card on the left | photo | 220 / 220 |
| 2 | best-sellers | Product carousel with three category tabs above it, so browsing and buying sit in one block right under the hero | white #FFFBF3 (looks cream on screen) | 60 / 100 |
| 3 | ingredients | What the core ingredient is and what the food leaves out, text left, photo with two round badges right | tint #8CD1FF | 149 / 60 |
| 4 | compare | Us-vs-them table, ticks against crosses, against generic store brands | white | 105 / 99 |
| 5 | benefits | Three icon cards (pale green) with a rounded photo beside them, one button | off-white (cream) | 60 / 60 |
| 6 | bundle | Build-a-bundle panel: a rounded light-blue card with dashed product slots and one button | white (blue card inside) | 176 / 176 |
| 7 | story | Mission and impact told as three icon steps joined by arrows | tint #8CD1FF | 86 / 96 |
| 8 | offer | Subscribe-and-save: four icon reasons in a hand-drawn peach shape, one button | tint #FFBF99 (blob on white) | 124 / 124 |
| 9 | reviews | Stars and a big customer count on the left, three pale-green quote cards with customer photos on the right | off-white (cream) | 60 / 88 |
| 10 | story | Founders' photo and a short origin paragraph, in a white wavy-edged shape | off-white (cream), white shape inside | 124 / 124 |
| 11 | other | Help block: chat, email and help-centre buttons in a light-blue card | white (blue card inside) | 108 / 108 |
| 12 | best-sellers | A second, wider product carousel with stars, review counts and a bundle price tag | off-white (cream) | 60 / 60 |

`order: hero, best-sellers, ingredients, compare, benefits, bundle, story, offer, reviews, story, other, best-sellers`

Against the measured bands:
- The reader classes the cream sections (5, 9, 10, 12) as white: its "white #FFFFFF 2304" run covers sections 4 to 6 and its last two white runs cover sections 9 to 12, although sections 5, 9 and 12 show a faint cream that alternates with pure white on screen.
- The peach offer (section 8) is an irregular shape, not a straight band: the reader counts 395 px of tint plus two picture strips (69 and 54 px in all_bands), while the shape fills most of the 742 px section.

## Colour pacing
- Bands: 4 white-class bands, 3 tint bands, 0 solid, 0 dark (counts of 150 px or more). There is no single strong band; the loudest colour is the light blue #8CD1FF, used twice (sections 3 and 7) with three quieter sections between the two uses. The peach #FFBF99 offer shape is the only other full-width colour.
- No two colour bands touch. Where two quiet sections touch (4 white, 5 cream, 6 white; 9 cream, 10 cream), the page separates them with a faint cream-to-white step, a rounded card, or a wavy white shape laid over the cream.
- Most colour lives in cards, not bands: pale green benefit and review cards, a lilac comparison table, a light-blue bundle card and a light-blue help card. That is how the page reads as colourful while 0.72 of it is ground.

## Type, buttons and spacing
- Headings: one condensed serif at weight 400 everywhere (desktop-metrics.json), section headings almost all 54 px, the H1 and the bundle heading 60 px. Body text is the sans-serif Centra. Small labels (benefit names, step names) are bold uppercase sans.
- Buttons: square-ish (radius 4px). The measured colour rgb(30, 226, 113) is the hero's bright green button; most section buttons on screen are near-black with white uppercase text, and the help block uses green buttons.
- Spacing: generous around single-message sections (hero 220 / 220, bundle 176 / 176, offer and founder story 124 / 124, help 108 / 108). Tighter where the content is dense: product rows and benefit cards sit at 60, the reviews top at 60. Median 102 puts it in the "clean" group of ratings.md.

## Proof
- Section 2 (first content section): star rows and review counts under every product card.
- Section 3: two round badges on the photo carry short product claims.
- Section 4: comparison table, ticks versus crosses.
- Section 9: the main review block, five stars over a big customer count, then three quote cards with a customer photo and first name each.
- Section 10: founders' photo as a trust signal.
- Section 12: stars and review counts again on the second carousel.
- No press logos and no separate stat band.

## Phone
- Same 12 sections in the same order; page grows from 8907 to 10891 px.
- H1 drops from 60 to 40 px; section headings to 35 px (reviews 44, bundle 40, from phone-spacing.json).
- A row of plain-text category links appears under the phone header (not on desktop).
- The hero photo is cropped to the birds and the product bag drops out of view; the headline card and button stay centred over the photo.
- Two-column sections stack: in the ingredients and benefits sections the photo goes first or between heading and text (benefits top gap 432 because the photo sits above the heading); founder photo moves under the heading.
- Carousels show one card plus a peek of the next (products, reviews). Offer icons go to a 2 x 2 grid. Help buttons go full width.
- Pad on phone (full-width photo sections left out): median 66, p25-p75 45-86. Per section: products 45 / 45, compare 74 / 62, bundle 93 / 85, impact steps 36 / 60, offer 93 / 93, reviews 87 / 45, help 69 / 69, last product row 45 / 45.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- Pad: aim for a desktop median near 102 px (p25-p75 60-124) and a phone median near 66 px; give single-message sections 120-220 px and keep dense product or card rows near 60 px.
- Use one soft tint for full-width bands and repeat it at most twice, with at least two quiet sections between the repeats (here sections 3 and 7).
- Keep about 0.72 of the page as ground and put the second colour into cards (benefit, review, help) rather than into more bands.
- Put category tabs on the first product row, directly under the hero, so the shopper can browse and buy in one section.
- One heading family at one weight; section headings at one size (54 px here) with the H1 only one step larger (60 px).
- Phone: drop headings to about two thirds (60 to 40, 54 to 35) and keep the same section order.

Avoid:
- A second product carousel near the end that repeats the first one; one product row plus categories is enough.
- A hero photo whose product disappears when cropped for phone; check the phone crop keeps the product.
- Hand-drawn blob shapes for the offer band: they are hard to build cleanly and read as a loose edge next to straight bands.
- Cream and white sections so close in colour that they read as one run; either make the step visible or use one ground.
- Extra card colours outside the palette (here lilac and peach); for our palette keep cards to a pale blue and a pale green.
