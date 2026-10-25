// n8n Code node "Write the Digest" in "Reel Factory: Find References" (mode: Run Once for All Items).
// Input: the references just saved in dtj_reel_library (each with its row id), or one empty item when nothing new was found.
// Output, per chat that gets the digest (the person who asked with /refs, or the active admins for the weekly scan): one summary
// message, then one message per new reference (at most MAX_SHOWN) with Keep / Skip buttons. A button carries the bot's answer format
// "a:refs-<row id>:keep:<n>" (n8n/store-factory/bot_ask.py), so the reel bot's "Reel Factory: Telegram Bot" saves the tap in
// dtj_bot_answers and "Match the Taps" here writes keep = yes / no on the row. The messages go out through the reel bot
// ("DTJ Reel Bot"). A Pinterest pin's "likes" are its saves. Every item is { chat_id, text, summary, keep_data, skip_data }
// (HTML, text escaped).
const MAX_SHOWN = 15;
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const NAMES = { instagram: 'Instagram', pinterest: 'Pinterest', meta: 'Meta Ad Library' };
const big = (n) => {
  const v = Number(n);
  if (!Number.isFinite(v) || v <= 0) return '';
  return v >= 1e6 ? (v / 1e6).toFixed(1).replace(/\.0$/, '') + 'M' : v >= 1e3 ? (v / 1e3).toFixed(1).replace(/\.0$/, '') + 'k' : String(Math.round(v));
};

const saved = $input.all().map((i) => i.json || {}).filter((r) => r.id && r.url);
const results = $('Read the Results').all().map((i) => i.json || {});
const marker = results.find((r) => r.marker) || {};
const plans = $('Plan the Searches').all().map((i) => i.json || {});
const first = plans[0] || {};
const chats = [...new Set(plans.flatMap((p) => p.chat_ids || []).map(String).filter(Boolean))];
if (!chats.length) return [];

const what = first.mode === 'weekly' ? 'the weekly scan of the watchlist' : esc(first.label || first.query || 'your search');
const perSource = {};
for (const r of saved) perSource[r.source] = (perSource[r.source] || 0) + 1;
const found = Number(marker.found || 0);
let head = saved.length
  ? '<b>' + saved.length + ' new reference video' + (saved.length === 1 ? '' : 's') + '</b> from ' + what + ' ('
    + Object.keys(perSource).map((s) => (NAMES[s] || s) + ' ' + perSource[s]).join(', ') + ').'
  : 'No new reference videos from ' + what + '.';
if (found > saved.length) head += ' ' + (found - saved.length) + ' found were already in the library.';
if (saved.length > MAX_SHOWN) head += ' The first ' + MAX_SHOWN + ' are below; all ' + saved.length + ' are saved in dtj_reel_library.';
if (saved.length) head += '\nTap <b>Keep</b> to add one to the reel library (/reel and /remake can use it), <b>Skip</b> to leave it out.';
const skipped = [...new Set(plans.flatMap((p) => p.skipped || []))].map((s) => (NAMES[s] || s) + ': nothing to search for there');
const problems = [...(marker.problems || []), ...skipped].slice(0, 6);
if (problems.length) head += '\n\nNotes: ' + problems.map((p) => esc(p)).join('; ') + '.';

const order = { meta: 0, instagram: 1, pinterest: 2 };
const shown = saved.slice().sort((a, b) => (order[a.source] ?? 3) - (order[b.source] ?? 3)
  || Number(b.days_running || 0) - Number(a.days_running || 0) || Number(b.views || 0) - Number(a.views || 0)).slice(0, MAX_SHOWN);
const out = [];
for (const chat of chats) {
  out.push({ json: { chat_id: chat, text: head, summary: true, keep_data: '', skip_data: '' } });
  shown.forEach((r, i) => {
    const facts = [r.days_running ? 'running ' + r.days_running + ' days' : '', big(r.views) ? big(r.views) + ' views' : '',
      big(r.likes) ? big(r.likes) + (r.source === 'pinterest' ? ' saves' : ' likes') : ''].filter(Boolean).join(' · ');
    const caption = String(r.caption || '').replace(/\s+/g, ' ').trim();
    const text = '<b>' + (i + 1) + '/' + shown.length + ' · ' + esc(NAMES[r.source] || r.source) + (r.brand ? ' · ' + esc(r.brand) : '') + '</b>\n'
      + (caption ? '"' + esc(caption.slice(0, 220)) + (caption.length > 220 ? '…' : '') + '"\n' : '')
      + (facts ? facts + '\n' : '')
      + '<a href="' + esc(r.url) + '">Open it</a>' + (r.video_url ? ' · <a href="' + esc(r.video_url) + '">video file</a>' : '');
    out.push({ json: { chat_id: chat, text, summary: false, keep_data: 'a:refs-' + r.id + ':keep:0', skip_data: 'a:refs-' + r.id + ':keep:1' } });
  });
}
return out;
