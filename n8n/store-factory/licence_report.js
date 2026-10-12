// n8n Code node "Licence Report" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Turns the catcher's answers (full responses: statusCode + body, one per app, in the order of "Licence Calls") into the message for
// the admin who asked, grouped per shop, and, after a switch, a note to every other admin. Every item out is { chat_id, text } for
// the "Send" step.
const a = $('Pick the Shop').first().json;
const calls = $('Licence Calls').all().map((i) => i.json);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const parse = (b) => { if (b && typeof b === 'object') return b; try { return JSON.parse(String(b || '{}')); } catch (e) { return {}; } };
const word = (v) => (v === 'active' ? 'ON' : v === 'inactive' ? 'OFF' : v ? String(v) : 'not set (blocks hidden)');
const rows = $input.all().map((it, i) => {
  const r = it.json || {};
  const code = Number(r.statusCode || (r.error ? 0 : 200));
  const body = parse(r.body !== undefined ? r.body : r);
  const call = calls[i] || {};
  return { label: call.label || 'App ' + (i + 1), client: call.client || '', code, body, error: String(body.error || '') };
});
const line = (r) => {
  if (r.code === 200 && a.state === 'status') return r.label + ': ' + word(r.body.licence);
  if (r.code === 200) return r.label + ': ' + word(r.body.before) + ' -> ' + word(r.body.after) + (r.body.verified ? ' (checked)' : ' (NOT confirmed)');
  if (r.code === 404 && /no store key|has not installed/i.test(r.error)) return r.label + ': not installed on the shop';
  if (r.code === 404 && /organization/i.test(r.error)) return r.label + ': DTJ\'s app is not installed there, or the shop is outside DTJ\'s Shopify organization';
  if (r.code === 404) return r.label + ': not connected (' + esc(r.error || 'not installed') + ')';
  if (r.code === 401) return r.label + ': the bot\'s key was refused (ask Harsh to check the credential "DTJ Catcher Bot Key")';
  return r.label + ': failed (' + esc(r.error || ('HTTP ' + r.code)) + ')';
};
const block = (s) => rows.filter((r) => r.client === s.client).map(line).join('\n');
const head = (s) => esc(s.name) + ' (' + esc(s.shop) + (s.kind === 'dtj apps' ? ', DTJ\'s own apps' : '') + ')';
const fit = (text) => (text.length > 4000 ? text.slice(0, 3990) + '\n...' : text);  // Telegram's limit is 4096 characters

if (a.listing) {
  const parts = (a.shops || []).map((s) => head(s) + '\n' + block(s));
  const rest = (a.missing || []).length ? '\n\nSet up for pages, but not on the switch yet: ' + a.missing.map(esc).join(', ') + ' (ask Harsh).' : '';
  const example = (a.shops || [])[0] ? '\n\nUse a name with /status, /on or /off, for example: /status ' + esc(a.shops[0].name) : '';
  return [{ json: { chat_id: a.chat_id, text: fit('Shops on the switch:\n\n' + parts.join('\n\n') + rest + example) } }];
}
const shop = (a.shops || [])[0] || { name: '?', shop: '?', client: '' };
if (a.state === 'status') return [{ json: { chat_id: a.chat_id, text: fit('DTJ apps on ' + head(shop) + ':\n' + block(shop)) } }];

const ok = rows.length > 0 && rows.every((r) => r.code === 200 && r.body.verified);
const word2 = a.state === 'active' ? 'ON' : 'OFF';
const lines = block(shop);
const top = ok ? 'Done: all DTJ apps on ' + esc(shop.name) + ' are ' + word2 + '.' : 'Not everything switched on ' + esc(shop.name) + '. Check the lines below.';
const out = [{ json: { chat_id: a.chat_id, text: fit(top + '\n' + lines) } }];
for (const id of a.admins || []) {
  out.push({ json: { chat_id: id, text: fit(esc(a.actor) + ' switched ' + word2 + ' the DTJ apps on ' + esc(shop.name) + ' via Telegram.\n' + lines) } });
}
return out;
