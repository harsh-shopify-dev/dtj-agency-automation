# Product pages the agency likes (read 9 Oct 2026 from Harsh's 3 samples)

The samples: **aura Daily Complex** (supplement, green on cream), **ROSÉE Hydra-Glow Cream** (face cream, rose on blush) and **goodboy
Happy Gut** (dog supplement, brown and orange on cream). Three categories, ONE structure, recoloured per brand. These notes are for rhythm, order
and mood only. **Never copy their text, numbers, claims, logos or pictures.** Their percentages, "as seen in" logos and "60 days" are examples of
layout, not facts: a client's page shows such things only when the client's own sourced facts contain them.

## The order of ideas (the same in all three)
| # | Section in the samples | The shopper's question it answers | Our section |
|---|---|---|---|
| 0 | Buy box: promise headline on the hero picture, stars + count, price with compare-at and a badge, 3 ticks, pack-size pills, add to cart, payment icons, ONE short review card with a photo, 3 trust icons, accordions | What is it, what does it cost, can I trust it | the buy box (fixed by rules) |
| 1 | Logo strip right under the first screen ("as seen in") | Is this legit? | `trust_marquee` (with the brand's real trust points; press logos only if real) |
| 2 | "What is in the jar": product in the centre, 2 benefits left, 2 right, each with a small icon | Why this product | `why_features` |
| 3 | The key ingredients one by one (tabs) with a picture card | What is actually in it | none yet (closest: `pack_inside`) |
| 4 | "Four capsules, one morning, done": 3 to 4 photo cards, one per step | Is it easy | `how_split` (ours: one picture + a list) |
| 5 | Short customer videos with stars and first names | Do real people use it | none wired yet (Shoppable Reels block, needs videos) |
| 6 | "Another cream? We hear you.": picture left, empathy text, ticks, a review card | My objection ("I have tried things before") | `story_split` |
| 7 | ONE dark band: picture + 3 measured results ("Measured, not promised") | Does it really work | `proof_panel` (signature) |
| 8 | 3 big percentage cards ("From greasy, to gone") | How many people saw a change | `facts_glance` (only with real survey figures) |
| 9 | Comparison table, product picture on our column | Why not the usual alternative | `comparison` (only when the brand approved it) |
| 10 | Photo testimonials slider ("Three months on one jar") | Will it last / do people stay | `reviews_slider` (only real reviews) |
| 11 | Expert cards (supplement sample only) | Do experts agree | none |
| 12 | Guarantee band: "60 days to fall in love", picture, button, 3 icons | What if it does not work for me | none yet (facts schema has `guarantees`) |
| 13 | FAQ: heading left, questions right | Last doubts | `faq` (always last of ours) |
| 14 | "Complete your ritual" products, then the full reviews widget | (theme and review app, not ours) | — |

What the order does: proof of legitimacy first, then the product's idea, then ease, then other people, then the objection, then hard proof,
then risk removal, then last doubts. Every section answers one doubt; nothing repeats.

## Look and feel shared by all three
- One brand colour on a warm light background (cream or blush); the brand colour fills buttons, ticks, accent words and ONE dark band.
- Headings are short, outcome-led, often a contrast pair or a twist: "From greasy, to gone", "Sat for, not spat out", "Measured, not promised",
  "Treats, but smarter". One word of the heading is accented in the brand colour.
- Serif headings in the beauty and supplement samples; every section has a small one-line subheading under a centred heading.
- Rounded cards and pill buttons; lots of real photography (product in hand, in use, the person or pet); icons small and quiet.
- Density: generous space, but every band carries content; no empty decorative sections.
- The dark band appears once, two thirds down, for the strongest proof.

## What this means for a plan
- Lead with legitimacy (trust strip) and the product's idea (`why_features`) before anything else.
- Put ease (`how_split`) early, objection handling (`story_split`) in the middle, the dark signature proof after it, FAQ last.
- Pick the signature by the brand's strongest REAL proof: measured results -> `proof_panel`; what it is free of -> `free_from_band`; a story -> `story_card`.
- When the client has no reviews, no survey figures or no approved comparison, those sections are simply absent: the page gets shorter, never padded.
- Gaps in our library these samples show (worth building): press logo strip, ingredient tabs, photo step cards, guarantee band with a button,
  expert cards, and a builder for the Shoppable Reels block.
