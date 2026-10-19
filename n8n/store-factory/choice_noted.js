// n8n Code node "Choice Noted" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Note the Choice" saved the answer to "collect the brand's data first?" on the brief (dtj_client_intake.brand_intake):
// tell the person what the designer will do. "Note the Choice" gives back the updated row, or nothing when the brief is gone.
// After a Yes the bot also asks for the brand's OWN website (19 Oct 2026, Harsh: "it didnt asked for the brand website link?"): the
// shop a product link comes from is not always the brand's site (DTJ's demo shop carries other brands' products). The question is
// sent with Telegram's "reply" box ("Ask for the Website"); the reply comes back as kind "site" (bot_read.js reads "for brief N?").
const ask = $('Who Is It').first().json;
const row = ($input.all().map((i) => i.json).find((r) => r && r.id) || null);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (!row) return [{ json: { chat_id: ask.chat_id, text: 'That page request (brief ' + esc(ask.row_id) + ') is not on the list any more. Nothing was changed.' } }];
const brand = row.brand_name ? ' for ' + esc(row.brand_name) : '';
const done = row.page_status
  ? '\nThis page is already marked "' + esc(row.page_status) + '", so tell the designer if it should be done again.' : '';
if (ask.brand_intake !== 'yes') {
  return [{ json: { chat_id: ask.chat_id, text: 'Noted: the designer will design the page' + brand
    + ' with the data we already have, without collecting it again.' + done } }];
}
const known = row.brand_website || ((String(row.product_url || '').match(/^https?:\/\/[^/]+/i) || [])[0])
  || (row.store_domain ? 'https://' + row.store_domain : '');
const host = String(known).replace(/^https?:\/\//i, '').replace(/^www\./i, '').replace(/[/?#].*$/, '');
return [{ json: { chat_id: ask.chat_id, site_question: true,
  text: 'Noted: the designer will collect the brand\'s data first' + brand + ', then design the page from it.' + done + '\n\n'
    + 'Which website is the brand\'s own for brief ' + esc(row.id) + '? Reply to this message with its address, for example senso.in.'
    + (host ? ' If it is ' + esc(host) + ', reply: same' : '') } }];
