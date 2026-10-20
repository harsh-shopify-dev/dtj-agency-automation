# book-01 v2 vs the 5 book winners: physical continuity (20 Oct 2026)

Harsh's feedback: the book drops randomly, disappears, hands look weird. Confirmed. My first review sampled 1-3 frames
a second and called these "natural"; at 4-6 frames a second they are clear defects. Revised score for v2: about 58/100.

Sources: 4 fps contact sheets of `book-01_final_v2.mp4`; 6 fps strips of winners 0831 and 3.mp4; SIFT cover
tracking against the real cover photo at 6 fps (script in the session scratchpad, `booktrack.py`).

## Defects in v2

| Time | Defect |
|---|---|
| 3.75-4.25 s | Book whips out of frame as a blur |
| 4.25-8.0 s | Book absent while she talks about it |
| 6.5-7.0 s | Waving hand smears, fingers melt |
| 8.0 s cut | Book teleports back to her cheek |
| 8.25-8.75 s | Book warps while swinging to her chest |
| 12.75-15.75 s | Book floats at her chest, no hand holding it |
| 15.9 s cut | Book teleports to her cheek again |
| 22.75 s | Pointing finger smears |
| 23.75-24.0 s | Book missing, then flies in from the side as a blur |
| 37.25-37.5 s | Book swings as a blur before the hug |

## What the winners do instead

- Time on screen is not the difference: the cover is visible 35-92% of the time in the winners (tracker), 86% in v2.
- **Book state changes only at cuts.** 0831: book in hand until the 10.0 s cut, the next clip starts without it;
  at 28.3 s she lifts it slowly into view from the bottom edge. Inside a clip the book is held still or absent.
- **No book = both hands free** (0831's second clip: phone propped, two-hand gestures).
- **One hand grips the book steadily; the other gestures slowly** (3.mp4 18-20 s). No fast swings, no flicks.
- No mid-clip teleports: tracker found no position jumps in 4 of 5 winners; book_3 has one at 27.7 s, a slow lift.

## Root cause

The v2 prompts asked for book movement ("lowers the book", "pulls the book in against her chest", "lifts the
book", "hugs the book") and pointing/counting at the camera. Omni Flash renders these as fast, warped motion,
and every clip restarted from the same start image, so each cut reset the pose.

## New rules for every clip prompt

1. One book state per clip, matching that beat's start image. Write: "she holds the book steadily in her left hand
   at cheek height for the whole clip; the book never leaves her hand, never moves quickly, never leaves the frame."
2. No book actions (no lower, lift, hug, swing, toss). Book state changes happen only between clips.
3. Free-hand gestures small and slow, at chest height, fingers relaxed. No pointing or counting toward the lens.
4. A beat without the book uses a start image without the book and a propped phone (both hands free).
5. Nothing new in the last second: she finishes the line and holds.

## New automatic checks (reject the take)

- Book visible at the start but lost later in the same clip (cover tracker).
- Cover position jump > 0.15 of the frame between frames at 6 fps.
- Motion spikes (optical flow in the hand/book area) are reported for a by-eye check only: the winners' real
  handheld footage trips the same threshold, so it cannot reject a take on its own.
- Words: every scripted word present (Whisper), as before.

## v3.2 result (20 Oct 2026): about 81/100

File: `Downloads/dtj-ugc-book-01/v3/book-01_final_v3_2.mp4` (38.5 s, 1080x1920, -14.0 LUFS, peak -1.4 dBFS).
Start image per beat made in Flow (Nano Banana 2.1, 0 credits); clips in Omni 1.1 Flash, Ingredients, 9:16, 8 s, 2 takes.
All 10 takes passed: every scripted word (Whisper) and book visible 100% with no jumps (cover tracker).

| Measure (source: ffmpeg, Whisper, booktrack.py) | v2 | v3.2 |
|---|---|---|
| Book visible | 86% | 100% |
| Book disappears | 4x | 0 |
| Book jumps | mid-clip and at cuts | only at the 4 cuts (setup changes) |
| Voice level spread across clips | ~6 dB | 1.3 dB |
| Words in first 3 s | 10 | 14 |

Still open: tiny cover text (badge, tagline, top line) is garbled by the image/video models: fix with a real-cover overlay
pass (track the cover, paste the real artwork, keep fingers on top). Music ~12 dB under the voice (winners 15-22 dB).
Voice tone differs a little between clips (brightness 1523-2069 Hz): not checked by ear. Beat 4 is slow (1.88 words/s).
Google's sparkle mark is visible bottom right (left in place).

## v3.3 (20 Oct 2026): caption placement per Harsh

Rule: captions at the bottom mark (text centre ~69% of height) by default; the top mark (~14%) only when the top band
is empty and the bottom band would hide the product name. Applied: beats 1, 2, 3, 5 bottom; beat 4 (title + author) top.
File: `Downloads/dtj-ugc-book-01/v3/book-01_final_v3_3.mp4` (-14.0 LUFS, peak -1.4 dBFS). Placement check script:
`capplace.py` (session scratchpad).
