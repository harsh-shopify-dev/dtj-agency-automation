---
name: dtj-pdp-factory
description: DTJ store factory runbook for designing and shipping a client's Shopify product page (PDP) from our DTJ app blocks. Every page uses the same fixed set of sections from the agency's ThrillX wireframe ("DTJ Standard Product Page v1"), each section analysed and then designed, filled completely (real facts first, clearly marked sample content for the rest), coloured to the product's vibe, reviewed for design and CRO, and written only to a draft theme after Harsh's yes. Use it whenever the task is to build, redesign, plan or fix a product page / PDP / landing page for a client or test store. Also use it to onboard a new client store (app copies, install catcher, licence, block addresses), to answer a Store Factory plan or copy request from n8n, or when Harsh says a page looks dull, thin or repetitive, even if he only pastes a store, theme or product link and says "design this". Also use it whenever someone wants product copy (a short description, tagline, benefit lines, headlines) that makes shoppers feel the product, for any category.
---

# DTJ product page factory

You are the designer AND the engineer on this page. The bar: a senior D2C designer would sign it, a CRO lead would not find an
unanswered doubt, and nothing on it pretends to be true when it is a sample. The same inputs must give the same page whichever
model or account runs this: the judgement is written down here and in `references/`, and the checks are code. Follow the phases
in order; each ends with a gate.

