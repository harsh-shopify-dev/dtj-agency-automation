// n8n Code node "Licence Report" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Turns the catcher's three answers (full responses: statusCode + body) into the message for the admin who asked and, after a switch,
// a note to every other admin. Every item out is { chat_id, text } for the "Send" step.
const a = $('Who Is It').first().json;
const calls = $('Licence Calls').all().map((i) => i.json);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const parse = (b) => { if (b && typeof b === 'object') return b; try { return JSON.parse(String(b || '{}')); } catch (e) { return {}; } };
const word = (v) => (v === 'active' ? 'ON' : v === 'inactive' ? 'OFF' : v ? String(v) : 'not set');
const rows = $input.all().map((it, i) => {
  const r = it.json || {};
  const code = Number(r.statusCode || (r.error ? 0 : 200));
  const body = parse(r.body !== undefined ? r.body : r);
  return { label: (calls[i] || {}).label || 'App ' + (i + 1), code, body };
});
const unknown = rows.every((r) => r.code === 404 && /unknown app/i.test(String(r.body.error || '')));
if (unknown) {
  return [{ json: { chat_id: a.chat_id, text: esc(a.shop_name) + ' uses DTJ\'s own apps, not client copies: the switch only manages client '
    + 'app copies (installed through the install catcher). Nothing was changed.' } }];
}
const line = (r) => {
  if (r.code === 200 && a.state === 'status') return r.label + ': ' + word(r.body.licence);
  if (r.code === 200) return r.label + ': ' + word(r.body.before) + ' -> ' + word(r.body.after) + (r.body.verified ? ' (checked)' : ' (NOT confirmed)');
  if (r.code === 404) return r.label + ': not connected (' + esc(r.body.error || 'not installed') + ')';
  if (r.code === 401) return r.label + ': the bot\'s key was refused (ask Harsh to check the credential "DTJ Catcher Bot Key")';
  return r.label + ': failed (' + esc(r.body.error || ('HTTP ' + r.code)) + ')';
};
const lines = rows.map(line).join('\n');
if (a.state === 'status') return [{ json: { chat_id: a.chat_id, text: 'DTJ apps on ' + esc(a.shop_name) + ':\n' + lines } }];

const ok = rows.every((r) => r.code === 200 && r.body.verified);
const word2 = a.state === 'active' ? 'ON' : 'OFF';
const head = (ok ? 'Done: all DTJ apps on ' + esc(a.shop_name) + ' are ' + word2 + '.' : 'Not everything switched on ' + esc(a.shop_name) + '. Check the lines below.');
const out = [{ json: { chat_id: a.chat_id, text: head + '\n' + lines } }];
for (const id of a.admins || []) {
  out.push({ json: { chat_id: id, text: esc(a.actor) + ' switched ' + word2 + ' the DTJ apps on ' + esc(a.shop_name) + ' via Telegram.\n' + lines } });
}
return out;
