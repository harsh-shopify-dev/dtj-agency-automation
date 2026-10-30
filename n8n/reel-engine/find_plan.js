// n8n Code node "Plan the Search" in "Reel: Find Diwali Campaigns" (mode: Run Once for All Items).
// From the form (niche, count): which Instagram hashtags to ask Apify for. Output: { actor, input, max_items, max_usd, timeout_s, niche, count, days }.
const i = $input.first().json || {};
const niche = String(i.niche || '').trim().toLowerCase();
const tag = niche.replace(/[^\p{L}\p{N}]+/gu, '');
if (!tag) throw new Error('No niche: say what the brand sells, like watches or dry fruits');
const n = parseInt(String(i.count || ''), 10);
const count = Number.isFinite(n) && n > 0 ? Math.min(n, 15) : 10;
const hashtags = [`diwali${tag}`, `${tag}diwali`, `festive${tag}`, 'diwalicampaign', 'diwaliad', 'diwaligifts', 'diwali2026', 'diwalivibes'];
const MAX_ITEMS = 100;   // Apify charges per result: 10 results cost about $0.03-0.04 (refs_plan.js, 25 Oct 2026)
return [{ json: { actor: 'apify/instagram-hashtag-scraper', input: { hashtags, resultsType: 'reels', resultsLimit: 15 }, max_items: MAX_ITEMS,
  max_usd: 0.30, timeout_s: 280, niche, count, days: 1100 } }];
