// n8n Code node "Write the Digest" in "Reel Factory: Find References" (mode: Run Once for All Items).
// Input: the rows just saved in dtj_reel_library (each with its row id), or one empty item when nothing new was found.
// Output, per chat that gets it (the person who asked through the reel bot, or the active admins for the weekly scan):
//  - reference videos (kind "refs"): one summary message, then one message per new reference (at most MAX_SHOWN) with Keep / Skip
//    buttons. A button carries the bot's answer format "a:refs-<row id>:keep:<n>" (n8n/store-factory/bot_ask.py), so the reel bot's
//    "Reel Factory: Telegram Bot" saves the tap in dtj_bot_answers and "Match the Taps" here writes keep = yes / no on the row.
//  - an audience scan: one short message per audience, no buttons ("Audience scan <audience>: N reels saved, top 5 ..."), so the
//    reel watcher can build audiences/<slug>.md from the saved rows (source "audience" and "trending_audio", column audience).
// The messages go out through the reel bot ("DTJ Reel Bot"). A Pinterest pin's "likes" are its saves. Every item is
// { chat_id, text, summary, keep_data, skip_data } (HTML, text escaped).
const MAX_SHOWN = 15, TOP = 5;
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const NAMES = { instagram: 'Instagram', pinterest: 'Pinterest', meta: 'Meta Ad Library' };
const AUDIENCE_KINDS = ['audience', 'profiles', 'trending'];
const big = (n) => {
  const v = Number(n);
  if (!Number.isFinite(v) || v <= 0) return '';
  return v >= 1e6 ? (v / 1e6).toFixed(1).replace(/\.0$/, '') + 'M' : v >= 1e3 ? (v / 1e3).toFixed(1).replace(/\.0$/, '') + 'k' : String(Math.round(v));
};
const clip = (s, n) => { const t = String(s || '').replace(/\s+/g, ' ').trim(); return t.length > n ? t.slice(0, n) + '…' : t; };

const saved = $input.all().map((i) => i.json || {}).filter((r) => r.id && r.url);
const results = $('Read the Results').all().map((i) => i.json || {});
const marker = results.find((r) => r.marker) || {};
const plans = $('Plan the Searches').all().map((i) => i.json || {});
const refPlans = plans.filter((p) => !AUDIENCE_KINDS.includes(p.kind));
const audPlans = plans.filter((p) => AUDIENCE_KINDS.includes(p.kind));
const ownProblem = (ps) => (msg) => ps.some((p) => String(msg).startsWith(p.source + ' ' + (p.query || p.label || '') + ':'));
const out = [];

// ---- reference videos with Keep / Skip
const refs = saved.filter((r) => r.source !== 'audience' && r.source !== 'trending_audio');
const refChats = [...new Set(refPlans.flatMap((p) => p.chat_ids || []).map(String).filter(Boolean))];
if (refPlans.length && refChats.length) {
  const first = refPlans[0];
  const what = first.mode === 'weekly' ? 'the weekly scan of the watchlist' : esc(first.label || first.query || 'your search');
  const perSource = {};
  for (const r of refs) perSource[r.source] = (perSource[r.source] || 0) + 1;
  const found = Number(marker.found_refs != null ? marker.found_refs : marker.found || 0);
  let head = refs.length
    ? '<b>' + refs.length + ' new reference video' + (refs.length === 1 ? '' : 's') + '</b> from ' + what + ' ('
      + Object.keys(perSource).map((s) => (NAMES[s] || s) + ' ' + perSource[s]).join(', ') + ').'
    : 'No new reference videos from ' + what + '.';
  if (found > refs.length) head += ' ' + (found - refs.length) + ' found were already in the library.';
  if (refs.length > MAX_SHOWN) head += ' The first ' + MAX_SHOWN + ' are below; all ' + refs.length + ' are saved in dtj_reel_library.';
  if (refs.length) head += '\nTap <b>Keep</b> to add one to the reel library (/reel and /remake can use it), <b>Skip</b> to leave it out.';
  const skipped = [...new Set(refPlans.flatMap((p) => p.skipped || []))].map((s) => (NAMES[s] || s) + ': nothing to search for there');
  const problems = [...(marker.problems || []).filter((m) => !ownProblem(audPlans)(m)), ...skipped].slice(0, 6);
  if (problems.length) head += '\n\nNotes: ' + problems.map((p) => esc(p)).join('; ') + '.';

  const order = { meta: 0, instagram: 1, pinterest: 2 };
  const shown = refs.slice().sort((a, b) => (order[a.source] ?? 3) - (order[b.source] ?? 3)
    || Number(b.days_running || 0) - Number(a.days_running || 0) || Number(b.views || 0) - Number(a.views || 0)).slice(0, MAX_SHOWN);
  for (const chat of refChats) {
    out.push({ json: { chat_id: chat, text: head, summary: true, keep_data: '', skip_data: '' } });
    shown.forEach((r, i) => {
      const facts = [r.days_running ? 'running ' + r.days_running + ' days' : '', big(r.views) ? big(r.views) + ' views' : '',
        big(r.likes) ? big(r.likes) + (r.source === 'pinterest' ? ' saves' : ' likes') : ''].filter(Boolean).join(' · ');
      const caption = clip(r.caption, 220);
      const text = '<b>' + (i + 1) + '/' + shown.length + ' · ' + esc(NAMES[r.source] || r.source) + (r.brand ? ' · ' + esc(r.brand) : '') + '</b>\n'
        + (caption ? '"' + esc(caption) + '"\n' : '')
        + (facts ? facts + '\n' : '')
        + '<a href="' + esc(r.url) + '">Open it</a>' + (r.video_url ? ' · <a href="' + esc(r.video_url) + '">video file</a>' : '');
      out.push({ json: { chat_id: chat, text, summary: false, keep_data: 'a:refs-' + r.id + ':keep:0', skip_data: 'a:refs-' + r.id + ':keep:1' } });
    });
  }
}

