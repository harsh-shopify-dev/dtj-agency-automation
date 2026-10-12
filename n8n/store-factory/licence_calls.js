// n8n Code node "Licence Calls" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// One request per app of every shop "Pick the Shop" chose, for the install catcher's /licence (the HTTP step "Ask the Switch" sends
// each one with the bot's key from the n8n credential "DTJ Catcher Bot Key"). The apps come from the catcher's own list, so client
// copies (<client>-blocks / -sections / -sections2) and DTJ's original apps on organization stores are asked the same way.
const a = $input.first().json || {};
const ts = Math.floor(Date.now() / 1000);
const out = [];
for (const s of a.shops || []) {
  for (const p of s.apps || []) {
    const body = a.state === 'status'
      ? { app: p.app, state: 'status', ts }
      : { app: p.app, state: a.state, ts, approved_by: a.approved_by, reason: a.reason || '' };
    out.push({ json: { app: p.app, label: String(p.label || p.app).split(' - ')[0], client: s.client, body: JSON.stringify(body) } });
  }
}
return out;
