// n8n Code node "Answer Noted" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Save the Answer" wrote a store job's answer into dtj_bot_answers: a short confirmation for the person who answered.
// "Save the Answer" continues on an error, so an answer that was not saved is said (the laptop would otherwise wait for it).
const a = $('Who Is It').first().json;
const saved = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (saved.error) {
  return [{ json: { chat_id: a.chat_id, text: 'I could not save that answer (' + esc(String(saved.error.message || saved.error).slice(0, 200))
    + '). Tap the button again in a minute.' } }];
}
let text;
if (a.value === 'Approve') text = 'Approved by ' + esc(a.by) + '. The laptop goes on with exactly that.';
else if (a.value === 'Skip') text = 'Skipped: that stays undone.';
else if (a.key === 'chat' && /^page-\d{1,9}$/.test(String(a.job))) {  // a message about a finished page (page_chat.py)
  text = 'Noted for brief ' + esc(String(a.job).slice(5)) + '. Claude picks it up within a minute and answers here.';
}
else text = 'Noted: ' + esc(String(a.value).slice(0, 200));
return [{ json: { chat_id: a.chat_id, text } }];
