# Colour and vibe: choosing a palette the way a senior designer would

The first Go Mints page was correct and still failed: an energy mint dressed in white and the palest tint of its cyan reads as a
pharmacy leaflet. The colours were legal (contrast passed); the VIBE was wrong. This file is the procedure that prevents that.
The measurable side lives in the review skill: `../../dtj-pdp-design-review/scripts/vibe_profiles.json` (targets) and
`palette_report.py` (measurement). Use the same profile names here and there.

## Step 1: pick the vibe from what the product PROMISES, not only its category

| Promise / category | Vibe |
|---|---|
| energy, focus, caffeine, pre-workout, sports nutrition, gaming | **electric** |
| everyday vitamins, protein, clinical skincare, oral and home care | **fresh** |
| sleep, stress, calm, baby, intimate care | **calm** |
| premium beauty, fragrance, jewellery, luxury gifting | **premium** |
| kids, snacks, pet, confectionery, novelty | **playful** |
| fashion, apparel, footwear, accessories, books | **editorial** |
| food and non-energy drinks, spices, sweets | **appetite** |
| ayurveda, herbal, organic, eco | **natural** |

The promise wins over the category: an energy SUPPLEMENT is electric, a sleep supplement is calm. Write the choice and one line of
why in `wireframe-plan.md`. If the brand already has a strong site or pack with a different mood, follow the brand and say so.

## Step 2: read the brand's colours from the PACK first

The pack and logo are the truth (the build guide or a client's hex codes come second). Name four things:
- **ink**: the darkest brand colour (text, dark bands). Go Mints: navy `#082A45`.
- **brand**: the signature hue the shopper recognises from the pack. Go Mints: cyan `#12BEE9`.
- **accent**: the highlight colour (stickers, flashes). Go Mints: volt `#E9EF12`.
- **neutrals**: page white or off-white, a soft surface.

## Step 3: build the role palette for the vibe

| Role | electric | fresh | calm | premium | playful | editorial | appetite | natural |
|---|---|---|---|---|---|---|---|---|
| Page | white | white | warm off-white | off-white or near-black | white | white | warm white | paper / cream |
| Alternate band | **full brand colour** (not a tint) | light brand tint | soft tint, low saturation | surface grey or deep tone | a second brand colour | light grey | warm tint | earthy tint |
| Emphasis band | ink (dark) with accent text, up to 2 | ink, 1 | none or 1 soft | deep tone, 1 | brand colour, 2 | black, 1 | deep warm, 1 | deep green/brown, 1 |
| CTA | accent fill + ink text (loudest thing) | brand fill + white or ink | brand, soft | ink or metallic outline | accent | black | warm saturated | deep earthy |
| Headings | 800-900 weight, tight | 700 | 500-600 | serif or light | 800, rounded | 600, roomy | 800 | serif 600 |
| White share of page | at most 55% | 40-85% | any | high or very low | low | high | low | medium |

Contrast is never traded for vibe: body text 4.5:1, large text and icons 3:1. Measure every pair you plan before building
(`palette_report.py --contrast "FG:BG" ...`). Neon colours (volt, lime, hot pink) are FILLS and accents on dark, never text on white.

## Step 4: pace the colour down the page

Walk the wireframe slots and give each a role so the page has rhythm (lint L04: neighbours never share a background):
- electric / playful (the builder's `recipes/dtj-standard-v1.json` "bold" roles, Harsh's review of Go Mints v2, 10 Oct 2026):
  W02 white, W03 white (customer photos carry the colour), W04 brand with WHITE ticks, W05 white with an INK story card (white
  words, accent ticks with ink checks), W06 brand, W07 ink with WHITE review cards (dark words, ink star tiles with accent stars),
  W08 white, W09 accent, W10 brand with white icon badges, W11 accent, W12 white with ink number cards and accent figures, W13
  brand with INK question boxes (white questions and answers, accent open / close button), W14 white, W15 photo + ink overlay.
  Never two strong bands touching.
- Calm pages: story cards are the brand colour deepened until white words read (default), or with `brand.card_tone: "neutral"` a
  minimalist grey with the brand colour only on the tick checks (Harsh's choice for Hope N Skin, 10 Oct 2026, when the orange card
  felt brown and heavy). Offer the grey when the brand colour turns muddy once deepened (orange, yellow, kraft).
- White words never sit on the brand colour itself when it is bright: white on Go Mints cyan #12BEE9 is 2.2:1. When Harsh asks
  for white text there, the words go into an ink box instead (his choice, 10 Oct 2026: "navy boxes, white text").
- calm and premium: white and one soft surface alternating, ONE emphasis band at the signature slot.

## Step 5: check it like a designer before the code does

- Squint test: blur your eyes at the 1280 px screenshot. An electric page should look loud even blurred; a calm one should not.
- The CTA must be the most saturated and highest-contrast element in its viewport. If the band behind it uses the same colour,
  the button disappears: change the button, not the band.
- No more than 3 hue families (playful excepted). Product photos bring their own colours: let them be the loudest thing on
  editorial pages.
- Run `palette_report.py` on the screenshots with the chosen profile. Below 70 fit: fix the palette, rebuild, measure again.

## What the builder does today (10 Oct 2026) and the change it needs

Status: V1 is BUILT (10 Oct 2026): `brand.vibe` electric / playful gives the bold roles above; every other vibe keeps the calm
column. The original gap description, kept for reference: `direction.py` implemented the fresh/calm column for every brand
(alternate band = a very light tint of the brand colour, one dark band, accent pushed to 4.5:1), so every brand looked calm.
The change, as built: a `vibe` field in the brand profile that `direction.derive()` reads:
- electric: band = the brand colour itself (text = ink or white, whichever passes 4.5:1; if neither passes, darken the band until one
  does), up to 3 emphasis bands (lint L05 limit raised for electric only), CTA = accent fill with ink text, heading weight 800+.
- playful: second brand colour for bands, 2 emphasis bands.
- premium: deep tone page option, 1 band, serif accents.
Until V1 exists, say in the report that the page cannot reach the electric targets and why; do not fake it by hand-editing the
template JSON (the next build would undo it and lint could not check it).

## Worked example: Go Mints Energy + Focus (electric)

Measured page (10 Oct 2026, 1280 px): white 74%, dark 0.7%, vivid 6%, fit 40 as electric (75 as fresh). Verdict: dull.
The palette a designer would choose, all pairs measured:
| Use | Colours | Contrast |
|---|---|---|
| Brand bands (W04, W06, W10) | navy `#082A45` text on cyan `#12BEE9` | 6.70:1 |
| Ink bands (W03, W07, W14) | white on navy; volt `#E9EF12` accents on navy | 14.71:1; 11.78:1 |
| CTA | navy text on volt fill | 11.78:1 |
| Body on white | navy | 14.71:1 |
| Accent text on white (when needed) | cyan-deep `#0A6E93` | 5.73:1 |
| Never | white on cyan (2.19), cyan text on white (2.19), volt on white (1.25) | fail |
Marquee (W04) on navy with volt icons, moving (electric allows it). Headings 800, Urbanist (the brand's font, set at theme level).
