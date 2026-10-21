// n8n Code node "Add Shop Started" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Start Add Shop" handed /addshop to "Store Factory: Add Shop" (it does not wait): the answer for the admin who asked.
// "Start Add Shop" continues on an error, so a start that failed is said plainly instead of "Got it".
const ask = $('Who Is It').first().json;
const started = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (started.error) {
  const why = typeof started.error === 'string' ? started.error : (started.error.message || JSON.stringify(started.error));
  return [{ json: { chat_id: ask.chat_id, text: 'Could not start adding ' + esc(ask.label) + ' (' + esc(ask.shop) + '): '
    + esc(String(why).slice(0, 300)) + '\nNothing was made. Harsh will take a look.' } }];
}
return [{ json: { chat_id: ask.chat_id, text:
  'Got it: adding ' + esc(ask.label) + ' (' + esc(ask.shop) + ').\n\n'
  + 'A DTJ laptop\'s Claude Code now makes, links and releases the seven DTJ app copies (a progress bar shows up here), then I send you '
  + 'seven Install buttons for the store OWNER (logged in to that shop\'s admin; forward them if that is not you).\n\n'
  + 'If no laptop is listening: open Claude Code in the dtj-agency-automation folder and type: handle the Claude Code trigger in n8n',
} }];
