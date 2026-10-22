// n8n Code node "Who Is It" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Only people in the data table dtj_bot_users (active) may use the bot. Roles: requester (sends links), designer (also gets told
// when a page waits for Claude Code), admin (both, plus the app switch: /shops, /status, /on, /off).
// Output: one item with action
//   addshop -> an admin adds a client shop (Store Factory: Add Shop: the laptop's Claude Code does it)
//   store  -> an admin's store link (no /products/): the whole store (Store Factory: New Store: questions, apps, every page)
//   answer -> a tap or typed reply to a store job's question: saved in dtj_bot_answers ("Save the Answer")
//   design -> start a page (Store Factory: New Page)
//   switch -> an admin's switch command or button tap: the shop is found after the install catcher's list ("Pick the Shop")
//   intake -> start a brand intake on GitHub ("Start Brand Intake")
//   stop   -> /stop or a Stop tap: GitHub's list of brand intake runs ("List Intakes"), then "Stop Plan"
//   brief  -> the answer to "collect the brand's data first?" after a page was started: saved on the brief ("Note the Choice")
//   site   -> the reply with the brand's own website for a brief: saved on the brief ("Note the Website")
//   pictures -> the answer to "upload the brand's pictures to the shop?": saved on the brief ("Note the Pictures")
//   reply  -> just answer
const msg = $('Read the Message').first().json;
if (msg.kind === 'ignore') return [];
const users = $('Load Bot Users').all().map((i) => i.json).filter((u) => u && u.telegram_user_id && u.active !== false);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const reply = (text) => [{ json: { action: 'reply', chat_id: msg.chat_id, text } }];
const me = users.find((u) => String(u.telegram_user_id).trim() === msg.user_id);
const roleOf = (u) => String((u && u.role) || '').toLowerCase().trim();
const BUTTON_SECONDS = 120;

