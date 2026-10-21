// n8n Code node "Claude Code Reply: Add Shop" in "Store Factory: Add Shop" (mode: Run Once for All Items).
// Reads what Claude Code posted to the Wait node (a timeout resumes with no body) and keeps only well-formed values: the same rules as
// n8n/store-factory/reply.py, which refuses a malformed answer before sending it.
const posted = $input.first().json.body;
const b = posted && typeof posted === 'object' && !Array.isArray(posted) ? posted : {};
const allowed = ['done', 'waiting for installs', 'could not add'];
let status = allowed.includes(b.shop_status) ? b.shop_status : (Object.keys(b).length ? 'reply not understood' : 'timed out (no reply in 3 days)');
const installed = Number.isInteger(b.installed) && b.installed >= 0 && b.installed <= 7 ? b.installed : null;
if (status === 'done' && installed !== 7) status = 'reply not understood (done needs all 7 installed)';
const req = $('Request for Claude Code: Add Shop').first().json.request;
return [{ json: {
  shop: req.shop,
  label: req.label,
  chat_id: req.telegram_chat_id,
  shop_status: status,
  installed,
  note: String(b.note || '').slice(0, 800),
} }];
