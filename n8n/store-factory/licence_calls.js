// n8n Code node "Licence Calls" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// One request per DTJ app of the shop for the install catcher's /licence (the HTTP step "Ask the Switch" sends each one with the
// bot's key from the n8n credential "DTJ Catcher Bot Key"). The catcher names a client's apps <client>-blocks / -sections / -sections2.
const a = $input.first().json || {};
const ts = Math.floor(Date.now() / 1000);
return [['blocks', 'DTJ Blocks'], ['sections', 'DTJ Sections'], ['sections2', 'DTJ Sections 2']].map(([part, label]) => {
  const app = a.client + '-' + part;
  const body = a.state === 'status'
    ? { app, state: 'status', ts }
    : { app, state: a.state, ts, approved_by: a.approved_by, reason: a.reason || '' };
  return { json: { app, label, body: JSON.stringify(body) } };
});