if (msg.kind === 'secret') {
  return reply('That looks like a password or a key. Please delete your message now (press and hold it, then Delete). '
    + 'Never send passwords or keys here, or in any chat.');
}
if (!me) {
  return reply('Hi ' + esc(msg.name) + '. This bot is only for the DTJ team. To get access, send Harsh this number: '
    + esc(msg.user_id));
}
const isAdmin = roleOf(me) === 'admin';
const myName = me.name || msg.name;
// an answer to a store job's question or Approve button (21 Oct 2026): saved in dtj_bot_answers ("Save the Answer"), where the
// laptop's store_job.py reads it. Anyone on the bot (an Approve tap is that person's yes, with their name: CLAUDE.md rule 2).
// a plain message while one of the store job's typed questions is open in this chat is its answer (22 Oct 2026: Harsh sent the
// brand's link as a new message, not a reply, and the bot took it for a second store). "Load Open Questions" holds the laptop's
// open / closed marks for this chat; the newest one decides.
let openQ = null;
try {
  const marks = $('Load Open Questions').all().map((i) => i.json)
    .filter((r) => r && String(r.chat_id) === msg.chat_id && !String(r.value || '').trim() && ['open', 'closed'].includes(r.choice));
  marks.sort((a, b) => (String(a.at).slice(0, 19) < String(b.at).slice(0, 19) ? -1 : 1));
  const last = marks[marks.length - 1];
  if (last && last.choice === 'open') openQ = last;
} catch (e) { openQ = null; }  // the step is not there (an older bot): only a reply counts
if (openQ && (msg.kind === 'link' || msg.kind === 'nolink') && String(msg.text || '').trim()) {
  return [{ json: { action: 'answer', chat_id: msg.chat_id, job: openQ.job, key: openQ.key, choice: '',
    value: String(msg.text).trim().slice(0, 500), by: myName, at: new Date().toISOString() } }];
}
if (msg.kind === 'answer') {
  const value = String(msg.arg || '').trim();
  if (!value) return reply('I could not read that answer. Tap the button again, or reply to the question with your answer.');
  return [{ json: { action: 'answer', chat_id: msg.chat_id, job: msg.job, key: msg.key, choice: String(msg.choice || ''), value,
    by: myName, at: new Date().toISOString() } }];
}
// /commands: every command, one line each; the admin ones only for admins (Harsh, 19 Oct 2026: "create a command so it can show
// all the commands in the bot available"). Keep this list in step with bot_read.js when a command is added.
if (msg.kind === 'commands') {
  const lines = [
    'Everything I can do:',
    '',
    '<b>Pages</b>',
    'a product link: start a product page in the shop\'s draft theme (anything after the link is a note for the designer). '
      + 'I then ask whether to collect the brand\'s data first, and from which website.',
    '',
    '<b>Brand data</b>',
    '/intake shop.com: collect a shop\'s pictures, videos, colours and details into Google Drive, with a live progress bar',
    '/stop: the brand intakes running now, each with a Stop button',
    '',
    '<b>Help</b>',
    '/help: how to send a product link, with an example',
    '/commands: this list',
  ];
  if (isAdmin) {
    lines.push('', '<b>Admin: the DTJ apps on each shop</b>',
      '/shops: every shop on the switch and whether its DTJ apps are on',
      '/status shop: one shop\'s DTJ apps',
      '/off shop and /on shop: switch all DTJ apps of a shop off or on (you confirm with a button)',
      '/addshop name.myshopify.com Client Name: add a client shop (the seven DTJ app copies, then seven Install buttons for you)',
      'a store\'s own link (https://brand.com, no /products/): design the whole store; I ask a few questions here first');
  }
  return reply(lines.join('\n'));
}
if (msg.kind === 'help') {
  return reply('Hi ' + esc(myName) + '! Send me a product link from the shop\'s website and I will start a full '
    + 'product page in the shop\'s draft theme.\n\nExample:\nhttps://myshop.com/products/my-product lead with the glow, real rating 4.6 on Judge.me\n\n'
    + '- The link must have /products/ in it (not a Shopify admin link).\n'
    + '- Anything after the link is a note for the designer.\n'
    + '- I send you the preview link here when the page is ready. Nothing goes live without Harsh.'
    + '\n\nBefore a redesign: /intake shop.com collects the shop\'s pictures, videos, colours and details into Google Drive.'
    + ' /stop shows the intakes running now, each with a Stop button.'
    + '\n\n/commands lists everything I can do.'
    + (isAdmin ? '\n\nAdmin: /shops lists every shop the switch reaches and whether its DTJ apps are on, /status shop shows one shop, '
      + '/off shop and /on shop switch all its DTJ apps (you confirm with a button).' : ''));
}
// a brand intake (19 Oct 2026, Harsh: "scrapes everything and uploads to the google drive"): GitHub Actions runs it ("Brand intake"
// workflow on the repo's default branch) and answers in this chat with the Drive folder's link. Anyone on the bot may ask.
if (msg.kind === 'intake') {
  const store = /^(https?:\/\/)?([A-Za-z0-9-]+\.)+[A-Za-z]{2,}(\/\S*)?$/.test(msg.arg) ? msg.arg : '';
  if (!store) {
    return reply('Send the shop\'s address after /intake, for example:\n/intake freesoul.com\n\n'
      + 'I read the shop\'s public pages (pictures and videos of up to 20 products, logo, colours, fonts, policies) and send you the '
      + 'Google Drive folder here in a few minutes.');
  }
  return [{ json: { action: 'intake', chat_id: msg.chat_id, store, requested_by: myName,
    body: { ref: 'chore/initial-import', inputs: { store, requested_by: myName, telegram_chat_id: msg.chat_id } } } }];
}
// the brand's own website for a brief (19 Oct 2026, Harsh: "it didnt asked for the brand website link?"): the shop a product link
// comes from is not always the brand's own site (DTJ's demo shop carries other brands), so after "Yes, collect it first" the bot asks.
if (msg.kind === 'site') {
  const arg = String(msg.arg || '').trim();
  if (/^(same|yes|ok|okay)$/i.test(arg)) return reply('OK: for brief ' + esc(msg.row_id) + ' the designer will read the shop itself.');
  const m = arg.match(/^(?:https?:\/\/)?((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})(?:[/?#]\S*)?$/);
  if (!m) {
    return reply('That does not look like a website address. Reply to my question again with the brand\'s own website, '
      + 'for example senso.in, or reply: same');
  }
  const host = m[1].toLowerCase().replace(/^www\./, '');
  return [{ json: { action: 'site', chat_id: msg.chat_id, row_id: msg.row_id, website: 'https://' + host, by: myName } }];
}
// "upload the brand's pictures to the shop?" (19 Oct 2026, Harsh: "it should ask either upload the assets from google drive to
// the store"): a Yes is that person's approval for this one upload (store_files.py --approved-by). Anyone on the bot.
if (msg.kind === 'button' && /^brief:(upload|keep):/.test(String(msg.data || ''))) {
  const p = String(msg.data).match(/^brief:(upload|keep):(\d{1,9})$/);
  if (!p) return reply('That button is not valid any more.');
  return [{ json: { action: 'pictures', chat_id: msg.chat_id, row_id: Number(p[2]), upload_assets: p[1] === 'upload' ? 'yes' : 'no',
    by: myName } }];
}
// "collect the brand's data first?" (19 Oct 2026, Harsh: "it should ask me if it should run the scraper or not and using the data
// available it should start designing"): the Yes / No buttons under "Intake Question" carry the brief's row id. Anyone on the bot.
if (msg.kind === 'button' && String(msg.data || '').startsWith('brief:')) {
  const b = String(msg.data).match(/^brief:(intake|skip):(\d{1,9})$/);
  if (!b) return reply('That button is not valid any more.');
  return [{ json: { action: 'brief', chat_id: msg.chat_id, row_id: Number(b[2]), brand_intake: b[1] === 'intake' ? 'yes' : 'no', by: myName } }];
}
// stopping a brand intake (19 Oct 2026, Harsh: "add a stop feature so it can stop any ongoing specific task"; he chose brand intakes
// only): /stop lists the intakes running on GitHub, each with a Stop button; the Stop button under an intake's progress bar stops
// that run. "Stop Plan" checks that the run is a brand intake that is still going before anything is cancelled. Anyone on the bot.
if (msg.kind === 'stop') return [{ json: { action: 'stop', mode: 'list', chat_id: msg.chat_id, run_id: '', by: myName } }];
if (msg.kind === 'button' && String(msg.data || '').startsWith('stop:')) {
  const s = String(msg.data).match(/^stop:intake:(\d{1,20})$/);
  if (!s) return reply('That button is not valid any more.');
  return [{ json: { action: 'stop', mode: 'cancel', chat_id: msg.chat_id, run_id: s[1], by: myName } }];
}
// adding a client shop (21 Oct 2026, Harsh: "one step process from telegram"): admins only. The laptop's Claude Code makes, links and
// releases the seven app copies and the install links (Store Factory: Add Shop); the person then taps seven Install buttons here.
if (msg.kind === 'addshop') {
  if (!isAdmin) return reply('Only an admin can add a shop.');
  const a = String(msg.arg || '').match(/^(?:https?:\/\/)?(?:admin\.shopify\.com\/store\/([a-z0-9][a-z0-9-]*)|([a-z0-9][a-z0-9-]*)\.myshopify\.com)\/?(?:\s+([\s\S]+))?$/i);
  if (!a) {
    return reply('Send the shop\'s ORIGINAL Shopify address and the client\'s name, for example:\n/addshop royal-dosa.myshopify.com Royal Dosa\n\n'
      + 'The address is in the shop\'s admin: admin.shopify.com/store/&lt;name&gt; means &lt;name&gt;.myshopify.com. I make, link and release the '
      + 'seven DTJ app copies, then send you seven Install buttons for the store owner to tap.');
  }
  const shop = ((a[1] || a[2]) + '.myshopify.com').toLowerCase();
  const label = String(a[3] || '').replace(/\s+/g, ' ').trim().slice(0, 60);
  if (!label) return reply('And the client\'s name, for the app names. For example:\n/addshop ' + esc(shop) + ' Royal Dosa');
  return [{ json: { action: 'addshop', chat_id: msg.chat_id, shop, label, requested_by: myName } }];
}
if (msg.kind === 'nolink') {
  return reply('Please send a product link from the shop\'s website (it has /products/ in it). You can add a note after the link.');
}

// ---- the app switch (admins only). Which shops exist is the install catcher's to say, so the shop is matched in "Pick the Shop".
if (msg.kind === 'command' || msg.kind === 'button') {
  if (!isAdmin) return reply('Only an admin can see or switch the DTJ apps of a shop.');
  const otherAdmins = users.filter((u) => roleOf(u) === 'admin' && String(u.telegram_user_id).trim() !== msg.user_id)
    .map((u) => String(u.telegram_user_id).trim());
  const ask = { action: 'switch', chat_id: msg.chat_id, actor: myName, admins: otherAdmins, command: msg.command, arg: msg.arg || '',
    state: '', client: '' };
  if (msg.kind === 'button') {
    if (msg.data === 'lic:cancel') return reply('Cancelled. Nothing was switched.');
    const b = msg.data.match(/^lic:(on|off):([a-z0-9-]+):(\d{9,11})$/);
    if (!b) return reply('That button is not valid any more. Send the command again.');
    const age = Math.floor(Date.now() / 1000) - Number(b[3]);
    if (age < 0 || age > BUTTON_SECONDS) return reply('That button has expired (it works for 2 minutes). Send the command again.');
    return [{ json: { ...ask, command: 'tap', state: b[1] === 'on' ? 'active' : 'inactive', client: b[2] } }];
  }
  if (msg.command !== 'shops' && !msg.arg) return reply('Which shop? For example: /' + msg.command + ' test store. Send /shops for the list.');
  return [{ json: ask }];
}

// ---- a store's own link (no /products/ in it): the whole store (21 Oct 2026, Harsh: "i just share the brand store link and it starts
// designing the store and it asks the specific questions it needs along with the app installation"). Admins only: it makes app copies.
if (!/\/products\//i.test(msg.product_link)) {
  if (!isAdmin) {
    return reply('That is a store\'s own link. For one product page, send a product link (it has /products/ in it). '
      + 'A whole store is started by an admin.');
  }
  const link = msg.product_link.match(/^(?:https?:\/\/)?(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:[/?#][^\s]*)?$/) ? msg.product_link : '';
  if (!link) return reply('That does not look like a store\'s address. Send it like this: https://brand.com');
  return [{ json: { action: 'store', chat_id: msg.chat_id, link: /^https?:\/\//i.test(link) ? link : 'https://' + link,
    note: msg.note || '', requested_by: myName } }];
}

// ---- a product link: start a page
const designers = users.filter((u) => ['designer', 'admin'].includes(roleOf(u))).map((u) => String(u.telegram_user_id).trim());
return [{ json: {
  action: 'design', chat_id: msg.chat_id, product_link: msg.product_link, note: msg.note,
  requested_by: myName + ' (Telegram)', requester_name: myName, requester_id: msg.user_id,
  designers: [...new Set(designers)],
} }];
