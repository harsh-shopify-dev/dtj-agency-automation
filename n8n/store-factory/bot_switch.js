// n8n Code node "Pick the Shop" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Input: the install catcher's list of every shop the switch reaches ("Ask for the Shop List": full response, statusCode + body):
// client app copies AND stores in DTJ's own organization running DTJ's original apps (Harsh, 12 Oct 2026: "on every store we work
// on the switch must work"). Finds the shop the admin named and decides the next step. Output: one item with action
//   licence -> ask the catcher about (or switch) every app of `shops`: status for /shops and /status, active|inactive after a tap
//   confirm -> send the "Yes, switch ..." / "Cancel" buttons
//   reply   -> just answer
// dtj_stores ("Load Shops") only adds friendlier names and the shop's other addresses, and shows shops set up for pages whose apps
// are not on the switch yet.
const ask = $('Who Is It').first().json;
const res = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const reply = (text) => [{ json: { action: 'reply', chat_id: ask.chat_id, text } }];
const parse = (b) => { if (b && typeof b === 'object') return b; try { return JSON.parse(String(b || '{}')); } catch (e) { return {}; } };
const code = Number(res.statusCode || (res.error ? 0 : 200));
const body = parse(res.body !== undefined ? res.body : res);
if (code === 401) {
  return reply('The install service refused the bot\'s key (ask Harsh to check the n8n credential "DTJ Catcher Bot Key"). Nothing was changed.');
}
if (code !== 200 || !Array.isArray(body.shops)) {
  const why = body.error || (typeof res.error === 'string' ? res.error : (res.error && res.error.message)) || ('HTTP ' + code);
  return reply('I could not reach the install service (' + esc(why) + '). Nothing was changed. Please try again in a minute.');
}

const low = (x) => String(x == null ? '' : x).toLowerCase().trim();
const rows = $('Load Shops').all().map((i) => i.json).filter((r) => r && r.myshopify_domain && r.active !== false);
const stem = (r) => (String(r.client_registry || '').match(/clients\/([a-z0-9-]+)\.json$/) || [])[1] || '';
const shops = body.shops.map((s) => {
  const row = rows.find((r) => low(r.myshopify_domain) === low(s.shop) || stem(r) === s.client);
  const name = (row && row.store_name) || s.name || s.client;
  const names = [name, s.name, s.client, s.shop, ...(row ? [row.myshopify_domain, ...String(row.other_domains || '').split(',')] : [])]
    .map(low).filter(Boolean);
  return { client: s.client, shop: s.shop, name, kind: s.kind, apps: (s.apps || []).map((a) => ({ app: a.app, label: a.label })), names };
});
const missing = rows.filter((r) => !shops.some((s) => low(s.shop) === low(r.myshopify_domain) || s.client === stem(r)))
  .map((r) => ({ name: r.store_name || r.myshopify_domain, names: [r.store_name, r.myshopify_domain, stem(r), ...String(r.other_domains || '').split(',')].map(low).filter(Boolean) }));
const plain = (s) => ({ client: s.client, shop: s.shop, name: s.name, kind: s.kind, apps: s.apps });
const licence = (state, list, extra) => [{ json: { action: 'licence', chat_id: ask.chat_id, state, shops: list.map(plain), listing: false,
  missing: [], approved_by: '', reason: '', actor: ask.actor, admins: [], ...extra } }];

if (ask.command === 'tap') {
  const shop = shops.find((s) => s.client === ask.client);
  if (!shop) return reply('That shop is not on the switch any more. Nothing was switched.');
  const word = ask.state === 'active' ? 'on' : 'off';
  return licence(ask.state, [shop], { approved_by: ask.actor + ' via Telegram', reason: 'Telegram /' + word, admins: ask.admins || [] });
}
if (ask.command === 'shops') {
  if (!shops.length) {
    return reply('No shop is on the switch yet.' + (missing.length ? ' Set up for pages only: ' + missing.map((m) => esc(m.name)).join(', ') + '.' : ''));
  }
  return licence('status', shops, { listing: true, missing: missing.map((m) => m.name) });
}

const q = low(ask.arg).replace(/^https?:\/\//, '').replace(/\/.*$/, '');
let found = shops.filter((s) => s.names.includes(q));
if (!found.length) found = shops.filter((s) => s.names.some((n) => n.includes(q)));
if (!found.length) {
  const pagesOnly = missing.find((m) => m.names.includes(q) || m.names.some((n) => n.includes(q)));
  if (pagesOnly) return reply(esc(pagesOnly.name) + ' is set up for pages, but its DTJ apps are not on the switch yet. Ask Harsh to add it.');
  return reply('No shop matches "' + esc(ask.arg) + '". Send /shops for the list.');
}
if (found.length > 1) {
  return reply('More than one shop matches "' + esc(ask.arg) + '": ' + found.map((s) => esc(s.name)).join(', ') + '. Please be more specific.');
}
const shop = found[0];
if (ask.command === 'status') return licence('status', [shop], {});
const off = ask.command === 'off';
const word = off ? 'OFF' : 'ON';
const yes = 'lic:' + ask.command + ':' + shop.client + ':' + Math.floor(Date.now() / 1000);
if (yes.length > 64) return reply('That shop\'s name is too long for a Telegram button. Ask Harsh to switch it with licence_call.py.');
return [{ json: { action: 'confirm', chat_id: ask.chat_id,
  text: 'Switch ' + word + ' all DTJ apps on ' + esc(shop.name) + ' (' + esc(shop.shop) + ')?\n'
    + (off ? 'Every DTJ block disappears from that shop for its shoppers at once.' : 'Every DTJ block comes back on that shop at once.')
    + '\nTap the button within 2 minutes.',
  yes_text: 'Yes, switch ' + word, yes_data: yes } }];
