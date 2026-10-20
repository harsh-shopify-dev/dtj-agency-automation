# Ritual (supplements): home page study, 19 Oct 2026
Source: https://ritual.com/, captured 19 Oct 2026 at 1440 and 390 px (private capture). Harsh's rating in ratings.md: 86 ("yellow and navy only, airy, one idea per section"). Numbers: measured by `scripts/study_numbers.py` from the saved capture; "not measured" where the files do not hold it.

## Numbers
| Measure | Value |
|---|---|
| Sections measured (desktop / phone) | 17 / 18 |
| Page length px (desktop / phone) | 7621 / 6890 |
| Pad median, p25-p75 (desktop / phone) | 80, 48-141 (min 0, max 474, n 32) / 48, 30-102 (min 0, max 425, n 30) |
| H1 / hero heading px | H1 66 desktop, 40 phone / hero heading 48 desktop, 40 phone |
| Section headings px (median, min-max; desktop / phone) | 40, 16-40 / 32, 14-40 |
| Button (radius, colour) | 25px, rgb(20, 43, 111) |
| Body font | CircularXX |
| Colour share between header and footer | ground 0.90 (white 0.82 + offwhite 0.08), tint 0.0, solid 0.0, dark 0.0, picture 0.09 |
| Colour bands of 150 px or more, in order | offwhite #F5F7F8 544, white #FFFFFF 4788, picture 530, white #FFFFFF 545 |

Other measured values: 3 colour changes, 0 gradient bands, longest white run 4788 px, longest off-white run 544 px; bands of 150 px or more: white 2, offwhite 1, tint 0, solid 0, dark 0, picture 1.
Corrected 19 Oct 2026 after the reader fixes: an impossible phone gap (-872) is left out.

## Section order (read from the screenshots)
| # | Section | What it is for | Background | Pad desktop top/bottom |
|---|---|---|---|---|
| 1 | hero | Split: lifestyle photo with a free-gift sticker on the left; headline, one offer line and two navy pill buttons on a pale panel on the right | photo + off-white #F5F7F8 panel | 48 / 48 |
| 2 | other | New-range spotlight: pale yellow rounded card, heading, one line, outline button, photo on the right | white (yellow card inside) | 181 / 133 (text centred in the card) |
| 3 | best-sellers | Product row cut off at the right edge: yellow photo tiles, "best seller" / "new" tag, add button, name, one line, price with strike price; "shop all" text link by the heading | white | 48 / 24 |
| 4 | proof-numbers | Six line icons with one short fact each, two of them numbers | white | 144 / 48 |
| 5 | story | Science promise: square yellow product video on the left, heading, one line and two underlined text links on the right | white | 223 / 64 (text beside a square video) |
| 6 | ingredients | Traceable sourcing: heading, one line, two text links on the left, yellow world-map video on the right | white | 211 / 80 |
| 7 | categories | Heading only ("Find your...") | white | 64 / 0 |
| 8 | categories | Four photo cards on yellow (sets, pregnancy, multivitamin, relaxation) with a name under each, two with a tag | white | 353 / 64 (names under tall photos) |
| 9 | reviews | One quote at a time: stars, the quote, name and product, a slider bar | white | 80 / 92 |
| 10 | story | Heading and one line introducing the leadership | white | 48 / 0 |
| 11 | story | Four portraits with name, degree and job title | white | 445 / 112 (names under tall photos) |
| 12 | other | Community call: heading, one line, one navy button on a soft yellow glow | white (yellow glow, no edge) | 64 / 64 |
| 13 | social | Row of square brand and event videos running edge to edge | picture | 474 / 16 (the photo row itself) |
| 14 | categories | One centred line introducing the range | white | not measured |
| 15 | categories | Five round photos with a category name under each | white | 227 / 80 |
| 16 | newsletter | Heading, email field with a text button, social icons; the footer links follow in the same block | white | 80 / 67 |

`order: hero, other, best-sellers, proof-numbers, story, ingredients, categories, categories, reviews, story, story, other, social, categories, categories, newsletter`

