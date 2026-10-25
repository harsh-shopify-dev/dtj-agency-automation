// n8n Code node "Pick the New Ones" in "Reel Factory: Find References" (mode: Run Once for All Items).
// Input: the references whose link is not yet in dtj_reel_library ("Only New Links"; one empty item when there are none). Output:
// those references (the columns of dtj_reel_library only), or one { url: '' } item so "Anything New?" sends just the summary.
const COLS = ['source', 'url', 'video_url', 'brand', 'niche', 'caption', 'views', 'likes', 'days_running', 'posted_at', 'query', 'actor',
  'found_at', 'found_for', 'keep', 'kept_by', 'kept_at'];
const seen = new Set();
const out = [];
for (const it of $input.all()) {
  const r = it.json || {};
  if (r.marker || !r.url || seen.has(r.url)) continue;
  seen.add(r.url);
  const row = {};
  for (const c of COLS) row[c] = r[c] == null ? (['views', 'likes', 'days_running'].includes(c) ? null : '') : r[c];
  out.push({ json: row });
}
return out.length ? out : [{ json: { url: '' } }];
