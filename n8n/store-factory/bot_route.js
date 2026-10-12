// n8n Code node "Who Is It" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Only people in the data table dtj_bot_users (active) may use the bot. Roles: requester (sends links), designer (also gets told
// when a page waits for Claude Code), admin (both, plus the app switch: /shops, /status, /on, /off).
// Input: the shops (dtj_stores, from "Load Shops"). Output: one item with action
//   design  -> start a page (Store Factory: New Page)
//   licence -> ask the install catcher (status, or a confirmed switch)
//   confirm -> send the "Yes, switch ..." / "Cancel" buttons
//   reply   -> just answer
const msg = $('Read the Message').first().json;
if (msg.kind === 'ignore') return [];
const users = $('Load Bot Users').all().map((i) => i.json).filter((u) => u && u.telegram_user_id && u.active !== false);
const shops = $input.all().map((i) => i.json).filter((s) => s && s.myshopify_domain && s.active !== false);
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
    + (isAdmin ? '\n\nAdmin: /shops lists the shops, /status shop shows whether its DTJ apps are on, '
      + '/off shop and /on shop switch all its DTJ apps (you confirm with a button).' : ''));
}
if (msg.kind === 'nolink') {
  return reply('Please send a product link from the shop\'s website (it has /products/ in it). You can add a note after the link.');
}

// ---- the app switch (admins only)
if (msg.kind === 'command' || msg.kind === 'button') {
  if (!isAdmin) return reply('Only an admin can see or switch the DTJ apps of a shop.');
  const clientOf = (s) => (String(s.client_registry || '').match(/clients\/([a-z0-9-]+)\.json$/) || [])[1] || '';
  const otherAdmins = users.filter((u) => roleOf(u) === 'admin' && String(u.telegram_user_id).trim() !== msg.user_id)
    .map((u) => String(u.telegram_user_id).trim());
  if (msg.kind === 'button') {
    if (msg.data === 'lic:cancel') return reply('Cancelled. Nothing was switched.');
    const b = msg.data.match(/^lic:(on|off):([a-z0-9-]+):(\d{9,11})$/);
    if (!b) return reply('That button is not valid any more. Send the command again.');
    const age = Math.floor(Date.now() / 1000) - Number(b[3]);
    if (age < 0 || age > BUTTON_SECONDS) return reply('That button has expired (it works for 2 minutes). Send the command again.');
    const shop = shops.find((s) => clientOf(s) === b[2]);
    if (!shop) return reply('That shop is not set up any more. Nothing was switched.');
    return [{ json: { action: 'licence', chat_id: msg.chat_id, state: b[1] === 'on' ? 'active' : 'inactive', client: b[2],
      shop_name: shop.store_name || shop.myshopify_domain, approved_by: myName + ' via Telegram', reason: 'Telegram /' + b[1],
      actor: myName, admins: otherAdmins } }];
  }
  if (msg.command === 'shops') {
    if (!shops.length) return reply('No shops are set up yet.');
    return reply('Shops:\n' + shops.map((s) => '- ' + esc(s.store_name || s.myshopify_domain) + ' (' + esc(s.myshopify_domain) + ')').join('\n')
      + '\n\nUse a name with /status, /on or /off, for example: /status ' + esc(shops[0].store_name || shops[0].myshopify_domain));
  }
  if (!msg.arg) return reply('Which shop? For example: /' + msg.command + ' test store. Send /shops for the list.');
  const q = msg.arg.toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '').trim();
  const names = (s) => [s.store_name, s.myshopify_domain, clientOf(s), ...String(s.other_domains || '').split(',')]
    .map((x) => String(x || '').toLowerCase().trim()).filter(Boolean);
  let found = shops.filter((s) => names(s).includes(q));
  if (!found.length) found = shops.filter((s) => names(s).some((n) => n.includes(q)));
  if (!found.length) return reply('No shop matches "' + esc(msg.arg) + '". Send /shops for the list.');
  if (found.length > 1) return reply('More than one shop matches "' + esc(msg.arg) + '": ' + found.map((s) => esc(s.store_name)).join(', ') + '. Please be more specific.');
  const shop = found[0];
  const client = clientOf(shop);
  const shopName = shop.store_name || shop.myshopify_domain;
  if (!client) return reply(esc(shopName) + ' has no app copies saved, so it cannot be checked or switched here.');
  if (msg.command === 'status') {
    return [{ json: { action: 'licence', chat_id: msg.chat_id, state: 'status', client, shop_name: shopName, approved_by: '', reason: '',
      actor: myName, admins: [] } }];
  }
  const off = msg.command === 'off';
  const word = off ? 'OFF' : 'ON';
  const stamp = Math.floor(Date.now() / 1000);
  return [{ json: { action: 'confirm', chat_id: msg.chat_id,
    text: 'Switch ' + word + ' all DTJ apps on ' + esc(shopName) + '?\n'
      + (off ? 'Every DTJ block disappears from that shop for its shoppers at once.' : 'Every DTJ block comes back on that shop at once.')
      + '\nTap the button within 2 minutes.',
    yes_text: 'Yes, switch ' + word, yes_data: 'lic:' + msg.command + ':' + client + ':' + stamp } }];
}

// ---- a product link: start a page
const designers = users.filter((u) => ['designer', 'admin'].includes(roleOf(u))).map((u) => String(u.telegram_user_id).trim());
return [{ json: {
  action: 'design', chat_id: msg.chat_id, product_link: msg.product_link, note: msg.note,
  requested_by: myName + ' (Telegram)', requester_name: myName, requester_id: msg.user_id,
  designers: [...new Set(designers)],
} }];
