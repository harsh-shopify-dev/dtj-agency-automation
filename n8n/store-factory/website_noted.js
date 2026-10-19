// n8n Code node "Website Noted" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Note the Website" saved the brand's own website on the brief (dtj_client_intake.brand_website, 19 Oct 2026): confirm it.
// The designer's Claude Code reads it when it starts and collects the brand's data from that site (request_page_design.js, step 2).
const ask = $('Who Is It').first().json;
const row = ($input.all().map((i) => i.json).find((r) => r && r.id) || null);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (!row) return [{ json: { chat_id: ask.chat_id, text: 'That page request (brief ' + esc(ask.row_id) + ') is not on the list any more. Nothing was changed.' } }];
const host = String(ask.website).replace(/^https?:\/\//i, '');
let text = 'Got it: for brief ' + esc(row.id) + ' the designer will collect the brand\'s data from ' + esc(host) + '.';
if (row.page_status) text += '\nThis page is already marked "' + esc(row.page_status) + '", so tell the designer if it should be done again.';
return [{ json: { chat_id: ask.chat_id, text } }];
