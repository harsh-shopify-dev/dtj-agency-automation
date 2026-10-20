// n8n Code node "Tell the Requester" in "Reel Factory: New Reel" (mode: Run Once for All Items).
// When the reel was asked for from Telegram (the job has a telegram_chat_id), send the result back. Output: [] or one { chat_id, text }.
const job = $('Save Reel Job').first().json || {};
const chat = String(job.telegram_chat_id || '').trim();
if (!chat) return [];
const r = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
let text;
if (r.reel_status === 'reel ready') {
  text = 'Your reel for ' + esc(job.product_name) + ' is ready (' + esc(r.duration_s) + ' s). File on the reel VPS:\n' + esc(r.final_path)
    + '\nNothing was posted. A person watches it and decides where it goes.';
} else {
  text = 'The reel for ' + esc(job.product_name) + ' is not finished (' + esc(r.reel_status || 'no answer') + ')'
    + (r.reel_note ? ': ' + esc(String(r.reel_note).slice(0, 600)) : '.');
}
return [{ json: { chat_id: chat, text } }];
