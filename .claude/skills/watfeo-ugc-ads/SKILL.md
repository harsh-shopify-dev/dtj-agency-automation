---
name: watfeo-ugc-ads
description: Makes UGC video ads (Reels, 9:16) for ONE product only - the novel "We Are There For Each Other" by Sagar Chudesara (WATFEO) - from the full manuscript bundled inside. Picks a fresh angle from the 58-angle bank, writes natural never-repeating scripts with every detail checked against the book, designs a unique real-looking Indian book creator (never the generic AI face), writes character, start-picture and Omni Flash prompts, and runs or guides the Google Flow production, take checks, phone-camera realism pass, captions and quality score. Use it whenever someone wants an ad, reel, UGC video, script, hook, angle, creator, prompts or ad copy for "We Are There For Each Other", WATFEO, Sagar Chudesara's book, "the book ad", Malar / Harsh / Sagar / Sai, or says "make the next book ad", "write 5 book scripts", "which angles are left", "handle the WATFEO ad request", even without naming the skill. Not for other products, never for posting ads.
---

# WATFEO UGC ad factory

One job: finished, realistic UGC ads for "We Are There For Each Other" by Sagar Chudesara, that do not repeat each other, say
nothing the book does not say, and do not look like AI. Everything the job needs is in this folder, so the skill works on any
Claude that has Python 3 and ffmpeg (plus a signed-in browser for the generation steps).

Paths below are relative to this skill's folder.

## What is in here
| File | Read it when |
|---|---|
| `references/house-rules.md` | Always, first. Harsh's 16 rules and why each exists. |
| `references/book-bible.md` | Before writing: characters, places, chapter map, quotable lines, allowed claims, reserved scenes. |
| `references/angle-bank.md` | Choosing an angle (58 angles grounded in the manuscript). |
| `references/scripts-library.md` | Before writing: every anchor and opener already used (never repeat them). |
| `references/script-writing.md` | Writing: ad shapes, hooks, spoken language, timing, CTA, the script.json format, a worked example. |
| `references/creators.md` | Designing the person on camera: what the real creator references have, a 10-persona bank, the log. |
| `references/prompts.md` | Writing the character, book-in-hand, start-picture and clip prompts. |
| `references/production.md` | Making it: Flow steps, take checks at 4 fps, the sparkle, edit, captions, sound, final score. |
| `references/campaign/` | The full earlier campaign docs and the original script chat (deep context; open only when needed). |
| `assets/book_full_text.txt` | The whole manuscript. Search it with `scripts/book_search.py`; do not read it top to bottom. |
| `assets/cover_front.jpg`, `cover_back.jpg` | The real covers: the book-in-hand prompt and the cover check use them. |
| `assets/example-script.json` | A complete lint-clean script (book-02). Copy its shape. |
| `assets/angle-ledger.json` | Which angles have been used (created and kept by `scripts/angles.py`). |

| Script | Does |
|---|---|
| `python scripts/angles.py fresh` / `show N` / `use N --ad ID` | lists unused angles, shows one, records a used one |
| `python scripts/book_search.py "phrase"` / `--names X Y` / `--chapter N` | finds any detail in the manuscript with its page |
| `python scripts/lint_script.py script.json` | refuses a script that breaks a house rule (exit 2 + the reasons) |
| `python scripts/phone_look.py in.mp4 out.mp4` | adds only the missing phone wobble/softening (before captions) |
| `python scripts/realism.py video.mp4` | measures wobble, sharpness, grain, colour, room tone vs real phone footage |

## The job, step by step

### 1. Understand the ask (1 minute)
Most requests are one of: (a) "make the next ad" (full reel); (b) "write N scripts / hooks / angles" (writing only, in chat);
(c) "give me the prompts for this script" (prompts only, in chat); (d) an n8n hand-off ("handle the WATFEO ad request").
Language: English unless told (Hindi and Hinglish are fine; casual, spoken). If the person gives a reference reel, copy its
shape and energy, never its words or its person. Do not ask questions the files answer.

