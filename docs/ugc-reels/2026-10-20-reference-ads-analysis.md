# AI UGC reels: analysis of Harsh's 11 finished ads (20 Oct 2026)

What this is: a frame-by-frame and audio breakdown of the AI UGC ads Harsh made by hand (Google Flow, image-to-video),
so the automation can copy what works. Performance results (spend, hook rate, CTR, cost per purchase) were **not shared yet**:
nothing below says which ad won. Every number here comes from the tools named next to it.

Sources: the video files in `Downloads` (5 book ads, 6 beauty ads). Tools: `ffprobe` (format), `ffmpeg` scene detection
(threshold 0.25), `ffmpeg ebur128` (loudness, true peak), `ffmpeg volumedetect` (music level where nobody speaks),
OpenAI Whisper `medium` (speech, word timings), 1-frame-per-second contact sheets plus 4-frames-per-second hook strips (looked at by Claude).

## The short version

1. **Two different styles, both work.** Book ads are pure "phone selfie" UGC: one person, one room, talking to camera.
   Beauty ads are a mini story: problem face, salon scene, product close-ups, result, presenter with the product, and an "Order Now" card.
2. **Hooks are spoken from frame 0.** Every ad starts talking at 0.0 s (book_3 at 0.6 s), with 7–14 words in the first 3 seconds,
   and the product is already in the hand in frame 0 in most ads.
3. **Book ads feel more real because the voice is messy.** 3–9 pauses over 0.4 s per ad, a false start ("It has... It has completely
   consumed me"), filler ("bestie"). Beauty voices run almost non-stop (0–1 pauses over 0.4 s): they sound like a voice-over, not a person.
4. **Audio is too hot on the beauty ads.** Their peaks go above 0 dB (+0.5 to +0.7 dBFS true peak), which can crackle after
   Instagram re-encodes them. Book ads range from -12.6 to -21.2 LUFS, so some play much quieter than others.
5. **AI slips to catch automatically:** a jar that changes, clothes that change between clips, a "before" face that is a different woman.
6. **Some lines would fail our own rules:** made-up personal stories and numbers (details in "Claims to check").

## The 11 ads

| Ad | Length | Format | Visible cuts | Language | Product named at | Style |
|---|---|---|---|---|---|---|
| book_0831 | 47.6 s | 1080×1920, HEVC | 3 | English | 13.9 s | Selfie, arm out, fairy lights, polaroid wall, wired earphone mic |
| book_0831a | 44.2 s | 1080×1920, HEVC | 1 | English | 9.1 s | Selfie, dim warm room, earphone mic held to mouth |
| book_1 | 49.6 s | 16:9 inside 9:16 (black bars) | 1 | English | 10.1 s | Young man at a desk, end card 44–49.6 s |
| book_2 | 41.6 s | 16:9 inside 9:16 (black bars) | 1 | English | 9.4 s | Man on a sofa, story-led, end card ~38 s |
| book_3 | 37.0 s | 1080×1920, HEVC | 1 | English | 26.4 s | Pyjamas on a bed, bold caption style |
| beauty_luster1 | 40.0 s | 1080×1920, H.264 | 9 | Hinglish | 4.9 s | Product macro, salon, bride, presenter, end card |
| beauty_luster2 | 44.0 s | 1080×1920, H.264 | 9 | Hinglish | 13.5 s | Melting-makeup face hook, then the same story |
| beauty_luster3 | 32.2 s | 1080×1920, H.264 | 9 | Hinglish | 11.0 s | Social-proof hook, macro, bride, presenter |
| beauty_lv213746 | 41.7 s | 1080×1920, H.264 | 7 | Hinglish | 17.8 s | "Makeup artist" price hook, swatch, sponge close-ups |
| beauty_lv224341 | 45.9 s | 1080×1920, H.264 | 10 | Hinglish | 18.3 s | "Two brides, one makeup artist" story |
| beauty_lv224802 | 47.0 s | 1080×1920, H.264 | 7 | Hinglish | 17.7 s | "Makeup industry doesn't want you to know" hook |

All are 30 fps. "Visible cuts" = ffmpeg scene changes; book ads join 8-second clips of the same room, so most joins don't register as cuts (that's good).