- The reader splits heading and content into two sections three times (7-8, 10-11, 14-15). Measured section 17 is the footer's bottom bar (89 / 80) and is left out of the table.
- Measured data vs the picture: the page reads as yellow and navy, but the band reader finds no colour band at all, because every yellow sits inside a card, photo, map or glow that stops short of the 32 px side margins. "offwhite #F5F7F8 544" is the hero's right panel (the photo touches only the left edge). "picture 530" is the video row (section 13).
- The reader's footer starts at 6609, inside the newsletter block, so the newsletter is not in the colour share.

## Colour pacing
- Bands of 150 px or more: 2 white, 1 off-white, 1 picture, no tint, solid or dark band. One white ground runs 4788 px without a single colour change (sections 2 to 12).
- Two colours carry the whole page: navy #142B6F for every heading, body line, button and the announcement bar, and yellow for picture backgrounds (product tiles, category cards, the map, the science video, the glow behind the community call). Yellow shows up in nearly every section, never as a full-width band.
- Neighbours all share white; sections are told apart by white space and by alternating the photo side (5 left, 6 right). No lines or dividers between sections.

## Type, buttons and spacing
- Section headings 40 px at weight 450 (desktop-metrics.json); card names and people's names 18 px at 500 (they pull the min and p25 down to 16-18). Text is navy, never black. A few headings switch one word to an italic serif.
- Buttons: 25px radius, solid navy for the main actions (hero, community call), outline navy in the spotlight card, white "add" pills on the product tiles. Secondary actions are underlined text links (shop all, science, ingredients, impact report).
- Spacing: pad median 80 (p25 48, p75 141). Compact strips use 48-64 (hero 48 / 48, product row 48 top, community call 64 / 64); the large values (353, 445, 474) are names under tall photos and the video row, not empty space.

## Proof
- #1 hero: an offer line and a free-gift sticker (offer, not proof).
- #3 best-sellers: "best seller" and "new" tags and strike prices; no stars or review counts on the cards.
- #4 proof-numbers: six icon facts right after the product row: a units-sold count, a certification, traceability, research spending, who formulates, vegan.
- #6 traceable sourcing with links to an ingredient page and an impact report.
- #9 one customer quote at a time with stars, name and product. #11 named leaders with degrees and titles.
- No press logos, no review count, no guarantee section on the home page.

## Phone
- Same order; the phone adds a swipe strip of category pills under the header (first one highlighted in yellow). Page 6890 px, shorter than desktop.
- Hero: photo on top, headline (H1 40 px), offer line and the two buttons below on the pale panel. Split sections put the picture on top and the text under it.
- Product row, category cards, leadership portraits, videos and the round categories become swipe rows with the next card cut off. The six proof facts become a vertical list, one icon per line.
- Section headings 32 px (min 14, max 40). Pad median 48 (p25 30, p75 102, n 30); the -872 of an extra menu element is left out.

## For a multi-product Indian home-care store (blue and green, never yellow or brown)
Copy (as a rule):
- Two brand colours with fixed jobs: the dark one for all text and buttons, the accent only behind product and category photos and in cards. Ground stays white or near-white for nearly the whole page (here 0.90).
- A row of up to 6 icon facts directly after the first product row, each a short phrase, with a number only where the client has a real one.
- One idea per section: heading, one or two lines, one action (a button or up to two text links).
- One heading size and weight (here 40 px desktop / 32 px phone, weight 450); card names 18 px.
- Alternate the photo side in back-to-back split sections, so white neighbours still read as separate sections.
- Compact strips 48-64 px top and bottom; desktop pad median near 80, phone near 48.

Avoid:
- A review block that shows one quote at a time; it hides most of the proof.
- Three separate browsing blocks (phone pill strip, category cards, round category photos) on one page.
- Free-gift stickers and discount lines on the hero unless the offer is real, current and approved.
- Zero colour bands on a long page: here 4788 px of unbroken white works only because every section is short.