### 2. Pick the angle
`python scripts/angles.py fresh`, then read the candidates in `references/angle-bank.md` and `references/scripts-library.md`.
Pick an angle whose anchor (character + conflict) and real-life moment have not been used. Prefer angles with a concrete,
surprising detail a viewer can repeat to a friend. Say in one line why this angle. For a batch, every script gets a different
anchor, a different real-life moment and a different opening shape.

### 3. Collect the facts
For every story detail you want to use, run `scripts/book_search.py` and keep the page. If a detail is not found, drop it.
Names: `book_search.py --names ...`. The official-site claims and the never-use list are in `book-bible.md` section 6.
Why: the campaign's own angle bank was partly written from memory, and an invented detail is a false claim in a paid ad.

### 4. Write the script
Follow `references/script-writing.md`. Spoken, not written; a hook in the first 2 s tied to a real-life moment; one book state per
clip; the title + author + a spoken "Read Now" / "Shop Now" / "Abhi padhe" in the last clip. Save it as `script.json`
(see `assets/example-script.json`) and run `python scripts/lint_script.py script.json` until it exits 0 (for a writing-only
job with no prompts yet: `--lines-only`). Read each line aloud
in your head: if it sounds like copy, rewrite it.
For writing-only requests, stop here: give the scripts in chat (and the file), each with its angle, anchor and page refs.

### 5. Design the creator
Follow `references/creators.md`: an unused persona or a new one, imperfect and specific, with her own set, clothes and light; one
setup for the whole ad. Write the character prompt from `references/prompts.md` section 1.

### 6. Write the prompts
Character -> book in hand -> one start picture per clip -> one Omni Flash prompt per clip (`references/prompts.md`).
Give them in chat as plain code blocks in clip order, no clip numbers or timestamps inside the blocks (Harsh pastes them straight
into Flow), and save them next to the script.

### 7. Produce (when the job is a full reel and a signed-in browser is available)
Follow `references/production.md`: pictures, then 2 takes per clip, every take checked at 4 fps and by Whisper, the sparkle
removed, the edit, `scripts/phone_look.py` before captions, captions at the bottom mark, licensed music only, -14 LUFS.
On DTJ machines the reel factory automates this (`services/reel-factory`, `python -m reel_factory.job new|refs|lint|character|
images|pick|clips|edit|result`); use this skill's script and prompts as its `script.json`.
Stop and ask a person for: a sign-in or human check, more than 3 failed rounds on one clip, unlicensed music, anything that
would post or spend beyond Flow credits.

### 8. Check, score, deliver, record
Run the hard checks and the 100-point score in `references/production.md` section 8. Below 80, fix it first. Deliver the files
and a short plain-English report (what was made, the score, what a person should look at). Then record the angle
(`scripts/angles.py use N --ad ID --note "..."`), add a row to `references/scripts-library.md` and the creators log. Recording is
what keeps the next ad fresh.
Record an angle as soon as its script is delivered (note "planned, reel not made yet"), not only when a reel exists: in the
skill's first test, two separate runs both picked angle #14 because nothing marked it taken. For a writing job that is only a
test or a draft the person has not accepted, say which angles you would record and let them decide.

## DTJ automation (n8n)
DTJ runs this as **WATFEO Ads: New Ad** in n8n (form: language, optional angle, count, notes). The run pauses at "Wait for Claude
Code: WATFEO Ad"; a Claude Code session with this skill reads the task in "Request for Claude Code: WATFEO Ad", makes the ad,
and answers with `python n8n/store-factory/reply.py --resume-url "<resume_url>" --body <ad folder>/result.json`
(`{"reel_status": "reel ready" | "needs a look" | "could not make", "final_path": ..., "angle": N, "note": ...}`).
The n8n table `dtj_watfeo_ads` is the team's shared record of angles used; the request lists them, and they count as used here.

## Never
Post, schedule or start an ad; invent a name, plot point, quote, number, review or personal story; use the reserved terrace
rescue scene; change the room mid-ad; reuse an anchor or an opener; ship a take with a dropped or redrawn book; type a password.
