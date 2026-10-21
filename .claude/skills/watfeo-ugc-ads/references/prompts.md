# Prompts: character, start pictures, clips

Write every prompt as a description of a real phone video. The words decide whether it looks like a creator or like an ad.

## Words to use and to avoid
Use: "candid", "front camera of a mid-range Android phone", "phone on a small stand at chest height", "selfie at arm's length",
"natural slight hand shake", "slightly soft focus", "mild noise in the shadows", "off-centre framing", "warm table lamp",
"window light from one side", "visible pores", "uneven skin tone", "a few stray hairs", "slightly creased", "lived-in room".
Avoid (lint refuses them): cinematic, studio, flawless, perfect skin, porcelain, airbrushed, 8k, 4k, ultra-detailed,
hyperrealistic, photorealistic, masterpiece, professional photo, commercial, bokeh, dramatic lighting, softbox, ring light,
glossy, beautiful lighting, perfect composition, perfectly symmetrical. ("not symmetrical" is fine: it asks for the opposite.)

## 1. Character (fresh chat, text only)
```
Candid front-camera phone photo of <persona: age, who she is>. <skin tone with natural uneven tone and visible pores>, <face
shape>, <nose, brows, one or two real imperfections>, <hair: texture, length, how it is worn>, <glasses/accessories>.
<clothes: colour, fabric, print, slightly creased>. Not a model, not symmetrical, no retouching, everyday look. She sits <where>
in <the set: shelf, lamp, window, props>. Shot on a mid-range Android phone's front camera <on a stand at chest height | at
arm's length>, slightly soft focus, mild noise in the shadows, off-centre framing, 9:16 vertical.
```
Check the result against `creators.md` rules: if she looks like a model or a stock photo, say what to change ("rounder face,
darker skin, more frizz, remove the makeup") and regenerate in a new chat.

## 2. The book in her hands (second fresh chat: her picture + `assets/cover_front.jpg`)
```
Keep this exact woman, her face, clothes, room and light. Put this exact paperback (second picture) in her hands: same cover art,
same title "We Are There For Each Other" and author name, same size as a real paperback (about 13 x 20 cm). She holds it the way
people hold a book: fingers over an edge, slightly tilted. The cover must match the reference exactly; do not redraw the text.
9:16 vertical, same phone-camera look.
```
Then check the cover against `assets/cover_front.jpg`: title, the couple artwork, the author name. A redrawn or misspelt cover =
regenerate. Fine print may blur; it must never be wrong text.

## 3. Start picture for each clip (Flow, Nano Banana, 9:16, x2; ingredients: the hero picture + the cover)
```
Same woman, same room, same light, same clothes as the reference. <book state for this clip>. <expression and small pose>.
<phone setup>, off-centre framing, slight phone softness.
```
One start picture per clip: a new pose per beat (book-01 v2: every clip starting from the same pose made each cut look like a
reset). Keep the face identical: if Nano Banana drifts (nose, skin tone, glasses), pick the closer take or regenerate.

## 4. Clip (Flow, Omni 1.1 Flash, Ingredients, 9:16, 720p, 8 s or 4 s, x2; ingredients: that clip's start picture + the cover)
Order: phone setup -> book state for the whole clip -> one emotion with a body cue -> the exact line in quotes -> what must not
happen.
```
<Phone on a small stand at chest height filming her | Selfie at arm's length>, natural slight shake. She holds the same book
<state> steadily for the whole clip; it never drops, never leaves her hand, never moves fast. <Emotion with a cue: "amused, laughs
on 'shayari', then deadpan">. She says, in a light Indian accent: "<exact line>". Nothing new in the last second: she finishes
and holds. No camera moves, no zoom, no slow motion.
```
Book continuity (from book-01's failures): no lifting, lowering, hugging, swinging or tossing inside a clip; the free hand makes
small slow gestures at chest height; no pointing or counting toward the lens (counting on her own fingers at chest height is
fine); a clip without the book starts from a picture without it.
Hindi/Hinglish lines: write the line in Romanized Hindi exactly as it should be heard; add "speaks casual Hindi" and check the
words by ear (Omni Flash only claims full English support).

## 5. Ad copy (for the person who posts it)
Primary text: the hook as a line + one sentence of the story + "We Are There For Each Other by Sagar Chudesara, a National
Bestseller" + the signed-letter fact if wanted. Headline: 4-7 words from the hook. Button: Shop Now. No invented numbers.
