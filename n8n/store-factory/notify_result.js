// n8n Code node "Tell the Requester" in "Store Factory: Page Design" (mode: Run Once for All Items).
// When a page request came from Telegram (the brief has a telegram_chat_id), send its result back to that person.
// Input: the checked answer from "Claude Code Reply: Page Design". Output: [] (nothing to send) or one { chat_id, text }.
const brief = $('Load Brief').first().json || {};
const chat = String(brief.telegram_chat_id || '').trim();
if (!chat) return [];
const r = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const handle = (String(brief.product_url || '').match(/\/products\/([a-z0-9-]+)/i) || [])[1] || 'your product';
let text;
if (r.page_status === 'written to draft') {
  text = 'Your page for ' + esc(handle) + ' is ready in the draft theme (shoppers cannot see it yet):\n' + esc(r.preview_url) + '\n\n'
    + 'Design checks passed: ' + esc(r.design_checks || '?') + '. Samples to replace before it goes live: ' + esc(r.samples == null ? '?' : r.samples) + '.\n'
    + 'Send the link to Harsh; he decides what goes live and when.';
} else {
  text = 'The page for ' + esc(handle) + ' was not finished (' + esc(r.page_status || 'no answer') + ')'
    + (r.page_note ? ': ' + esc(String(r.page_note).slice(0, 600)) : '.') + '\nHarsh will take a look.';
}
// a reply to this message reaches the page's own Claude session on the VPS (Harsh, 24 Oct 2026: "once we build the page i can also
// chat with you there"): page_chat.py and worker.py read the last line
const id = String(brief.id || '').trim();
if (/^\d{1,9}$/.test(id)) text += '\n\nReply to this message to change something on the page.\n(job page-' + id + ', answer chat)';
return [{ json: { chat_id: chat, text } }];
