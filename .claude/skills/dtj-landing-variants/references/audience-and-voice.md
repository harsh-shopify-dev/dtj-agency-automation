# Audience and voice

## Who reads these pages

Gujarati D2C founders (food, fashion, beauty, kids, supplements, home). Harsh's estimate (10 Oct 2026): of 100 founders only
20–25 understand D2C technicals (ROAS, CVR, funnels, PDPs). The other 75–80 run the business, pay for ads, see orders and money
in the bank, and do not think in marketing metrics.

- `/` (original) and `/v2` speak to the technical 20–25%: dashboards, ROAS tables, "funnel", "CVR lift". Keep them as they are.
- The simple pain pages (`components/simple/`) are for the other 75–80%. Every new variation for this audience follows this file.

## They look, they don't read

Harsh, 10 Oct 2026: "our target audience is much a visual audience as Gujaratis don't love to read much; they speak only
numbers and results; they are not interested in a complex process we do." So:

- **Numbers and pictures carry the page; words only label them.** Every block shows a number, a photo, a screenshot or an
  icon. No paragraphs. On a phone no text block runs past two lines except reviews.
- **Results right under the hero**, in rupees, big. Before → after, today's number largest.
- **Don't explain the process.** "How it works" is three short step titles (no bodies). No "why it happens" essays and no
  "what we do" descriptions; one "What we fix" block of three problem → fix pairs replaces both.
- **Show all the proof** (Harsh: "we have to fully show our case studies, work, reviews"): every result, every case study,
  the reels and every review on every page. Long sets go in a row you swipe (phones) instead of stacking, so "all" stays short.
- **Word budgets:** headline ≤ 9 words · sub-line ≤ 14 · symptom ≤ 7 · each side of a fix ≤ 7 · step title ≤ 5 ·
  FAQ answer ≤ 16 · 4 FAQ questions · section headings ≤ 6 words where possible. The whole page outside reviews, form and
  FAQ stays ≤ 200 words (`check_pages.py` enforces it; the three pain pages sit at 136–159, the main page at ~570).

## Language: founder English

**Plain English, short sentences, no jargon. Not Gujlish** (Gujarati in English letters) and not Gujarati script unless Harsh asks
for a Gujarati version (Harsh, 10 Oct 2026: "don't keep it gujilish but speak founder language"). If a Gujarati version is ever
asked for, a native speaker on the team checks it before it goes live.

Write the way a founder would describe the problem to a friend: "Ads are running but orders aren't coming", not "Your ROAS is
below breakeven".

## Rules

1. **One pain per page.** The headline is that pain as a question in the founder's words. The founder should read it and think
   "yes, that's me".
2. **No jargon.** Translate every metric into rupees, orders or people (table below). If a term has no plain version, leave it out.
3. **Rupees, not percentages, where possible.** "₹1.5L → ₹40.18L in sales" beats "+2,578%".
4. **Symptoms are things the reader recognises, not claims about DTJ.** "Lots of likes, very few buyers."
5. **In "What we fix", the problem side is a general cause, never a statistic; the fix side restates a DTJ service** from the
   main page (see `claims-and-proof.md`). Never a new promise.
6. **Short.** Keep to the word budgets above; when in doubt, cut.
8. **Sentence case** for every heading and button label in copy files (buttons render uppercase via CSS).
9. **The offer is always "free growth audit".** One name everywhere (button: "Get my free growth audit"; header: "Free growth
   audit", shortened to "Free audit" under 380 px by `HeaderCtaLabel`).
10. **The next step is always the real lead process:** "We check your details first, then our team gets in touch" (call, WhatsApp
    or email). Never "a call with Tushar", never a response time until DTJ confirms one.

## Jargon → founder words

| Don't write | Write |
|---|---|
| ROAS 4.42X | "For every ₹1 spent on these ads, ₹4.42 came back in sales" / "₹1 → ₹4.42" |
| CVR 1.4% → 2.8% / +100% CVR lift | "Out of every 1,000 visitors, 14 bought before; now 28 do" / "Same visitors, twice as many buyers" |
| Funnel | "the path from your ad to a paid order" |
| PDP / product detail page | "product page" |
| CAC / cost per acquisition | "what each order costs you in ads" |
| ACOS | leave out (no plain version a founder uses) |
| Scaling spend | "spending more on ads" |
| Creative | "ads" / "ad videos" |
| Retargeting / audiences / targeting | "the people your ads reach" |
| Conversion / converts | "buy" / "turns visitors into buyers" |
| Meta | "Facebook and Instagram" (keep "Meta" only next to "Google Ads" in service lists) |
| SEO | "showing up on Google when people search" (the service list may say "Google search") |
| Marketplace | "Amazon" |
| D2C | fine in the trust line ("Trusted by 90+ D2C brands"); avoid elsewhere |

## Lines in use (approved in this project)

- Hero: "Spending on ads every month, but *orders aren't coming?*" / "Sales stuck at the same number *for months?*" /
  "People visit your website, but *they don't buy?*"
- Sub-line: "We find where your ad money leaks, and fix it." / "We find what's holding your sales back. Then we fix it." /
  "You already paid to bring them. We fix your pages so they buy."
- Under the button: "Free · No pressure · Takes under a minute".
- Symptoms: "Ads run every month. Orders don't." / "Lots of likes, very few buyers." / "More ad spend, same sales." /
  "Carts filled, then left."
- What we fix: "Ads reach the wrong people → We fix who sees your ads" / "More visitors, same orders → Pages that turn visitors
  into buyers" / "Selling in one place only → Google and Amazon working too".
- Form panel: "Get your *free growth audit*" + How it works: "Tell us about your brand · We check your details · Our team gets
  in touch" + "If we don't see a clear opportunity, we'll tell you."
- FAQ: "I don't understand ads. Is that a problem?" → "No. Just fill in the form. We'll look at the rest."

## Never write

- A call with Tushar, Tushar personally, "direct strategy call" (not how DTJ works).
- A response time ("within 24 hours"), fees, minimum spend, contract length, "no lock-in", who works on the account,
  time to results — until DTJ confirms the real answer (then add it to the FAQ).
- Any number not already on the page or in its screenshots. Any "verified", "guaranteed", "#1 agency", "best in India".
- Gujlish, Hinglish, or Title Case headings.
