---
name: dtj-ugc-reel
description: Make a finished 9:16 UGC ad reel for a product by copying DTJ's winning reference reels closely - breakdown of the references, a script with exact lines, a new character made in a fresh ChatGPT chat, the product in hand, start pictures and clips in Google Flow (Nano Banana, Omni Flash, Ingredients, 9:16), take checks at 4 fps, Flow's sparkle removed with LaMa, edit with music, beat cuts, punch-ins, bottom-mark animated captions and -14 LUFS. All in the logged-in browser on the reel VPS (no API) through services/reel-factory. Use it whenever someone says "make a reel", "UGC ad", "AI UGC", "reel for <product>", "copy this winning reel", "handle the reel request", "listen for reel requests", "Reel Factory", or pastes a product picture and winning reels and asks for an ad video, even if they don't name the skill. Not for editing a reel a person shot (use hyperframes / embedded-captions) and never for posting or starting ads.
---

# DTJ UGC reel factory

Result first: one `final/reel_final.mp4` (1080x1920, 30 fps, -14 LUFS, true peak under -1 dB) that a person watches and
decides on. Nothing is posted and no ad is started here (Tier 2: a person's yes, every time).

Decisions this runbook carries (Harsh, 20-21 Oct 2026):
- **No API.** Claude Code and ChatGPT run on the reel VPS; Google Flow is driven in the same logged-in Chrome.
  CLAUDE.md rule 9: a subscription Claude Code session is the AI step only while a person is on duty ("listen" mode).
- **Copy the winners closely**: same set, framing, pace, hook and line rhythm; new character, new words where the reference
  says something only true of its own product.
- **Character from text in a FRESH ChatGPT chat**, never from the reference creator's photo; product put in hand in another fresh chat.
- **Flow: Omni 1.1 Flash only, 9:16, Ingredients mode** (start/end frames are not needed). 2 takes per shot.
- **Flow's sparkle is removed with LaMa** on every raw clip (reel_factory/watermark.py), exactly as senso-01 v5. Not delogo.
- **Captions at the bottom mark** (~69 % down); top (~14 %) only when the top band is empty AND the bottom would hide the product name.
- **Languages**: English, Hindi, Hinglish. Music: only what the person supplies, and it must be licensed for paid ads.

## Where things are
- Worker: `services/reel-factory/` (`python -m reel_factory.job <stage> --job <dir>`, stages in `reel_factory/job.py`'s header).
- n8n: **Reel Factory: New Reel** (form "New UGC reel", data table `dtj_reel_jobs`), source `n8n/reel-factory/`.
  Answer a waiting run with `python n8n/store-factory/reply.py --resume-url "<resume_url>" --body <job>/result.json`.
- Listen on the reel VPS: `python n8n/store-factory/listen.py --workflow "Reel Factory: New Reel"` (background; one listener at a time).
- Past runs and why the rules exist: `docs/ugc-reels/` (book-01, senso-01, the reference analysis, the editing-tools research).

## Steps
1. **Request** (`new`): the inputs are downloaded into the job folder; refused when a field is missing.
2. **References** (`refs`): for each winner, LOOK at `refs/<n>/hook.jpg` and every `sheet_*.jpg` (4 fps) and read
   `breakdown.json`: first word time, words per second, cuts, pauses. Write down: set, lens/framing, wardrobe, what the hands do,
   where the product is in each beat, the hook in the first 2 s, the line rhythm.
3. **Script** (`script.json`, below), then `lint` (exit 0 needed). Lint refuses: numbers or result words not in the approved
   facts, lines too fast for the clip (over 3 words a second), lengths other than 4/6/8/10 s, product shots whose video prompt
   does not say how the product stays.
4. **Character** (`character`): LOOK at both pictures. Reject plastic skin, a studio/showroom set, perfect symmetry, a label
   that is not the real one. Fix the prompt in script.json and run again.
5. **Start pictures** (`images`): one per beat (the pose and product state of THAT beat). LOOK at `checks/images_sheet.jpg`,
   then `pick --shot <id> --image <file>` for every shot.
6. **Clips** (`clips`): 2 takes per shot, cleaned with LaMa, checked (words by Whisper, product by the SIFT tracker,
   4 fps sheet). The best passing take is picked automatically. You still LOOK at the picked take's sheet in `checks/`:
   reject a drop, float, teleport, smear, extra or melted fingers, a different product, a cut-off line. Fix that shot's
   `video_prompt` and run `clips --shots <id>` again; at most 3 rounds per shot, then answer "needs a look".
   For Hindi/Hinglish lines Whisper is not reliable enough to reject: read `said` against the line yourself.
   A take you judge good that the checks refused (e.g. Whisper hears "No" for "Nope"): `pick --shot <id> --take <clean file>`.
7. **Edit** (`edit`): trims (dead air before the line cut to 0.9 s), cuts on the music beat, punch-in on every second shot's
   punchline, captions (script spelling, never across a cut, none on a shot with `no_captions`), music ducked under the voice,
   two-pass loudness. Then WATCH: make a 4 fps sheet of `final/reel_final.mp4`
   (`python -c "from reel_factory.media import sheet; sheet('<final>', '<out>.jpg', fps=4, cols=8, rows=6, length=12)"`, and again
   with `start=12`, `start=24`) and check captions are on no face, the product name is right, no sparkle in the corner.
8. **Answer** (`result`, then reply.py). `reel ready` only when every shot passed and you watched it; otherwise `needs a look`
   with what a person must check; `could not make` with the reason (a sign-in, a refusal, credits).
9. Dated entry in `docs/HANDOFF.md`; tell the person on duty in plain words where the file is and what to look at.

## script.json
```json
{"language": "en", "product_name": "<as on the pack>", "phrases": ["<product name>"], "keywords": ["<words to colour>"],
 "spelling": {"<what Whisper hears>": "<right spelling>"}, "music_db": -13,
 "character": {"chatgpt_prompt": "<written description: age, look, clothes, room, light, phone-camera feel; no real name>",
               "product_prompt": "Put this exact product (2nd picture) in her right hand, label to camera, readable, same size as real; keep her face, clothes and room exactly."},
 "shots": [{"id": "s1", "seconds": 4, "line": "<exact words>", "product": false, "no_captions": false,
            "image_prompt": "<this beat's pose, product state, framing>",
            "video_prompt": "<what moves, slowly; the exact line in quotes; product state for the whole clip>"}]}
```

## Prompt rules (from book-01 v2: drops, floats and weird hands)
1. One product state per clip, matching the start picture: "holds the same box steadily in her left hand at chest height for
   the whole clip; it never leaves her hand, never moves quickly, never leaves the frame".
2. No product actions inside a clip (lift, lower, hug, swing, toss, open). State changes happen between clips.
3. Free hand: small, slow gestures at chest height, fingers relaxed. No pointing or counting at the lens.
4. A beat without the product starts from a picture without it.
5. Nothing new in the last second: she finishes the line and holds.
6. Anti-slop set words: real lived-in home, natural window light, slight phone-camera grain, ordinary clothes; never
   "cinematic", "studio", "perfect", "flawless".
7. Policy words that make Flow refuse: real people's names, other brands, medical promises. Keep lines plain.

## Facts
Only the approved facts in the request. No numbers, reviews, results, prices, offers or health claims that are not in them;
pack text counts as a fact only when the picture shows it. Unknown = leave it out.

## Costs (read in Flow, 20 Oct 2026)
Nano Banana images: 0 credits. Omni Flash: 14 credits per 4 s x2, 24 per 8 s x2; 6 s and 10 s not read ("not available").
`lint` prints one round's credits; `result` reports what was used.

## When something stops
- `needs a person` (exit 3): Google or ChatGPT wants a sign-in or a human check in the reel Chrome. Answer "could not make"
  with that note; never type a password or solve a captcha.
- A selector stopped matching (FlowError / ChatGPTError): Flow or ChatGPT changed its page. Do that one step by hand in the same
  Chrome window (the Claude in Chrome or built-in browser tools), save the file where the stage would, record it with `pick`,
  carry on, and say in the note which selector broke.
