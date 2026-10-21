# Production: from script to finished reel

## Contents
1. Tools and costs · 2. Making pictures and clips in Flow · 3. Checking every take · 4. Flow's sparkle · 5. Edit · 6. Captions ·
7. Sound · 8. Final checks and score · 9. Deliverables

## 1. Tools and costs
- Pictures: ChatGPT (fresh chat per character) or Google Flow's Nano Banana 2.1 (0 credits, 9:16, x2).
- Clips: Google Flow, Omni 1.1 Flash, Ingredients mode, 9:16, 720p, 4/6/8/10 s, x2 takes. Credits read 20 Oct 2026: 14 per 4 s
  x2, 24 per 8 s x2; 6 s and 10 s not read. A 5 x 8 s ad = 120 credits per round. Veo 3.1 is being shut down (22 Oct 2026).
- Both run in a browser that a person signed in to once. Never type a password or solve a captcha; if a sign-in or a human check
  appears, stop and ask the person.
- Editing: ffmpeg; Whisper (medium on a GPU, small on a CPU) for word timings; Python with opencv-python and numpy for the
  bundled scripts. DTJ machines also have the reel factory (`services/reel-factory`, `python -m reel_factory.job ...`), which
  automates sections 2-8; use it when present.

## 2. Flow, step by step (learned driving it by hand, 20-21 Oct 2026)
1. New project. Settings (the button showing the model name): Image or Video; for Video choose Ingredients, 9:16, 720p, the
   length, x2, Omni 1.1 Flash. Set the mode BEFORE adding ingredients: switching Frames/Ingredients drops attached pictures.
2. Add ingredients with the "+" at the prompt's bottom-left: upload from the computer, or pick from the project. The project list
   loads lazily and re-orders as new items finish: find a picture by its id (the uuid in its image link), never by position.
   (Clipboard paste works only in Ingredients mode; some built-in browsers block file pickers: then the person drags the file in.)
3. Paste the prompt, generate, wait for both takes to finish (a percentage shows while rendering).
4. Download: a picture's link is on its thumbnail; a video's signed link is on its own page (open the tile, read the video's
   source, go back). Signed links download without cookies.
5. Name files by clip and take: `s3_t1.mp4`, `s3_t2.mp4`. Keep the raw takes; never edit them in place.

## 3. Check every take (before choosing)
- Look at it at 4 frames a second (a contact sheet: `ffmpeg -i take.mp4 -vf "fps=4,scale=180:-1,tile=8x5" sheet.jpg`).
  1-2 fps hides drops: book-01 v2 was called "natural" at 1 fps and was full of defects at 4 fps.
- Reject: the book drops, floats, vanishes, teleports, warps, or swings as a blur; a melted or extra finger; a different cover;
  a different face or clothes from the start picture; the line cut off or changed (Whisper the take and compare word by word);
  a voice that changes between clips.
- Fix the prompt, not the luck: if a take fails, say in the prompt what must not happen and regenerate that clip only. At most
  3 rounds per clip, then tell the person what keeps failing.

## 4. Flow's sparkle
Flow stamps a visible two-star sparkle bottom-right on video for users in India (unless on AI Ultra 20x). DTJ's decision (Harsh,
21 Oct 2026): remove it on every reel with LaMa inpainting on each raw 720x1280 clip before the edit (`reel_factory/watermark.py`
on DTJ machines). delogo (blurry box) was rejected. If LaMa is not available, ask the person before delivering a reel that still
shows it. The invisible SynthID stays.

## 5. Edit (ffmpeg; the reel factory's `job edit` does all of this)
- Trim each take to its line: dead air before the first word cut to ~0.9 s; end 0.15-0.35 s after the last word; never past
  the take's end.
- Scale to 1080x1920 (bicubic), 30 fps. Level each clip's voice to the same loudness before joining (book-01: one clip was 6 dB
  quieter).
- Phone look: `python scripts/phone_look.py joined.mp4 joined_phone.mp4`; it measures first and adds only the missing wobble and
  softening (a handheld-selfie take already wobbles). Do this BEFORE captions.
- One small punch-in (1.15-1.2x) on the punchline of every second clip is enough; not on the cover shot.

## 6. Captions
- Words and timing from Whisper; spelling, capitals and missing words from the script (Whisper mishears "Chudesara", writes "10"
  for "ten", drops fillers). 1-3 words per card; break at punctuation and at every cut; the title stays on one card.
- Placement: Harsh's bottom mark (text centre ~69 % down; bottom margin ~548 px at 1920). Top (~14 %) only when the top band is
  empty and the bottom would hide the title. Never over a face.
- Style: white bold rounded font with a dark stroke; the spoken word or a keyword in yellow (#FFD400); a small pop-in.
  Optional hook box at the top (white rounded box, black text) like the creator references.

## 7. Sound
- Keep each take's own room sound; never dead silence between lines.
- Music only from a licensed source (a track DTJ licensed, Meta Sound Collection, or one the person supplies with its licence);
  15-22 dB under the voice, ducked when she speaks. A popular song ripped from somewhere is preview-only.
- Final loudness -14 LUFS integrated, true peak under -1 dBFS (two-pass loudnorm).

## 8. Final checks and score
Hard checks (all must pass): every scripted word is heard; the title is said and shown; the CTA is said; the book never drops or
changes; no caption on a face; no sparkle (or the person agreed); `python scripts/realism.py final_nocap.mp4` reads as phone
footage (wobble 0.5-1.6 px, sharpness 40-650); loudness -14 LUFS, peak under -1 dBFS; 1080x1920.
Score out of 100 (the rubric used on book-01): Hook 20 · Real UGC feel 20 · Product (cover right, on screen, steady) 15 ·
Story and real-life link 15 · Audio 15 · Captions and edit 10. Write down why points were lost; below 80 = fix before delivering.

## 9. Deliverables
`final.mp4` (captioned), `final_nocap.mp4`, the script, the prompts used (one code block per clip, no clip labels inside), the
ad copy, a short report: angle, persona, takes used, credits used, the score and anything a person must look at. Record the
angle (`scripts/angles.py use N --ad <id>`) and add the ad to `references/scripts-library.md` and the creators log.
