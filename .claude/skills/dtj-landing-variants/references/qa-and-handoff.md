# QA gates, reporting and handoff

Run every gate after every change. Report what passed, what failed and what was not run, in plain words.

## Gate 1 — code

```
cd "D:\CODE CONTAINERR\WEB DEV\DTJ"
npx tsc --noEmit
npx eslint app components
```
Both must be silent.

## Gate 2 — the original page did not change

```
python "D:/CODE CONTAINERR/WEB DEV/dtj-agency-automation/.claude/skills/dtj-landing-variants/scripts/diff_original.py"
```
Must print "Original page unchanged". If Harsh asked for a change to `/`, verify it, then save the new baseline with `--update`
and say so in the report.

## Gate 3 — behaviour and accessibility

```
python "D:/CODE CONTAINERR/WEB DEV/dtj-agency-automation/.claude/skills/dtj-landing-variants/scripts/check_pages.py" --pages <slugs> --shots --out <scratchpad>/qa
```
Must end "RESULT: PASS". It checks, at phone and desktop: HTTP 200, no console errors, noindex, no footer, no exit links,
button targets exist, no overflow (and at 10 widths), no text under 12px on phones, no broken images, no empty band taller
than 72px (phone) / 104px (desktop) (it prints where: "empty band 144px at y=… (above -> below)"), one heading style,
"208+" once, ≤ 200 words outside reviews/form/FAQ, axe-core WCAG 2.2 AA clean, and no scroll trap on a touch phone. (`/v2` uses the main page's legacy styles and
is expected to fail "one heading style" and the 200-word budget (it has ~244 since the 12 Oct cuts); check it for everything else.)

## Gate 4 — look at it (the script can't judge taste)

Open `<out>/<slug>-phone-sheet.png` and `<slug>-desktop-full.png` and go section by section with `design-system.md`'s premium
checklist. Also look at 312px (Harsh checks there): numbers that collide, buttons that wrap. Look for: shapes that don't share
geometry, cramped or wrapping buttons, odd gaps, blocks taller than they need to be, images that prove nothing,
repetition, anything centred that should be left-aligned, anything that reads as jargon. Also check the first phone screen:
pain headline, promise, button and the start of the proof should be visible.

## Gate 5 — honesty

Every new sentence traces to `claims-and-proof.md`. No "call with Tushar", no response time, no invented number. Placeholders
from the client-approval phase are used as they are and listed in the report.

## Report to Harsh (plain words, result first)

1. What changed and where (URLs).
2. What was verified (gates 1–4 results) and what was not (Hostinger build, real phones, a real form submission, tracking).
3. Anything that needs his decision or facts (from `claims-and-proof.md` section 5).
4. The pre-launch list (placeholders to replace) whenever the pages are being shown to the client.

## Handoff

At the end of a session update `D:\CODE CONTAINERR\WEB DEV\DTJ\HANDOFF.md` (what changed, branch/commit state, open items) and,
for plan changes, `dtj-agency-automation/docs/landing-page/2026-10-10-variants-plan.md`. Don't commit or push without Harsh's ask.