## Hooks (first 3 seconds)

| Ad | What you hear | What you see |
|---|---|---|
| book_0831 | "I am completely obsessed with every single sentence of this book." | Wide-eyed "O" face, book held up beside the face |
| book_0831a | "This book is for anyone who is still in love with someone they never ended up with" | Soft smile, book against chest, mic to mouth |
| book_1 | "If someone recommends you this book, that person genuinely cares about you." | Pointing finger, book in hand |
| book_2 | "A few months ago, I had a serious bike accident..." | Tired face, book on knee |
| book_3 | "This is why I will never ever get over fictional men." | Laughing, book pressed to cheek |
| beauty_luster1 | "Yeh product kyun kisi ko nahi pata?" | Finger dipping into the jar (macro) |
| beauty_luster2 | "Kaash koi pehle bata deta..." | Close-up of a woman with melting, streaked makeup (strongest visual stop) |
| beauty_luster3 | "Ek hazar se zyada logon ne try kiya..." | Wide-eyed woman holding the jar to camera |
| beauty_lv213746 | "10,000 rupaye, 15,000, 20,000... bridal makeup pe loot-te hai" | Woman counting on fingers, salon background |
| beauty_lv224341 | "Do brides, ek hi makeup artist..." | Two brides and the artist standing together |
| beauty_lv224802 | "Makeup industry nahi chahti ki tum ye jaano" | Plain-faced woman, then the bottle pushed to camera |

Patterns: an opinion or confession (book), a pain or curiosity line (beauty), a number, a "secret". The product is in frame from 0 s in 9 of 11.

## Structure (same skeleton in all 11)

Hook (0–3 s) → story or pain (3–12 s) → product name (9–18 s; book_3 holds it until 26 s) → how it feels or how it works
(demo, swatch, sponge, emotional reaction) → result or proof → call to action in the last 3–5 s → end card (beauty, book_1, book_2).

## Movement and realism cues (to put in every video prompt)

Book ads (the most "real" looking):
- Selfie framing with the arm visible and slight hand wobble; the camera is never perfectly still.
- Expression changes every 1–2 s: wide eyes, eye-roll while thinking, hand on chest, hugging the book, a pained "it hurts" face.
- Book moves: raised beside the face, lowered, turned toward camera for the title, pressed to chest.
- Everyday setting: fairy lights, polaroids, an unmade bed, a striped tee or pyjamas, a desk with a calendar.
- Props that say "real phone video": wired earphones used as a mic.
- Speech with false starts, pauses and filler.

Beauty ads (polished, more "ad" than "UGC"):
- Warm salon lighting with bulb mirrors; bridal outfits and jewellery.
- Macro product shots (finger dip, damp sponge press, swatch on the back of the hand) carry the "how it works" part.
- Before/after told through a person's face (melting makeup vs glowing skin).
- A final two-shot: presenter holding the product next to the "after" bride.

## Captions

- Beauty (one house style): bold rounded white font, 1–3 words at a time, one keyword in yellow, sitting about 55–65% down the frame.
- book_0831/0831a: small white text building word by word, mid-frame.
- book_3: white capitals with one coloured word.
- book_2: karaoke style, the current word in green.
- book_1 and book_2 place captions in the black bar under a 16:9 picture: the person fills only about a third of the phone screen.

## Audio (measured)

