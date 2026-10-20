# Realism: no AI slop (21 Oct 2026)

Harsh's bar: Higgsfield-level realistic UGC. Higgsfield is a wrapper over the same kind of models we use (Veo, Nano Banana;
its own Soul model for pictures). What it adds is a workflow: phone-look starting pictures ("iPhone", "old smartphone" presets
with grain and flash), preset handheld camera moves, and per-clip emotion, accent and background-sound controls. We get the
same result with the rules below. Sources: Higgsfield's Soul and UGC Builder pages, practitioner prompt guides (vendor content,
not independent tests); the numbers are DTJ's own measurements.

## 1. What gives an AI reel away (measured with reel_factory/realism.py)

| | Hand wobble (px) | Sharpness | Grain | Source |
|---|---|---|---|---|
| Real phone reels (senso reference, pin) | 0.73-0.76 | 47-162 | 0.27-0.30 | Downloads, 21 Oct |
| Harsh's AI winners (book 0831, book 3, luster 3) | 0.73-0.86 | 124-614 | 0.28-0.66 | Downloads, 21 Oct |
| Raw Omni Flash takes (senso-01) | 0.20-0.26 | 1,058-1,517 | 0.39-0.41 | senso-01 clips |
| senso test reel after the phone pass | see qc.json "realism" | | | edit stage |

Raw Flow takes are locked off (tripod-steady) and hyper-detailed (every wood fibre and hair crisp). The edit's phone pass
(edge-keeping soften + slow hand wobble, `edit.py`) fixes both; `job edit` refuses "reel ready" outside
shake 0.5-1.3 and sharpness 40-650.

## 2. Start pictures (the biggest lever)

The picture a clip starts from sets the whole look. Write the character and every image_prompt like a real phone photo:
- Camera: "a candid photo from a mid-range Android phone's front camera at arm's length" (or "rear camera, propped on the
  counter", "a friend holding the phone"). Slightly soft focus, mild noise in the shadows, auto white balance a little warm.
- Framing: off-centre, a bit too close, the top of the head sometimes cut, a hint of arm or shoulder at the edge. Not centred.
- Light: one real source (window light from one side, an overhead tube light, a warm bulb). Uneven exposure is fine; a
  window may blow out. Never studio, ring light or softbox.
- Skin and person: visible pores, under-eye lines, uneven tone, stray hairs, everyday or no makeup, real body shape, glasses
  smudges. Ordinary clothes with creases. Age-appropriate.
- Room: lived-in Indian home with everyday clutter that fits the person (steel tumbler, charger cable, wall calendar,
  pressure cooker, school bag). Not a showroom, not everything brand new, not symmetrical.
- Product: the exact pack from the client photo, held the way people hold it (fingers over an edge, a little tilted), label
  readable but not perfectly square to the lens.
lint refuses the AI-ad words (cinematic, studio, flawless, 8k, hyperrealistic, bokeh, ring light, glossy, symmetrical ...).

**Pack text check (found 21 Oct 2026 on the senso test):** Omni re-draws the pack, and fine print comes out wrong
("3g x 10 Seshets", "Not Quantity" on a pack that says "Sachets", "Net Quantity"). Big words (brand, product name) held up.
Every take with the product: compare the pack in the 4 fps sheet with the client's photo, word by word for anything readable.
Prompt for it: the pack held a little angled or at mid distance so fine print is not readable, never a flat close-up of the
back panel; a full-screen readable pack shot uses the client's real photo (a cut-in), not a generated one.

## 3. Video prompts

Order: phone setup -> what moves (small) -> the exact line in quotes -> one emotion with a physical cue -> product state -> what
must not happen.
- Phone setup is required (lint): "handheld selfie at arm's length, natural slight hand shake", "phone propped on the counter,
  she leans in and out of frame", "a friend holds the phone, a little unsteady".
- No smooth camera moves, no slow motion, no zoom, no lens flare: real phones don't dolly.
- One emotion per clip with a body cue (Higgsfield's emotion selector, done by words): "deadpan, rolls her eyes",
  "excited, eyebrows up, leans toward the phone", "sceptical, one eyebrow raised, small head tilt". Not "happy" alone.
- Eyes: mostly to the lens, glancing away to think or to the product once; blinks. Mouth: natural speech, not over-articulated.
- Product rules from feedback-ugc-clip-continuity still apply: one product state per clip, never dropped, never floating.

## 4. Script (from the book winners: a messy voice feels real)

- Talk to one person ("you"), short sentences, contractions; Hinglish where the audience speaks it.
- One or two natural fillers or a restart per reel, written into the script so captions match: "I mean", "honestly",
  "arre", "wait, wait", "it has... it has completely changed my mornings" (only where the claim is an approved fact).
- 2-4 short pauses (over 0.4 s) per reel, as in the book winners; the beauty winners' non-stop delivery sounds like a voice-over.
- No ad-speak: "revolutionary", "game-changer", "elevate", "unlock", "transform your", "must-have", "say goodbye to".

## 5. Edit and sound

- The phone pass is on by default (`"phone_look": true` in the edit plan); turn it off only for a deliberately polished ad.
- Keep each clip's own room sound; music stays ducked under the voice (-13 dB default). No dead-silent gaps.
- One slightly abrupt jump cut is fine; perfect beat-synced cutting everywhere reads as an edit, not a person.
- Captions: Harsh's bottom mark; casual, script-spelled.

## 6. Not yet measured / next

- Voice timbre (AI voices are very clean). Measure room tone and voice spectrum against the real reels before adding any
  phone-mic colouring.
- Hindi lip sync on Omni Flash (untested).
- A face-realism check (waxy skin) needs a model; for now the 4 fps look covers it.
