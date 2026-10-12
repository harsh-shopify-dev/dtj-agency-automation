# Claims and proof

Every sentence about DTJ on a variant must trace to one of three sources: (1) a claim already on the main page `/`, (2) a number
visible in one of the project's screenshots, or (3) DTJ's confirmed lead process. If it traces to none, it doesn't go on the page.

## 1. Claims already on the main page (restate freely, don't extend)

- Offer: "free growth audit"; "Get a free audit of your ads, store and funnel, and see exactly where sales are leaking";
  "Free. No pressure. No generic pitch."; "Takes under a minute. It's free."
- Risk reversal: "If we don't see a clear opportunity, we'll tell you."
- What DTJ does: "We look at the whole journey, from your ads and targeting to your website, product pages and checkout, to find
  where you're losing potential customers and fix it." / "We find what's holding your sales back. Then we fix it."
- Ads: "One ad rarely works for everyone. We create different ways to show your product, from real customer-style videos to
  product demos, then keep testing to find what brings in more buyers." / "We optimize around profitable growth, not clicks that
  look good in a report." (Meta + Google)
- Website: "You already paid to bring them to your website. We build and improve your Shopify store and product pages so more of
  those visitors have a reason to buy."
- SEO: "When people search for products you sell, your brand should be there… without paying for every click."
- Amazon: "We improve how your products show up on Amazon, how they're presented, and what shoppers see before they decide to buy."
- Choosing: "Tell us about your brand and we'll show you what to fix first, whether it's ads, your store, SEO or marketplaces."
- Booking panel: "Let's look at your business and tell you what's actually going wrong." / "Get a clear outside perspective on
  your ads, store, and funnel, and know exactly what we'd fix first." / "No generic pitch. No pressure. No guessing." /
  What you'll walk away with: see where your ad spend is leaking; know what to fix first; understand which growth lever deserves
  attention; leave with a clear action plan.
- Contact consent: "contacted… on call, WhatsApp and email about your audit. We don't share your details."
- Thank-you message (`LeadForm.tsx`): "We'll review your brand and reach out on {phone} to walk you through what we'd fix first."
- Stats (shown as they are, see section 4): ₹70Cr+ ad spend managed; 90+ D2C brands; 16X peak reported ROI; 208+ five-star reviews.

## 2. Confirmed lead process (Harsh, 10 Oct 2026)

DTJ checks each lead's quality first, then the team gets in touch (call, WhatsApp or email). **Tushar does not take the first
call.** "Direct strategy call with Tushar" was removed from `/` and every variant; never write it back. How-it-works steps live in
`components/v2/HowItWorks.tsx` (`STEPS`): Tell us about your brand → We check your details → Our team gets in touch.

## 3. Asset inventory (what each proves, exact numbers)

