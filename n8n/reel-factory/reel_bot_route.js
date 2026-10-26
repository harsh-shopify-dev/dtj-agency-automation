// n8n Code node "Who Is It" in "Reel Factory: Telegram Bot" (mode: Run Once for All Items).
// Only active people in dtj_bot_users may use the bot (the same people as the store bot); /reels N is for admins.
// Output: one item with `action`:
//   answer -> "Save the Answer" (dtj_bot_answers: job, key, value, choice, by, chat_id, at), where reel_job.py, the worker and
//             Find References read it; a plain message while a typed question is open in this chat is that question's answer
//   photo  -> "Save the Photo" (dtj_bot_answers, job reelpics-<chat>): a /remake or /reel in the next 30 minutes takes it
//   reel   -> "Start New Reel" (Reel Factory: New Reel, not waited for), unless today's limit is used
//   limit  -> "Save the Limit" (dtj_reel_settings, key daily_limit)
//   refs   -> "Start Find References" (Reel Factory: Find References: /refs and /audience)
//   reply  -> just answer (help, status, refusals)
const msg = $('Read the Message').first().json;
if (msg.kind === 'ignore') return [];
// /refs and /audience need "Reel Factory: Find References" published (it needs the DTJ Apify credential and its live test first);
// deploy_reel_bot.py sets this to true and switches "Start Find References" on when that workflow is published
const REFS_READY = false;
const all = (n) => { try { return $(n).all().map((i) => i.json).filter(Boolean); } catch (e) { return []; } };
const esc = (v) => String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const reply = (text) => [{ json: { action: 'reply', chat_id: msg.chat_id, text } }];
const now = new Date().toISOString();
const users = all('Load Bot Users').filter((u) => u.telegram_user_id && u.active !== false);
const me = users.find((u) => String(u.telegram_user_id).trim() === msg.user_id);

if (msg.kind === 'secret') {
  return reply('That looks like a password or a key. Please delete your message now (press and hold it, then Delete). '
    + 'Never send passwords or keys here: they go into n8n or the VPS at a hidden prompt.');
}
if (!me) return reply('Hi ' + esc(msg.name) + '. This bot is only for the DTJ team. To get access, send Harsh this number: ' + esc(msg.user_id));
const myName = me.name || msg.name;
const isAdmin = String(me.role || '').toLowerCase().trim() === 'admin';

// an open typed question in this chat (reel_job.py marks it open / closed): a plain message is its answer
const marks = all('Load Open Questions').filter((r) => String(r.chat_id) === msg.chat_id && !String(r.value || '').trim()
  && ['open', 'closed'].includes(r.choice)).sort((a, b) => (String(a.at) < String(b.at) ? -1 : 1));
const openQ = marks.length && marks[marks.length - 1].choice === 'open' ? marks[marks.length - 1] : null;
if (openQ && msg.kind === 'plain' && msg.text) {
  return [{ json: { action: 'answer', chat_id: msg.chat_id, job: openQ.job, key: openQ.key, choice: '', value: msg.text.slice(0, 1000), by: myName, at: now } }];
}
if (msg.kind === 'answer') {
  const value = String(msg.arg || '').trim();
  if (!value) return reply('I could not read that answer. Tap the button again, or reply to the question.');
  return [{ json: { action: 'answer', chat_id: msg.chat_id, job: msg.job, key: msg.key, choice: String(msg.choice || ''), value, by: myName, at: now } }];
}
if (msg.kind === 'photo') {
  return [{ json: { action: 'photo', chat_id: msg.chat_id, job: 'reelpics-' + msg.chat_id, key: 'photo', choice: 'photo', value: msg.photo_id, by: myName, at: now } }];
}

const settings = all('Load Settings');
const limitRow = settings.find((r) => r.key === 'daily_limit');
const limit = Math.max(0, parseInt((limitRow && limitRow.value) || '10', 10) || 10);
const today = all("Load Today's Reels");

