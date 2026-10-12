# Page anatomy

## The simple pain page (current standard)

Built by `components/simple/SimpleLanding.tsx`; the copy comes from one `PainPage` entry in `components/simple/content.ts`.
Order and the job of each block:

| # | Block | Job | Rules |
|---|---|---|---|
| 0 | Header (`Header ctaLabel={<HeaderCtaLabel/>} logoLink={false}`) | Brand + one button to the form | Logo is not a link. No nav. Button stays one line on phones. |
| 1 | Rating strip (`TrustStrip reviewLabel="208+ 5-star" stacked`) | Instant credibility | The only place "208+" appears. Phones: one joined card (Google band on top, Trustpilot below). |
| 2 | Hero (`SimpleHero`) | Name the pain, one promise, the button, one real proof | Headline = pain question with an italic accent phrase, ≤ 9 words. No eyebrow line above it (Harsh removed it). Sub-line ≤ 14 words. Under the button: "Free · No pressure · Takes under a minute". Proof card on the right (desktop) / below (phone): `meta-report`, `page-screens` (scrollable before/after phones, auto-pan on touch) or `royal-dosa`. |
| 3 | Real results (`ResultCards`) | Numbers first | Heading "Real results" + every `ROWS` brand: earlier sales small in red → today's big in green, "in sales". 2 per row on phones, 3 on desktop. Footnote "From each brand's own Shopify sales report." |
| 4 | Logo wall (`LogoWall`) | "Others like me trust them" | Small centred label "Trusted by 90+ D2C brands". 12 logos on phones, 27 from md. Never linked. |
| 5 | Symptoms (`Symptoms`) | Recognition: "that's me" | "Does this sound like you?" + 4 short tick cards (2×2 from sm) + button. |
| 6 | What we fix (`Fixes`) | Problem → result, no process | Dark band (rhythm: light → dark → light). 3 cards: ✕ problem (muted) → fix (bold). |
| 7 | Case studies (`CaseStories`) | Full proof | Every case study (picture + brand + numbers). Swipe row on phones, 2×2 grid from md. |
| 8 | Our work (reels) | Show the ads | "Ads that get people interested in buying." + `PerformanceCreative embedded showHeader={false} keyboardRows`, full bleed. |
| 9 | Reviews (`SimpleReviews`) | Social proof | Every review as it is, full text, one swipe row with arrow buttons on desktop. No second rating badge. |
| 10 | Form (`SimpleForm`) | Convert | Dark panel, kept short: "Get your free growth audit", "Takes under a minute. It's free.", 3 numbered step titles (shared `STEPS`, list labelled "How it works"), `LeadForm markRequired compact`. The "clear opportunity" line is in the FAQ right below, so it isn't repeated here. Ids `#audit` / `#audit-form`. |
| 11 | FAQ (`Faq headingClass=…`) | Remove last doubts | 4 questions, confirmed answers only, ≤ 16 words each. Ends with a button. |

Since 12 Oct 2026 every variant also has `FounderBand` (after the logo wall) and `StickyCta` (phones).

**`/audit` (form-first page):** pain headline + one line + the 5-step `StepForm` as the hero (facts row beside it on desktop, under it on phones) → real results → logos → `FounderBand` → `TodayVsAfter` → `AuditContents` → case studies → reels → reviews → closing dark band → FAQ. Built from the competitor study (`docs/landing-page/2026-10-12-competitor-landing-pages/README.md`): Hormozi's one-question form, Rahul Malodia's Today/Shift and facts row, the founder-led pages, the always-visible phone button.

No footer, no social links, no links that leave the page.

## The ThrillX B2B wireframes (reference blueprint)

Source: Figma "Public Landing Page – ThrillX", page "LANDING Page Public" (analysed 10 Oct 2026). Two B2B pages, each a desktop
and a 414 px phone frame. View a frame read-only with the prototype URL (the design canvas is too small in the pane):
`https://www.figma.com/proto/Rf0YJB4UQpWiOsuhuMFesX/Public-Landing-Page---ThrillX?node-id=<id>&scaling=scale-down-width&content-scaling=fixed&hide-ui=1`
— V1 desktop `2-15`, V1 phone `37-5504`, V2 phone `37-5727`. (Headless browsers are blocked by Figma; use the built-in browser.)