| Ad | Loudness (LUFS) | True peak (dBFS) | Words/sec | Pauses > 0.4 s | Music where nobody speaks (mean dB) |
|---|---|---|---|---|---|
| book_0831 | -17.0 | -0.0 | 3.06 | 7 | -22.3 |
| book_0831a | -14.6 | -1.4 | 3.15 | 3 | not measured |
| book_1 | -16.2 | -0.1 | 2.34 | 9 | -21.9 (end card) |
| book_2 | -12.6 | -0.1 | 3.02 | 6 | -20.6 (end card) |
| book_3 | -21.2 | -4.7 | 2.72 | 5 | -52.3 (no music) |
| beauty_luster1 | -9.3 | +0.6 | 3.24 | 0 | -17.3 (end card) |
| beauty_luster2 | -7.9 | +0.6 | 2.93 | 4 | -16.2 (end card) |
| beauty_luster3 | -6.7 | +0.6 | 2.82 | 0 | not measured (no gaps) |
| beauty_lv213746 | -8.0 | +0.6 | 3.05 | 0 | not measured (no gaps) |
| beauty_lv224341 | -8.2 | +0.5 | 2.79 | 1 | -15.2 (end card) |
| beauty_lv224802 | -8.0 | +0.7 | 2.22* | 1* | not measured |

\* Whisper missed 29.8–44.3 s of speech in lv224802 (the captions show it), so its pace and pause numbers are wrong.

What the audio says:
- Speaking pace is steady at about 2.8–3.2 words per second.
- Beauty mixes are pushed hard (-6.7 to -9.3 LUFS) and clip above 0 dB. Book mixes vary by 8.6 LU between the loudest and quietest ad.
  A single target for every ad (for example around -14 LUFS with peaks under -1 dB; a common streaming target, not a Meta rule) would fix both.
- Music sits about 15–22 dB under the voice in the gaps. book_3 has no music at all.

## AI slips found (the automatic checker must catch these)

| Ad | When | What |
|---|---|---|
| beauty_luster3 | 11–12 s | The jar becomes a clear glass jar with a label missing "RR"; from 13 s it is the white jar again |
| beauty_lv224341 | 6–9 s | The makeup artist's top changes from orange to black, then back to orange at 15 s |
| beauty_luster1 | 4–6 s vs 13–22 s | The bride in the wide shot does not look like the bride in the close-ups |
| beauty_lv224802 | 9–15 s vs 24–37 s | The "before" bride and the "after" bride look like different women |
| book_0831 | 36 s | The book blurs into an unreadable shape mid-move (brief) |
| beauty ads | throughout | A small sparkle mark in the bottom-right corner (looks like Google's AI mark); leave it in |

## Claims to check (our rule: no invented reviews, numbers or stories)

These lines are in the finished ads. Each needs real proof from the client, or a rewrite before an automated version uses it:
- book_2: "I had a serious bike accident and had to undergo major surgery" (a personal story told by an AI person).
- book_1: "I'm doing unpaid PR for this book" (it is a paid ad).
- beauty_lv213746: "Main ek makeup artist hoon... apni clients pe secretly use karti hoon" (an AI person claiming a profession).
- beauty_luster3: "1,000 se zyada logon ne try kiya"; beauty_lv224802 captions: "1,103 logon ne try kiya, 4.9 stars".
- Beauty: "12 ghante", "sweat-proof", "poore din tikta hai", "₹999" (must match the live price and product facts).
- The Luster pack says "Fairness". None of the ads claims fairness; keep it that way.

## What this means for the automation

1. **Hook writer:** speak from 0 s, 7–14 words in the first 3 s, product in hand in frame 0, one of the hook types above.
2. **Video prompts:** carry the realism cues (wobble, expression change every 1–2 s, props, everyday room) for UGC style,
   or the macro, salon and two-shot pattern for "demo story" style.
3. **Voice:** write false starts and pauses into the script for UGC style (3–9 pauses over 0.4 s per 40 s looked natural here).
4. **Mix:** one loudness target, peaks under -1 dB, music 15–20 dB under the voice, a music choice per vibe (Harsh supplies the tracks).
5. **Checker:** compare every frame's product with the product photo, compare faces and clothes across clips, flag claims without a source.
6. **Speech-to-text:** Whisper `medium` is good for English but weak for Hinglish (Devanagari output, misspellings, one 15-s miss).
   Use a larger model on the RTX 3050, and take captions from the script instead of from speech recognition.

## Not available yet

- Which of these ads performed best (no results shared). With an Ads Manager export per ad, we can tie hooks and styles to results.
- The original reference reels for the book ads, and the prompts used for the characters and clips.
