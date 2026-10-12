# Design principles from Harsh's reviews (why the changes made the page better)

Source: Harsh's review of Go Mints v2 on the Test Store (10 Oct 2026, 11 points over two rounds), applied as v3/v4. Every
principle below is general: it is written for any brand and category, with Go Mints as the measured example. Read this in
P4 (design each section) and check it in P6 with `../../dtj-pdp-design-review/scripts/design_checks.py`.

**Honesty note.** "Better" here means better on measured design criteria (contrast, separation, density, consistency) and on
established CRO practice. No conversion data exists yet for either version; only a test with real traffic can show a lift.

## The measured difference (same product, same facts, same pictures)

| | v2 (first live draft) | v4 (after Harsh's review) | Source |
|---|---|---|---|
| Harsh's design checks passed | 2 of 9 | 9 of 9 | `design_checks.py run/template.json --compare <v2 backup>` |
| Cards against their section | review and number cards 1.34:1 (navy on navy) | 14.71:1 (white on navy, navy on white) | H01 |
| Story card text | 23-word paragraph, points up to 38 characters | 9 words, points up to 24 characters | H05 |
| Buy-box points | 2 of 4 are doses ("Natural caffeine 50 mg") | 4 benefits ("Fast-acting energy") | H06 |
| Button labels | 11 buttons, 1 label | 11 buttons, 11 labels (+ the buy button) | H04, page audit |
| Closing banner picture | cropped to 4:5 (pack text cut at both edges) | the picture's own 1:1 shape | H07 |
| Dark sections | 4 (photos, reviews, numbers, final) | 2 (reviews, final) | H08 |
| Words on the brand colour | FAQ answers black on cyan (fine), white on cyan asked = 2.19:1 | white on navy boxes, 14.71:1 | H02, page |
| Text closer than 12 px to the screen edge | review heading at 1.6 px | none | `page_audit.js` |
| Desktop colour balance | white 28%, dark 13%, vivid 37%, energy fit 100 | white 30%, dark 15%, vivid 35%, fit 100 | `palette_report.py` |
| Review rubric (new weights) | 62/100 (the old rubric gave 76) | 75/100 | `calibration-log.md` |

The last-but-one row is the key insight: the page kept **the same amount of navy and the same energy**. Harsh's changes did not
remove colour, they **moved the dark from the ground to the figures**: whole navy sections became navy cards and boxes on light
sections. The page reads lighter and more organised without losing its vibe.

## The principles

### 1. Dark is for figures, light is for ground
A dark section behind dark-ish cards (1.34:1) is a smudge: nothing stands out and the page feels heavy. Put content that brings
its own colour (photos, number cards) on white; use the ink colour as a card or box ON a light section, or as a section whose
cards are WHITE. At most 2 dark sections per page (lint L05, H08), the closing banner counted.
Apply anywhere: a calm skincare page has one deep-tone band at most; its cards are white on a soft tint.

### 2. Every card is clearly a card (figure and ground)
A card must either contrast with its section (3:1 or more) or be the same colour with an outline. Between 1.05 and 1.5 it reads
as a mistake (H01). Words inside a card read on the card, at 4.5:1 (H02), which is why a block needs its own card text colour
when light cards sit on a dark band (`testimonials-slider.card_text_color`).

### 3. Icons stand apart from their words
An icon in the same colour as its title, on a coloured band, blends into the text and stops doing its job (scanning). Give it a
contrasting badge (white circle on a band, brand-colour circle on white; `feature-showcase.icon_bg`) or a contrasting colour
(white ticks on the brand band). Decoration that would vanish (white on yellow) keeps the word colour (H03).

### 4. White text only where white reads
When the brief or the client asks for white text on a bright brand colour (white on Go Mints cyan = 2.19:1), change the BOX, not
the rule: put the words on an ink card (Harsh's choice, 10 Oct 2026). Never trade contrast for a colour wish.

### 5. Say it short: one glance per card
On a phone, a story card sits under a full-width picture: a 23-word paragraph plus four long points is a wall. One sentence of at
most 20 words and four points of at most 32 characters (lint L17, H05). The detail lives in the FAQ and the proof sections.

### 6. The buy box sells outcomes, the proof sections hold the specs
The buy box answers "what do I get?" in the shopper's words ("Fast-acting energy", "Fits in your pocket"). Doses, measures and
ingredient names are proof: they belong in the ingredients, science and numbers sections (lint L18, H06). Write each point as a
result the shopper feels or a problem that goes away.

### 7. Every button continues its section
Eleven identical "Get my pack" buttons read as one repeated ad and stop being noticed. One action everywhere, but each label
finishes its section's thought: "Make the switch" after "What people say after the switch", "Feel it in 4 minutes" after the
numbers, "Try it risk-free" after the guarantee (lint L16, H04). Rules: 2-5 words, verb first, buying intent, the brand's main
label on the last button.

### 8. Pictures keep their own shape
A crop that cuts a pack's printed claims looks broken and hides the product. Single pictures use the block's adapt option
(H07). Card rows need one shape per row: ask for that shape in the graphics brief (reels 9:16, stories 1:1, a wide banner with
calm space in the middle and no printed text).

### 9. Side space for every word
Nothing touches the screen edge: at least 12 px everywhere (lint L02). A block without a side-space setting can still break it,
so the review measures it on the real page (`page_audit.js` `text_near_edge`).

### 10. One colour must not do every job (H10)
Hope N Skin, 10 Oct 2026: a peach card with orange-brown accent words, orange-brown ticks and an orange button: "everything is
orangish". Go Mints had the same failure in navy and cyan. Every coloured surface needs a detail that is NOT its colour: white
accent words and white tick circles with the check in the card colour (Harsh's fix), white icon badges, an accent colour from
another family (Go Mints' volt). When white words must sit on the card, deepen the card until white reads (3:1 for large words)
while the body text still reads at 4.5:1 (`direction.py` role `panel`), but only for colours that stay themselves when
deepened (blue, green, red, purple): a bright orange or yellow turns brown (principle 11). Checked by `design_checks.py` H10 on
every build and every re-verification.

### 11. A bright warm colour is a fill, never a deep surface (H11)
White words need 4.5:1. Orange #FF8C11 reaches that only at #B2620C, lightness 37 % instead of 53 %, and at that point it is
brown; as a dark band (#402305) it is brown at once. Blue keeps its character when deepened (navy), orange, amber and yellow do
not. Use a bright warm brand colour where it stays bright: as a FILL with dark words (the button, 7.5:1), as small marks (the
check inside a tick, a star tile deepened only to 3:1 for its white star, #D4750E). The builder does this by itself for any
brand colour with hue 15-65°, saturation ≥ 70 % and lightness ≥ 45 % (`direction._turns_brown`: light cards, the ink as the dark
band); `card_tone: "brand"` forces the deep card if a client insists.

### 12. On a light, calm page the cards whisper
Hope N Skin went #767676 → #E5E9EA → #F6F6F6 → #FAFAFA before Harsh said "looks cool". For a calm or clinical page the card is
almost white (lightness ≥ 96 %, 1.04-1.08:1 from white) with dark words; the picture, the round corners and the content give the
card its edge, not a colour. Warm meets cool badly: a cool grey (#E5E9EA, hue 192°) on a warm cream band (#F6EFE7) looked dirty;
a near-white without a visible hue sits on any band. The closing banner follows the same card colour (role `banner`).

### 13. A named reference is a brand until shown otherwise: measure it first
"Grey like minimalist" meant the Minimalist skincare BRAND; a generic mid grey (#767676) with white words was the wrong reading.
When Harsh or a client names a brand, a site or a page as the reference, open it and measure its computed colours before
choosing (beminimalist.co: white page, black words and buttons, #F6F6F6 boxes, #E5E9EA photo backdrop, orange only as a hairline
on the label). Earlier wishes belong to their context: "keep every text white" was about a dark card; when the card turned
light the words had to turn dark. Contrast decides the text colour; say so when an old wish can no longer hold.

### 14. Change a role, then sweep the page
A colour change is page-wide. The dark brown closing banner stayed through 10 card-colour pushes because it used a different
role (`dark`) than the cards (`panel`), and nobody listed it. After any colour change, read the `palette` inventory that
`design_checks.py` prints (every area colour and the sections using it): an old colour still listed is a section the change
missed. Change the role in `direction.py`, never one section by hand.

## What the old review missed, and why
The v2 review scored 76/100 with "Calls to action 10/10" (one label was then a RULE) and "Vibe 14/15" (the palette numbers were
right). It never looked at figure and ground, icon separation, story length, buy-box framing, cropping or edge space. Those are
now checks (H01-H11), rubric lines and lint rules, so the next page is caught before Harsh has to point at it.

## Colour palette: what did not work on Hope N Skin, and what fixed it (10 Oct 2026)
Brand orange #FF8C11 on a calm "fresh" skincare page; 11 pushes to the draft, measured from the backups in
`.work/clients/test-store-hopenskin-vitc/run/backup-*` with `design_checks.py`.

| Push | Story card | Words on it | Harsh | What was wrong (measured) |
|---|---|---|---|---|
| 1 | peach #FFB567 | dark, burnt-orange accent #794308 | "everything is orangish" | one hue (31°) on card, words, ticks and buttons (H10) |
| 2 | orange deepened #DB780F | white accent words and ticks, dark body | "keep every text white" | white only 3.13:1 on it, so the paragraph had to stay dark |
| 3 | deepened to #B2620C | all white (4.52:1) | "that dark brown" | lightness 53 % → 37 %: the orange became brown (H11) |
| 4 | grey #767676 | all white | "grey like minimalist -- minimalist brand" | "minimalist" read as a style; he meant the brand (principle 13) |
| 5 | Minimalist photo grey #E5E9EA | dark | "doesn't look good" | cool grey on the warm cream band, heavy (principle 12) |
| 6 | Minimalist box grey #F6F6F6 | dark | "more lighter" | still too visible next to white |
| 7 | #FAFAFA | dark words, dark tick circles, orange check | "looks cool" | none: 11 of 11 checks |
| all | closing banner #402305, brown in pushes 1-7 | white | "this section didnt got updated" | another role, never swept (principle 14) |
| last | review star tiles ink #1A1A1A, peach stars | | "star square blocks orange and stars white" | white star on #FF8C11 is 2.33:1: tile #D4750E (3.31:1) |

H11 (no brown) fails all 9 earlier serum pushes and passes the final page, Go Mints and the book page. The final page: white
and cream sections, near-white cards, dark words, orange only as buttons, check marks and star tiles.