## What you produce (per product)
In `.work/clients/<client>-<product>/` (git-ignored): `brand.json` (with `vibe`), `facts.json` (every fact with a source; samples
have a source starting with `SAMPLE`), `SOURCES.md`, `wireframe-plan.md` (sections, claim ledger, section notes, samples list),
`plan-answer.json`, `copy-answer.json`, `run/` (builder output), `review/` (the review skill's report), `content-needed.md`
(what the client must send, which replaces the samples) and a graphics brief for every sample or empty picture.

## Non-negotiables (why in brackets)
1. **The sections are fixed.** Every page = "DTJ Standard Product Page v1" in `references/wireframe-ecom-product.md` section 1:
   the same sections, order and blocks for every product. Never choose, drop, reorder or add sections per product. (Harsh,
   10 Oct 2026: one proven base; a human CRO expert customises later as the brand grows.)
2. **Fill every section; mark every sample.** Real content first (client facts, the brand's public pages, the pack); then
   realistic, modest SAMPLE content so the design is complete. Every sample's source starts with `SAMPLE`, is listed in the plan
   and the build report, and is replaced or signed off by Harsh before live. Never sample medical claims, "clinically proven",
   competitor names, licences or certifications, prices, discounts or offers. (Harsh, 10 Oct 2026; CLAUDE.md rule 5 "mark
   unknowns clearly".)
3. **Analyse each section fully before designing it** (`references/section-design-method.md`: material, ledger, 8 steps).
4. **The vibe decides colour and motion** (`references/colour-and-vibe.md`, `references/motion-by-category.md`): an energy
   product must look energetic, a calm or fashion product must not shout. Contrast is never traded away.
5. **Mobile first.** Design and review at 390 px before 1280 px.
6. **Draft theme: push without asking; live theme: never without Harsh's go-ahead.** Harsh's standing rule (10 Oct 2026): "push the
   design to draft theme without asking", once the target draft is clear (it matches his global "dev themes are fine once the target
   is clear"). Use the build's own approve code with `--approved-by "Harsh (standing: draft pushes without asking)"`. App releases,
   product or store creation and anything live still need his yes. A page with samples goes only to a draft theme. Automation never writes a live theme; `--allow-live` is blocked in `.claude/settings.json` on purpose: never hide
   it inside a script. (Tier 2; CLAUDE.md rules 2 and 10.)
7. **Secrets stay in Windows variables.** Never print, paste or commit them; check them by name, length and prefix only.
8. **Honest reporting.** Say what was verified and how (tests, screenshots, storefront HTML) and what was not.
9. **Copy that makes the shopper feel it, never claim more.** Every page gets voice lines written with
   `references/copywriting.md` (the MojoVibe standard: an enemy, a sensory paradox, a payoff). Each line stands on a sourced
   fact, is marked `DTJ COPY (basis: ...)` and is signed off by the client; no health, body or new claim words (lint L19).
   (Harsh, 10 Oct 2026: "whatever the category, the copy should kill it.")
10. **Harsh's design principles** (`references/design-principles.md`): dark for figures, light for ground; cards and icons
   stand apart; white words only on dark; short story cards; benefits in the buy box; one label per button; whole pictures;
   12 px side space; no single colour everywhere (white or contrasting details on every coloured surface); a bright orange or
   yellow is a fill, never darkened into brown; calm pages get near-white cards; a named reference brand is measured first; a
   colour change is swept across the whole page. `design_checks.py` must pass all 11 checks before any push, and again on every
   re-verification.

## Phases

### P0. Orient (every session)
Read `CLAUDE.md`, the latest entry of `docs/HANDOFF.md` and the client's folder if it exists. Confirm: store (original
`.myshopify.com` address), theme id and role (draft or live), product handle, and whether the client's app copies are installed
(`python services/install-catcher/tools/licence_call.py <client>-blocks status`). **Gate:** all four known, or one precise question.

### P1. Client store setup (new store only)
`references/pipeline-commands.md` section A, exactly. **Gate:** all 3 licences `active`; `page_builder/clients/<name>.json`
exists with no `pending` handle.

### P2. Facts, store checks, brand
- **Ask first: collect the brand's data?** (Harsh, 19 Oct 2026: "it should ask me if it should run the scraper or not and using
  the data available it should start designing"). A brief from n8n carries the answer in `brand_intake` (read the row when you
  start: the requester taps Yes / No in Telegram after the page is started); otherwise ask the person at the laptop.
  - Yes: `python -m page_builder.brand_intake <brand site> --client ../../.work/clients/intake-<host>` (add `--drive "DTJ Clients"`
    when the laptop has the DTJ_GDRIVE_* keys): pictures and videos of up to 20 products, logo, policies, fonts, theme colours and
    a palette proposal in `.work/clients/intake-<host>/intake/`, one folder per website, shared by every page of that brand.
  - No: do not collect it again; use an earlier `.work/clients/intake-<host>/intake/` when there is one.
  - Start P2 from its BRAND.md, brand.json (draft) and brand-intake.json (every fact with its source); the colours, category and
    price tier are guesses to confirm against the pack and the brand site.
- Material in order: client facts, the brand's own public pages (product page, FAQ, policies, a public reviews widget) with URL
  and date as source, the pack and every product picture (read what they print). `references/facts-intake-checklist.md`.
- Store checks (public product JSON and page): title (placeholder?), stock ("Sold out"?), pictures (how many, any with printed
  claims that are unconfirmed?), policy pages (missing or template text?). Anything wrong goes to Harsh before design.
- Write `facts.json`, `brand.json` (with `vibe` and one line of why), `SOURCES.md` (what is real, what is sample, what was left
  out), and start `content-needed.md`.
- Collect the SENSORY material for the copy (`references/facts-intake-checklist.md`, "Voice"): what it tastes, feels, smells,
  sounds or looks like in customers' own words, the situation they hate, how they use it, the badges the label really supports.
**Gate:** every fact has a source or a SAMPLE mark; no forbidden sample; vibe chosen; store problems reported; every badge
checked against the ingredient list and label.

### P3. Plan the fixed sections
Claim ledger, then every section of the fixed set in order with its block, background role, headline, item counts, samples and
readiness (block or builder gap), using the template in `section-design-method.md`. Choose the CTA label and action and the
signature section(s). Write the seven **voice lines** (`references/copywriting.md` section 3: core, paradox, enemy, payoff,
rhythm, identity, before and after), each with the fact it stands on, and place them with the table in its section 6.
**Gate:** every section planned and FILLED (real or sample); no claim has more than one home; the samples list is complete;
every voice line names its fact and passes the self-check in `copywriting.md` section 8.

### P4. Design each section (the 8 steps, one at a time)
For every section: spec and screenshot, material, the block's real settings, words, look, phone form, CTA, self-check; a short
paragraph each under "Section notes". Words follow `references/copywriting.md` (the vibe sets the voice dial); look follows
`references/design-principles.md`. **Gate:** every section has notes and passes its self-check.

### P5. Build
Builder (pipeline section B): first `--plan dry --copy dry`, answer `plan-request.json` / `copy-request.json` so they match the
plan, then run with `answer` and `--client-registry`. Sections the builder cannot make yet (gaps G1, G9...) are listed as
"designed, waiting for the builder" with their full content in the plan, so they can be built the moment the gap closes.
Never hand-edit `template.json` (the next build undoes it and lint cannot check it).
**Gate:** exit 0 or 2, lint errors 0, build problems 0.
**Standard run since 10 Oct 2026:** once facts, brand, copy answer and media are ready, `python -m page_builder.ship_draft` (pipeline
section B0) does P5, the design-check part of P6 and P8 in one command with every gate in front of the draft write, and writes
`run/ship-result.json` (the answer for n8n). Use the separate commands only to debug a step.

### P6. Review (call the `dtj-pdp-design-review` skill)
Give it the run folder, the vibe and the plan. Fix and rebuild, at most 3 rounds. The local preview has a placeholder price and
grey stand-ins for theme parts: it checks structure only. The real verdict comes from the review on the draft page in P8/P9.
**Gate:** score >= 80 with samples counted as present, and no blocking finding; or after 3 rounds, show Harsh what is left and why.

### P7. Approval (Tier 2)
Draft theme: no approval step (non-negotiable 6); go to P8 and show Harsh the result afterwards (screenshots, samples, score).
Live theme: show Harsh in plain words the screenshots (390 and 1280), what each section does for the shopper, the list of SAMPLES
to replace, what needs a builder gap, the review score, the target and the approval code.
**Gate (live only):** Harsh's message contains "yes" and the exact code. One approval covers one page and one theme.

### P8. Write
Draft theme only: `push_page` (pipeline section D). There is no tool for a live theme: Harsh duplicates the theme or decides.
**Gate:** read-back identical, action-log row written.

### P9. Verify and hand over
Storefront check (pipeline section E) on the draft preview; run the review skill on that real page; optional kill-switch test
only when Harsh asks. Update `docs/HANDOFF.md`. Give Harsh `content-needed.md`, the samples list and the graphics brief.
Before any page with samples may go live: every sample replaced (rebuild) or signed off by Harsh one by one.

## Answering an n8n page request (a fresh session can do the whole page)
"Store Factory: New Page" (n8n `Z3s9hqny1d2shvXT`) turns a product link into a brief (the shop from the data table `dtj_stores`) and
starts "Store Factory: Page Design" (n8n `n8MzskKamTbVhZ3h`), which pauses at "Wait for Claude Code: Page Design". Its "Request for Claude Code:
Page Design" output holds a complete numbered task list (`instructions`): fetch the product (`page_builder.fetch_product`), P2-P4
here, a `ship_draft --design-only` run for the copy request, the `ship_draft` run that writes the draft, the real-page check, the
answer with `n8n/store-factory/reply.py`, the handoff entry. Follow it in order; how to find the waiting run is in `CLAUDE.md`
("n8n hand-offs"). The step code lives in `n8n/store-factory/*.js` (tested by `test_page_design_nodes.py`) and is deployed with
`n8n/store-factory/deploy_page_design.py`.

## Talking to Harsh
Lead with the result in one line, then what he must do (numbered, exact clicks), then detail. No jargon. Never ask him to paste a
secret in chat. When something failed: what, why, what you tried, the next step.

## Known gaps on 10 Oct 2026 (check `docs/HANDOFF.md` for newer status)
`references/wireframe-ecom-product.md` section 4: G1 `dtj-cta`, G9 the fixed set, V1 bold colours by vibe and S1 sample tracking
are BUILT (10 Oct); still open: G2-G8, D1 (built-in shadows), D2 (FAQ heading case). Until they
are built, plan the full content anyway and say which sections are waiting for which gap. New blocks:
`references/building-a-missing-block.md`.

## References (read when the phase says so)
| File | Read in |
|---|---|
| `references/wireframe-ecom-product.md` + `assets/wireframe/*.jpg` | P3, P4 |
| `references/section-design-method.md` | P3, P4 |
| `references/colour-and-vibe.md`, `references/motion-by-category.md` | P2, P4 |
| `references/facts-intake-checklist.md` | P2 |
| `references/copywriting.md` (MojoVibe analysis, method, voice dial, category starters, truth rules, Go Mints example) | P2, P3, P4 |
| `references/design-principles.md` (Harsh's reviews: 14 principles, Go Mints v2 vs v4 and the Hope N Skin colour rounds measured) | P2, P4, P6 |
| `references/pipeline-commands.md` | P0, P1, P5, P8, P9 |
| `references/errors-playbook.md` | whenever anything fails |
| `references/building-a-missing-block.md` | when a gap blocks a section |
| `../dtj-pdp-design-review/SKILL.md` | P6, P9 |
