# DTJ social media automation (SMM): plan (20 Oct 2026)

**Status: BUILT 20 Oct 2026** after Harsh's "build the automation and it should post daily" (how to run it: `README.md` in this
folder). No account is connected and nothing has been posted; every public post still needs a named yes (CLAUDE.md rule 2). **[VERIFY]** = not checked yet.

Harsh's request (20 Oct 2026): automate "DTJ Process for SMM": research → scripts and captions → graphics and videos → QC →
deck with the calendar → final approval → scheduled → published → audit the results and change → repeat to scale.

**Harsh's decisions (20 Oct 2026):**
- **DTJ's own accounts first.** Client accounts come later, on the same pipeline.
- **Platforms:** Instagram, Facebook Page, LinkedIn, YouTube Shorts, X.
- **Making the content:** Claude and ChatGPT hosted on a VPS (the same set-up as the reel factory, `docs/ugc-reels/2026-10-20-build-plan.md`).
- **Publishing:** Meta's own API (Instagram and Facebook). The other three use their own official APIs (see step 7).

---

## 1. The short version

- **One weekly loop.** On Monday a person opens the "content session" on the VPS. Claude researches, writes, makes the pictures
  (ChatGPT) and short videos (the reel factory), checks everything and builds the week's deck. The person approves it in Telegram.
  After that, code posts each item at its time on every platform, reads the results, and next Monday's plan starts from them.
- **The AI steps need a person present; the posting does not.** Claude Code and ChatGPT run on subscription logins, and our rule 9
  says unattended AI must use the API key. So steps 1–5 run while a teammate is at the VPS (about one sitting a week). Steps 7–9
  are plain code (no AI), so they run on their own, around the clock.
- **The AI never draws numbers or text.** ChatGPT makes the background picture; our code puts the words, the real dashboards and
  the exact numbers on top, in DTJ's own templates. So a figure on a post is always the figure in our proof list, never an AI
  guess, and the text is never garbled.
- **Every number and claim comes from the approved proof list** (`.claude/skills/dtj-landing-variants/references/claims-and-proof.md`),
  and no post describes how DTJ's automation or process works (Harsh's rule).

---

## 2. The 10 steps

| # | Step (Harsh's list) | What runs | Where | Person? | Output |
|---|---|---|---|---|---|
| 1 | **Research** | Claude reads: last week's results (step 9), the founder pains from real lead answers, what founders search for (the SEO engine's keyword plan), and the public posts of a list of agencies and D2C pages Harsh names | VPS, Claude Code | yes | Week brief: 3–5 topics, each with its reason and source |
| 2 | **Scripts and captions** | Claude writes each post once, then one version per platform (length, tone and format rules per platform in code) | VPS, Claude Code | yes | `week.json`: every post, its platform versions, its proof ids |
| 3 | **Graphics and videos** | Pictures: ChatGPT makes the background or scene; code (HTML template → PNG) adds the words, logo and real proof images. Carousels the same, slide by slide. Videos: the reel factory for AI reels, or a re-cut of DTJ's existing reels | VPS: ChatGPT in the browser + code; reel factory | yes | Files in the right size for each platform |
| 4 | **QC the whole work** | 1) Code gate (below). 2) Claude looks at every finished file at phone size. 3) Anything that fails is remade (max 3 tries), then flagged | VPS: code + Claude | yes | Pass/fail per post, with reasons |
| 5 | **Deck with the calendar** | Code builds the deck from `week.json`: a calendar slide (day × platform), then one slide per post with the picture, caption per platform, date and time (IST) and the proof it uses | code (python-pptx) | no | `.pptx` in DTJ's Drive + a PDF for phones |
| 6 | **Final approval** | Telegram: the deck, then **Approve week** / **Change post N** / **Drop post N**. A change request goes back to step 2 for that post only | n8n + Telegram bot | **the approver** | Named approval stored with the exact files (hash) |
| 7 | **Post scheduled** | Approved posts go into the data table with their time. Every 15 minutes n8n posts whatever is due | n8n, no AI | no | Rows in `dtj_smm_posts` |
| 8 | **Published** | Each platform's official API. Then the post's link is read back, the action log gets a row, and Telegram says "posted, here's the link". Fails: retry with backoff (max 3), then alert with the error | n8n, no AI | no | Live post + link |
| 9 | **Audit the results** | Code pulls each post's numbers at 24 hours and 7 days (reach, views, likes, comments, saves, shares, profile visits, link clicks) and the audit-form leads that came from social (by the link's tracking tag). Monday: a plain-words report, every number with its source, and "keep / change / stop" suggestions | n8n pull (no AI); report by Claude in the content session | report: yes | `dtj_smm_results` + weekly report |
| 10 | **Repeat and scale** | Next Monday's research starts from step 9. Scale = more posts per week, then client accounts (section 6) | | | |

