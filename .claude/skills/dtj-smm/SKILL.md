---
name: dtj-smm
description: Run DTJ's social media automation for DTJ's OWN accounts (Instagram, Facebook Page, LinkedIn, YouTube Shorts, X), which posts one approved post a day. The weekly content session (research, write the posts for each platform, make the pictures from DTJ's templates and ChatGPT backgrounds, the code gate, the approval deck with the calendar, send for approval), recording a named yes, checking what was posted, reading the Monday results report and changing next week's plan from it, and connecting a platform or going live. Use it whenever someone says "social media", "SMM", "make next week's posts", "content calendar", "Instagram posts", "LinkedIn post", "post daily", "approve the posts", "yes p1-p7", "what got posted", "social results", "connect Instagram", or "go live on social", even if they don't name the skill. Not for client accounts yet (later), ad campaigns (paid ads), or reels made by the reel factory (docs/ugc-reels).
---

# DTJ social media (SMM)

Harsh, 20 Oct 2026: automate DTJ's SMM process (research, scripts and captions, graphics and videos, QC, a deck with the calendar,
final approval, scheduled, published, audit the results and change, repeat) and "it should post daily". His choices: DTJ's own
accounts first; Instagram, Facebook Page, LinkedIn, YouTube Shorts, X; Claude + ChatGPT on the VPS; Meta's own API.
Code: `services/smm/` (run every command from that folder). Setup and platform facts: `docs/smm/README.md`.

## How the week works
1. **Content session** (a person present; this skill): make next week's 7 posts, one a day, and send them for approval.
2. **Approval**: a named yes per post (Tier 2). `python -m smm approve --week <W> --posts p1-p7 --by "<name>"`, or GitHub >
   Actions > "SMM approve posts". Harsh, or a teammate by name when Harsh can't be reached (`--harsh-unreachable`).
3. **Daily posting** (GitHub Actions, no AI, hourly 07:05-22:05 IST): each approved post goes out at its time on the platforms
   that are switched on; every other platform gets the picture and exact words in Telegram for a person to post by hand.
4. **Results** (daily 10:20 IST; report on Monday): numbers from each platform's API at 24 hours and 7 days.

## The content session, step by step
Do these in order. Make the week by Thursday so there's time for the yes before Monday.

1. **Open the store and last week's report.** `python -m smm store` (prints the content folder). Read `reports/<last week>.md`
   if it exists: it says which posts got the most views. Keep what worked, change what didn't, and write the reason into the
   new week's `research` list.
2. **New week.** `python -m smm new <YYYY-Www>` makes 7 daily posts at 19:00 IST (`SMM_POST_TIME` changes the default). The
   time is a starting point, not a known best time: let the results decide after a month.
3. **Research** (fill `research`: topic, why, source). Sources that count: Harsh's words, the live lead pages' pains (memory:
   ad-money-leak, ads-no-orders, tushar-joshi "paid an agency, then silence?", audit), the proof list, last week's results, the
   SEO engine's keyword plan (what founders search). Never invent a pain point; never study a competitor by logging in to it.
4. **Write each post.** One idea per post, one pain per post, plain founder English (no jargon, not Gujlish), few words, numbers
   first. Mix the themes: client results, a founder pain, before/after, tips; never two of the same in a row.
   - Every number must be a figure of the proof item the post cites (`proof_ids`, `services/smm/smm/data/proof.json`).
     Our words never repeat a blocked figure (the % growths, the unconfirmed before-values, 16X, 208+, 90+, ₹70Cr+).
   - Never describe how DTJ works inside (no AI, automation, tools, bots, "our process"); no promises, fees, response times,
     or "call with Tushar". Next step wording: "we check your details first, then our team gets in touch".
   - Lines DTJ already uses on its site can be restated (`.claude/skills/dtj-landing-variants/references/claims-and-proof.md` §1).
   - Instagram: end with "Link in bio" (links are not clickable there); other platforms: `{link}` (code puts in the tracked
     audit link). X: 280 characters with the link counting 23. Hashtags: Instagram ≤5, Facebook/LinkedIn ≤3, X ≤2.
   - YouTube only takes video posts (Shorts): from the reel factory or an approved existing reel.
5. **Pictures.** Put each picture in the post's `render` list: templates `result` (a real dashboard), `pain`, `before_after`,
   `slide` (carousel), `cta` (`services/smm/smm/render.py`). Then `python -m smm render <W>`; it fills `overlay_text` itself.
   **ChatGPT backgrounds** (optional, a person logged in on the VPS browser): ask ChatGPT for a picture with **no text, no numbers,
   no logos, no real people**, save it in `media/bg-<n>.png`, pass it as `"background": "<full path>"` to `pain` or `slide`, and set
   `ai_media: {"used": true, "what": "background"}`. A realistic AI person needs `realistic_person` and `label_on` and never stands
   for a client, a teammate or Tushar. Never type a password; if ChatGPT asks for a login, stop and ask the person.
6. **Check.** `python -m smm check <W>`. Fix every BLOCKED line (never weaken the gate or add a figure to the proof list without a
   source from Harsh). Look at every picture yourself at phone size: words readable, nothing cut off, the dashboard sharp.
7. **Deck and send.** `python -m smm submit <W>`: gate, deck (`DTJ-social-<W>.pptx`: calendar + one slide per post), saves to the
   store, sends the deck and each picture to the team's Telegram. Show Harsh the deck in chat too.
8. **The yes.** Only when the person says yes in this session, by name, for named posts: `python -m smm approve --week <W>
   --posts p1-p7 --by "<name>"`. Changing a post afterwards voids its yes (fingerprint), so re-run check + approve.

## Other jobs
- **What got posted:** `python -m smm status <W>`.
- **Withdraw a yes before it posts:** `python -m smm approve --week <W> --posts p3 --revoke --by "<name>"`. A live post is taken
  down by a person in the app, never by code (Tier 3).
- **Results:** read `reports/<W>.md` in the store; every number names its API. Say "not available" for what isn't there.
- **Connect a platform / go live:** `docs/smm/README.md` "Going live". Switching SMM_MODE to `approve` or adding a platform to
  SMM_LIVE_PLATFORMS is Harsh's decision; tell him what it changes and wait for his yes.

## Never
Post or approve on anyone's behalf; put a token in a file, chat or log (GitHub secrets only); delete a live post; invent a
number, review, pain or claim; publish for a client account (not built yet).
