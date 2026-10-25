// n8n Code node "Say What Happened" in "Reel Factory: Telegram Bot" (mode: Run Once for All Items).
// After an answer, a photo, a new reel, a limit or a reference search was handed on: one short message for the person. The step
// before it continues on an error, so a failure is said (nobody would otherwise know the tap or the request was lost).
const a = $('Who Is It').first().json;
const got = $input.first().json || {};
const esc = (v) => String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
if (got.error) {
  return [{ json: { chat_id: a.chat_id, text: 'That did not go through (' + esc(String(got.error.message || got.error).slice(0, 200))
    + '). Please try again in a minute.' } }];
}
let text = '';
if (a.action === 'answer') {
  if (a.value === 'Approve') text = 'Approved by ' + esc(a.by) + '. The reel goes on with exactly that.';
  else if (a.value === 'Change something') text = 'OK. Reply to the next message with what should change.';
  else if (a.value === 'Skip') text = 'Skipped.';
  else if (a.value === 'Keep') text = 'Kept for the reference library.';
  else if (/^Start/.test(a.value)) text = 'Thanks ' + esc(a.by) + ', you are watching this one. Claude starts on DTJ\'s server now.';
  else text = 'Noted: ' + esc(String(a.value).slice(0, 200));
} else if (a.action === 'photo') {
  text = 'Photo saved. Now send /remake or /reel with the links (photos from the last 30 minutes are used as the product pictures).';
} else if (a.action === 'reel') {
  const i = a.inputs || {};
  text = 'Saved: ' + (i.reel_type === 'remake' ? 'a remake' : 'a UGC reel') + ' for ' + esc(i.product_name) + '. In a minute I ask here '
    + '"tap Start if you are watching"; nothing starts before someone taps it. Then you approve the plan, the pictures and the reel here.';
} else if (a.action === 'limit') {
  text = 'Daily limit set to ' + esc(a.value) + ' reels by ' + esc(a.set_by) + '.';
} else if (a.action === 'refs') {
  text = (a.inputs && a.inputs.mode === 'audience' ? 'Studying the audience ' + esc(a.inputs.audience) : 'Looking for winning reels of '
    + esc(a.inputs && a.inputs.query)) + '. The results come here in a few minutes.';
}
return text ? [{ json: { chat_id: a.chat_id, text } }] : [];
