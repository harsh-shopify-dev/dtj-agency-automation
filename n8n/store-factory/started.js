// n8n Code node "Started" in "Store Factory: New Page" (mode: Run Once for All Items): the answer for the person who asked
// (shown in n8n, and sent back by the Telegram bot).
const match = $('Match the Store').first().json;
const saved = $('Save Brief').first().json;
return [{ json: {
  ok: true,
  row_id: saved.id,
  message: 'Got it: designing ' + match.handle + ' on ' + match.store_name + ' (brief ' + saved.id + '). '
    + 'Next: open Claude Code in the dtj-agency-automation folder and type: handle the Claude Code trigger in n8n. '
    + 'The preview link comes back when the page is in the draft theme (about 15 to 20 minutes).',
} }];
