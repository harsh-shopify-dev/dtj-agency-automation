# Remake a reference edit, shot for shot (music only, no voiceover)

Use this when the person says "make an ad for <product> exact same as this reel" and the reel is an EDIT (product shots, food,
graphics, music; nobody talking to camera). First done for Mahalaxmi Garam Masala, mahalaxmi-02 (24-25 Oct 2026); the finished
run is in `docs/ugc-reels/runs/mahalaxmi-02/` (notes.md, plan.md, cut.json). Follow every step in order; each step ends with a
check that must pass before the next. Do not improvise a step that is written here. When something new is learned, add it to
the **Lessons log** at the bottom and, if it is a rule, to Do / Don't, in the same session.

Tools: `services/reel-factory/tools/remake/` (measure_motion.py, recut.py, fixpack.py, clean_brand.py, grab.sh,
gpt_helpers.js, flow_helpers.js). Python with opencv, numpy, Pillow, simple_lama_inpainting (the GPU env from setup_vps.sh),
ffmpeg, and the browser pane signed in to ChatGPT and Google Flow. HyperFrames CLI (`npx hyperframes`, Node 22+) for effects
the measurement cannot copy (step 7).

## Inputs (ask once, in one message, if missing)
1. The reference reel (download it to `<job>/inputs/reference.mp4`).
2. The product pack picture, used as it is (`<job>/inputs/<pack>.png`). Never redraw the pack or the logo.
3. The music: the person's file (normally the reference's own track). No voiceover unless asked.
4. The brand's logo file (the brand's website, as SVG/PNG) for the corner mark and end card.
Job folder: `Downloads/dtj-ugc-<brand>-<nn>/` with inputs/, refs/, images/, clips/, brand/, music/, final/, tools/.

## Steps
1. **Cut list.** Scene-detect the reference (ffmpeg `select='gt(scene,0.12)'`), write `plan.md`: one row per shot with time,
   what is in it, bright or stylised, and whether something really moves (pour, flame, hand) or it is a still with an edit.
   Check: the times add up to the reel length; every shot has a row.
2. **Measure the edit.** `python tools/measure_motion.py inputs/reference.mp4 cut.json <anchor times> refs/ref_motion.json`
   (anchor = the time inside each shot whose frame you will copy). It records, per frame: zoom, shift, turn, blur, leftover
   change, brightness. Read the printout: scale far from 1.00 at a shot's start/end = an arrival/exit move; blur 13 = a
   motion-blurred frame; brightness jumps = a flash. Check: every shot printed; weak-match frames are only at cuts.
3. **Clean reference frames.** One frame per shot at the anchor time; erase the other brand's logo and text strips with
   `clean_brand.py` (edit its BOXES to where the marks sit). Check: zoom in, no trace of their name, logo, store or website.
4. **Pictures in ChatGPT** (browser pane, two chats in parallel, odd shots in one, even in the other). First message of each
   chat: the pack + one cleaned frame + this text:
   > Image 1 is our real product box (<brand> <product>). Image 2 is a frame from a real ad that we are remaking shot by shot.
   > Generate now, without asking questions: recreate image 2 as a new vertical 9:16 photo that matches it EXACTLY: same camera
   > angle and distance, same crop, same composition, same props, same background, same lighting, same colour grade, same blur
   > and the same real-photo look. The only change: every box in image 2 becomes the exact box from image 1 (same size and
   > position in the frame, every word, logo and picture on it copied exactly, no new text). It must look like a real camera
   > photo from a professional food shoot, not CGI: no extra props, no glossy or HDR look, no added text or logos. I will send
   > more frames from the same ad in this chat; generate each one straight away with these same rules.
   Next messages: the next cleaned frame + "Next frame attached. Same rules ... Generate now." (name what is in it when the
   frame has no box). Save each with `gpt_helpers.js` `__save('<name>')` then `grab.sh <job> <name>` within 40 s.
   Check every picture next to its reference frame (side-by-side sheet): same layout, real-photo look, pack text right.
   Pack text garbled (small packs)? `fixpack.py inputs/<pack>.png images/pNN.png images/fixed/pNN.png x,y,w,h ...` with the
   box rectangles measured on a grid; check the zoomed result.
