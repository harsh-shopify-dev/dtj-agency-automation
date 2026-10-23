// n8n Code node "Stop Plan" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// Stopping a brand intake (19 Oct 2026, Harsh: "add a stop feature so it can stop any ongoing specific task"; brand intakes only).
// After "List Intakes" asked GitHub for the latest runs of the "Brand intake" workflow (full response). Only a run of THAT workflow
// that is still going can be stopped, so a Stop button can never cancel anything else (the SEO runs, for example).
// Output: one or more items with action
//   cancel -> "Cancel the Intake" (run_id)
//   choose -> "Ask to Stop": one message per running intake, each with its own Stop button (/stop)
//   reply  -> just answer
const ask = $('Who Is It').first().json;
const res = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const reply = (text) => [{ json: { action: 'reply', chat_id: ask.chat_id, text } }];
const parse = (b) => { if (b && typeof b === 'object') return b; try { return JSON.parse(String(b || '{}')); } catch (e) { return {}; } };
const status = Number(res.statusCode || 0);
const body = parse(res.body !== undefined ? res.body : res);
if (status === 401 || status === 403) {
  return reply('GitHub refused the bot\'s key (the n8n credential "DTJ GitHub Actions"). Nothing was stopped. Please tell Harsh.');
}
if (status !== 200 || !Array.isArray(body.workflow_runs)) {
  return reply('I could not reach GitHub (' + (status || 'no answer') + '). Nothing was stopped. Please try again in a minute.');
}
const GOING = ['queued', 'in_progress', 'waiting', 'requested', 'pending'];
const store = (r) => String(r.display_title || '').replace(/^Brand intake:?\s*/, '').trim() || 'a store';
const ago = (r) => {
  const m = Math.max(0, Math.round((Date.now() - Date.parse(r.run_started_at || r.created_at || '')) / 60000));
  return Number.isFinite(m) ? (m < 1 ? 'less than a minute ago' : m + ' min ago') : 'a moment ago';
};
const runs = body.workflow_runs;

if (ask.mode === 'cancel') {
  const run = runs.find((r) => String(r.id) === String(ask.run_id));
  if (!run) return reply('That brand intake is not on GitHub\'s list of recent intakes. Nothing was stopped.');
  if (!GOING.includes(run.status)) {
    return reply('The brand intake for ' + esc(store(run)) + ' has already finished, so there is nothing to stop.');
  }
  return [{ json: { action: 'cancel', chat_id: ask.chat_id, run_id: String(run.id), store: store(run), by: ask.by } }];
}
const running = runs.filter((r) => GOING.includes(r.status));
if (!running.length) return reply('No brand intake is running right now. To stop a page or store job, tap "Stop this job" under its '
  + '"Started" message.');
return running.map((r) => ({ json: { action: 'choose', chat_id: ask.chat_id,
  text: 'Running: brand intake for ' + esc(store(r)) + ', started ' + ago(r) + '.', stop_data: 'stop:intake:' + r.id } }));
