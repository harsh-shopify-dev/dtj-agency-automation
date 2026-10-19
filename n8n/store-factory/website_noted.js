// n8n Code node "Website Noted" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Note the Website" saved the brand's own website on the brief (dtj_client_intake.brand_website, 19 Oct 2026): confirm it.
// The designer's Claude Code reads it when it starts and collects the brand's data from that site (request_page_design.js, step 2).
// Then the third question (Harsh, 19 Oct 2026: "it should ask either upload the assets from google drive to the store"): a new shop
// needs the brand's pictures uploaded, an old shop already has them. "Need the Pictures?" sends it with Yes / No buttons.
const ask = $('Who Is It').first().json;
const row = ($input.all().map((i) => i.json).find((r) => r && r.id) || null);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (!row) return [{ json: { chat_id: ask.chat_id, text: 'That page request (brief ' + esc(ask.row_id) + ') is not on the list any more. Nothing was changed.' } }];
const host = String(ask.website).replace(/^https?:\/\//i, '');
let text = 'Got it: for brief ' + esc(row.id) + ' the designer will collect the brand\'s data from ' + esc(host) + '.';
if (row.page_status) {
  text += '\nThis page is already marked "' + esc(row.page_status) + '", so tell the designer if it should be done again.';
  return [{ json: { chat_id: ask.chat_id, text } }];
}
text += '\n\nLast question: upload the brand\'s pictures from ' + esc(host) + ' to the shop, so the page can use them? '
  + 'Yes for a new shop; No when the shop already has them.';
return [{ json: { chat_id: ask.chat_id, text, pictures_question: true,
  yes_data: 'brief:upload:' + row.id, no_data: 'brief:keep:' + row.id } }];
