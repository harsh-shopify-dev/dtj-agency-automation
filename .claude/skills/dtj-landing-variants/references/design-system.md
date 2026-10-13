# Design system and premium checklist

## Tokens (app/globals.css, overridden for variants in app/landing-fixes.css under `.lp-fixes`)

| Token | Value | Notes |
|---|---|---|
| paper (page background) | `#f7f5f2` | cream |
| ink (dark panels) | `#111111` | |
| text / text-2 / text-3 | `#151515` / `#555555` / `#6b6b6b` (`.lp-fixes`; original `#777`) | |
| brand (original) | `#ff5500` | use as-is only on dark backgrounds (5.89:1 on `#111`) |
| brand in `.lp-fixes` | `#e64c00` | accent text on paper 3.57:1 and white 3.89:1 (large text only), dark text on it 4.69:1 |
| button orange (white label) | `#d64000` | 4.57:1 — `.lp-fixes .bg-brand.text-white` does this automatically |
| accent in white cards | `#d64000` | 4.57:1 — `.lp-fixes .bg-white .text-brand` |
| grey labels on paper/white | `#63636b` | 5.47:1 / 5.95:1 |
| grey label on ink | `#8b8b95` | 5.6:1 |

Fonts: Figtree (sans, everything), Instrument Serif italic (accent phrase in headings, `font-accent`), Geist Mono (small labels).
Check any new colour pair with
`python D:/CODE CONTAINERR/WEB DEV/dtj-agency-automation/.claude/skills/dtj-pdp-design-review/scripts/palette_report.py --contrast "#FG:#BG"`.
Normal text needs 4.5:1; text 24px+ (or 18.66px+ bold) needs 3:1.

## One style for the simple pages (`components/simple/styles.ts`)

- `H2`: `clamp(28px,4vw,46px)`, semibold (600), `leading-[1.08]`, `tracking-[-0.035em]`, left aligned, sentence case. Add the
  colour (`text-text` on light, `text-paper` on dark). Every section heading uses it (the check script enforces one style).
- `ACCENT`: the italic serif accent phrase (`text-brand`).
- `LEAD`: one-line intro under a heading (16–17px, text-2).
- `SECTION`: `bg-paper px-5 py-12 sm:px-8 md:py-16`. `SECTION_TOP`: the same with top padding only, for a light section
  followed by another light section (case studies → reels → reviews), so the gap is one step, not two.
  `CONTAINER`: `mx-auto max-w-[1240px]` so every left edge lines up.
