// n8n Code node "Tell the Requester" in "Store Factory: New Store" (mode: Run Once for All Items).
// The result of a whole-store run for the admin who sent the link, with a preview link per page written to the draft.
// Output: [] (no chat) or one { chat_id, text } for "Send Result".
const r = $input.first().json || {};
const chat = String(r.chat_id || '').trim();
if (!chat) return [];
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const attr = (s) => esc(s).replace(/"/g, '&quot;');
const who = esc(r.name || r.link) + (r.shop ? ' (' + esc(r.shop) + ')' : '');
const pages = (r.pages || []).map((p) => '- <a href="' + attr(p.preview) + '">' + esc(p.part) + '</a>').join('\n');
const draft = r.draft_theme_id ? ' in the draft copy (theme ' + esc(r.draft_theme_id) + ', unpublished)' : '';
let text;
if (r.store_status === 'done') {
  text = who + ' is designed' + draft + '. Nothing is published.' + (pages ? '\n\n' + pages : '')
    + (r.note ? '\n\n' + esc(r.note) : '');
} else if (r.store_status === 'partly done') {
  text = who + ' is partly done' + draft + '.' + (r.note ? '\nOpen: ' + esc(r.note) : '') + (pages ? '\n\nReady so far:\n' + pages : '');
} else {
  text = who + ' was not started (' + esc(r.store_status || 'no answer') + ')' + (r.note ? ': ' + esc(r.note) : '.') + '\nHarsh will take a look.';
}
return [{ json: { chat_id: chat, text } }];
