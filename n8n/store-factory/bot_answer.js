// n8n Code node "Write the Answers" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Store Factory: New Page" ran: one message for the person who asked and, when a page was started, one for each designer
// (a designer who asked gets both in one message). Every item is { chat_id, text } for the "Send" node (HTML mode, text escaped).
const ask = $('Who Is It').first().json;
const res = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (!res.ok) return [{ json: { chat_id: ask.chat_id, text: esc(res.message || 'That did not work. Please ask Harsh.') } }];

const what = (res.handle ? res.handle : 'your page') + (res.store_name ? ' on ' + res.store_name : '');
const toDesigner = 'New page waiting (brief ' + esc(res.row_id) + ') from ' + esc(ask.requester_name) + ': ' + esc(what) + '.\n'
  + 'Open Claude Code in the dtj-agency-automation folder and type:\nhandle the Claude Code trigger in n8n';
const askerIsDesigner = (ask.designers || []).includes(ask.requester_id);
const out = [{ json: { chat_id: ask.chat_id, text: 'Got it: designing ' + esc(what) + ' (brief ' + esc(res.row_id) + ').\n'
  + (askerIsDesigner ? '\n' + toDesigner : 'A designer will start it on their laptop. A progress bar shows up here when they do, and I will send you the preview link here when it is ready.') } }];
for (const d of ask.designers || []) {
  if (d !== ask.requester_id) out.push({ json: { chat_id: d, text: toDesigner } });
}
return out;