### The code gate (step 4)
A post is blocked if any of these fail:
- a number, result, review or client name that is not in the proof list, or is written differently from it;
- a word from the "never say" list: DTJ's process or automation ("our AI", "n8n", "automation pipeline", …), guaranteed results,
  fees or prices (not available yet), "call with Tushar";
- jargon the audience doesn't read (ROAS, CVR, funnel, …) unless the topic explains it, from the jargon table in `dtj-landing-variants`;
- platform limits: length (X 280 characters), hashtags, picture size and shape, video length, file size;
- a link that is not the audit page with its tracking tag;
- an AI picture of a person presented as a real client, a real DTJ team member or Tushar; a realistic AI video without the
  platform's "AI-made" label switched on (Meta and YouTube both ask for this) **[VERIFY each platform's current label rule]**;
- the same picture, hook or caption used in the last 8 weeks.

---

## 3. What the content is about (proposal; Harsh decides, D3)

Built only from what we can prove today:
1. **Client results:** one brand a post, the real Shopify dashboard picture and its "₹X → ₹Y in sales" (6 brands in the proof list).
2. **One founder pain per post:** "ads run but no orders", "people add to cart and leave"… only pains from real lead answers.
3. **Before and after:** the Pro Effex product page rebuild (1.4% → 2.8% conversion rate).
4. **Our work:** the 16 real ad reels.
5. **Tushar as the founder voice:** short tips, his real portrait; no AI Tushar.
6. **Plain-words tips** that answer what founders search for (from the SEO engine's keyword plan), each ending in the audit link.

Open: **may we name client brands on social?** The website already does; social is a wider audience. **[VERIFY with Harsh]**

---

## 4. Platforms and what each needs

| Platform | How we post | What it needs | Notes |
|---|---|---|---|
| Instagram | Meta Graph API (Instagram content publishing): photo, carousel, reel | DTJ Instagram as a Business/Creator account linked to the DTJ Facebook Page; a Meta app; permissions for publishing and insights; a long-lived token in n8n credentials | Posting through the API has a daily limit per account **[VERIFY current number]**. Our schedule lives in n8n, so we don't depend on the API's own scheduling. |
| Facebook Page | Meta Graph API (Page posts, photos, videos, reels) | Same Meta app and Page access | |
| LinkedIn | LinkedIn's posting API for a company page | DTJ company page; a LinkedIn developer app with access to post for an organisation **[VERIFY: this access needs LinkedIn's approval]** | Until approved: the deck marks LinkedIn posts "post by hand", files ready in Drive |
| YouTube Shorts | YouTube Data API (video upload) | DTJ YouTube channel; Google Cloud project | **[VERIFY]** uploads from an API project that Google hasn't audited may be forced to "private": plan for the audit form, or post by hand until then |
| X | X API (post with media) | DTJ X account; developer account | **[VERIFY]** posting through the API needs a paid X plan: Harsh decides (D4) whether to pay or post by hand |

For our own accounts the Meta app can probably stay in development mode with DTJ's admins, without Meta's app review
**[VERIFY]**. Client accounts later will need the review.

---

## 5. Rules built in

- **Tier 2 every time:** nothing is posted without a named approval in Telegram (Harsh, or a teammate when he isn't reachable,
  recorded as "<name> (Harsh not reachable)"). If a file changes after approval, its hash changes and it needs a new yes.
