// n8n Code node "Read the Results" in "Reel Factory: Find References" (mode: Run Once for All Items).
// Input: one "Ask Apify" answer per planned call, in the same order as "Plan the Searches" ({ statusCode, body } with the run's
// dataset items as body, or { error } when the call failed). Output: one item per reference video found, in the columns of
// dtj_reel_library (videos only: an item without a direct video link is left out), then always one marker item
// { marker: true, url: '', found, problems } that carries the counts and what failed to "Write the Digest".
// Field names: the picked actors and their fallbacks (refs_plan.js), as in the sample outputs on their Apify Store pages.
const plans = $('Plan the Searches').all().map((i) => i.json || {});
const answers = $input.all().map((i) => i.json || {});
const now = new Date();
const str = (v) => (v == null ? '' : String(v)).trim();
const first = (...vals) => { for (const v of vals) if (v != null && String(v).trim() !== '') return v; return null; };
const count = (...vals) => { const v = first(...vals); const n = Number(v); return v == null || !Number.isFinite(n) ? null : Math.round(n); };
const https = (u) => (/^https:\/\/[^\s"<>]+$/i.test(str(u)) ? str(u) : '');
const days = (start) => {
  if (start == null || start === '') return null;
  const t = typeof start === 'number' || /^\d{9,13}$/.test(String(start)) ? new Date(Number(start) * (String(start).length > 11 ? 1 : 1000))
    : new Date(String(start).length === 10 ? String(start) + 'T00:00:00Z' : String(start));
  return Number.isNaN(t.getTime()) ? null : Math.max(0, Math.floor((now - t) / 86400000));
};
const iso = (v) => {
  if (v == null || v === '') return '';
  const t = typeof v === 'number' || /^\d{9,13}$/.test(String(v)) ? new Date(Number(v) * (String(v).length > 11 ? 1 : 1000)) : new Date(String(v));
  return Number.isNaN(t.getTime()) ? str(v).slice(0, 30) : t.toISOString();
};

function instagram(x) {
  if (x.productType && !['clips', 'igtv', 'feed'].includes(x.productType) && !x.videoUrl) return null;
  return { url: https(x.url) || (x.shortCode ? 'https://www.instagram.com/reel/' + x.shortCode + '/' : ''), video_url: https(x.videoUrl),
    caption: str(x.caption), views: count(x.videoPlayCount, x.igPlayCount, x.videoViewCount), likes: count(x.likesCount),
    owner: str(first(x.ownerFullName, x.ownerUsername)), posted_at: iso(x.timestamp), days_running: null };
}
function pinterest(x) {
  if (x.isVideo === false) return null;   // silentflow returns image pins too
  return { url: https(x.url), video_url: https(first(x.mp4Url, x.videoUrl, x.hlsUrl)), caption: str(first(x.title, x.description, x.altText)),
    views: count(x.viewCount), likes: count(x.saveCount, x.likeCount, x.saves),
    owner: str(first(x.creatorUsername, x.pinnerUsername, (x.pinner || {}).username)), posted_at: iso(x.createdAt), days_running: null };
}
function meta(x) {
  const snap = x.snapshot || {};
  const vids = [].concat(x.videoUrls || [], (snap.videos || []).map((v) => first(v.videoHdUrl, v.video_hd_url, v.videoSdUrl, v.video_sd_url)),
    (snap.cards || []).map((c) => first(c.videoHdUrl, c.video_hd_url, c.videoSdUrl, c.video_sd_url)));
  const id = str(first(x.adArchiveId, x.adArchiveID, x.ad_archive_id));
  const start = first(x.startDate, x.start_date, x.startDateFormatted);
  return { url: https(x.adLibraryUrl) || (id ? 'https://www.facebook.com/ads/library/?id=' + id : ''), video_url: https(vids.find(Boolean)),
    caption: str(first(x.bodyText, (snap.body || {}).text, x.title, snap.title)), views: null, likes: null,
    owner: str(first(x.pageName, snap.page_name, x.page_name)), posted_at: iso(start), days_running: days(start) };
}
const READ = { instagram, pinterest, meta };

const out = [];
const problems = [];
const seen = new Set();
plans.forEach((plan, i) => {
  const a = answers[i] || {};
  const what = plan.source + ' ' + (plan.query || plan.label || '');
  let body = a.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) { /* kept as text */ } }
  const status = Number(a.statusCode || 0);
  if (a.error || !Array.isArray(body)) {
    const why = (body && body.error && (body.error.message || body.error.type)) || (a.error && (a.error.message || a.error)) || (status ? 'HTTP ' + status : 'no answer');
    problems.push(what + ': ' + String(why).replace(/Bearer\s+\S+/gi, 'Bearer ***').slice(0, 160));
    return;
  }
  const read = READ[plan.source];
  let rows = body.map((x) => (x && typeof x === 'object' && read ? read(x) : null)).filter((r) => r && r.url && r.video_url);
  if (plan.source === 'meta') rows.sort((p, q) => (q.days_running || 0) - (p.days_running || 0));
  rows = rows.slice(0, plan.keep_n || rows.length);
  for (const r of rows) {
    if (seen.has(r.url)) continue;
    seen.add(r.url);
    out.push({ source: plan.source, url: r.url, video_url: r.video_url, brand: plan.brand || r.owner, niche: plan.niche || '',
      caption: r.caption.slice(0, 2000), views: r.views, likes: r.likes, days_running: r.days_running, posted_at: r.posted_at,
      query: str(plan.query).slice(0, 300), actor: plan.actor, found_at: now.toISOString(), found_for: plan.found_for || '', keep: '', kept_by: '', kept_at: '' });
  }
  if (!rows.length && !body.length) problems.push(what + ': nothing found');
});
return [...out, { marker: true, url: '', found: out.length, problems }].map((json) => ({ json }));
