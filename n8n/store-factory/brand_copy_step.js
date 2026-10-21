// n8n Code node "Copy Step Body" in "Store Factory: Brand Copy" (mode: Run Once for All Items).
// One request for the install service's POST /copy (op "step": the next few products, collections or policy pages). The run comes
// back here after every step until "Copy Progress" says finished; `round` counts the steps (a guard against a loop that never ends).
const start = $('From the Telegram Bot').first().json;
const prev = $input.first().json || {};
const round = Number.isInteger(prev.round) ? prev.round : 0;
const job = String(start.job || '');
if (!/^[a-z0-9][a-z0-9-]{1,40}$/.test(job)) throw new Error('No copy job reached this step');
const by = String(start.approved_by || '').trim();
if (!by) throw new Error('No approver reached this step: a copy writes to the store');
return [{ json: { round, body: { ts: Math.floor(Date.now() / 1000), op: 'step', job, approved_by: by.slice(0, 100) } } }];
