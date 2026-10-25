// n8n Code node "Claude Code Reply: New Store" in "Store Factory: New Store" (mode: Run Once for All Items).
// Reads what Claude Code posted to the Wait node (a timeout resumes with no body) and keeps only well-formed values: the same rules as
// n8n/store-factory/reply.py, which refuses a malformed answer before sending it.
const posted = $input.first().json.body;
const b = posted && typeof posted === 'object' && !Array.isArray(posted) ? posted : {};
const allowed = ['done', 'partly done', 'could not start'];
const status = allowed.includes(b.store_status) ? b.store_status : (Object.keys(b).length ? 'reply not understood' : 'timed out (no reply in 7 days)');
const pages = (Array.isArray(b.pages) ? b.pages : []).slice(0, 40)
  .filter((p) => p && /^https:\/\/[a-z0-9.-]+\/\S*$/i.test(String(p.preview || '')))
  .map((p) => ({ part: String(p.part || 'page').slice(0, 60), preview: String(p.preview).slice(0, 400) }));
const req = $('Request for Claude Code: New Store').first().json.request;
return [{ json: {
  link: req.link,
  chat_id: req.telegram_chat_id,
  store_status: status,
  shop: String(b.shop || '').slice(0, 100),
  name: String(b.name || '').slice(0, 100),
  draft_theme_id: /^\d{6,20}$/.test(String(b.draft_theme_id || '')) ? String(b.draft_theme_id) : '',
  pages,
  note: String(b.note || '').slice(0, 800),
} }];
