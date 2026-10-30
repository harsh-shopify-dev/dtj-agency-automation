// n8n Code node "Pick the Best" in "Reel: Find Diwali Campaigns" (mode: Run Once for All Items).
// Input: the Apify answer ({ statusCode, body }). Keeps Reels of the last 3 Diwalis that mention Diwali, without comedy and memes, at most
// one per account: reels naming the niche first, then ones that read like a brand's campaign, then the most viewed. Output: one item { results: [...], html, found, problems } for the form's result page. A person checks them and picks one.
const plan = $('Plan the Search').first().json;
const a = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const DIWALI = /diwali|deepavali|deepawali|dipawali|divali|दीवाली|दिवाली|દિવાળી/i;
const cutoff = Date.now() - plan.days * 86400000;
const items = Array.isArray(a.body) ? a.body : [];
const problem = (a.statusCode && a.statusCode >= 300) || a.error
  ? `Apify answered ${a.statusCode || ''} ${(a.error && (a.error.message || a.error)) || (a.body && a.body.error && a.body.error.message) || ''}`.trim() : '';
const word = String(plan.niche || '').replace(/[^\p{L}\p{N} ]+/gu, ' ').trim().replace(/s\b/gi, '').split(/\s+/).filter(Boolean).join('|');
const NICHE = word ? new RegExp(word, 'i') : /$^/;
const BRANDISH = /campaign|\bad\b|\bfilm\b|collection|presents|\bbrand\b|commercial|\bgift|\bshop\b|\bstore\b/i;
const JOKE = /comedy|funny|\bmemes?\b|😂|🤣|😅|💀|kalesh|prank|roast|corporate|employee/i;
const reels = [];
for (const x of items) {
  const url = /^https:\/\/\S+$/.test(String(x.url || '')) ? x.url : (x.shortCode ? `https://www.instagram.com/reel/${x.shortCode}/` : '');
  const isReel = x.productType === 'clips' || (!x.productType && x.videoUrl) || (x.type === 'Video' && x.videoUrl);
  const when = Date.parse(x.timestamp || '');
  const text = `${x.caption || ''} ${(x.hashtags || []).join(' ')}`;
  if (!url || !isReel || !DIWALI.test(text) || JOKE.test(text) || !(when >= cutoff)) continue;
  reels.push({ rank: NICHE.test(text) ? 2 : BRANDISH.test(text) ? 1 : 0, url, video_url: x.videoUrl || '', username: String(x.ownerUsername || '').toLowerCase(), name: x.ownerFullName || x.ownerUsername || '',
    views: Number(x.videoPlayCount ?? x.igPlayCount ?? x.videoViewCount ?? 0) || 0, likes: Number(x.likesCount || 0), caption: String(x.caption || '').slice(0, 220),
    posted: new Date(when).toISOString().slice(0, 10) });
}
reels.sort((p, q) => q.rank - p.rank || q.views - p.views);
const seen = new Set();
const results = [];
for (const r of reels) {
  if (seen.has(r.username)) continue;
  seen.add(r.username);
  results.push(r);
  if (results.length >= plan.count) break;
}
const card = (r, i) => `<div style="margin:0 0 18px;text-align:left"><b>${i + 1}. <a href="${esc(r.url)}" target="_blank">${esc(r.name || r.username)}</a></b><br>`
  + `@${esc(r.username)} · ${r.views.toLocaleString('en-IN')} views · ${r.likes.toLocaleString('en-IN')} likes · ${esc(r.posted)}<br><small>${esc(r.caption)}</small></div>`;
const html = results.length
  ? `${results.map(card).join('')}<p>Check these. Then tell Claude which number to make for which brand.</p>`
  : `<p>Nothing found for ${esc(plan.niche)}${problem ? ': ' + esc(problem) : ''}. Try a wider word for the niche.</p>`;
return [{ json: { results, html, found: reels.length, scanned: items.length, problems: problem } }];
