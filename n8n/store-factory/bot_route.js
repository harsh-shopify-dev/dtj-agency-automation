// n8n Code node "Who Is It" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Only people in the data table dtj_bot_users (active) may use the bot. Roles: requester (sends links), designer (also gets told
// when a page waits for Claude Code), admin (both). Output: action "design" (start a page) or "reply" (just answer).
const msg = $('Read the Message').first().json;
if (msg.kind === 'ignore') return [];
const users = $input.all().map((i) => i.json).filter((u) => u && u.telegram_user_id && u.active !== false);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const reply = (text) => [{ json: { action: 'reply', chat_id: msg.chat_id, text } }];
const me = users.find((u) => String(u.telegram_user_id).trim() === msg.user_id);

if (msg.kind === 'secret') {
  return reply('That looks like a password or a key. Please delete your message now (press and hold it, then Delete). '
    + 'Never send passwords or keys here, or in any chat.');
}
if (!me) {
  return reply('Hi ' + esc(msg.name) + '. This bot is only for the DTJ team. To get access, send Harsh this number: '
    + esc(msg.user_id));
}
if (msg.kind === 'help') {
  return reply('Hi ' + esc(me.name || msg.name) + '! Send me a product link from the shop\'s website and I will start a full '
    + 'product page in the shop\'s draft theme.\n\nExample:\nhttps://myshop.com/products/my-product lead with the glow, real rating 4.6 on Judge.me\n\n'
    + '- The link must have /products/ in it (not a Shopify admin link).\n'
    + '- Anything after the link is a note for the designer.\n'
    + '- I send you the preview link here when the page is ready. Nothing goes live without Harsh.');
}
if (msg.kind === 'nolink') {
  return reply('Please send a product link from the shop\'s website (it has /products/ in it). You can add a note after the link.');
}
const designers = users.filter((u) => ['designer', 'admin'].includes(String(u.role || '').toLowerCase().trim()))
  .map((u) => String(u.telegram_user_id).trim());
return [{ json: {
  action: 'design', chat_id: msg.chat_id, product_link: msg.product_link, note: msg.note,
  requested_by: (me.name || msg.name) + ' (Telegram)', requester_name: me.name || msg.name, requester_id: msg.user_id,
  designers: [...new Set(designers)],
} }];
