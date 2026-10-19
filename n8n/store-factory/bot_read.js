// n8n Code node "Read the Message" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Turns one Telegram update into: who wrote, in which chat, and what they want: help, a page from a product link, an admin command
// (/shops, /status, /on, /off) or a tap on one of the bot's buttons.
const update = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s);
const cq = update.callback_query;
if (cq) {  // a tap on a button the bot sent (the confirm / cancel buttons of /on and /off)
  const chat = (cq.message || {}).chat || {};
  const from = cq.from || {};
  const name = [from.first_name, from.last_name].filter(Boolean).join(' ') || from.username || 'there';
  const base = { chat_id: esc(chat.id), chat_type: esc(chat.type), user_id: esc(from.id), name, text: '', callback_id: esc(cq.id) };
  if (!chat.id || chat.type !== 'private' || from.is_bot) return [{ json: { ...base, kind: 'ignore' } }];
  return [{ json: { ...base, kind: 'button', data: esc(cq.data).slice(0, 64) } }];
}
const msg = update.message || update;
const chat = msg.chat || {};
const from = msg.from || {};
const text = String(msg.text || '').trim();
const name = [from.first_name, from.last_name].filter(Boolean).join(' ') || from.username || 'there';
const base = { chat_id: String(chat.id || ''), chat_type: String(chat.type || ''), user_id: String(from.id || ''), name, text, callback_id: '' };

// group chats, channels, other bots and empty updates are ignored: the bot only talks one to one
if (!chat.id || chat.type !== 'private' || from.is_bot) return [{ json: { ...base, kind: 'ignore' } }];

// a message that looks like a password, token or key is never used (the person is asked to delete it)
const secret = /\bshp(at|ca|ss|tka)_[0-9a-z]{8,}/i.test(text) || /\b[0-9]{8,10}:[A-Za-z0-9_-]{30,}\b/.test(text)
  || /\b[0-9a-f]{32,}\b/i.test(text) || /\beyJ[A-Za-z0-9_-]{20,}\./.test(text) || /\bsk-ant-[A-Za-z0-9_-]{10,}/.test(text);
if (secret) return [{ json: { ...base, kind: 'secret' } }];

if (/^\/(start|help)\b/i.test(text) || !text) return [{ json: { ...base, kind: 'help' } }];

// a brand intake before a redesign: /intake <the store's address> (19 Oct 2026; runs on GitHub, the Drive link comes back here)
const intake = text.match(/^\/intake(?:@[A-Za-z0-9_]+)?(?:\s+([\s\S]*))?$/i);
if (intake) return [{ json: { ...base, kind: 'intake', arg: String(intake[1] || '').trim().slice(0, 200) } }];

// admin commands: /shops, /status <shop>, /on <shop>, /off <shop> (the bot's @name may follow the command)
const cmd = text.match(/^\/(shops|status|on|off)(?:@[A-Za-z0-9_]+)?(?:\s+([\s\S]*))?$/i);
if (cmd) return [{ json: { ...base, kind: 'command', command: cmd[1].toLowerCase(), arg: String(cmd[2] || '').trim().slice(0, 100) } }];

// the first link in the message; everything else is the note for the designer
const m = text.match(/https?:\/\/[^\s<>"]+/i) || text.match(/\b(?:[a-z0-9-]+\.)+[a-z]{2,}\/[^\s<>"]*/i);
if (!m) return [{ json: { ...base, kind: 'nolink' } }];
const product_link = m[0].replace(/[).,;!?]+$/, '');
const note = (text.slice(0, m.index) + ' ' + text.slice(m.index + m[0].length)).replace(/\s+/g, ' ').trim().slice(0, 1500);
return [{ json: { ...base, kind: 'link', product_link, note } }];
