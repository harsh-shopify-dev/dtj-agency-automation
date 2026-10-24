# mahalaxmi-02: Mahalaxmi Garam Masala, shot-for-shot remake of a reference edit (24 Oct 2026, DELIVERED v1)

Harsh: "create an ad for this mahalaxmi product exact same as shown in this reel" (instagram.com/reel/DZhYs5wu_n3, a Ramdev
Kitchen King edit). Box used as is; music: the reel's own track (ReelAudio-23203.mp3, Harsh's file), no voiceover.
Job folder: `Downloads/dtj-ugc-mahalaxmi-02/` (plan.md = the shot list, cut.json = the edit).

Result: `final/mahalaxmi02_v1.mp4`, 22.5 s, 1080x1920, -13.7 LUFS. 16 shots on the reference's exact cut times + logo end card.
Mahalaxmi logo (brand's own logo.svg from mahalaxmispices.com) top right. No claims, no prices, no "since" year.
v1-v4 had "Video created using AI" bottom left; removed in v5 (Harsh, 25 Oct: the AI label is added in Instagram / Meta).
**Current version: `final/mahalaxmi02_v5.mp4`** = v4 without the AI line.

## How it was made
1. Reference cut points by scene detection (threshold 0.12); one frame per shot, then the Ramdev logo and the "Available on
   amazon / bigbasket / Ramdevstore.com" strip erased with LaMa (scratchpad clean_brand.py) before ChatGPT ever saw them.
2. Pictures: ChatGPT only, two chats in parallel. Each message = the cleaned reference frame (+ the real box in message 1):
   "recreate this frame exactly, swap only the box". Written-description pictures (first try) were rejected by Harsh as AI slop.
3. Motion: Flow (Omni 1.1 Flash, Frames mode, 9:16, 6 s, x1, 10 credits each) only for the bright action shots: oil pour,
   flame, vegetable pour, hand placing the plate. Flow sparkle removed with watermark.Remover (Harsh's 21 Oct decision).
   The red "king" shots are stills (Harsh: "the red graphic part in the video was only an image... the video i provided was an
   edit"); two red clips made before that message are unused (clips/unused/, 20 credits).
4. Picture 13's small boxes had garbled text: real pack artwork pasted and relit (scratchpad fixpack.py, boxes measured by hand;
   automatic detection fails on red backgrounds). Picture 1 and 16 boxes read correctly; the plate clip's boxes go out of focus.
5. Edit (scratchpad recut.py): stills get push-in / pull / slow rotate; whip-pan transitions (outgoing and incoming slide
   together with motion blur) and zoom-blur transitions where the reference has them; end card pops in.

## v2 (25 Oct 2026): the reference's effects added
Harsh: "it must have effects too... there is an effect in the red king parts of the reference". Measured on the reference
(change maps + start/middle/end frames per shot): the red shots change 3-5x more than the plain ones because of these effects,
now rebuilt at the same moments in `final/mahalaxmi02_v2.mp4`:
| Shot | Effect |
|---|---|
| 3 box, 7 fire, 11 vegetables | mirror zoom-out over the last 0.3 s (frame shrinks to ~72 %, mirrored copies fill the edges) |
| 5 oil, 9 spoon + box | zoom punch with radial blur into the oil stream / the wordmark, last 0.3 s |
| 13 table | blur-in: starts soft and 12 % closer, sharp after 0.3 s |
| all red stills | push-in 10 % (plain stills 6-7 %) |
| between shots | whip-pan slides (2-3, 10-11, 14-15), zoom-blur cuts (8 in, 9 out), logo end card pop |
No extra tool was needed (OpenCV in recut.py). Effects are now step 4 of "Copying a reference edit exactly" in the skill.

## v3 / v4 (25 Oct 2026): the reference's motion replayed exactly
Harsh: "still the effect isnt that well, learn the types of edit pro editors apply". Measured every frame of the reference
(`tools/remake/measure_motion.py` -> refs/ref_motion.json): the stills NEVER push in (scale 1.00 for the whole shot), every
cut is a zoom-blur arrival (overshoot 1.4-1.5x, settles in 3-4 frames), red shots exit with a mirror shrink (3, 7, 11 to
0.72-0.93) or a zoom punch (5 to 1.85x, 9 to 1.66x); there are no sideways whips. v2's push-ins and whips were therefore wrong.
v3 replays the measured zoom/shift/turn/blur on our pictures and clips frame by frame (`recut.py`, "move": "ref"); v4 swaps the
soft blur for shutter motion blur on fast frames so the zoom reads. Checked: 30 fps sheets of the cuts at 4.07, 8.70, 13.03 next
to the reference. **Current version: `final/mahalaxmi02_v4.mp4`** (cut.json in this folder is its edit).
Research (25 Oct): people editing with Claude use Remotion or HyperFrames for motion graphics, ffmpeg for cuts, video-use for
talking-head cleanup, MCP servers for DaVinci Resolve / After Effects. HyperFrames CLI 0.8.193 installed (448 catalog moves:
shader zoom blur, light, glitch); it is the source for effects that measurement cannot copy.

Flow project: https://flow.google.com/project/a9278a91-ea85-4dd7-afc5-3bf6775f1107 (60 credits used).
Tools: `services/reel-factory/tools/remake/`; the runbook is `.claude/skills/dtj-ugc-reel/references/remake-a-reference-edit.md`.