// ---- audience scans: one short summary each, no buttons
const score = (r) => [r.views_per_follower == null ? 1 : 0, -(r.views_per_follower || 0), -(r.views || 0)];
const byScore = (p, q) => { const a = score(p), b = score(q); for (let k = 0; k < a.length; k++) if (a[k] !== b[k]) return a[k] - b[k]; return 0; };
for (const name of [...new Set(audPlans.map((p) => p.audience))]) {
  const mine = audPlans.filter((p) => p.audience === name);
  const reels = saved.filter((r) => r.source === 'audience' && r.audience === name).sort(byScore);
  const sounds = saved.filter((r) => r.source === 'trending_audio' && r.audience === name);
  const found = Number((marker.by_audience || {})[name] || 0);
  const from = mine.filter((p) => p.kind === 'audience').map((p) => p.query).join(', ');
  let text = '<b>Audience scan ' + esc(name) + '</b>: ' + reels.length + ' reel' + (reels.length === 1 ? '' : 's') + ' saved'
    + (found > reels.length ? ' (' + (found - reels.length) + ' more were already in the library)' : '') + (from ? ', from ' + esc(from) : '') + '.';
  if (reels.length) {
    text += '\nTop ' + Math.min(TOP, reels.length) + (reels.some((r) => r.views_per_follower != null) ? ' by views per follower' : ' by views') + ':';
    reels.slice(0, TOP).forEach((r, i) => {
      const facts = [big(r.views) ? big(r.views) + ' views' : '', r.views_per_follower != null ? r.views_per_follower.toFixed(1) + '× followers' : '',
        r.comments_per_view != null ? (r.comments_per_view * 100).toFixed(2) + '% comments' : '', r.audio_name ? 'audio ' + clip(r.audio_name, 50) : '']
        .filter(Boolean).join(' · ');
      text += '\n' + (i + 1) + '. <a href="' + esc(r.url) + '">' + esc(r.brand || 'reel') + '</a>' + (facts ? ' · ' + esc(facts) : '');
    });
  }
  if (sounds.length) text += '\nTrending audio in India: ' + sounds.slice(0, TOP).map((r) => esc(clip(r.audio_name || r.caption, 60))).join('; ') + '.';
  text += '\nRows: dtj_reel_library, audience "' + esc(name) + '" (audiences/' + esc(mine[0].slug || '') + '.md).';
  const problems = (marker.problems || []).filter(ownProblem(mine)).slice(0, 4);
  if (problems.length) text += '\nNotes: ' + problems.map((p) => esc(p)).join('; ') + '.';
  for (const chat of [...new Set(mine.flatMap((p) => p.chat_ids || []).map(String).filter(Boolean))]) {
    out.push({ json: { chat_id: chat, text, summary: true, keep_data: '', skip_data: '' } });
  }
}
return out;
