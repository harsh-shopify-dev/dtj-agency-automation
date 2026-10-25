// n8n Code node "Pick the New Ones" in "Reel Factory: Find References" (mode: Run Once for All Items).
// Input: the rows not yet in dtj_reel_library ("Only New Links" by link_key = "<link>|<audience>", so one reel is saved once per
// audience scan and once as a reference; one empty item when there are none). Output: those rows (the columns of
// dtj_reel_library only), or one { url: '' } item so "Anything New?" sends just the summary.
const COLS = ['source', 'url', 'video_url', 'brand', 'niche', 'caption', 'views', 'likes', 'days_running', 'posted_at', 'query', 'actor',
  'found_at', 'found_for', 'keep', 'kept_by', 'kept_at', 'audience', 'audio_name', 'comments', 'followers', 'views_per_follower',
  'comments_per_view', 'link_key'];
const NUMBERS = ['views', 'likes', 'days_running', 'comments', 'followers', 'views_per_follower', 'comments_per_view'];
const seen = new Set();
const out = [];
for (const it of $input.all()) {
  const r = it.json || {};
  const key = r.url + '|' + (r.audience || '');
  if (r.marker || !r.url || seen.has(key)) continue;
  seen.add(key);
  const row = {};
  for (const c of COLS) row[c] = r[c] == null ? (NUMBERS.includes(c) ? null : '') : r[c];
  out.push({ json: row });
}
return out.length ? out : [{ json: { url: '' } }];