| Asset | Where | What it shows (use exactly these numbers) |
|---|---|---|
| 6 Shopify sales dashboards | `components/proof/RealResults.tsx` `ROWS` (images `public/images/proof/sales-orders-N-mobile.webp`) | proof-1 Pro Effex ₹1.5L → ₹40.18L; proof-2 The Royal Dosa Paper ₹0.8L → ₹5.28Cr; proof-3 Zebein ₹9L → ₹3.56Cr; proof-4 Sindhoi Patola Arts ₹52.7L → ₹2.78Cr; proof-5 Little Rituals ₹46.7L → ₹1.92Cr; proof-6 Saatvi ₹37.6L → ₹1.07Cr. Show "₹X → ₹Y in sales" + "Numbers from each brand's own Shopify sales report." |
| Case studies | `components/case-studies/CaseStudies.tsx` `caseStudies` | Zebein ₹3.56Cr, +746% sales, +719% orders; Royal Dosa Paper ₹5.28Cr, 1.68L orders, ₹70L+ peak month, "from almost no sales when we started in March 2025"; Little Rituals ₹1.92Cr, +312%, +296%; Pro Effex ₹40.18L, 3,071 orders, ₹12L+ peak month. Images in `public/images/case-studies/`. |
| Meta Ads report | `public/images/results/meta-ads-dashboard.webp` | Totals row: ₹5,15,566.40 spent; 9,680 checkouts initiated; 41,970 adds to cart; ₹170.72 per purchase; 3,020 purchases; 4.42X average purchase ROAS. No brand or dates on it: say "Real Meta ads report", never name a client. |
| Product page rebuild | `public/images/shopify/before-pdp.webp`, `after-pdp.webp` (Pro Effex), `cvr-lift.webp` | Conversion rate 1.4% → 2.8% (+100%), "Same traffic. More customers." Harsh prefers the two scrollable phones (`ShopifyPDPVisual`) over the CVR card in a hero. |
| Google search result | `public/images/results/google-search.webp` | Dadu Fresh as the #1 organic result for "healthy juice". |
| Amazon Ads | `components/services/visuals/MarketplaceVisual.tsx` | 18.02% ACOS, ₹6,00,090.71 total cost, 5.55X ROAS, ₹31,25,120.76 sales. **These don't agree** (sales ÷ cost = 5.21); confirm with Harsh before turning them into "₹1 → ₹X". |
| 16 ad reels | `public/video/reels/reel-N.mp4` + posters `public/images/social/reel-N.webp`; component `PerformanceCreative` | Real DTJ ads (fashion, food, beauty, founder videos). |
| Client logos (27) | `components/proof/ClientShowcase.tsx` `CLIENTS` (`public/images/clients/`) | "Trusted by 90+ D2C brands". |
| Partner badges | `components/proof/PlatformStrip.tsx` | Google Partner (shows "Premier"), Meta Business Partner, Amazon Selling Partner 360, Shopify Partner. Statuses not verified; not used on the simple pages. |
| Reviews (20) | `components/reviews/ReviewsMasonry.tsx` `reviews` | 6 verified Google reviews (ids 1 hiral dhamecha, 6 Apekksha Goyal, 8 Dixit rakholia, 12 het digital, 17 Riddhi Patel, 20 Tarun Parmar of Sindhoi Patola Arts: "remarkable 10x ROI on our ad spend for our Shopify store") + 14 placeholders (`demo()`). |
| Tushar's photo | source `D:\Extra Data\DTJ\dtj\tushar joshi.png`; on the pages as `public/images/founder/tushar-joshi.webp` (4:5 crop, placeholder until Harsh sends an edited portrait) | In `FounderBand` on every variant (Harsh, 12 Oct 2026: founder section for trust and brand identity). Caption: "Tushar Joshi, Founder, Digital Tushar Joshi". Credibility only; never next to a "call with Tushar" claim. |
| Testimonial headshots | `public/images/testimonial/testimonial-N.webp` | Stock photos. Never on a verified reviewer. |

## 4. "Use the assets as they are" (client-approval phase)

Harsh, 10 Oct 2026: the pages are for showing the client; use every asset as it is; he replaces placeholders after approval.
So the variants show, unchanged and from their single source files: all 20 reviews (14 are placeholders), the Trustpilot
"Rated 4.8" badge (no Trustpilot profile was found for digitaltusharjoshi.com or dtjgrowth.com), "208+" reviews, 16X, ₹70Cr+,
90+, and the dashboard before-values (rows 1–3 are marked "illustrative" in a code comment; Harsh says they're real).

What still applies:
- Don't **remove or "fix"** these on your own, and don't **add** new ones.
- Don't remove the code comments that mark them (Harsh asked; the history showed the values were never changed after being
  marked). Ask for the source instead.
- Every report and handoff repeats the pre-launch list: replace the 14 placeholder reviews, confirm or remove Trustpilot,
  source 16X, confirm rows 1–3 baselines, confirm partner statuses, add a privacy policy link in the form's consent line.
- Known framing issue (audit F4): Zebein, Sindhoi, Little Rituals and Saatvi percentages compare Jan 2023–Jan 2025 with
  Dec 2020–Dec 2022, but DTJ started in May 2024. Don't make it more prominent (no "up 746% thanks to us").

## 5. Not available yet (ask, never invent)

Fees and pricing model, minimum ad spend, contract length / lock-in, who works on the account, time to results, response time,
WhatsApp number for leads, the real list of pain points (the leads Sheet's "biggest challenge" answers), real client video
testimonials, team/office photos, privacy policy URL, company address.
