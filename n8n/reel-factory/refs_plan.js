// n8n Code node "Plan the Searches" in "Reel Factory: Find References" (mode: Run Once for All Items).
// Reads "Load Bot Users" (dtj_bot_users), "Load Watchlist" (dtj_reel_watchlist), "Load Audiences" (dtj_reel_audiences) and, when
// the reel bot started the run, "From the Telegram Bot" (query, sources, limit, requested_by, chat_id; for an audience scan also
// mode "audience", audience, hashtags, creators). Output: one item per Apify call { kind, mode, label, query, source, actor, input,
// max_items, keep_n, max_usd, timeout_s, brand, niche, audience, slug, chat_ids, found_for }, or for a request that cannot be
// searched one { chat_id, text, summary: true } item for "Send the Summary" (no actor: nothing is called).
// kind "refs" (reference videos, Keep / Skip) or, for an audience scan (Harsh, 25 Oct 2026: "analyze what type of content holds
// them the longest, whats the trend going on insta"): "audience" (top reels of the audience's hashtags and creators), "profiles"
// (the creators' follower counts, for views per follower) and "trending" (India's trending Reels audio).
// The actors were picked on 25 Oct 2026 from their Apify Store pages (price per result, a direct video link in the output);
// each gets a 3-result live test once the "DTJ Apify" credential exists:
//   instagram  apify/instagram-reel-scraper (a profile) / apify/instagram-hashtag-scraper (a hashtag, resultsType reels)
//   pinterest  apt_marble/pinterest-video-scraper (video pins only, mp4Url)
//   meta       automation-lab/facebook-ads-library (country IN, active, video; startDate -> days running)
//   audience   the two Instagram actors above; followers from apify/instagram-profile-scraper ($2.60 per 1,000 profiles);
//              trending audio from s_actors/instagram-trending-audio (country IN, no keyword: $1.99 per 1,000 sounds, plus
//              $0.34 once a day when its Indian list is built; seemuapps/instagram-music-scraper $8 / 1,000 and
//              memo23/instagram-audio-scraper $4 / 1,000 need a song or keyword and have no per-country flag)
// Fallbacks whose output "Read the Results" also reads: apify/instagram-scraper, silentflow/pinterest-scraper-ppr,
// apify/facebook-ads-scraper.
const MAX_PER_SOURCE = 10, DEFAULT_PER_SOURCE = 5, MAX_CALLS = 60;
const MAX_USD = 0.10;        // Apify's charge cap per call (maxTotalChargeUsd); 10 results cost about $0.03-0.04
const MAX_AUDIENCE = 30, AUDIENCE_SOURCES = 10;   // an audience scan: reels per hashtag or creator, hashtags + creators
const AUDIENCE_USD = 0.15, TRENDING_USD = 0.50;      // 30 reels cost about $0.08; the trending list up to $0.36 on its first run of the day
const META_POOL = 3;         // ads are fetched 3x the limit and the longest running ones kept (Meta cannot sort by run time)
const SOURCES = ['instagram', 'pinterest', 'meta'];
const ALIASES = { instagram: 'instagram', insta: 'instagram', ig: 'instagram', reels: 'instagram', pinterest: 'pinterest', pin: 'pinterest',
  pins: 'pinterest', meta: 'meta', fb: 'meta', facebook: 'meta', ads: 'meta', ad: 'meta', adlibrary: 'meta', all: 'all' };
