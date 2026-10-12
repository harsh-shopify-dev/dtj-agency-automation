// n8n Code node "Claude Code Reply: Page Design" in "Store Factory: Page Design" (mode: Run Once for All Items).
// Reads what Claude Code posted to the Wait node (a timeout resumes with no body) and keeps only well-formed values: the same rules as
// n8n/store-factory/reply.py, which refuses a malformed answer before sending it.
const posted = $input.first().json.body;
const b = posted && typeof posted === 'object' && !Array.isArray(posted) ? posted : {};
const allowed = ['written to draft', 'designed (not written)', 'needs a look', 'could not build'];
let status = allowed.includes(b.page_status) ? b.page_status : (Object.keys(b).length ? 'reply not understood' : 'timed out (no reply in 3 days)');
const code = /^[0-9a-f]{12}$/.test(String(b.approve_code || '')) ? String(b.approve_code) : '';
const previewOk = /^https:[/][/][a-z0-9-]+[.]myshopify[.]com[/][^ ]*preview_theme_id=[0-9]+/.test(String(b.preview_url || ''));
if (status === 'written to draft' && !(code && previewOk)) status = 'reply not understood (no code or preview link)';
const count = (v) => (Number.isInteger(v) && v >= 0 ? v : null);
return [{ json: {
  row_id: $('Request for Claude Code: Page Design').first().json.request.row_id,
  page_status: status,
  approve_code: code,
  preview_url: status === 'written to draft' ? String(b.preview_url) : '',
  design_checks: /^[0-9]+[/][0-9]+$/.test(String(b.design_checks || '')) ? String(b.design_checks) : '',
  samples: count(b.samples),
  page_summary: String(b.summary || '').slice(0, 500),
  page_note: String(b.note || '').slice(0, 1000),
  approved_by: status === 'written to draft' ? 'Harsh (standing: draft pushes without asking)' : '',
} }];
