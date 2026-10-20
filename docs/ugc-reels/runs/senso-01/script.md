# Run senso-01: Senso Instant Detox Green Tea Kahwa — copy of a "Cooking with Lynja" style reel (20 Oct 2026)

Reference: `Downloads/dtj-ugc-senso-01/ref/reference.mp4` (32.2 s, 576×1024, -14.3 LUFS). What it does:
- Elderly woman, bold print tee, warm wooden-cabinet kitchen, wooden counter; extreme wide-angle lens at counter height,
  so faces, hands and food loom close to the lens.
- About 33 cuts in 28 s of content (one every ~1 s), comedy pacing; ingredients flying; her face cut out and pasted
  over shots ("throws her face"); a bored "This is so boring." beat at 12.6 s; ends on an extreme close-up sip and
  "It's good, this one's really good."
- Spoken lines are short, punchy and playful ("Ginger, mince it, yeet it").

What we do not copy: the real creator's face or likeness (new character), her words verbatim (new lines, same rhythm),
the US-flag tee (India's Flag Code bars the national flag as clothing; we use a bold red-and-white printed top instead).
Optional per Harsh: the face cut-out gag is skipped.

## Facts used (from the pack photo Harsh shared; no official listing found online on 20 Oct 2026)

- Name: SENSO Instant Detox Green Tea Kahwa. Pack text: "With natural ingredients", "Just add hot water",
  "Net Quantity 3g x 10 Sachets = 30g", green veg mark.
- NOT used: ingredient names (the pictured spices are marked "Images are for illustration purpose only"), any detox or
  health benefit, price. The "old way" in the ad uses generic kahwa spices as cooking props, not as product claims.

## Character and set (one look for all shots)

Indian grandmother, about 70, short grey hair, rectangular glasses, warm cheeky face, bold red-and-white printed cotton
top. Warm Indian home kitchen: honey-wood cabinets, wooden counter, steel utensils, two-burner gas stove, a window with
greenery. Every shot: extreme wide-angle lens (14-16 mm look) at counter height, slightly low, bright soft daylight.

## Shots (4 s each, one product state per shot, English with an Indian accent)

| # | Shot | Line (exact) | Product |
|---|---|---|---|
| 1 | She sips steaming kahwa from a glass cup at the counter, then leans into the lens with a cheeky grin | "Does kahwa make you happy?" | none |
| 2 | Low wide shot over a wooden board: she chops fresh ginger with a big knife, slow steady strokes | "Ginger... chop chop chop." | none |
| 3 | Glass pot on the gas stove: she tips a small bowl of cinnamon sticks and cardamom into the boiling water, slowly | "Boil it. Ten whole minutes." | none |
| 4 | She leans on the counter beside the pot, chin on hand, deadpan bored, big sigh | "Arre... this is so boring." | none |
| 5 | She pushes the pot away along the counter, folds her arms, shakes her head | "Nope. Not today." | none |
| 6 | She holds the Senso box up close to the lens with both hands, steady, front of box facing camera | "Senso Instant Detox Green Tea Kahwa." | box held still |
| 7 | Box standing on the counter beside a glass cup; she pours hot water from a steel kettle into the cup, steam rises | "Just add hot water." | box standing still |
| 8 | Extreme close-up: she sips from the cup, eyes wide over the rim, box on the counter behind | "Mmm... this one's really good." | box standing still |

Captions: Harsh's rule (bottom mark ~69%; top ~14% only when the top is empty and the product name would be hidden).
Music: the reference's background bed is not reused (it is the creator's audio); pick from DTJ's licensed library.

## Result v2 (20 Oct 2026)

File: `Downloads/dtj-ugc-senso-01/final/senso-01_v2.mp4` (27.7 s, 1080x1920, -14.0 LUFS, peak -1.1 dBFS).
Start images: Flow Nano Banana 2.1 (0 credits), character made from text only; box from Harsh's pack photo (dragged in once by Harsh:
the built-in browser blocks file pickers, clipboard paste and local fetches). Clips: Omni 1.1 Flash, Ingredients, 9:16, 4 s, 2 takes,
16 takes / 8 generations (14 credits each per Flow's settings panel).
Checks: every line spoken (Whisper; shot 3 says "10" for "ten", one shot-5 take said "No" and was not used); box visible 100% in
all product takes (tracker); 4 fps sheets reviewed by eye. Takes used: s1_5182, s2_c78c, s3_da0a, s4_414f, s5_b8ec, s6_77ef, s7_e427, s8_6394.
Captions: bottom mark (top band busy in every shot); none on shot 6 (box shows the name); captions end at each cut.
Music: placeholder bed from DTJ's own book_2 ad (the reference creator's music is not reused); swap for a licensed light/comic track.
Not done vs the reference: cut pace is ~1 per 3.5 s (reference ~1 per s); no face cut-out gag (optional per Harsh); not heard by ear.

## v3 / v4 (20 Oct 2026): livelier edit + animated captions

- Music: Harsh's file "BOP" (DaBaby, commercial). Vocals removed with Demucs (instrumental only, no explicit lyrics), 30.36 s in,
  129 BPM. PREVIEW ONLY: needs a licensed track before it runs as a paid Meta ad.
- Edit: cuts snapped to the beat (6 of 7 land within 0.05 beat), dead air before each line trimmed to 0.9 s, a 1.18x punch-in
  from each shot's punchline (none on the product shot), music -13 dB ducked under the voice, -14.0 LUFS, peak -1.3 dBFS.
- Captions v4: Remotion TikTok template (`D:\CODE CONTAINERR\WEB DEV\dtj-reel-captions`, create-video 4.0.537), fed by
  edit_reel's pages.json: script spelling, missing words inserted, pages end at cuts, none on shot 6, bottom mark,
  spoken word + keywords in #FFD400, spring pop-in. Remotion licence: free only for companies of up to 3 people.
- Files: `final/senso-01_v3_live.mp4` (ASS captions), `final/senso-01_v4_tiktok.mp4` (Remotion captions).
- Also installed (project skills): HyperFrames from heygen-com/hyperframes (12 skills, Apache 2.0); not used yet.

## v5 (21 Oct 2026): Flow sparkle removed with AI inpainting

- Decision (Harsh, 21 Oct 2026): remove Flow's visible sparkle with LaMa for all reels, exactly as here.
- Method: on each raw 720x1280 clip, before the edit/zooms. Upper star is fixed (573,1133, 54 px); lower star drifts
  (up to ~25 px) and is found per frame by shape match; LaMa (big-lama, Apache-2.0) repaints a 7 px-dilated star mask inside a
  256 px window, feathered back. delogo (blurry box) and 4 formula methods were tried first and rejected (visible outlines).
- Check: bottom-right corner sampled at 2 fps over the whole reel (53 frames): no sparkle visible. Invisible SynthID stays.
- File: `final/senso-01_v5_final.mp4` (26.5 s, 1080x1920, -14.0 LUFS, peak -1.3 dBFS). Cleaned clips: `clips_clean/`.
