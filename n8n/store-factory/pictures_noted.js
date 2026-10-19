// n8n Code node "Pictures Noted" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Note the Pictures" saved the answer to "upload the brand's pictures to the shop?" on the brief (dtj_client_intake.upload_assets
// and upload_assets_by, 19 Oct 2026). A Yes is that person's approval for this one upload: the designer's Claude Code uploads the
// intake's pictures with page_builder.store_files --approved-by "<name> (Telegram, brief N)" (request_page_design.js, step 2).
const ask = $('Who Is It').first().json;
const row = ($input.all().map((i) => i.json).find((r) => r && r.id) || null);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (!row) return [{ json: { chat_id: ask.chat_id, text: 'That page request (brief ' + esc(ask.row_id) + ') is not on the list any more. Nothing was changed.' } }];
let text = ask.upload_assets === 'yes'
  ? 'Noted: the designer will upload the brand\'s pictures to the shop\'s Files (approved by ' + esc(ask.by) + ') and design the page with them.'
  : 'Noted: nothing is uploaded; the designer will use the pictures the shop already has.';
if (row.page_status) text += '\nThis page is already marked "' + esc(row.page_status) + '", so tell the designer if it should be done again.';
return [{ json: { chat_id: ask.chat_id, text } }];