**V1 (B2B / General Landing Page V1)**
1. Phone-number bar (phone) / header with logo, phone number, CTA button.
2. Hero, split: eyebrow "Social proof #1"; H1 "Dream outcome and 'what's in it for me'"; sub "Stop doing X | No more Y |
   pain point. Our solution does X, Y, Z (explain how, in a proprietary or unique way)"; main CTA; under it "Reduce friction and
   FUDs (fear, uncertainty, doubts)"; right: image, video or form that reinforces the value proposition.
3. Social proof #2 strip (logos).
4. Social proof section (stats, testimonials, case studies): 3 cards + CTA.
5. Pain: "Address the largest pain point you solve and the 'old way' while tying in your unique benefit" (paint the prospect's
   pain, expose the flaws of the status quo) + CTA.
6–8. Value prop and big benefit #1, #2, #3 ("WIIFM"), eyebrow "Dream outcome summary", image/text alternating, CTA each.
9. Social proof section (one large proof) + CTA.
10. "Benefit-driven headline: how you do it and what makes you different" + 6 differentiators + CTA.
11. "How it works? (make the perceived likelihood of success high and effortless)" + 3 steps + CTA.
12. Meet the team + CTA. 13. Guarantee (optional) + CTA. 14. Social proof #2 strip again.
15. FAQ (6 questions) + CTA.
16. Final recap: "Why should people take action today (create urgency)", one final reason, value-prop checklist ×3, CTA,
    friction reducer. 17. Footer.

**V2 (B2B / General Landing Page V2)** — same spine, three changes: a dark hero with a background image/video; the hero sub-line
becomes a 3-tick value-prop checklist; and a **lead-capture form in the hero** ("capitalize on above-the-fold real estate").
The phone frame drops Meet the team and Guarantee. (The desktop frame has a grid block that could not be read at the zoom
available; unverified, possibly a comparison table.)

**ThrillX principles worth keeping:** lead with the dream outcome and WIIFM; a friction reducer right under every main CTA; the
same single action repeated after every section; social proof early and again near the end; name the pain and the "old way";
make success feel likely and effortless (How it works); finish with a recap that gives one reason to act today.

## How DTJ maps to ThrillX

| ThrillX | DTJ simple page | Status |
|---|---|---|
| Header phone + CTA | Header CTA only | Phone left out on purpose: DTJ checks leads first; ask Harsh before adding a phone/WhatsApp. |
| Hero: outcome H1, pain sub, CTA, FUD reducer, visual | Pain-question H1, promise, CTA, reducer, proof card | Adapted (pain-first for non-technical founders). Outcome-first H1 = test candidate. |
| V2 form in hero | Form at the end | **Test candidate**: short form in the hero for cold traffic. |
| Social proof #1/#2 | Rating strip + logo wall + results + reviews | Have. |
| Pain + old way | Symptoms + What we fix (problem side) | Have, in a few words. |
| Value props ×3 with images | What we fix (fix side) + results/case studies | Have, as numbers and pictures (no text blocks: the audience doesn't read). |
| Differentiators ×6 | — | Missing: needs real DTJ differentiators from Harsh (don't invent). |
| How it works | Folded into the form panel | Have. |
| Meet the team | — | Missing: needs approved team/Tushar photos and captions. |
| Guarantee | "If we don't see a clear opportunity, we'll tell you." | Have (light risk reversal). Never invent a guarantee. |
| FAQ ×6 | FAQ 5–6 | Have. |
| Final recap + urgency | — | **Candidate**: recap checklist + button after the FAQ. Urgency must be real (no fake deadlines or scarcity). |
| Footer | — | Dropped on purpose (Harsh: no distractions). |
| CTA after every section | Hero, symptoms, form, FAQ | Option: add buttons after results and reviews (they're not exits). |
| Long text blocks | — | Dropped on purpose (Harsh: visual audience, numbers and results, no process). |

## Variants

Built (branch `feature/landing-v2`): `/` (original, control), `/v2` (technical audience + audit fixes),
`/ads-no-orders` (S1), `/sales-stuck` (S3), `/website-no-sales` (S2).

Planned candidates (pains are hypotheses until Harsh confirms): S4 "I pay an agency but don't know what's happening with my money";
S5 "My Amazon sales are low" (fix the Amazon numbers first); S6 "My shop sells well offline; I want to sell online" (needs a real
client example); S7 SEO (fold into S3). Structural tests: form in the hero (ThrillX V2), outcome-first headline, final recap.
Language: founder English only (Gujarati version only if Harsh asks). Judge by cost per **qualified** lead once tracking exists.
