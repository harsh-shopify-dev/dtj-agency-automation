// n8n Code node "Stop Report" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Cancel the Intake" asked GitHub to cancel one brand intake run (full response): GitHub answers 202 when it starts cancelling.
// The run itself then closes its progress message and says in the chat that it was stopped (.github/workflows/brand-intake.yml).
const ask = $('Stop Plan').first().json;
const res = $input.first().json || {};
const status = Number(res.statusCode || 0);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
let text;
if (status === 202) {
  text = 'Stopping the brand intake for ' + esc(ask.store) + ' (asked by ' + esc(ask.by) + '). Its progress message will say when it has '
    + 'stopped. Files it already put in Google Drive stay there.';
} else if (status === 409) {
  text = 'The brand intake for ' + esc(ask.store) + ' had already finished, so there was nothing to stop.';
} else {
  const why = status === 401 || status === 403 ? 'the GitHub key in n8n is missing or not allowed to stop runs' : 'GitHub did not accept it';
  text = 'Could not stop the brand intake for ' + esc(ask.store) + ': ' + why + ' (' + (status || 'no answer') + '). Please tell Harsh.';
}
return [{ json: { chat_id: ask.chat_id, text } }];
