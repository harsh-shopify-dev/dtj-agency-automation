// n8n Code node "Tell the Requester" in "Store Factory: Add Shop" (mode: Run Once for All Items).
// The result of /addshop for the admin who asked (in the chat it came from). Output: [] (no chat) or one { chat_id, text } for "Send Result".
const r = $input.first().json || {};
const chat = String(r.chat_id || '').trim();
if (!chat) return [];
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const who = esc(r.label) + ' (' + esc(r.shop) + ')';
let text;
if (r.shop_status === 'done') {
  text = who + ' is added: all 7 DTJ apps are installed and their licences are on.\n\n'
    + 'Before page requests for it work: its draft theme id goes into the shop list, and the shop installs Shopify\'s Theme Access app '
    + '(Harsh saves the password it emails). Then send any product link from that shop.';
} else if (r.shop_status === 'waiting for installs') {
  text = who + ': ' + (r.installed == null ? 'some' : r.installed) + ' of 7 apps installed so far. Tap the remaining Install buttons '
    + '(the store owner, logged in to that shop), then send /addshop ' + esc(r.shop) + ' ' + esc(r.label) + ' again: it continues where it stopped.'
    + (r.note ? '\n' + esc(r.note) : '');
} else {
  text = who + ' was not added (' + esc(r.shop_status || 'no answer') + ')' + (r.note ? ': ' + esc(r.note) : '.') + '\nHarsh will take a look.';
}
return [{ json: { chat_id: chat, text } }];