- **Kill switch:** `AUTOMATION_ENABLED` plus a `SMM_ENABLED` flag. Off = nothing posts; due posts wait. Dry-run mode logs what
  would be posted and posts nothing.
- **Shadow first:** the first 2 weeks deliver the deck and files only; a person posts by hand. Then "approve" mode (code posts
  after the yes). It never becomes automatic without a yes.
- **Never delete** a live post from the automation (Tier 3). A mistake gets a person's attention through Telegram.
- **Action log row** for every post: what, when, platform, file hash, approver, result link or error.
- **Secrets** only in n8n credentials / the vault. Tokens never in files, workflow JSON or chat.
- **ChatGPT on the VPS:** a dedicated DTJ account, human pace, a person present (the same risk note as the reel factory: the
  site may flag automated use; plan B is the image API).

---

## 6. Later: client accounts (step 10, "scale")

Same pipeline, with: a brand profile per client (from `dtj-brand-intake`), the client's own proof list, the client approving
their deck (contacting a client and posting on their account are both Tier 2), the client's Meta account connected to our app
(needs Meta app review), and the results report per client.

---

## 7. Build order

| # | Piece | Needs accounts? | Done when |
|---|---|---|---|
| 1 | **Post format + code gate + platform rules** (`services/smm/`): `week.json` schema, the checks above, tests | no | gate blocks a set of bad test posts and passes good ones |
| 2 | **DTJ post templates** (HTML → PNG): single post, carousel slide, quote, result card with the real dashboard, story; every platform size | no | Harsh approves the look on 5 sample posts |
| 3 | **Deck builder**: `week.json` → `.pptx` + PDF | no | a sample week deck Harsh approves |
| 4 | **First real week by hand-off** on this laptop: Claude researches and writes, ChatGPT in the built-in browser makes backgrounds, a person posts by hand (shadow week 1) | DTJ ChatGPT account | 1 week posted, gate 0 failures |
| 5 | **Meta app + n8n publisher + data tables** (`dtj_smm_weeks`, `dtj_smm_posts`, `dtj_smm_results`) + Telegram approval buttons | Meta app, tokens | a test post to a test Page, then shadow week 2 |
| 6 | **Results pull + weekly report** | Meta insights permission | first Monday report, every number sourced |
| 7 | **LinkedIn, YouTube, X** publishers, each when its access is granted | each platform's access | |
| 8 | **VPS** (shared with the reel factory): move steps 1–4 there | the VPS | one full week run from the VPS |

---

## 8. What I need from Harsh

| # | Decision or item | My recommendation |
|---|---|---|
| D1 | Does **one named yes on the week's deck** approve every post in it (like the SEO fixes batch), or one tap per post? | One yes per week's deck, listing every post and its time; any change after that needs a new yes |
| D2 | **How many posts a week** per platform to start with? | You decide; I'd start small and let step 9 show what works. I won't guess "best times": the first month tests times, then the results pick them |
| D3 | The **content themes** in section 3, and may we **name client brands** on social? | |
| D4 | **X:** pay for API posting, or post by hand? | By hand until the other four run well |
| D5 | **Language:** plain founder English (as on the lead pages), or also Gujarati/Hindi versions? | Plain founder English first |
| D6 | **Accounts:** the DTJ handles on all 5 platforms, admin access to the DTJ Facebook Page and Meta Business account, a dedicated DTJ ChatGPT account | |
| D7 | **Competitor and inspiration list** for research (accounts to study) | |
| D8 | **One VPS** for both reel factory and SMM? | Yes: one machine, one login session, one person on duty |

## Sources
- Harsh's process list and answers: this session, 20 Oct 2026.
- Proof list: `.claude/skills/dtj-landing-variants/references/claims-and-proof.md`.
- Audience and "never reveal the process": `docs/DTJ-CONTEXT.md`, Claude memory notes.
- Reel factory and the VPS set-up: `docs/ugc-reels/2026-10-20-build-plan.md`.
- Weekly batch approval pattern: `docs/seo-aeo/README.md`.
- Platform API facts marked [VERIFY] were not checked today against each platform's current documentation.