5. **Motion in Flow** only for shots where something really moves. Frames mode, 9:16, 6 s, x1 (10 credits), start frame =
   that shot's picture (`flow_helpers.js`), prompt: "Real food commercial footage, locked-off camera ... <the action> ... Keep
   <everything> exactly as in the start frame. Natural motion, no cuts, no text, no music, no faces." Download each clip's
   signed URL, remove Flow's sparkle (`reel_factory.watermark.Remover`, Harsh's 21 Oct decision). Stylised/graphic shots stay
   stills. Check a 4-frame sheet per clip: no drift of the pack, no melted hands; pick the window you will use.
6. **Edit by replaying the reference's motion.** `cut.json`: every shot `"move": "ref", "shot": n`, `"in"/"out": "cut"`,
   `"ref_motion": "refs/ref_motion.json"`, music, corner logo where theirs sits, `"label": ""` (no burned-in AI line), end card.
   `python tools/recut.py cut.json`. recut applies the reference's exact zoom/shift/turn/blur on the same frame, with a
   shutter-style motion blur on fast moves, mirrored edges when the frame shrinks (the mirror effect comes out by itself).
7. **Effects the measurement cannot copy** (light leaks, flash frames, glitch, particles, text, shapes): find the move in
   HyperFrames first (`npx hyperframes catalog --query "<the effect in plain words>"`, e.g. "light leak", "flash
   transition", "glitch"), use its block over our cut at the same time; only build one by hand when nothing fits.
8. **Compare before delivering.** (a) 30 fps sheets of 0.4 s around 3+ cuts, reference above ours; (b) one frame per shot,
   reference vs ours; (c) loudness about -14 LUFS; (d) no other brand's mark anywhere; (e) no burned-in AI line. Fix and re-render
   until (a) and (b) match. Then send the file and write notes.md (what was done, credits, versions).

## Do
- Copy the reference's frames and motion; measure, never eyeball, timings, zoom curves and blur.
- Keep stills dead still where the reference is still (it holds at scale 1.00; the energy is at the cut edges).
- Use the reference's own music file from the person.
- No "Video created using AI" line in the video: the AI label is applied in Instagram / Meta at posting (Harsh, 25 Oct).
  Remind the person of that when delivering.
- Two ChatGPT chats in parallel; Flow clips while pictures generate; edit as soon as pieces land.
- Post a progress bar with done/total and a measured time left on long steps.
- Update this file's Lessons log and Do/Don't every run.

## Don't
- Don't write pictures from descriptions: rejected as "AI slop" (Harsh, 24 Oct).
- Don't send ChatGPT a frame that still has the other brand's logo, store names or website strip: it copies them.
- Don't make Flow video for graphic/stylised shots that are stills in the reference ("the red graphic part in the video was
  only an image... the video i provided was an edit", Harsh 24 Oct).
- Don't add slow push-ins, whips or effects the reference does not have; don't skip effects it does have ("it must have
  effects too", Harsh 25 Oct).
- Don't put a heavy soft blur on fast-move frames: it hides the zoom (motion blur only there).
- Don't use JS .click() on Flow tiles or the frame slot (opens a detail view); real clicks only.
- Don't invent claims, prices, years ("since 19xx") or offers; no other brand's name anywhere.

## Time (measured, mahalaxmi-02)
16 pictures in 2 parallel chats: ~45 min. 4 Flow clips: ~15 min. Measure: 2 min. Render: 3-4 min per version.
Comparing and fixing: 10-20 min. A repeat run with this file: about 1.5 h.

## Lessons log (newest first; add one line per lesson, with the date and the reel)
- 25 Oct, mahalaxmi-02 v5: Harsh: remove the burned-in "Video created using AI"; the AI label is added in Instagram / Meta.
- 25 Oct, mahalaxmi-02 v3/v4: measured the reference: stills never push in; every cut is a zoom-blur arrival (overshoot to
  1.4-1.5x, settle in 3-4 frames) and the red shots exit with a mirror shrink (to 0.72) or a zoom punch (to 1.2-1.85x).
  Replaying the measured motion beat hand-made effects. Fast-move frames need motion blur, not soft blur.
- 25 Oct, mahalaxmi-02 v2: hand-built mirror/punch/blur-in looked "not that well": approximations of timing and curve.
- 24 Oct, mahalaxmi-02 v1: pictures from reference frames matched; Ramdev's logo/strip got copied until erased first.
  Small packs garble text: paste the real pack (fixpack.py), measured boxes; auto-detect fails on red backgrounds.
- 24 Oct: ChatGPT downloads land as <guid>.tmp then rename; copy within 40 s (grab.sh). A message sent while an upload is
  still running does not send: wait for the send button.
