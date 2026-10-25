// n8n Code node "Read the Message" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Turns one Telegram update into: who wrote, in which chat, and what they want: help, a page from a product link, an admin command
// (/shops, /status, /on, /off, /addshop), a brand intake (/intake), /stop (running brand intakes), a tap on one of the bot's buttons,
// or an answer to a store job's question (a tap or a typed reply). A store's own link (no /products/ in it) is a whole store (Who Is It).
const update = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s);
const cq = update.callback_query;
if (cq) {  // a tap on a button the bot sent (the confirm / cancel buttons of /on and /off)
  const chat = (cq.message || {}).chat || {};
  const from = cq.from || {};
  const name = [from.first_name, from.last_name].filter(Boolean).join(' ') || from.username || 'there';
  const base = { chat_id: esc(chat.id), chat_type: esc(chat.type), user_id: esc(from.id), name, text: '', callback_id: esc(cq.id) };
  if (!chat.id || chat.type !== 'private' || from.is_bot) return [{ json: { ...base, kind: 'ignore' } }];
  // a store job's question or Approve button (21 Oct 2026, store_job.py / bot_ask.py): "a:<job>:<key>:<n>"; the answer is the
  // label of the tapped button, read from the message it sits under
  const ans = esc(cq.data).match(/^a:([a-z0-9][a-z0-9-]{1,23}):([a-z0-9_]{1,20}):(\d{1,2})$/);
  if (ans) {
    const keys = [].concat(...(((cq.message || {}).reply_markup || {}).inline_keyboard || []));
    const tapped = keys.find((k) => k && k.callback_data === cq.data) || {};
    return [{ json: { ...base, kind: 'answer', job: ans[1], key: ans[2], choice: ans[3], arg: esc(tapped.text).slice(0, 100) } }];
  }
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

// a reply to the bot's "Which website is the brand's own for brief N?" (19 Oct 2026): the brand's website for that brief
const asked = msg.reply_to_message || {};
// a typed answer to a store job's question: a reply to it, whose last line is "(job <job>, answer <key>)" (store_job.py)
const forJob = asked.from && asked.from.is_bot ? String(asked.text || '').match(/\(job ([a-z0-9][a-z0-9-]{1,23}), answer ([a-z0-9_]{1,20})\)\s*$/) : null;
if (forJob && text && !text.startsWith('/')) {
  // a message about a finished page may be longer than a store job's answer (Harsh, 24 Oct 2026: the page chat)
  const room = forJob[2] === 'chat' ? 1500 : 500;
  return [{ json: { ...base, kind: 'answer', job: forJob[1], key: forJob[2], choice: '', arg: text.slice(0, room) } }];
}
const forBrief = asked.from && asked.from.is_bot ? String(asked.text || '').match(/brand's own for brief (\d{1,9})\?/) : null;
if (forBrief && text && !text.startsWith('/')) return [{ json: { ...base, kind: 'site', row_id: Number(forBrief[1]), arg: text.slice(0, 200) } }];

if (/^\/(start|help)\b/i.test(text) || !text) return [{ json: { ...base, kind: 'help' } }];

// every command the bot knows, one line each (19 Oct 2026, Harsh: "create a command so it can show all the commands")
if (/^\/(commands|menu)(?:@[A-Za-z0-9_]+)?\s*$/i.test(text)) return [{ json: { ...base, kind: 'commands' } }];

// a brand intake before a redesign: /intake <the store's address> (19 Oct 2026; runs on GitHub, the Drive link comes back here)
const intake = text.match(/^\/intake(?:@[A-Za-z0-9_]+)?(?:\s+([\s\S]*))?$/i);
if (intake) return [{ json: { ...base, kind: 'intake', arg: String(intake[1] || '').trim().slice(0, 200) } }];

// add a client shop (21 Oct 2026, Harsh: "one step process from telegram ... i will provide the shopify domain of the store"):
// /addshop <store>.myshopify.com <the client's name>
const addshop = text.match(/^\/addshop(?:@[A-Za-z0-9_]+)?(?:\s+([\s\S]*))?$/i);
if (addshop) return [{ json: { ...base, kind: 'addshop', arg: String(addshop[1] || '').trim().slice(0, 200) } }];

// stop a running brand intake: /stop lists them, each with a Stop button (19 Oct 2026)
if (/^\/stop(?:@[A-Za-z0-9_]+)?\s*$/i.test(text)) return [{ json: { ...base, kind: 'stop' } }];

// admin commands: /shops, /status <shop>, /on <shop>, /off <shop> (the bot's @name may follow the command)
const cmd = text.match(/^\/(shops|status|on|off)(?:@[A-Za-z0-9_]+)?(?:\s+([\s\S]*))?$/i);
if (cmd) return [{ json: { ...base, kind: 'command', command: cmd[1].toLowerCase(), arg: String(cmd[2] || '').trim().slice(0, 100) } }];

// the first link in the message; everything else is the note for the designer
const m = text.match(/https?:\/\/[^\s<>"]+/i) || text.match(/\b(?:[a-z0-9-]+\.)+[a-z]{2,}\/[^\s<>"]*/i);
if (!m) return [{ json: { ...base, kind: 'nolink' } }];
const product_link = m[0].replace(/[).,;!?]+$/, '');
const note = (text.slice(0, m.index) + ' ' + text.slice(m.index + m[0].length)).replace(/\s+/g, ' ').trim().slice(0, 1500);
return [{ json: { ...base, kind: 'link', product_link, note } }];
