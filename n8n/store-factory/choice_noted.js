// n8n Code node "Choice Noted" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Note the Choice" saved the answer to "collect the brand's data first?" on the brief (dtj_client_intake.brand_intake):
// tell the person what the designer will do. "Note the Choice" gives back the updated row, or nothing when the brief is gone.
const ask = $('Who Is It').first().json;
const row = ($input.all().map((i) => i.json).find((r) => r && r.id) || null);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (!row) return [{ json: { chat_id: ask.chat_id, text: 'That page request (brief ' + esc(ask.row_id) + ') is not on the list any more. Nothing was changed.' } }];
const brand = row.brand_name ? ' for ' + esc(row.brand_name) : '';
let text = ask.brand_intake === 'yes'
  ? 'Noted: the designer will collect the brand\'s data first' + brand + ' (pictures, colours, fonts, policies), then design the page from it.'
  : 'Noted: the designer will design the page' + brand + ' with the data we already have, without collecting it again.';
if (row.page_status) {
  text += '\nThis page is already marked "' + esc(row.page_status) + '", so tell the designer if it should be done again.';
}
return [{ json: { chat_id: ask.chat_id, text } }];
