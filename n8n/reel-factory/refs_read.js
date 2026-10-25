// n8n Code node "Read the Results" in "Reel Factory: Find References" (mode: Run Once for All Items).
// Input: one "Ask Apify" answer per planned call, in the same order as "Plan the Searches" ({ statusCode, body } with the run's
// dataset items as body, or { error } when the call failed). Output: one item per reference video found, in the columns of
// dtj_reel_library (videos only: an item without a direct video link is left out; a trending sound is the one row without one),
// then always one marker item { marker: true, url: '', found, by_audience, problems } with the counts and what failed for
// "Write the Digest". An audience scan's reels (source "audience") carry the audience, comments, the audio's name, the creator's
// followers when "profiles" gave them, views per follower and comments per view; they are ranked by views per follower (reels
// with a follower count first), then views.
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
  const music = x.musicInfo || {};
  const song = str(first(music.song_name, music.title)), artist = str(first(music.artist_name, music.display_artist));
  return { url: https(x.url) || (x.shortCode ? 'https://www.instagram.com/reel/' + x.shortCode + '/' : ''), video_url: https(x.videoUrl),
    caption: str(x.caption), views: count(x.videoPlayCount, x.igPlayCount, x.videoViewCount), likes: count(x.likesCount),
    comments: count(x.commentsCount), username: str(x.ownerUsername).toLowerCase(),
    audio_name: song ? song + (artist ? ' · ' + artist : '') : '',
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
function trending(x) {   // one trending sound (s_actors/instagram-trending-audio): its page is the link, there is no video
  const title = str(x.title), artist = str(first(x.artist, x.artistUsername));
  const facts = [str(first(x.reelsCountText, x.reelsCount != null ? x.reelsCount + ' reels' : '')), x.isTrending ? 'trending in India' : '',
    x.isOriginalAudio ? 'original audio' : 'song', x.topReelUrl ? 'top reel ' + str(x.topReelUrl) : ''].filter(Boolean).join('; ');
  return { url: https(first(x.audioUrl, x.url)), video_url: '', caption: title + (artist ? ' · ' + artist : '') + (facts ? ' (' + facts + ')' : ''),
    audio_name: title + (artist ? ' · ' + artist : ''), views: null, likes: null, owner: artist, posted_at: iso(x.newestReelAt), days_running: null };
}
const READ = { instagram, pinterest, meta, audience: instagram, trending_audio: trending };

const answerOf = (i) => {
  const a = answers[i] || {};
  let body = a.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch (e) { /* kept as text */ } }
  return { a, body, status: Number(a.statusCode || 0) };
};
const problems = [];
const failed = (plan, a, body, status) => {
  const why = (body && body.error && (body.error.message || body.error.type)) || (a.error && (a.error.message || a.error)) || (status ? 'HTTP ' + status : 'no answer');
  problems.push(plan.source + ' ' + (plan.query || plan.label || '') + ': ' + String(why).replace(/Bearer\s+\S+/gi, 'Bearer ***').slice(0, 160));
};

// the creators' followers first (kind "profiles"), so every reel of theirs gets views per follower
const followers = {};
plans.forEach((plan, i) => {
  if (plan.kind !== 'profiles') return;
  const { a, body, status } = answerOf(i);
  if (a.error || !Array.isArray(body)) { failed(plan, a, body, status); return; }
  for (const x of body) {
    const n = count(x && x.followersCount, x && x.followers);
    if (x && x.username && n) followers[str(x.username).toLowerCase()] = n;
  }
});

const out = [];
const seen = new Set();
const byAudience = {};
plans.forEach((plan, i) => {
  if (plan.kind === 'profiles') return;
  const { a, body, status } = answerOf(i);
  if (a.error || !Array.isArray(body)) { failed(plan, a, body, status); return; }
  const read = READ[plan.source];
  let rows = body.map((x) => (x && typeof x === 'object' && read ? read(x) : null))
    .filter((r) => r && r.url && (r.video_url || plan.source === 'trending_audio'));
  if (plan.source === 'meta') rows.sort((p, q) => (q.days_running || 0) - (p.days_running || 0));
  if (plan.source === 'audience') rows.sort((p, q) => (q.views || 0) - (p.views || 0));
  rows = rows.slice(0, plan.keep_n || rows.length);
  const aud = plan.source === 'audience' || plan.source === 'trending_audio';
  for (const r of rows) {
    const key = r.url + '|' + (plan.audience || '');
    if (seen.has(key)) continue;
    seen.add(key);
    const f = r.username ? followers[r.username] || null : null;
    out.push({ source: plan.source, url: r.url, video_url: r.video_url, brand: plan.brand || (aud && r.username ? '@' + r.username : r.owner),
      niche: plan.niche || '', caption: r.caption.slice(0, 2000), views: r.views, likes: r.likes, days_running: r.days_running,
      posted_at: r.posted_at, query: str(plan.query).slice(0, 300), actor: plan.actor, found_at: now.toISOString(), found_for: plan.found_for || '',
      keep: '', kept_by: '', kept_at: '', audience: plan.audience || '', audio_name: (r.audio_name || '').slice(0, 300),
      comments: aud && r.comments != null ? r.comments : null, followers: f,
      views_per_follower: f && r.views != null ? Math.round((r.views / f) * 1000) / 1000 : null,
      comments_per_view: aud && r.views && r.comments != null ? Math.round((r.comments / r.views) * 1e6) / 1e6 : null,
      link_key: key });
    if (plan.source === 'audience') byAudience[plan.audience] = (byAudience[plan.audience] || 0) + 1;
  }
  if (!rows.length && !body.length) problems.push(plan.source + ' ' + (plan.query || plan.label || '') + ': nothing found');
});
// an audience's reels by views per follower (those with a follower count first), then views
const score = (r) => [r.views_per_follower == null ? 1 : 0, -(r.views_per_follower || 0), -(r.views || 0)];
const order = (p, q) => { const a = score(p), b = score(q); for (let k = 0; k < a.length; k++) if (a[k] !== b[k]) return a[k] - b[k]; return 0; };
const refs = out.filter((r) => r.source !== 'audience');
const reels = out.filter((r) => r.source === 'audience').sort((p, q) => (p.audience < q.audience ? -1 : p.audience > q.audience ? 1 : order(p, q)));
const foundRefs = refs.filter((r) => r.source !== 'trending_audio').length;
return [...refs, ...reels, { marker: true, url: '', found: out.length, found_refs: foundRefs, by_audience: byAudience, problems }].map((json) => ({ json }));