const clean = (s) => String(s == null ? '' : s).trim();
// @mamaearth.in -> "mamaearth": a handle's .in / _official / .india / _store ending is not part of the brand's name
const words = (s) => clean(s).replace(/^[@#]/, '').replace(/[._](in|india|official|store|shop|co)$/i, '').replace(/[._]+/g, ' ').replace(/\s+/g, ' ').trim();
const num = (v, d) => { const n = parseInt(String(v == null ? '' : v), 10); return Number.isFinite(n) && n > 0 ? Math.min(n, MAX_PER_SOURCE) : d; };

// a list given as an array, a JSON array or text with commas, spaces or new lines
const list = (v) => {
  if (Array.isArray(v)) return v.map(clean).filter(Boolean);
  const t = clean(v);
  if (t.startsWith('[')) { try { const a = JSON.parse(t); if (Array.isArray(a)) return a.map(clean).filter(Boolean); } catch (e) { /* as text */ } }
  return t.split(/[\s,;]+/).map(clean).filter(Boolean);
};
const hashtagsOf = (v) => [...new Set(list(v).map((h) => h.replace(/^#/, '').toLowerCase()).filter((h) => /^[\p{L}\p{N}_]{2,100}$/u.test(h)))];
const creatorsOf = (v) => [...new Set(list(v).map((c) => { const m = c.match(/instagram\.com\/([A-Za-z0-9._]{1,30})/i); return (m ? m[1] : c.replace(/^@/, '')).toLowerCase(); })
  .filter((c) => /^[a-z0-9._]{1,30}$/.test(c)))];
const slugOf = (s) => clean(s).toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);

// an audience scan: the top reels of each hashtag and creator, the creators' followers, India's trending audio
function audienceCalls(a, n, base) {
  const hashtags = hashtagsOf(a.hashtags), creators = creatorsOf(a.creators);
  const both = [...hashtags.map((h) => ({ h })), ...creators.map((c) => ({ c }))].slice(0, AUDIENCE_SOURCES);
  const common = { ...base, label: clean(a.audience), audience: clean(a.audience).slice(0, 100), slug: slugOf(a.slug || a.audience),
    source: 'audience', brand: '', niche: '' };
  const out = both.map((x) => (x.h
    ? { ...common, kind: 'audience', query: '#' + x.h, actor: 'apify/instagram-hashtag-scraper',
      input: { hashtags: [x.h], resultsType: 'reels', resultsLimit: n }, max_items: n, keep_n: n, max_usd: AUDIENCE_USD }
    : { ...common, kind: 'audience', query: '@' + x.c, actor: 'apify/instagram-reel-scraper',
      input: { username: [x.c], resultsLimit: n, skipPinnedPosts: true }, max_items: n, keep_n: n, max_usd: AUDIENCE_USD }));
  const asked = both.filter((x) => x.c).map((x) => x.c);
  if (asked.length) {
    out.push({ ...common, kind: 'profiles', query: asked.map((c) => '@' + c).join(' '), actor: 'apify/instagram-profile-scraper',
      input: { usernames: asked }, max_items: asked.length, keep_n: 0, max_usd: MAX_USD });
  }
  if (out.length) {
    const sounds = Math.min(n, MAX_PER_SOURCE);
    out.push({ ...common, kind: 'trending', source: 'trending_audio', query: 'trending Reels audio, India', actor: 's_actors/instagram-trending-audio',
      input: { countries: ['IN'], maxSounds: sounds, trendingOnly: true, soundType: 'all', topReels: 1 }, max_items: sounds, keep_n: sounds,
      max_usd: TRENDING_USD });
  }
  return out;
}

// what to search for one brand or query: { instagram: {handle} | {hashtag}, pinterest: 'words', meta: {query} | {page} | {library} }
function targets(row) {
  const t = {};
  const ig = clean(row.instagram);
  const igUrl = ig.match(/instagram\.com\/(?:explore\/tags\/([A-Za-z0-9_]+)|([A-Za-z0-9._]{1,30}))/i);
  if (igUrl) t.instagram = igUrl[1] ? { hashtag: igUrl[1] } : { handle: igUrl[2] };
  else if (/^#[\p{L}\p{N}_]{2,}$/u.test(ig)) t.instagram = { hashtag: ig.slice(1) };
  else if (/^@?[A-Za-z0-9._]{1,30}$/.test(ig)) t.instagram = { handle: ig.replace(/^@/, '') };
  if (clean(row.pinterest_query)) t.pinterest = clean(row.pinterest_query).slice(0, 100);
  const meta = clean(row.meta_advertiser);
  if (/^https:\/\/(www\.)?facebook\.com\/ads\/library\//i.test(meta)) t.meta = { library: meta };
  else if (/^https:\/\/(www\.)?facebook\.com\/[^\s]+$/i.test(meta)) t.meta = { page: meta };
  else if (meta) t.meta = { query: meta.slice(0, 100) };
  return t;
}

// the search in words, for the library's query column and the digest
const said = (source, t) => source === 'pinterest' ? t : t.handle ? '@' + t.handle : t.hashtag ? '#' + t.hashtag : t.library || t.page || t.query;

function call(source, target, n) {
  if (source === 'instagram') {
    return target.hashtag
      ? { actor: 'apify/instagram-hashtag-scraper', input: { hashtags: [target.hashtag], resultsType: 'reels', resultsLimit: n }, max_items: n }
      : { actor: 'apify/instagram-reel-scraper', input: { username: [target.handle], resultsLimit: n, skipPinnedPosts: true }, max_items: n };
  }
  if (source === 'pinterest') {
    return { actor: 'apt_marble/pinterest-video-scraper', input: { queries: [target], maxVideos: n, excludePromoted: false }, max_items: n };
  }
  const pool = Math.min(n * META_POOL, MAX_PER_SOURCE * META_POOL);
  const input = { country: 'IN', activeStatus: 'active', mediaType: 'video', maxAds: pool };
  if (target.library) input.adsLibraryUrls = [target.library];
  else if (target.page) input.pageUrls = [target.page];
  else input.searchQueries = [target.query];
  return { actor: 'automation-lab/facebook-ads-library', input, max_items: pool };
}

const rows = (name) => { try { return $(name).all().map((i) => i.json || {}); } catch (e) { return []; } };
const users = rows('Load Bot Users');
const audiences = rows('Load Audiences').filter((r) => r.audience);
let bot = null;
try { bot = $('From the Telegram Bot').first().json; } catch (e) { bot = null; }  // the weekly scan
const watch = rows('Load Watchlist').filter((r) => r.brand || r.instagram || r.pinterest_query || r.meta_advertiser);

const plans = [];
if (bot && clean(bot.mode).toLowerCase() === 'audience') {
  const chat = clean(bot.chat_id);
  if (!chat) return [];
  const name = clean(bot.audience).slice(0, 100);
  const saved = audiences.find((r) => clean(r.audience).toLowerCase() === name.toLowerCase() || clean(r.slug) === slugOf(name)) || {};
  const given = list(bot.hashtags).length || list(bot.creators).length;
  const a = given ? { audience: name, slug: saved.slug, hashtags: bot.hashtags, creators: bot.creators } : saved;
  const v = parseInt(clean(bot.limit) || clean(saved.per_source), 10);
  const n = Number.isFinite(v) && v > 0 ? Math.min(v, MAX_AUDIENCE) : MAX_AUDIENCE;
  if (name) plans.push(...audienceCalls({ ...a, audience: name }, n, { mode: 'bot', chat_ids: [chat], found_for: clean(bot.requested_by) || 'the bot' }));
  if (!plans.length) {
    return [{ json: { chat_id: chat, summary: true, text: 'An audience scan needs the audience (for example "Gen Z urban India") and at least one '
      + 'hashtag or @creator, or the name of an audience saved in dtj_reel_audiences.' } }];
  }
} else if (bot) {
  const chat = clean(bot.chat_id);
  const query = clean(bot.query).slice(0, 200);
  const asked = clean(bot.sources).toLowerCase().split(/[\s,;/+]+/).filter(Boolean);
  const unknown = asked.filter((s) => !ALIASES[s]);
  let sources = asked.length ? [...new Set(asked.map((s) => ALIASES[s]).filter(Boolean))] : ['all'];
  if (sources.includes('all')) sources = SOURCES.slice();
  const help = (why) => [{ json: { chat_id: chat, summary: true, text: why + '\n\nUse: /refs @handle, /refs #hashtag, /refs a brand on the '
    + 'watchlist, or /refs some words; add instagram, pinterest or meta to search only those, and a number (at most '
    + MAX_PER_SOURCE + ') for how many per source. Example: /refs @mamaearth.in meta 5' } }];
  if (!chat) return [];
  if (!query) return help('What should I search for?');
  if (unknown.length || !sources.length) return help('I do not know the source ' + unknown.join(', ') + '.');
  const lower = query.toLowerCase().replace(/^@/, '');
  const row = watch.find((r) => clean(r.brand).toLowerCase() === lower || clean(r.instagram).toLowerCase().replace(/^@/, '') === lower);
  let t;
  if (row) t = targets(row);
  else {
    const isUrl = /^https:\/\//i.test(query);
    t = targets({ instagram: isUrl ? (/instagram\.com/i.test(query) ? query : '') : query.startsWith('#') ? query : query.startsWith('@') ? query
      : '#' + query.toLowerCase().replace(/[^\p{L}\p{N}_]+/gu, ''),
      pinterest_query: isUrl ? '' : words(query), meta_advertiser: isUrl ? (/facebook\.com/i.test(query) ? query : '') : words(query) });
  }
  const n = num(bot.limit, row ? num(row.per_source, DEFAULT_PER_SOURCE) : DEFAULT_PER_SOURCE);
  const missing = sources.filter((s) => !t[s]);
  for (const s of sources.filter((x) => t[x])) {
    plans.push({ kind: 'refs', mode: 'bot', label: query, query: said(s, t[s]), source: s, ...call(s, t[s], n), keep_n: n, brand: row ? clean(row.brand) : '',
      niche: row ? clean(row.niche) : '', chat_ids: [chat], found_for: clean(bot.requested_by) || 'the bot', skipped: missing });
  }
  if (!plans.length) return help('I could not turn "' + query.replace(/[<>&]/g, '') + '" into a search for ' + sources.join(', ') + '.');
} else {
  const admins = [...new Set(users.filter((u) => u.telegram_user_id && u.active !== false && String(u.role || '').toLowerCase().trim() === 'admin')
    .map((u) => String(u.telegram_user_id).trim()))];
  for (const row of watch.filter((r) => r.active === true || String(r.active).toLowerCase() === 'true')) {
    const t = targets(row);
    const n = num(row.per_source, DEFAULT_PER_SOURCE);
    for (const s of SOURCES.filter((x) => t[x])) {
      plans.push({ kind: 'refs', mode: 'weekly', label: clean(row.brand), query: said(s, t[s]), source: s, ...call(s, t[s], n),
        keep_n: n, brand: clean(row.brand), niche: clean(row.niche), chat_ids: admins, found_for: 'weekly scan' });
    }
  }
  for (const a of audiences.filter((r) => r.active === true || String(r.active).toLowerCase() === 'true')) {
    const v = parseInt(clean(a.per_source), 10);
    plans.push(...audienceCalls(a, Number.isFinite(v) && v > 0 ? Math.min(v, MAX_AUDIENCE) : MAX_AUDIENCE,
      { mode: 'weekly', chat_ids: admins, found_for: 'weekly scan' }));
  }
}
return plans.slice(0, MAX_CALLS).map((p) => ({ json: { ...p, max_usd: p.max_usd || MAX_USD, timeout_s: 240 } }));
