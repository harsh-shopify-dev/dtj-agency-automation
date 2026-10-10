---
name: dtj-pdp-design-review
description: Design and conversion gate for a single Shopify product page (PDP) that DTJ builds or has built. It takes full-page screenshots at phone and desktop size, measures the colour palette against the product's vibe (an energy product must look energetic, a calm or fashion product must not shout), finds repeated claims and pictures, checks the first phone screen and the calls to action, scores the page on a fixed 100-point CRO rubric with blocking findings, and returns prioritised fixes mapped to the pipeline step that owns them. Use it after every page build in the dtj-pdp-factory pipeline, after writing a page to a store, and whenever someone asks whether a product page converts, why it looks dull, flat or repetitive, or what a designer would change. Use dtj-website-cro-analysis or dtj-landing-page-analysis instead for client-facing, site-wide or traffic-source audits with a PDF report.
---

# DTJ product page review: vibe, colour, repetition, CRO

A page can pass every lint rule and still not sell: the first Go Mints page had correct contrast and true copy, yet it looked like
a pharmacy leaflet, said the same four claims four times, used one picture eleven times and had one button on the whole page.
This review catches that, with numbers, so any model or account reaches the same verdict on the same page.

Work only from evidence. Every score cites a measurement, a quote or a screenshot region. The scripts are deterministic; your
judgement is used where the rubric says "looks" and must be written down with what you saw.

## Inputs
- A builder run folder (`.work/clients/<client>-<product>/run/`: `page-390.png`, `page-1280.png`, `template.json`,
  `build-report.json`) and/or a LIVE product URL (use `?view=<suffix>` for an unassigned template).
- The vibe (from `brand.json` or `wireframe-plan.md`; if missing, choose it with the table in
  `../dtj-pdp-factory/references/colour-and-vibe.md` and say so).
- `facts.json` and `wireframe-plan.md` when they exist (to check sources, omissions and the claim ledger).

## Steps

1. **Capture.**
   - Built page: use `page-390.png` and `page-1280.png` from the run.
   - Live page, desktop: full page in one shot (sections appear on scroll unless motion is reduced):
     `"<edge or chrome exe>" --headless=new --hide-scrollbars --force-prefers-reduced-motion --window-size=1280,9000
     --virtual-time-budget=10000 --screenshot=<review>/live-1280.png "<url>"` (find the exe with
     `python -c "from page_builder.browser import find_browser; print(find_browser())"` in `services/store-builder`).
   - Live page, phone: the built-in browser with the `mobile` preset (headless lays phones out too wide). Scroll from top to
     bottom taking a screenshot per screen; note each file path (the tool saves them). Reset the viewport afterwards.
   - Live page, facts: paste all of `scripts/page_audit.js` into the built-in browser's JavaScript tool at the phone preset,
     then again at desktop; save both JSON results in `review/`.
2. **Measure.**
   - `python scripts/palette_report.py <1280 shot(s)> --profile <vibe> --skip-top 120 --out <review>/palette`
     (and once on the phone shots). Read `dominant_colours`, `metrics`, `vibe.fit_score`.
   - `python scripts/template_audit.py <run folder>` for repeated text, reused pictures and which sections end in a CTA.
3. **Look** at every screenshot section by section against the wireframe
   (`../dtj-pdp-factory/references/wireframe-ecom-product.md` and its `assets/wireframe/` pictures). Squint test: blurred, does
   the page feel like its vibe? Is the buy button the loudest thing in its screen? Does each section have one job?
4. **Score** with `references/cro-rubric.md`. Blocking findings first. Separate the points lost only to missing client content.
5. **Recommend colours like a senior designer** when vibe or contrast lose points: give roles and hex values, and measure every
   new pair with `python scripts/palette_report.py --contrast "FG:BG" ...` before writing it down.
6. **Write the report** with `references/report-template.md` to `<run or client folder>/review/review.md`, and the metrics to
   `review/metrics.json`. Add a row to `references/calibration-log.md` whenever Harsh gives a verdict on the page's look.
7. **Return** to the caller (or to Harsh, in plain words): verdict, score, the three most important fixes, the content to ask
   the client for. In the factory pipeline, the parent skill applies the fixes; do not edit the page from inside the review.

## Judgement rules
- Score what the shopper sees. A section the builder omitted for lack of facts is "content-limited", not a design fault; a
  section that is present but thin, repeated or off-vibe IS a design fault.
- The vibe targets are starting points (`scripts/vibe_profiles.json`, calibrated in `references/calibration-log.md`). When the
  numbers and your eyes disagree, say both, and trust what a shopper would feel; record it in the log for calibration.
- Product photos carry their own colours: for editorial and appetite vibes judge the UI around the photos, not the photos.
- Never soften a blocking finding. Never invent a fix that needs facts the brand has not given; list the content instead.
- Report what you could not check (checkout, page speed, the theme editor, a password-protected store).
