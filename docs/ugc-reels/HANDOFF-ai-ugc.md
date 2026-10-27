# AI UGC ads: handoff for a teammate's Claude (27 Oct 2026)

Give this file to Claude Code on the teammate's laptop (open the `dtj-agency-automation` folder in the Claude desktop app, Code tab)
and say: **"Read docs/ugc-reels/HANDOFF-ai-ugc.md and set me up, then let's make an ad."** Claude reads it top to bottom and follows it.

What it does: a product + a winning reference ad (Instagram reel / Meta ad link) -> a finished 9:16 ad video, made with ChatGPT
(pictures) and Google Flow (moving clips), edited with music, captions and the brand's end card. Nothing is posted; a person decides.

---

## 1. Rules (from the owner's real corrections; never break them)

1. **Match the reference.** First study the reference's story, people, shot order, cut timing and captions, and keep that
   structure. A product montage that ignores the reference was rejected ("it doesn't match anywhere with the reference reel").
   When the person says "make it better / use it as inspiration", keep the reference's story beats and pace and improve the
   script, not the structure.
2. **Pictures are copies of real frames or real-photo scenes, never written from vague descriptions** ("AI slop"). Every prompt asks
   for a real phone-camera photo: natural light, real textures, no CGI, no glossy/HDR look, no extra text or logos.
3. **The product pack is used as it is:** always attach the real pack picture; every word, logo and colour exactly as on it. Small
   packs that come out garbled get the real pack pasted (`services/reel-factory/tools/remake/fixpack.py`).
4. **No other brand anywhere.** Erase the reference's logos, store names and captions from its frames before using them.
5. **No invented facts:** no claims, prices, offers, years, reviews or results unless the person gave them. Senso is an *instant
   premix* (hot water + premix), so never show milk boiling for it.
6. **People are new AI people,** never the reference's creator. Keep the same people across shots by attaching the first picture of
   them as a reference. AI people are presenters/actors, never customers telling results.
7. **No burned-in "AI" line.** The person switches on Instagram's / Meta's AI label when posting. Say so at delivery.
8. **Scripts sound spoken, not written:** short lines, everyday Hinglish in Roman script, one small true family/life insight,
   concrete details instead of adjectives (read `.claude/skills/dtj-ugc-reel/references/script-playbook.md` first).
9. **Ask before spending or agreeing:** show the plan/script and the picture sheet and get a yes before Flow credits; tapping
   "I agree" on any site's terms needs the person's yes. Never type a password; the person signs in.
10. **Never work around a block** (ChatGPT "unusual activity", a sign-in, a captcha): stop and tell the person.

Full rules and lessons: `.claude/skills/dtj-ugc-reel/SKILL.md`, `references/remake-a-reference-edit.md`,
`.claude/skills/dtj-reel-watcher/references/golden-set.md`.

---

## 2. One-time setup of the laptop (about 20 minutes)

In PowerShell, inside the `dtj-agency-automation` folder:

```
powershell -ExecutionPolicy Bypass -File tools\team-setup\setup-team-pc.ps1
winget install --id Gyan.FFmpeg -e
python -m pip install -r services\reel-factory\requirements.txt
```

Then, by the person (Claude never types passwords):
1. Install the **Claude in Chrome** extension and connect it to the Claude desktop app.
2. In that Chrome, sign in to **ChatGPT** with the DTJ Team account (Plus) for the pictures.
3. In that Chrome, open **flow.google.com**. If it says "you do not have access to Flow", click the avatar (top right) and switch to
   **dtj.siddharth@gmail.com** (the Ultra plan: 50 extra credits a day, and **no watermark**, so there is no watermark-removal step).
4. Chrome -> Settings -> Privacy and security -> Site settings -> Additional permissions -> **Automatic downloads** -> Allowed ->
   add `https://chatgpt.com` and `https://flow.google.com` (otherwise only the first picture or clip saves).

Claude checks: `ffmpeg -version`, `python -c "import cv2, PIL, numpy"`, and that both sites open signed in.

**One ChatGPT account for the whole team gets flagged** ("unusual activity"): only one person makes pictures at a time.

---

## 3. Making one ad (the working method, tested 27 Oct 2026)

Job folder: `Downloads/dtj-ugc-<brand>-<nn>/` with `inputs/ refs/ images/ clips/ music/ brand/ final/`.

