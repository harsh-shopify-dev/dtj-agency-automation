// n8n Code node "Tell the Requester" in "WATFEO Ads: New Ad" (mode: Run Once for All Items).
// When the ad was asked for from Telegram (the job has a telegram_chat_id), send the result back. Output: [] or one { chat_id, text }.
const job = $('Save WATFEO Ad').first().json || {};
const chat = String(job.telegram_chat_id || '').trim();
if (!chat) return [];
const r = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const what = { reel: 'reel', scripts: 'scripts', prompts: 'scripts and prompts' }[job.kind] || 'ad';
let text;
if (r.ad_status === 'reel ready') {
  text = 'Your WATFEO ' + what + ' ' + (what.endsWith('s') ? 'are' : 'is') + ' ready' + (r.angle_used ? ' (angle #' + r.angle_used + ')' : '')
    + '. File on the laptop:\n' + esc(r.final_path) + (r.ad_note ? '\n\n' + esc(String(r.ad_note).slice(0, 600)) : '')
    + '\nNothing was posted. A person watches it and decides.';
} else {
  text = 'The WATFEO ' + what + ' is not finished (' + esc(r.ad_status || 'no answer') + ')'
    + (r.ad_note ? ': ' + esc(String(r.ad_note).slice(0, 600)) : '.');
}
return [{ json: { chat_id: chat, text } }];
