# Multi-brand reel engine (design, 30 Oct 2026)

Harsh, 30 Oct 2026: one reel automation for every brand and every reel style (UGC, cinematic, founder, ...), built like the
Champfuel creative engine: thin n8n steps that each call a service on the VPS, one step per model. A person always watches.

## 1. What a run looks like (the person's view)

1. In Telegram (the Hermes bot): "cinematic Diwali reel for Brand A". The bot finds Brand A and starts **Reel: Brand A**.
2. "Tap Start if you are watching" (rule 9: subscription logins only while a person is on duty).
3. The person gets the **script + one picture per scene** (an album, numbered). Buttons: Approve / Change something.
   "Change something" -> "3, 5: the diya is too small" -> only scenes 3 and 5 are redrawn and sent again. Repeats until Approve.
4. Approved pictures become **clips** (Flow). Claude checks every clip and redoes the bad ones (max 3 rounds per scene).
5. Claude **edits** the reel (beat cuts, captions, music, -14 LUFS) and the person gets the **final reel**: Approve / Change something.
6. Approved: the reel, its scene pictures and clips are saved in the brand's Drive folder. Nothing is posted, no ad is started.

## 2. Decisions

| Question | Decision | Why |
|---|---|---|
| One workflow per brand? | **One shared "Reel Engine" workflow + one small "Reel: <Brand>" workflow per brand** | The wrapper is what the bot starts and what a person sees per brand; the steps exist once, so a fix lands everywhere. Champfuel's "Run settings" node is the same idea. |
| Heavy folders | **One Drive folder per brand, references per style; shared niche libraries** | Brand B in another niche never sees Brand A's references. |
| Re-watching references | **Gemini writes a "style card" per brand + style once**; refreshed only when references are added | Each reel reads one card, not 50 videos. |
| Script + reference analysis | **Gemini CLI** (Google login, `/home/ai/gemini-home`) | Harsh: Gemini 3.1 Pro writes the best scripts and reads video well. |
| Scene pictures | **Codex CLI + GPT Image** (ChatGPT login, `/home/ai/.codex`, `codex-accounts`) | Same as Champfuel's step 2. |
| Picture QC, clip QC, edit | **Claude Code** (Claude login volume) | Existing checks in `services/reel-factory` (realism, slop, product tracker, 4 fps sheets). |
| Video clips | **Google Flow on the Ultra plan, driven by a new `flow_cli`** in the logged-in Chrome | No API, no extra cost. Gemini CLI video = paid Vertex Veo (not the Ultra plan). `flow_cli` mirrors `chatgpt_cli`: one command, one JSON line. |
| Posting | Never | Tier 2. |

## 3. Pieces

### 3.1 n8n
- **Reel: <Brand>** (one per brand, 4 nodes): `When called by Hermes` / `Run now` -> `Run settings` (brand, default style,
  language) -> `Execute Workflow: Reel Engine` (waits). Making a new brand = duplicate and change `Run settings` only.
- **Reel Engine** (one, shared). Nodes named like Champfuel, each an HTTP call `POST http://reel-engine:8091/stage`
  `{brand, style, run, stage, ...}` with a 1 h timeout and 3 retries:
  - `0 [NO AI] Take request` (checks the brand row and the folder, makes the run id)
  - `1 [GEMINI] Style card` (skipped when the card is current)
  - `2 [GEMINI] Script + scenes` -> `3 [NO AI] Check claims` (every claim must be in the brand's facts)
  - `4 [CHATGPT + CLAUDE] Scene pictures` (Codex draws, Claude scores against the style card's quality bar, redraws failures)
  - `5 [PERSON] Approve script + pictures` -> Telegram album + buttons -> n8n **Wait** (resume link) -> `Approved?`
    - no -> `4b [CHATGPT + CLAUDE] Redraw named scenes` (or `2b [GEMINI] Rewrite script` when the note is about words) -> back to 5
  - `6 [FLOW + CLAUDE] Clips` (flow_cli, 2 takes per scene, Claude QC, up to 3 rounds per scene)
  - `7 [CLAUDE] Edit` -> `8 [PERSON] Approve final` (same Wait loop; changes go back to 6 or 7)
  - `9 [NO AI] Save to Drive` + `Record` (dtj_reel_jobs) + `Tell the requester`
- The person's taps arrive through the Hermes plugin (`tools/hermes/plugin/dtj-reels`), which calls the waiting run's resume link.
- The old **Reel Factory: New Reel** stays switched on until the new engine has made one reel a person approved.

### 3.2 Data
- n8n table **dtj_brands_reels**: brand, name, niche, drive_folder_id, languages, voice notes, palette, active.
- Drive per brand: `brief.md`, `facts.md` (the only claims allowed), `products/`, `references/<style>/`, `style-cards/<style>.json`,
  `reels/<run>/` (pictures, clips, final). Niche library: `Niches/<niche>/<style>/`, used when a brand has fewer than 3 references.

### 3.3 reel-engine box (VPS, Docker, inside the `n8n` app)
- Same image and the same three login folders as `brand-engine` (`n8n-royal-dosa`), own code folder `./reel-engine`
  (synced from `services/reel-engine` in this repo), `mem_limit` set, **one run at a time** (the VPS ran out of memory before).
- `POST /stage` runs one stage and returns JSON `{ok, run, stage, outputs, next, needs_person?}`; `GET /outputs?brand&run`.
- Stage code reuses `services/reel-factory` (breakdown, checks, edit, captions, beats, watermark) instead of copying it.
- Flow: the box calls `flow_cli` against the host's logged-in Chrome (CDP 9222) through `host.docker.internal`.
- Style playbooks per style (`playbooks/ugc.md`, `cinematic.md`, `founder.md`) and a `GEMINI.md` for the Gemini steps.

## 4. Errors
- A sign-in, captcha or quota message -> `needs_person` -> the bot asks the person on duty; the run waits.
- Same stage fails 3 times -> stop, keep everything, tell the person in Telegram what failed and what was tried.
- Nothing is deleted; every picture/clip version is kept in the run folder.

## 5. Tests
- Unit tests for every stage with fake model commands (no login, no credits); n8n Code nodes tested like `test_reel_nodes.py`.
- A dry run of the whole Reel Engine with fakes before any live run.
- First live run: one cinematic reel for one brand, watched end to end; Flow credits spent are written down.

## 6. Checks before building (no money spent)
1. Gemini CLI in the box reads a whole reel file and returns a breakdown.
2. Codex CLI in the box draws a scene with our product photo attached.
3. `flow_cli` from the box reaches the host Chrome and returns one clip.
4. Memory on the VPS with Chrome + one engine run.
If 1 or 2 fails, that step falls back to the reel-factory browser route (ChatGPT in Chrome); the n8n shape stays the same.

## 7. Not in scope
Posting or ads; paid Veo API; runs with nobody watching; changing Champfuel, royal-dosa or brand-engine.