**Step 1: get the reference.** Instagram: the VPS downloads it (`ssh root@srv2048145.hstgr.cloud`, then as user ai with the
worker's settings loaded: `bash tools/vps/reel.sh remake reference <link> <out.mp4>`), or the person sends the file. Meta Ad Library:
the card's video is a direct mp4 (read `video.currentSrc` in the page, download it). Put it in `inputs/reference.mp4`.

**Step 2: study it.** Cut list + one sharp frame per shot + a contact sheet:
`python <kit>/cutlist.py <job>` (or ffmpeg `select='gt(scene,0.12)'`). Transcribe the voiceover with Whisper
(`whisper.load_model('small')`, language 'hi', plus task 'translate' for the meaning). Write down per shot: who, what happens,
framing, time, caption text and position, and the voiceover line.

**Step 3: the plan / script.** One row per reference shot: time, our shot, our line, still or moving clip. Keep the reference's
order and timing. Show it to the person in **plain short lines** (not a long table dump) and get a yes.

**Step 4: pictures in ChatGPT (Chrome, 4 tabs at once).**
- Copy the attachments into a folder Claude may share (its scratchpad), because Chrome uploads only from there.
- Open 4 tabs on chatgpt.com. In each, find the "Attach photos" file input and upload the pack picture(s) + the set/frame guide
  with the Claude in Chrome upload tool; for several packs attach one combined picture of all packs (at most 4 attachments).
- First message per tab = the full rules (exact pack, guide only for home and light, real phone photo, no text, no other brand,
  vertical 9:16, generate now, more shots will follow). Next messages: "Next shot, same rules. ... Generate now."
- Type with `document.execCommand('insertText')` into the `[contenteditable].ProseMirror` box; send with
  `form button[type=submit]`. Wait ~2 minutes; save the newest non-attachment image with fetch + a download link named
  `<brand>_sNN.png`, copy it to `images/`. Check every picture (pack correct, same people, real-photo look) before the next round.
- Build a numbered picture sheet and send it to the person; **get a yes before any Flow credits.**

**Step 5: moving clips in Google Flow (Chrome, dtj.siddharth, Ultra).**
- New project. Upload all start pictures at once: `+` (Add media) -> Upload. Flow's file picker cannot open, so first hook
  `HTMLInputElement.prototype.click` to catch the file input, attach it to the page, then upload with the Claude in Chrome tool;
  tap "I agree" on the rights notice only with the person's yes.
- Turn off "Agent", open the model chip: **Video -> Frames -> 9:16 -> Omni 1.1 Flash -> 720p -> 6 s -> x1 = 10 credits** a clip.
  Never 4 s clips.
- Per clip: click **Start** -> search the picture's file name -> click it -> type the motion prompt -> the arrow. Queue them all;
  they render in parallel (about 1-2 minutes each).
- Motion prompt pattern: "Real festive home footage, locked-off camera, no camera movement. <one simple action>. Keep <the pack,
  its label, the people> exactly as in the start frame; the pack never moves. Natural motion, no cuts, no text, no music."
- Download: the **Videos** filter, hover each tile so its video loads, then fetch each `video.currentSrc` inside the page and save
  it with a download link (the signed links cannot be read out of the page). Tiles are newest first: map them to shots.
- Check a 6-frame strip per clip: no drifting pack, melted hands or new objects; use only the good part of a clip.

**Step 6: voiceover and music.** Music: only a licensed file (the person's, or a Pixabay track with its licence saved next to it).
Voice: an AI voice only with the person's OK, a teammate's phone recording, or lines spoken inside Flow clips. Music under a voice
sits low.

**Step 7: the edit.** `services/reel-factory/tools/remake/recut.py <job>/cut.json` (shots on the reference's times; `"move": "ref"`
replays the reference's measured camera motion from `measure_motion.py`; `"label": ""`). Captions: rendered with Pillow
(white, bold, soft shadow), placed where the reference places them, inside the safe zone (below the top 14 %, above the bottom
35 %, or at the bottom caption mark ~69 % when the reference does that), every line must fit the width. End card: the brand's logo
and the real packs on the brand's background. Loudness **-14 LUFS**, 1080x1920, h264 + aac.

**Step 8: check before sending.** A frame sheet across the reel next to the reference's frames at the same times: same story beats,
same pace, captions readable and inside the frame, packs right, no other brand. Then send the mp4 and say: "switch on the AI
label when you post".

Time for one ad: about 1-1.5 hours (pictures ~15 min with 4 tabs, clips ~15 min, edit ~15 min, checks and fixes).

---

## 4. Where things stand (27 Oct 2026)

- **Senso Diwali v1** (`docs/ugc-reels/senso-diwali-01-v1.mp4`): REJECTED by the owner: a product montage that did not follow the
  reference (a McCain x Blinkit host party reel). Lesson in rule 1.
- **Senso "family chai" (next ad, in progress):** reference `instagram.com/p/DPwFv_2kx-r` (Chaayos, 39.6 s, 15 shots, slow warm
  Hindi voiceover, small captions). Job folder on Harsh's laptop: `Downloads/dtj-ugc-senso-03/` (reference, cut list, voiceover
  transcript in `refs/vo_hi.json`, Senso packs and logo). The owner's idea: the family is busy (son gaming, husband on office
  laptop, daughter on her phone), mom makes chai, its aroma brings everyone together, with a voiceover. Draft script
  "Ghar ka sabse tez notification" (14 shots, mom narrates, son: "Mummy... chai?", husband: "Call baad mein") was shared;
  **waiting for the owner's OK on the script and on the voice** (AI voice / teammate recording / spoken in Flow clips).
- Pictures already made for Senso v1 (`Downloads/dtj-ugc-senso-01/images/`): a consistent host and the four packs; reuse only
  where they fit the new script.
- The Hermes Telegram reel bot and the VPS reel worker exist but **reels on the VPS are switched off** (the VPS ran out of memory);
  make ads on a laptop with this method until the office PC is set up.
