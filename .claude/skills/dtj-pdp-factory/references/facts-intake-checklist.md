# Facts intake: what the fixed sections need

The fixed set has 3 proof sections, a guarantee, a FAQ and 3 big-benefit sections. A page built from a pack photo alone (the first
Go Mints page) has almost nothing real to say. Ask for this list at the START (the n8n brief form collects part of it). During
design, whatever is missing becomes a marked SAMPLE (rules at the end) AND a `content-needed.md` line in words the client
understands, so the samples get replaced.

Every fact goes into `facts.json` with a `source` (at most about 60 characters: "pack print", "client WhatsApp 10 Oct",
"product description", "lab report p.2"). No source, no fact.

## Must have (the page cannot be honest without these)
- Product name as the brand says it; what it is in one line; who it is for.
- The biggest benefit and how the product delivers it (mechanism, ingredient, process): feeds W02 title, W05.
- 3 to 6 further benefits, each with its reason: W06, W10, icon strips.
- Price, real compare-at price (MRP), variants, bundles that exist in the store: W02.
- Pictures: pack front, pack back / label, product in use, texture / close-up, lifestyle; videos if any. Say what each shows.
- Shipping: delivery time, free-shipping threshold, COD yes/no, returns window and conditions: W00, W02 k, W13.

## Proof (real first; otherwise a marked SAMPLE until the client sends it)
- Reviews: export from the reviews app (Judge.me, Loox, etc.) or screenshots, with name and rating, and whether they may be shown.
- Rating and count (e.g. 4.7 from 1,240 reviews) with where it is measured.
- UGC photos / videos with the creator's permission: W03.
- Numbers: units sold, customers, repeat rate, with the source and date: W07 / W14 stats.
- Studies or lab tests: name, sample size, result, link: W07 measured results ("clinically proven" only with this).
- Press, awards, certifications (FSSAI number for food and nutraceuticals, ISO, GMP, cruelty-free, "Made in India").

## Objections (W11, W13)
- Guarantee in writing: days, how to claim, what is refunded.
- How to use: steps, dose, timing, how long until results.
- Safety: allergens, side effects, who should not use it, age limits.
- The 5-8 questions customers actually ask (from WhatsApp, DMs, support tickets).

## Differentiation (W08)
- Why this and not the usual alternative (coffee, a cheaper brand, a home remedy)? 4-6 points, each true.
- A comparison against named competitors only with the brand owner's written approval (`claims_approved: true`).

## Brand
- Logo, pack colours (hex if they have them), fonts, tone of voice examples, sites or pages they love or hate.

## Voice (for the copy: `copywriting.md`)
- The sensation, in customers' own words: what it tastes, feels, smells, sounds or looks like (read 20 reviews; copy the
  adjectives and verbs they use, with the review as source).
- The two qualities that make it different and seem to fight (sweet and hot, energy and calm, gentle and strong).
- The everyday situation the shopper hates that this ends (the enemy), and the moment of the payoff.
- Real use scenes, local and concrete (Maggi, momos, the Pune-Mumbai drive, exam week).
- Words the brand never uses, and jokes that are off limits for the category.
- Badge check: every "natural / no preservatives / vegan / sugar-free" claim checked against the ingredient list and label
  (MojoVibe's page says "No Preservatives" while listing Sodium Benzoate, INS 211).
- Picture check: read every picture's printed text against the ingredient list too. A picture whose printed claim is false or
  unverified stays OUT of `facts.media` entirely, because the builder fills empty picture slots with the media pictures (Hope N Skin,
  10 Oct 2026: the ingredients picture printed Alpha Arbutin, which is not in the formula; another printed an unproven 'Balanced pH';
  before/after photos with no proof they are real customers are never used as results).

## Sample content while designing (Harsh's decision, 10 Oct 2026)
Every section of the fixed set is filled during design. What the client has not sent yet becomes a marked SAMPLE (source starting
with `SAMPLE`), listed in the build report and in `content-needed.md`, and replaced or signed off by Harsh before the page goes
live. Samples are allowed for counts, ratings, reviews, UGC captions, stats, guarantee and delivery days. Never samples: medical
claims, "clinically proven", competitor names, licences and certifications, prices, discounts, offers. Pages with samples go to a
draft theme (or our own test store with Harsh's yes) only. Test pictures follow the same rule (graphics brief lists each one).

Before sampling, look for the real thing on the brand's own public pages (product page, FAQ, policies, a public reviews widget)
and use it with the URL and date as the source. If a public page looks unfinished (e.g. a refund policy with
"[INSERT RETURN ADDRESS]"), do not use it and tell Harsh.