- **One gap between blocks: 48px on phones, 64px on desktop**, and 32px (`mt-8`) from a heading to its content. Never stack
  paddings: a component nested in a padded section gets its own padding switched off (`PerformanceCreative flush`,
  `ServicesStack flushTop`), and the form section has no bottom padding (the FAQ's top padding is the gap).
- Dark panels: `bg-ink`, `rounded-[1.75rem] lg:rounded-[2.5rem]`, outer `px-3 sm:px-5 lg:px-8`.
- Cards: white, `rounded-2xl`/`rounded-3xl`, `border border-text/10`, soft shadow only on hero proof cards.
- Buttons: `FormLink` (orange pill, uppercase 13px, `tracking-[0.06em]`, arrow). Secondary: white pill with border.

## Components to reuse (optional props keep `/` identical)

| Component | Props for variants |
|---|---|
| `Header` | `ctaLabel` (node; use `<HeaderCtaLabel/>`), `logoLink={false}` |
| `TrustStrip` | `reviewLabel="208+ 5-star"`, `stacked` (phones: one joined card) |
| `Hero` (v2 only) | `eyebrow`, `brief` (13-word line under the headline, no slack under the stats) |
| `RealResults` (v2) | `collapse={{ mobile, desktop }}` |
| `ClientShowcase` | `link`, `brief` (heading's first line only; no paragraph, no link) |
| `ServicesStack` | `headlineIsHeading`, `mobileStats`, `outboundLinks={false}`, `keyboardRows`, `flushTop`, `brief` (name, tag, headline, proof; no paragraph; plainer Performance headline) |
| `MarketplaceVisual` | `fullChartLink` |
| `ShopifyPDPVisual` | `showLift={false}`, `autoPanOnTouch` (touch screens auto-pan; mouse scrolls by hand) |
| `PerformanceCreative` | `embedded`, `showHeader={false}`, `keyboardRows`, `flush` (no vertical padding), `brief` (no intro paragraph) |
| `ReviewsMasonry` | `brief` (short heading, no sub line, no second "208+" badge) |
| `CaseStudies` | `brief` ("Real Brands. Real Numbers."; headline + numbers + picture, no paragraph) |
| `SectionCTA` | `ariaLabel` (unique per band); `body` and `note` optional (variants: heading + button + short note) |
| `BookCall` / `LeadForm` | `markRequired`; BookCall `brief` (heading + 3 take-aways; no badge, intro lines or "clear opportunity" line); `compactForm` / `compact` (the short form: no title, 44px fields, name + brand side by side, two-line message box with a plain example, "Get my free audit" on the button under 380px) |
| `ReviewCard` | `clamp` (six lines + "Read more"; use in rows so one long review doesn't leave blank space under the rest) |
| `Faq` | `questions`, `headingClass` (left-aligned page style) |
| v2/simple only | `FormLink`, `SkipLink`, `HeaderCtaLabel`, `HowItWorks` (`STEPS`), `SimpleReviews`, `SimpleForm`, `LogoWall`, `ResultCards`, `CaseStories`, `HeroProofCard` |
| `FounderBand` | "Meet Tushar Joshi": photo, title, the company line (not a quote), ₹70Cr+ / 90+ tiles, button. On every variant, never `/`. `flushTop` when the section above ends with its own padding |
| `StickyCta` | Phone-only bottom bar ("Free growth audit · Start"), shows after the first screen, hides while `#audit` is on screen. The page wrapper adds `max-md:pb-20` |
| `StepForm` | The lead form as 5 steps (taps first: where you sell, ad spend, sales; then brand; then contact). Same fields/validation/payload as `LeadForm` (helpers exported from it), `form_step` dataLayer events. Used on `/audit` |
| `TodayVsAfter`, `AuditContents` | Red ✗ "Today" vs green ✓ "With DTJ" (pain-page lines); what the audit shows (3 items + a drawing, desktop only, until a real sample audit) |

Need a new behaviour in a shared component? Add an **optional prop whose default renders exactly what it renders today**, keep
the default class strings byte-identical, then prove it with `scripts/diff_original.py`.

## Premium checklist (lessons from 10 Oct 2026 — each one was a real correction)

1. **One heading style per page.** Mixing Title Case/centred legacy sections with the new style read as "two sites stitched
   together". Reused legacy sections get a page-style heading (`headingClass`, `showHeader={false}` + own heading).
2. **Shapes that join must share geometry.** A fully round pill sitting on a square-shouldered card "looked kinda weird". The fix:
   one card with one radius, one shadow, one hairline; the inner band's bottom corners curve into the band behind it.
3. **No scroll traps.** A scrollable box near the top of a phone page captures swipes. On touch screens make it auto-pan
   (`autoPanOnTouch`) and let swipes move the page; keep manual scroll for mouse users.
4. **Proof must be readable on a phone.** Put the number in a card (₹, orders); the screenshot is supporting evidence.
5. **Say a claim once.** "208+" once (top strip); no second rating badge in the reviews or form.
6. **No two look-alike numbered lists.** "What we do" (3 steps) and "How it works" (3 steps) side by side confused the service
   with the process; How it works lives inside the form panel.
7. **Show everything, keep it short.** Harsh wants all results, case studies, reels and reviews shown. Sets longer than a
   screen go in a swipe row (`snap-x`, next card peeking at 85–88% width, `relative`, focusable, arrow buttons on desktop) instead
   of stacking; 12 logos on phones.
8. **Rhythm:** light → dark band → light. Left-aligned sections; only small labels (logo strip) are centred.
9. **Phones:** nothing under 12px; header button one line (`HeaderCtaLabel` under 380 px); the form panel uses `px-3` so the
   form gets the width and its submit button stays on one line; no horizontal overflow from 320 to 1440 px.
10. **Numbers over words.** Big ₹ numbers and pictures carry the page; no paragraphs; ≤ 200 words outside reviews/form/FAQ.
    Process is never explained beyond three short step titles. (Harsh: visual audience, numbers and results only.)
11. **Hero:** no eyebrow line above the headline (Harsh removed it). The proof card is the visual; don't add images that don't
    prove something (Harsh: the conversion-rate card in the hero "doesn't make sense"; use the two scrollable screens).
12. **Accessibility:** contrast as above, skip link, `aria-required` on required fields, unique landmark names, focusable
    keyboard rows when motion is reduced, `aria-label` when a section has no visible heading.

Lessons from 12 Oct 2026 (Harsh: "huge white space top and bottom… make it extremely compact but neat… the contact form is
very long… verify the page is not long for stupid reasons"):

13. **No stacked spacing.** The reels block had section padding + its own padding (144px of nothing on a phone). One gap
    between blocks (see above); `check_pages.py` now fails any empty band over 72px (phone) / 104px (desktop).
14. **Compact form.** The form panel is heading, "Takes under a minute. It's free.", three numbered step titles, then the
    compact form. Don't repeat a line the FAQ right below already says. Keep every field (they qualify the lead).
15. **Rows keep one height.** Review cards are clamped to six lines with "Read more" and stretch to equal height; case-study
    numbers sit on one line at the top of each column (`whitespace-nowrap`, sized to fit 320px), labels below.
16. **Desktop is short too.** Four case studies sit in one row from 1280px (`xl:grid-cols-4`) instead of a tall 2 × 2.
17. **Headline + number + button, no paragraph.** (Harsh, 12 Oct 2026: "a lot of written content… make it shorter, cut the
    not needed stuff and speak directly".) Every variant uses the `brief` props above: paragraphs under headlines go, jargon
    headlines get a plain one ("Ads That Make Profit, Not Just Clicks."), CTA bands lose their body line, process steps are
    titles only, each line is said once ("clear opportunity" only in the FAQ, "208+" only in the top strip). v2 went from
    678 to 244 words outside reviews/form/FAQ. **The original page `/` keeps its full text** (Harsh: "leave that one").
18. **Premium = photography, bold type, big buttons, proof cards — not code.** Main buttons ≥ 48 px tall (`FormLink`);
    no page-builder tricks, sliders or animation libraries (competitors that use them load in 2.5–9.6 s on a phone).
