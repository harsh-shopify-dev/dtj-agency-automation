// n8n Code node "Copy Progress" in "Store Factory: Brand Copy" (mode: Run Once for All Items).
// After one /copy step: finished (the message for the person who tapped Approve) or not (back to "Copy Step Body" after a short wait).
// The install service answers with done / total counts; a refusal (not 200) ends the run with the reason, so it never loops on an error.
const MAX_ROUNDS = 400;  // 400 steps of up to 8 items: far more than the 2,500 products a plan may hold
const start = $('From the Telegram Bot').first().json;
const round = Number($('Copy Step Body').first().json.round || 0) + 1;
const res = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const ok = res.statusCode === 200 && res.body && typeof res.body === 'object';
const b = ok ? res.body : {};
const d = b.done || {};
const t = b.total || {};
const finished = !ok || Boolean(b.finished) || round >= MAX_ROUNDS;
let text = '';
if (!ok) {
  const why = (res.body && res.body.error) || res.error || ('HTTP ' + (res.statusCode || 'no answer'));
  text = 'The brand copy stopped: ' + esc(String(why).slice(0, 300)) + '\nWhat was copied so far stays. Harsh will take a look.';
} else if (finished) {
  text = (b.stopped ? 'The brand copy stopped: ' + esc(b.stopped) + '\n' : 'Brand copy done')
    + ' (' + esc(b.status === 'ACTIVE' ? 'products are live behind the store password' : 'products are drafts') + '):\n'
    + '- products: ' + (d.products || 0) + ' of ' + (t.products || 0) + '\n'
    + '- collections: ' + (d.collections || 0) + ' of ' + (t.collections || 0) + '\n'
    + '- policy pages: ' + (d.policies || 0) + ' of ' + (t.policies || 0)
    + (d.skipped ? '\n- left alone (the store has them already): ' + d.skipped : '')
    + (d.failed ? '\n- failed: ' + d.failed + ' (listed for Harsh)' : '')
    + (round >= MAX_ROUNDS && !b.finished ? '\nIt took too many steps and was stopped; send the copy again to go on.' : '');
}
return [{ json: { finished, chat_id: start.chat_id, text, round } }];
