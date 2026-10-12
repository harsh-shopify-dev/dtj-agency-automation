# DTJ landing page variations for non-technical Gujarati founders (plan)

**Date:** 10 Oct 2026. **Status:** round 1 built (uncommitted, branch `feature/landing-v2` in the DTJ site repo): S1 at `/ads-no-orders`, S3 at `/sales-stuck`, S2 at `/website-no-sales`. **Language decided: plain founder English, not Gujlish** (Harsh). Still open: WhatsApp vs form, the real pain list, tracking. Decisions marked **DECIDE** are Harsh's.

## Who we're writing for

Gujarati D2C founders. Harsh's estimate: of 100, only 20-25 know D2C technicals (ROAS, CVR, funnels). The current page and `/v2` speak to those 20-25: dashboards, ROAS tables, "funnel", "CVR lift". The new variations are for the other 75-80.

What that means for every variation:

1. **One pain per page.** The founder should read the headline and think "yes, this is my problem".
2. **Their words, not ours.** No ROAS, CVR, ACOS, funnel, PDP or CAC. Say it in rupees and plain sentences:
   - ROAS 4.42X → "for every ₹1 spent on ads, ₹4.42 came back"
   - conversion rate 1.4% → 2.8% → "out of 1,000 visitors, 14 used to buy; now 28 do"
   - funnel → "the path from your ad to a paid order"
3. **Show, don't explain.** Simple "before → after" cards in rupees with the brand's logo instead of full analytics dashboards (those confuse non-technical readers).
4. **Familiar, local trust.** Clients they recognise, the real Google rating (the main site's widget shows 216 Google reviews, 5.0), the team and the office, and short client videos if any exist. Only real things.
5. **Easy first step.** A WhatsApp button and/or a 4-field form. DTJ checks each lead first and then the team gets in touch, so the page says exactly that.
6. **Short and big.** About 7 sections, large text and buttons, built for phones first.
7. **No distractions (Harsh's rule).** Every block must move the visitor toward the form. No footer, no nav, no social or outbound links, no links that open a new tab or go to another page (the logo included). A privacy policy link, when needed, goes in the form's consent line.

## Pain points: candidates to confirm

These are **hypotheses** from the page's own services and the form's "biggest challenge" examples, **not research**. The real list should come from Harsh and from the "Biggest challenge right now" answers in the leads Sheet.

| # | Pain (founder's words, draft) | DTJ service behind it | Real proof already on the page |
|---|---|---|---|
| S1 | "Ads are running, but orders aren't coming" | Meta/Google ads, ad creative | 6 sales dashboards, Meta totals (₹1 → ₹4.42), 16 real ad reels |
| S2 | "People visit my website but don't buy" | Shopify store and product pages | Pro Effex page before/after: 14 → 28 buyers per 1,000 visitors |
| S3 | "Sales have been stuck at the same level for months" | All of the above | Before → after sales lines on 6 brands |
| S4 | "I pay an agency but don't know what's happening with my money" | Clear reporting, honest advice | Real review: "honest suggestions instead of fake promises" |
| S5 | "My Amazon sales are low" | Marketplace | Amazon totals (see data check below) |
| S6 | "My shop sells well offline; I want to sell online" | Store build + ads | **Needs a real client example** |
| S7 | "I want customers from Google without paying for every click" | SEO | Dadu Fresh #1 for "healthy juice" |

My suggestion for round 1: **S1, S3, S2**. They're closest to what the page already sells and have the strongest real proof. S7 (SEO) is rarely how a non-technical founder describes the problem, so fold it into S3 rather than giving it its own page.

## One simple template, many variations

Build one "simple page" template once. Each variation is then just a content file: the pain, the copy, which proof and which language. Adding a pain or a Gujarati version is a copy job, not a rebuild.

1. **Headline:** the pain in their words, then one plain promise line and the button.
2. **"Does this sound like you?"** 3-4 symptoms with ticks.
3. **Why it happens:** 3 reasons in plain words, no jargon.
4. **What we do:** 3 simple steps.
5. **Proof:** 2-3 real client results in rupees with logos; a short client video if one exists.
6. **Trust:** the real Google rating, client logos, team/office photo (only if they want it shown). Shown, never linked.
7. **What happens next:** you contact us → we check your details → our team gets in touch.
8. **Simple FAQ and the final button.** Only true answers, e.g. "Do I need to understand ads?"; whether DTJ can speak Gujarati on the call is for DTJ to confirm.

Routes like `/ads-not-converting`, `/website-not-selling`, `/sales-stuck` (Hostinger: `/free-growth-audit/<slug>/`). All `noindex` while they're tests. They share the real data files with `/` and `/v2`, so a number fixed once is fixed everywhere.

## Decisions needed

- **DECIDE: language.** Options are plain English, Gujarati (script), Gujlish (Gujarati in English letters), or two versions of the same page. Any Gujarati copy I draft must be checked by a native speaker on the team before it goes live.
- **DECIDE: first step.** WhatsApp button, short form, or both, and which WhatsApp number. The footer phone (+91 97378 88822) is from the main site; is it on WhatsApp?
- **DECIDE: the final pain list** and how many go live first. More pages split the ad budget, and each page needs enough leads to judge.
- **Supply:** which clients are Gujarati founders and OK to name; any client videos; team or office photos; real answers on fees, minimum spend and lock-in.

## How to judge them

- **Before any test:** install the Google tag, Meta pixel and a form-submit event (the handoff says these are missing). Without them no variation can be compared.
- **Matched ads:** each pain page gets its own ad set with matching creative (the ad says the same pain as the headline).
- **The number that matters is cost per *qualified* lead,** not cost per lead. DTJ already checks every lead, so add a "qualified yes/no" column to the leads Sheet. The Sheet already records the page each lead came from (`page_url`).
- **Keep `/v2`** for the technical 20-25%.

## Data check before reuse

- **Amazon block:** the four figures don't agree with each other. ₹31,25,120.76 sales ÷ ₹6,00,090.71 cost = 5.21, but the block shows 5.55X ROAS and 18.02% ACOS (5.55 implies 18.02%, while cost ÷ sales is 19.2%). It may be a different date window or cost basis in Amazon's report. Confirm before using it in a simple "₹1 → ₹X" line.
- **Results numbers, Trustpilot badge, 16X and reviews:** used as they are, per Harsh, until he updates them. The audit's honesty points (F1-F6) still apply before paid traffic.
