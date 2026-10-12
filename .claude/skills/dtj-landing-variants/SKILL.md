---
name: dtj-landing-variants
description: Runbook for DTJ's OWN lead-generation landing page ("free growth audit", digitaltusharjoshi.com/free-growth-audit, repo D:\CODE CONTAINERR\WEB DEV\DTJ) and every variation of it - the plain-English pain pages for non-technical Gujarati D2C founders (/ads-no-orders, /sales-stuck, /website-no-sales), the founder-led step-form page /audit, /v2, and any new one. It holds Harsh's standing rules (no footer or links off the page, the real lead process with no "call with Tushar", founder language not Gujlish, use the client's assets as they are, no new claims, the original page untouched), the copy voice and jargon table, the claims and asset inventory with exact numbers, the page anatomy mapped to the ThrillX B2B wireframes, the design system and premium checklist, the codebase map and pitfalls, and QA scripts (accessibility, overflow, scroll traps, exit links, original-page diff). Use it whenever the task touches DTJ's landing page or its variants - build, add, redesign, restyle, copy, audit, fix, review screenshots, "create another version/variant", "make a page for <pain point>", or Harsh pastes a screenshot of one of these pages and asks for a change - even if he doesn't name the skill. Not for client store product pages (use dtj-pdp-factory) or client-facing audits with PDFs (use dtj-landing-page-analysis).
---

# DTJ landing page variants

DTJ (Digital Tushar Joshi) gets its leads from one landing page: a free growth audit request form. This skill builds and maintains
that page's variations. Most founders it targets are Gujarati D2C owners who are **not** technical (about 75–80 of every 100),
so the variations speak plain founder English, take one pain per page, use very few words, and prove everything in rupees and
pictures (they look at numbers and results; they don't read paragraphs or care how the process works). The bar: a founder reads
the headline and thinks "that's me", trusts what they see, and fills the form, with nothing on the page pulling them away and
nothing on it untrue.

Read `HANDOFF.md` in the site repo first; it is the running log. Then follow the phases below. Each phase ends with a gate.

## Non-negotiables (why in brackets)

1. **No distractions.** No footer, no nav, no social or outbound links, no new-tab links, and the logo is not a link. Every button
   goes to the form. (Harsh, 10 Oct 2026: "we don't want our clients to get distracted"; he removed the footer and both exits.)
2. **The real lead process.** "We check your details first, then our team gets in touch" (call, WhatsApp or email). Never a
   "direct strategy call with Tushar", never a response time. (Harsh, 10 Oct 2026: Tushar doesn't take the first call.)
3. **No new claims; assets as they are.** Every sentence traces to the main page, a screenshot's numbers or the lead process
   (`references/claims-and-proof.md`). During client approval, reviews, ratings and stats are shown exactly as they are, placeholders
   included; never remove, "fix" or add them on your own, and list the pre-launch replacements in every report. (Harsh: "use all
   the assets as it is… once we get approved we will replace those"; CLAUDE.md rule 5.)
4. **Founder language, few words, numbers first.** Plain English, no jargon, not Gujlish; numbers and pictures carry the page,
   no paragraphs, no process explained; word budgets per block and ≤ 200 words outside reviews/form/FAQ
   (`references/audience-and-voice.md`). (Harsh, 10 Oct 2026: "a visual audience… they speak only numbers and results; they
   are not interested in a complex process we do".)
4a. **Show all the proof.** Every result, case study, the reels and every review on every page; long sets swipe instead of
   stacking. (Harsh, 10 Oct 2026: "we have to fully show our case studies, work, reviews".)
5. **The original page `/` stays as it is.** Shared components only gain optional props whose defaults render exactly as before;
   `scripts/diff_original.py` proves it. (`/` is the control for testing variants.)
6. **One premium design system.** One heading style, one button style, shared tokens and contrast fixes; follow the premium
   checklist (`references/design-system.md`). (Each item there was a real correction from Harsh.)
7. **Phone first.** Design and check at 390 px before 1440 px: no text under 12 px, no overflow, no scroll traps, buttons on one line.
8. **Test pages stay out of search** (`robots: noindex`). Deploying, uploading to Hostinger, committing and pushing are Tier 2: ask
   Harsh every time. Work on `feature/landing-v2` (or a branch Harsh names), never on `main`.
9. **Honest reporting.** Say what was verified and how, and what was not (Hostinger build, real phones, form submission, tracking).

## Phase 0 — Orient
- Read `D:\CODE CONTAINERR\WEB DEV\DTJ\HANDOFF.md`, check the branch and `git status`.
- Start the dev server (`references/codebase-map.md` → Run it). If `/` shows "not found", apply the stale-cache fix.
- **Gate:** `diff_original.py` says unchanged and `check_pages.py` passes on the existing variants, so you know the starting state.

## Phase 1 — Brief
- One pain per page, in the founder's words. Pains are hypotheses until Harsh confirms them (the leads Sheet's "biggest challenge"
  answers are the best source). Candidates and status: `references/page-anatomy.md` → Variants.
- Pick the hero proof and the results to show from the asset inventory (`claims-and-proof.md` §3). Match proof to pain (ads → Meta
  report and reels; website → before/after phones; growth → Royal Dosa and case studies).
- List any fact you need but don't have (§5) and ask Harsh in one short message. Don't block on it: build with what's confirmed.
- **Gate:** the pain, proof and open questions fit in three lines.

## Phase 2 — Copy
- Write the `PainPage` entry (`codebase-map.md` → Add a pain page) with `audience-and-voice.md`: pain-question headline
  (≤ 9 words) with an accent phrase, a ≤ 14-word promise, four short symptoms, three "problem → what we fix" pairs, four FAQs
  from confirmed answers only. Results, case studies, reels and reviews come in automatically, all of them.
- **Gate:** every line passes the jargon table and the word budgets, and traces to `claims-and-proof.md`.

## Phase 3 — Build
- Route file + content entry. Reuse the simple blocks; a new block goes in `components/simple/` and uses `styles.ts`.
- Changing a shared component: optional prop, default byte-identical, comment saying why.
- Layout and order: `references/page-anatomy.md` (and the ThrillX mapping for anything new: differentiators, final recap,
  form-in-hero are known candidates).
- **Gate:** `npx tsc --noEmit` and `npx eslint app components` silent.

## Phase 4 — QA (code)
- `scripts/diff_original.py` → unchanged. `scripts/check_pages.py --pages <slugs> --shots` → RESULT: PASS.
- **Gate:** both pass; failures fixed, not explained away.

## Phase 5 — Look
- Review the phone sheet and desktop screenshot against the premium checklist (`references/qa-and-handoff.md` → Gate 4).
- **Gate:** you would show it to Harsh's client without apologising for anything.

## Phase 6 — Report and hand off
- Report in plain words, result first (`qa-and-handoff.md` → Report). Update the site `HANDOFF.md`. Don't commit unless asked.

## Files
- `references/audience-and-voice.md` — who reads it, founder language, jargon table, approved lines, never-write list.
- `references/claims-and-proof.md` — allowed claims, the lead process, asset inventory with exact numbers, placeholders, missing facts.
- `references/page-anatomy.md` — the simple page block by block, the ThrillX B2B wireframes V1/V2 and how DTJ maps to them, variants.
- `references/design-system.md` — tokens and contrast, the one heading style, reusable components and props, premium checklist.
- `references/codebase-map.md` — repo, branch, file map, add-a-page template, run and build, pitfalls.
- `references/qa-and-handoff.md` — the gates, the report shape, the handoff.
- `scripts/check_pages.py` — behaviour/accessibility gate. `scripts/diff_original.py` — original-page gate.
- `assets/original-page-baseline.txt` — the normalised HTML of `/` the diff compares against.
