# The product gallery and the section pictures

Harsh, 23-24 Oct 2026, on brief 12 (NoCheat ProPeri, MojoVibe as the reference): "a product image is always 1:1 ... there should
be 5 - 6 images explaining the product perfectly such as whats the product, why this product, features, benefits, lifestyle like
that a pro DTC brand applies the images" and "for the other section ... plan images for that section" (a "What's inside" with
B6 and B12 shows the almond). Then, on the first try: "insanely unproffesional and cluttered with a complete AI SLOP RESULTS, you
have to get better results as same as mojovibe's if the results are bad then you have to regenerate them."

## Why the first try was slop (do not repeat)
- Everything at once: flying chillies and peanuts, splashes, crumbs on every surface, boards, callout lines, three props.
- The picture model drew the words: a different font on every picture, words over the food, no grid.
- Wide 3:2 and 16:9 pictures on a product page.

## What a pro gallery does (MojoVibe, measured 23 Oct 2026: 12 pictures, all 1080 x 1080)
- ONE subject per picture: a spoon drip, a bite, the jar, a hand. Large empty space.
- A flat, seamless colour ground from the brand's palette (their red, orange, yellow), one hard light, one clean shadow.
- One type system across the set: the same headline font, a short headline (2-5 words), at most one small line.
- Food in action is the hero (a drip, a bite, a dip); the pack shot is clean.

## The method (two steps, never one)
1. **The photo, no words** (`provision/ai_images.py`, Codex on the VPS; `--ref` our pack photo whenever the jar is in it). Every
   prompt: one subject; a flat seamless backdrop in ONE brand colour (name the hex); one hard key light and one clean shadow;
   "nothing else in the frame: no flying ingredients, no crumbs, no splashes, no props, no table edge, no garnish"; a real camera
   photo (100mm macro, f/8), no CGI or AI-glossy look; and WHERE the empty space is ("the whole left half is empty backdrop",
   "the top third is empty"), because the words go there. Positions in words, not percentages (the guard refuses `%`).
2. **The words** (`provision/gallery_compose.py`): the brand's colours, a headline font (default Shrikhand) and a body font
   (default Poppins) on one 1080 x 1080 grid with 72 px margins. Every line is checked against facts.json first (a sourced,
   non-SAMPLE fact; never a price, an offer, a count or a claim). Layouts: `pack`, `top`, `bottom`, `numbers`, `tiles`, `stack`.

## The set (6 square pictures, in this order, first in the product's gallery; the brand's own photos stay after them)
| # | Picture | Photo | Layout | Words |
|---|---|---|---|---|
| 1 | What it is | the jar in the right half on the light brand colour, one small dish of the product beside it | `pack` | the pack's name line, one line under it, a round sticker with the pack's key number |
| 2 | Why this one | the product in action, alone: a spoon drip, a pour, a scoop | `top` | the paradox voice line + one fact |
| 3 | The numbers | the jar centred in the middle third, dark brand colour | `numbers` | 4 numbers from the nutrition table or the pack |
| 4 | What's inside | one close-up per real ingredient (a neat heap on a cream ground), 3-6 of them | `tiles` | each ingredient's name (with its % when the pack gives one) |
| 5 | How to use | one dish per use (3), each alone on the same ground | `stack` | the uses line + the pack's serving ideas as labels |
| 6 | Lifestyle | a hand with the food, a bite with the product clearly visible, or a person using it (no face needed) | `bottom` | one voice line + one small line |

"What's inside" shows only what the product really contains (the ingredient list), each as real food: a vitamin is shown by the
real ingredient that carries it, never by one the product does not contain. A non-food product changes the photos, not the plan
(e.g. a serum: the bottle, a drop on skin, its actives, the routine, a person applying it).

## Section pictures (square, no words)
Every page section that shows a picture gets one planned for it, from the same shoot: Story 1 and Story 2 = the use photos (step
5's dishes) that match their headline; the final push = the clean pack photo (step 1's photo without words). Never a wide banner.

## The quality gate (look at every picture before it is used; regenerate the ones that fail, at most 3 tries each)
- One subject, flat ground, nothing floating, no crumbs or clutter; the product exactly like the reference (shape, cap, label).
- The food looks edible and the product is clearly visible (a bite must show the product, not just bread).
- No text over the product; every word spelled as given; the headline and the product never touch.
- Put the finished set next to the reference brand's contact sheet: if ours looks busier, cheaper or less appetising, redo it.
- Show the person the set (Telegram or chat) before it goes on the product.

## Commands (from services/store-builder; C = the client folder)
    python -m provision.ai_images --kind studio --prompt "<one subject, flat #hex backdrop, where the empty space is>" --ref <pack photo> --out C/gallery/<name>.png
    python -m provision.gallery_compose --spec C/gallery/compose.json --facts C/facts.json --out C/gallery/final
    python -m page_builder.store_files --store <store> --folder C/gallery/final --approved-by "<name> (<where the yes was given>)"
Putting the set first in the product's gallery changes the product: it needs the person's yes for that product (Tier 2).
