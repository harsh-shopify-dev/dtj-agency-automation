// n8n Code node "Intake Started" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Start Brand Intake" asked GitHub to run the "Brand intake" workflow: GitHub answers 204 when the run is queued. The run itself
// sends the Drive link to this chat when it is done (.github/workflows/brand-intake.yml), so here we only say it started, or why not.
const ask = $('Who Is It').first().json;
const res = $input.first().json || {};
const status = Number(res.statusCode || 0);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (status === 204) {
  return [{ json: { chat_id: ask.chat_id, text: 'Started the brand intake for ' + esc(ask.store) + '. I will send the Google Drive '
    + 'folder here when it is ready (a few minutes; shops with many videos take longer).' } }];
}
const why = status === 401 || status === 403 ? 'the GitHub key in n8n is missing or not allowed to start runs'
  : status === 404 ? 'GitHub cannot find the "Brand intake" workflow on the main branch yet'
  : status === 422 ? 'GitHub did not accept the request'
  : 'GitHub did not answer';
return [{ json: { chat_id: ask.chat_id, text: 'Could not start the brand intake for ' + esc(ask.store) + ': ' + why
  + ' (' + (status || 'no answer') + '). Please tell Harsh.' } }];
