# AI UGC reel factory: workflow, setup and build order (20 Oct 2026)

Goal: from a product photo plus a winning reference reel (or a brainstorm), produce a finished 9:16 Meta-ready reel that
matches the 11 winning ads in `2026-10-20-reference-ads-analysis.md`. Shadow first: the factory delivers the video and
ad copy to a person; it does not touch any ad account until Harsh moves it up.

**Harsh's decision (20 Oct 2026): no APIs.** We automate his exact manual process on a VPS: Claude Code, ChatGPT (website)
and Google Flow (website, Omni Flash) in a real browser with DTJ's logged-in accounts.

## Two conditions this setup comes with

1. **A person is in the loop for every run.** Claude Code runs on a subscription login, and our rule 9 (Anthropic's terms)
   says unattended AI steps need the Claude API key. So the VPS session works like the store factory's "listen" mode:
   it takes `/reel` requests while a teammate is on duty, and the 3 approval taps keep that person involved. It is not a
   24/7 unattended robot. If that is ever needed, the Claude steps move to the API key (and only those steps).
2. **ChatGPT and Google Flow may flag automated use.** Both sites' terms restrict automated access. Risk: the account gets
   limited or banned, along with its Flow credits. Mitigation: use dedicated DTJ accounts (not personal ones), a normal
   human pace, no parallel runs, and a person watching. Plan B if an account is blocked: the official APIs for the same
   models (Omni Flash `gemini-omni-1.1-flash`; [docs](https://ai.google.dev/gemini-api/docs/omni)).

## The workflow (10 steps, 3 human taps)

| # | Step | Where it runs | Output |
|---|---|---|---|
| 1 | **Request**: `/reel` in the Telegram bot with product photo(s), product link, client, language, and the reference reel file (or "brainstorm") | Telegram → n8n | Job row in `dtj_reel_jobs`, files in the job folder |
| 2 | **Product facts**: product page + the client's approved claims sheet | n8n | Facts list; any number or result claim must exist in `dtj_claims` |
| 3 | **Reference breakdown**: frames, scene cuts, loudness, transcript with word timings, pauses (what we did today) | VPS: FFmpeg + Whisper | Reference card: hook, beats with timings, movements, props, room, pace, pauses, caption style, music vibe |
| 4 | **Script + Flow prompts**: same beats, timing, rhythm and hook type as the reference; the client's product and facts; split into 8-second beats, one Omni Flash prompt per beat | VPS: Claude Code | Script table + clip prompts |
| — | **Tap 1: approve the script** | Telegram buttons | |
| 5 | **Character**: Claude Code opens ChatGPT. Chat A turns the reference picture into a written description. A **new chat** B makes the character from that text only, so it never copies the real person. 3–4 options | VPS browser: ChatGPT | Character options |
| — | **Tap 2: pick the character** | Telegram buttons | |
| 6 | **Scene images**: in ChatGPT, the chosen character holding the client's product in each setting the script needs (natural, imperfect, real-review look); Claude checks the product against the product photo | VPS browser: ChatGPT + Claude | 1–3 approved start images |
| 7 | **Clips**: Claude Code opens Flow, uploads the start image, picks Omni Flash, 9:16, image-to-video, pastes each beat's prompt, 2 takes per beat, downloads the clips | VPS browser: Google Flow | Raw clips |
| 8 | **Clip check**: product label and shape, same face and clothes across clips, spoken words match the line, no garbled audio; remake failures (max 3 tries) | VPS: FFmpeg + Whisper + Claude | Best take per beat |
| 9 | **Edit**: trim, join, captions from the script (house style, one keyword highlighted), music by vibe 15–20 dB under the voice, one loudness target (about -14 LUFS, peaks under -1 dB), end card, 1080×1920 H.264 | VPS: FFmpeg | Final MP4 + primary text + headline |
| — | **Tap 3: approve the final ad** | Telegram buttons | Delivered to the client's Drive folder |
| 10 | **Later (phase 3)**: upload to Meta as a PAUSED ad; going live is a separate yes every time | Meta | Paused ad |

Rules built into the steps (from our rulebook and the analysis):
- No number, review count, rating, price, duration ("12 ghante") or result claim unless it is in the client's claims sheet.
- No invented personal stories presented as real (accident, surgery) and no AI person claiming a profession ("main makeup artist hoon").
- Keep the reference's structure, hook mechanics and rhythm; reword the sentences rather than copying a creator's script word for word.
- Reference reels come in as files a person supplies (no Instagram scraping).
- Claude never types a password: a person logs in to ChatGPT and Google once through the VPS's remote screen; the browser keeps the session.

## Setup checklist

| What | Why | Who | Status |
|---|---|---|---|
| VPS with a desktop: Ubuntu, a light desktop, remote screen (noVNC), Chrome, at least 4 CPU cores, 8 GB RAM, 80 GB disk | Runs the browser, Claude Code, FFmpeg and Whisper | Harsh picks the plan; Claude writes the install script | needed |
| Claude Code on the VPS, logged in to the DTJ Claude account | The "brain" for steps 3–8 | Harsh logs in once | needed |
| Browser control for Claude Code on the VPS (Chrome DevTools or Playwright MCP) | Lets Claude operate ChatGPT and Flow | Claude sets up | to build |
| Dedicated DTJ ChatGPT account (paid plan for image generation) | Character and scene images | Harsh | needed |
| Dedicated DTJ Google account with a Flow plan that includes Omni Flash and enough credits | Clips | Harsh | needed |
| FFmpeg + Whisper on the VPS (no graphics card there, so Whisper runs on the processor: slower, fine for one job at a time) | Breakdown, checks, editing | Claude installs | to build |
| Reel tools in this repo (`services/reel-factory/`): breakdown, checks, edit | Steps 3, 8, 9 | Claude builds, with tests | to build |
| n8n workflow "Reel Factory: New Reel" + `/reel` in the Telegram bot + a "Wait for Claude Code: Reel" hand-off | Runs the steps and the taps | Claude builds, exported to git | to build |
| Data tables `dtj_reel_jobs`, `dtj_claims`, `dtj_music` | Job state, approved claims per product, music list | Claude creates | to build |
| Music library: a Drive folder of tracks, each tagged by vibe, with its licence | Background music per vibe | Harsh supplies the tracks | needed |
| Caption font (one open-licence bold rounded font) | House caption style | Claude picks, Harsh approves | to do |
| Drive folder per client for finished reels | Delivery | existing brand-intake Drive | exists |

## Build order

1. **Edit tools first (on this laptop, no accounts needed):** join, captions, music, loudness, end card. Tested by
   re-cutting the raw clips of one winning ad. Needs: the raw Flow clips of one of the 11 ads and 2–3 music tracks.
2. **Breakdown tool:** turn today's analysis scripts into the reference card; test on book_0831 and Luster 2.
3. **Script and prompt writer** with the claims gate; test on a book reference and a beauty brainstorm; Harsh compares against his own prompts.
4. **Browser steps on this laptop first:** Claude drives ChatGPT and Flow in the browser for one full ad while Harsh watches. This shows where the sites break.
5. **VPS:** install script, logins, then move steps 1–4 there.
6. **n8n workflow + Telegram `/reel` and taps**, in shadow mode.
7. **Phase 3:** Meta upload as paused ads.