if (msg.kind === 'limit') {
  if (!isAdmin) return reply('Only an admin can change the daily limit.');
  const n = parseInt(msg.arg, 10);
  if (!(n >= 0 && n <= 100)) return reply('Send /reels and a number from 0 to 100, e.g. /reels 10. Now: ' + limit + ' a day.');
  return [{ json: { action: 'limit', chat_id: msg.chat_id, key: 'daily_limit', value: String(n), set_by: myName, set_at: now } }];
}
if (msg.kind === 'status') {
  const lines = today.map((r) => '- ' + esc(r.product_name) + ' (' + esc(r.reel_type || 'ugc') + '): ' + esc(r.reel_status || r.status));
  return reply('<b>Today: ' + today.length + ' of ' + limit + ' reels</b>\n' + (lines.join('\n') || 'none yet'));
}
if (msg.kind === 'refs' || msg.kind === 'audience') {
  if (!REFS_READY) return reply('Finding reference reels (/refs, /audience) starts once Harsh adds the Apify key in n8n and its first test passes. '
    + 'Until then, send a reel link straight to /remake.');
  if (!msg.arg) return reply(msg.kind === 'refs' ? 'Send /refs and a brand or @handle, e.g. /refs Blue Tea India meta'
    : 'Send /audience, a name and its hashtags and creators, e.g. /audience Gen Z urban India #genz #mumbai @creator');
  const tags = (msg.arg.match(/#[\w.]+/g) || []).join(' ');
  const creators = (msg.arg.match(/@[\w.]+/g) || []).join(' ');
  const sources = (msg.arg.match(/\b(instagram|pinterest|meta)\b/gi) || []).map((x) => x.toLowerCase()).join(',');
  const words = msg.arg.replace(/[#@][\w.]+/g, ' ').replace(/\b(instagram|pinterest|meta)\b/gi, ' ').replace(/\s+/g, ' ').trim();
  return [{ json: { action: 'refs', chat_id: msg.chat_id, inputs: { mode: msg.kind === 'audience' ? 'audience' : 'refs',
    query: msg.kind === 'refs' ? (words || creators) : '', sources: sources || (msg.kind === 'refs' ? 'instagram,meta' : ''),
    limit: '5', audience: msg.kind === 'audience' ? words : '', hashtags: tags, creators, requested_by: myName, chat_id: msg.chat_id } } }];
}
if (msg.kind === 'remake' || msg.kind === 'reel') {
  if (today.length >= limit) return reply("Today's limit of " + limit + ' reels is used. An admin can change it: /reels <number>.');
  const links = (msg.arg.match(/https?:\/\/[^\s<>"]+/gi) || []).map((l) => l.replace(/[).,;!?]+$/, ''));
  const isRef = (l) => /instagram\.com\/(reel|p|tv)\/|facebook\.com\/(ads|reel|watch)|fb\.watch|pinterest\.|pin\.it|\.mp4(\?|$)/i.test(l);
  const refs = links.filter(isRef);
  const product = links.filter((l) => !isRef(l));
  const keyed = (k) => { const m = msg.arg.match(new RegExp('\\b' + k + ':\\s*([^\\n]+?)(?=\\s+\\w+:|$)', 'i')); return m ? m[1].trim() : ''; };
  const rest = msg.arg.replace(/https?:\/\/[^\s<>"]+/gi, ' ').replace(/\b(for|lang|brand|note):\s*[^\n]+?(?=\s+\w+:|$)/gi, ' ')
    .replace(/\s+/g, ' ').trim();
  const cutoff = Date.now() - 30 * 60 * 1000;
  const recent = all('Load Recent Photos').filter((r) => Date.parse(r.at || r.createdAt || 0) >= cutoff).map((r) => 'tg:' + r.value);
  const pictures = [...product, ...recent, ...(msg.photo_id ? ['tg:' + msg.photo_id] : [])];
  if (msg.kind === 'remake' && refs.length !== 1) {
    return reply('A remake copies ONE reference reel. Send: /remake &lt;the reel link&gt; &lt;the product page or picture link&gt; &lt;product name&gt;'
      + ' (photos sent just before also count). Optional: for: &lt;audience&gt;');
  }
  if (!refs.length) return reply('Add at least one winning reference reel link (Instagram, Meta Ad Library, Pinterest or an mp4).');
  if (!pictures.length) return reply('Add the product: a product page or picture link, or send the product photos first and then the command.');
  const name = rest || (product[0] ? product[0].replace(/^https?:\/\/(www\.)?/, '').split(/[/?#]/).filter(Boolean).slice(-1)[0].replace(/[-_]+/g, ' ') : 'the product');
  return [{ json: { action: 'reel', chat_id: msg.chat_id, inputs: {
    reel_type: msg.kind === 'remake' ? 'remake' : 'ugc', product_name: name.slice(0, 200), audience: keyed('for'),
    brand_name: keyed('brand'), product_images: pictures.join('\n'), reference_reels: refs.join('\n'), language: keyed('lang'),
    music: '', facts: '', notes: keyed('note'), requested_by: myName, chat_id: msg.chat_id } } }];
}
// help (and any other message)
return reply([
  '<b>DTJ reel bot</b>: reels are made on DTJ\'s server while a person watches; you approve the plan, the pictures and the reel here.',
  '',
  '/remake &lt;reel link&gt; &lt;product page or picture link&gt; &lt;product name&gt; - copy one winning edit shot for shot (music only)',
  '/reel &lt;product link&gt; &lt;reference reel links&gt; &lt;product name&gt; - a UGC script reel (add lang: gujarati / hindi / hinglish / english)',
  'Add for: &lt;audience&gt; (e.g. for: Gen Z urban India), brand: &lt;name&gt;, note: &lt;anything&gt;. Photos sent just before a command are its product pictures.',
  '/refs &lt;brand or @handle&gt; [instagram pinterest meta] - find winning reference reels (Keep / Skip each)',
  '/audience &lt;name&gt; #hashtags @creators - study what an audience watches (for the watcher)',
  '/status - today\'s reels;  /reels &lt;N&gt; - today\'s limit (admins). Now ' + today.length + ' of ' + limit + ' used.',
].join('\n'));
