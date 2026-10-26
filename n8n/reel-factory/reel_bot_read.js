// n8n Code node "Read the Message" in "Reel Factory: Telegram Bot" (mode: Run Once for All Items).
// The reel factory's own bot (Harsh, 25 Oct 2026: "we will create a new telegram bot for this automation"). Turns one Telegram
// update into who wrote, in which chat and what they want (`kind`):
//   answer  - a tap on a job's button ("a:<job>:<key>:<n>": worker Start/Stop wr<run>, reel approvals r<row>, Keep/Skip refs-<id>)
//             or a reply to a job's typed question (its last line "(job <job>, answer <key>)")
//   photo   - a product photo (the largest size is kept); a /remake or /reel in its caption is that command with the photo
//   remake  - /remake <reference reel link> [product page / picture links] [product name] [for: audience] [lang: ...]
//   reel    - /reel <product page / picture links> [reference links] [product name] [for: ...] [lang: ...]  (a UGC script reel)
//   limit   - /reels <N>: today's reel limit;  refs - /refs <brand or @handle> [instagram|pinterest|meta];
//   audience - /audience <name> #tag @creator ...;  status - /status;  help - /start, /help, anything without a command
//   secret  - a message that looks like a password, token or key (never used);  ignore - groups, channels, other bots
const update = $input.first().json || {};
const s = (v) => String(v == null ? '' : v);
const nameOf = (f) => [f.first_name, f.last_name].filter(Boolean).join(' ') || f.username || 'there';

const cq = update.callback_query;
if (cq) {
  const chat = (cq.message || {}).chat || {};
  const from = cq.from || {};
  const base = { chat_id: s(chat.id), user_id: s(from.id), name: nameOf(from), text: '', callback_id: s(cq.id), photo_id: '' };
  if (!chat.id || chat.type !== 'private' || from.is_bot) return [{ json: { ...base, kind: 'ignore' } }];
  const ans = s(cq.data).match(/^a:([a-z0-9][a-z0-9-]{1,23}):([a-z0-9_]{1,20}):(\d{1,2})$/);
  if (!ans) return [{ json: { ...base, kind: 'ignore' } }];
  const keys = [].concat(...(((cq.message || {}).reply_markup || {}).inline_keyboard || []));
  const tapped = keys.find((k) => k && k.callback_data === cq.data) || {};
  return [{ json: { ...base, kind: 'answer', job: ans[1], key: ans[2], choice: ans[3], arg: s(tapped.text).slice(0, 100) } }];
}

const msg = update.message || {};
const chat = msg.chat || {};
const from = msg.from || {};
const photos = Array.isArray(msg.photo) ? msg.photo : [];
const photo_id = photos.length ? s(photos[photos.length - 1].file_id) : '';
const text = s(msg.text || msg.caption).trim();
const base = { chat_id: s(chat.id), user_id: s(from.id), name: nameOf(from), text, callback_id: '', photo_id };
if (!chat.id || chat.type !== 'private' || from.is_bot) return [{ json: { ...base, kind: 'ignore' } }];

const secret = /\b[0-9]{8,10}:[A-Za-z0-9_-]{30,}\b/.test(text) || /\bapify_api_[A-Za-z0-9]{20,}/i.test(text)
  || /\b[0-9a-f]{32,}\b/i.test(text) || /\beyJ[A-Za-z0-9_-]{20,}\./.test(text) || /\bsk-(ant-)?[A-Za-z0-9_-]{16,}/.test(text);
if (secret) return [{ json: { ...base, kind: 'secret' } }];

const asked = msg.reply_to_message || {};
const forJob = asked.from && asked.from.is_bot ? s(asked.text).match(/\(job ([a-z0-9][a-z0-9-]{1,23}), answer ([a-z0-9_]{1,20})\)\s*$/) : null;
if (forJob && text && !text.startsWith('/')) {
  return [{ json: { ...base, kind: 'answer', job: forJob[1], key: forJob[2], choice: '', arg: text.slice(0, 1000) } }];
}

const cmd = text.match(/^\/([a-z]+)(?:@[A-Za-z0-9_]+)?(?:\s+([\s\S]*))?$/i);
const word = cmd ? cmd[1].toLowerCase() : '';
const arg = cmd ? s(cmd[2]).trim().slice(0, 1500) : '';
if (word === 'remake' || word === 'reel') return [{ json: { ...base, kind: word, arg } }];
if (word === 'reels') return [{ json: { ...base, kind: 'limit', arg } }];
if (word === 'refs') return [{ json: { ...base, kind: 'refs', arg } }];
if (word === 'audience') return [{ json: { ...base, kind: 'audience', arg } }];
if (word === 'status') return [{ json: { ...base, kind: 'status' } }];
if (photo_id) return [{ json: { ...base, kind: 'photo' } }];
if (word === 'start' || word === 'help' || word === 'commands' || !text) return [{ json: { ...base, kind: 'help' } }];
return [{ json: { ...base, kind: 'plain' } }];
