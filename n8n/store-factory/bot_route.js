// n8n Code node "Who Is It" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Only people in the data table dtj_bot_users (active) may use the bot. Roles: requester (sends links), designer (also gets told
// when a page waits for Claude Code), admin (both, plus the app switch: /shops, /status, /on, /off).
// Output: one item with action
//   design -> start a page (Store Factory: New Page)
//   switch -> an admin's switch command or button tap: the shop is found after the install catcher's list ("Pick the Shop")
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
if (msg.kind === 'help') {
  return reply('Hi ' + esc(myName) + '! Send me a product link from the shop\'s website and I will start a full '
    + 'product page in the shop\'s draft theme.\n\nExample:\nhttps://myshop.com/products/my-product lead with the glow, real rating 4.6 on Judge.me\n\n'
    + '- The link must have /products/ in it (not a Shopify admin link).\n'
    + '- Anything after the link is a note for the designer.\n'
    + '- I send you the preview link here when the page is ready. Nothing goes live without Harsh.'
    + (isAdmin ? '\n\nAdmin: /shops lists every shop the switch reaches and whether its DTJ apps are on, /status shop shows one shop, '
      + '/off shop and /on shop switch all its DTJ apps (you confirm with a button).' : ''));
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

// ---- a product link: start a page
const designers = users.filter((u) => ['designer', 'admin'].includes(roleOf(u))).map((u) => String(u.telegram_user_id).trim());
return [{ json: {
  action: 'design', chat_id: msg.chat_id, product_link: msg.product_link, note: msg.note,
  requested_by: myName + ' (Telegram)', requester_name: myName, requester_id: msg.user_id,
  designers: [...new Set(designers)],
} }];
