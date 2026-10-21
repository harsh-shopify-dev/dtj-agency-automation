// n8n Code node "Store Started" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Start New Store" handed an admin's store link to "Store Factory: New Store" (it does not wait): the answer for that admin.
// "Start New Store" continues on an error, so a start that failed is said plainly.
const ask = $('Who Is It').first().json;
const started = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (started.error) {
  const why = typeof started.error === 'string' ? started.error : (started.error.message || JSON.stringify(started.error));
  return [{ json: { chat_id: ask.chat_id, text: 'Could not start the store ' + esc(ask.link) + ': ' + esc(String(why).slice(0, 300))
    + '\nNothing was made. Harsh will take a look.' } }];
}
return [{ json: { chat_id: ask.chat_id, text:
  'Got it: the whole store ' + esc(ask.link) + '.\n\n'
  + 'A DTJ laptop\'s Claude Code reads the store and asks you a few questions here (whose store, what to design, which products, '
  + 'any offer). Before it makes or writes anything that needs a yes (the draft copy, the app copies, the header and footer, the '
  + 'collection page) it sends an Approve button. Nothing is published.\n\n'
  + 'If no laptop is listening: open Claude Code in the dtj-agency-automation folder and type: handle the Claude Code trigger in n8n',
} }];
