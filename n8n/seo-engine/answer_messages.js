// n8n Code node "Answer Messages" in "SEO Engine: Weekly Report" (mode: Run Once for All Items).
// After the answer was saved on its dtj_seo_batches row ("Save the Answer" only passes when the row was still waiting, so two quick
// taps cannot both count) and, when the apply switch is on, after "Start SEO Apply" (GitHub's answer, or its error).
// Tells the person what happened and the other admins who answered. The first item also carries the action-log row ("Log the
// Answer" runs once).
// When "Save the Answer" matched no row, someone else answered a moment earlier: this tap is not counted ("lost").
// "Start SEO Apply" keeps GitHub's answer (full response, never an error): 204 = the run was started.
// Output: items { chat_id, text } for "Send"; the first has log.
const d = $('Decide the Answer').first().json;
const saved = $('Save the Answer').first().json || {};
const got = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const label = 'batch ' + esc(d.batch_id) + ' (GitHub run ' + esc(d.run_id) + ')';
const applyPage = 'https://github.com/harsh-shopify-dev/dtj-agency-automation/actions/workflows/seo-apply.yml';
const started = Number(got.statusCode) >= 200 && Number(got.statusCode) < 300;
const state = !saved.id ? 'lost' : (d.status === 'no' ? 'no' : (!d.dispatch ? 'shadow' : (started ? 'started' : 'failed')));
const why = got.error ? (got.error.message || got.error.description || JSON.stringify(got.error))
  : ((got.body && got.body.message) || (got.statusCode ? 'GitHub answered ' + got.statusCode : 'no answer from GitHub'));
const err = state === 'failed' ? String(why).slice(0, 300) : (state === 'lost' ? 'someone else answered this batch a moment earlier' : '');
let mine;
let theirs;
if (state === 'lost') {
  mine = 'Someone else answered this ' + label + ' a moment ago, so your tap was not counted. One answer per batch.';
  theirs = null;
} else if (state === 'no') {
  mine = 'Recorded: <b>no</b> to ' + label + ', from ' + esc(d.answered_by) + '. Nothing will be applied from this batch.';
  theirs = esc(d.answered_by) + ' said <b>no</b> to the SEO fixes ' + label + '. Nothing will be applied.';
} else if (state === 'shadow') {
  mine = 'Recorded: <b>yes</b> to ' + label + ', approved by "' + esc(d.approved_by) + '".\n\n'
    + 'Test mode (shadow): nothing was changed on the site. To apply it now, by hand: GitHub > Actions > "SEO apply fixes" > Run workflow, '
    + 'run number ' + esc(d.run_id) + ', approved by "' + esc(d.approved_by) + '", batch ' + esc(d.batch_id) + '.\n' + applyPage;
  theirs = esc(d.approved_by) + ' said <b>yes</b> to the SEO fixes ' + label + '. Test mode: recorded only, nothing applied.';
} else if (state === 'started') {
  mine = 'Yes recorded for ' + label + ', approved by "' + esc(d.approved_by) + '". "SEO apply fixes" has started on GitHub: it applies the '
    + d.auto_changes + ' change(s), checks each live page and keeps the old values for an undo.\n' + applyPage;
  theirs = esc(d.approved_by) + ' said <b>yes</b> to the SEO fixes ' + label + '. "SEO apply fixes" has started.';
} else {
  mine = 'Your yes for ' + label + ' is recorded, but GitHub did not start "SEO apply fixes": ' + esc(err) + '\n'
    + 'Nothing was changed on the site. Start it by hand: run number ' + esc(d.run_id) + ', approved by "' + esc(d.approved_by) + '", batch '
    + esc(d.batch_id) + '.\n' + applyPage;
  theirs = esc(d.approved_by) + ' said <b>yes</b> to the SEO fixes ' + label + ', but GitHub did not start the apply run (see the bot chat).';
}
const log = {
  ts: new Date().toISOString(), run_id: String(d.run_id), client_id: 'dtj', automation: 'seo-engine-n8n', tier: 2,
  mode: d.dispatch ? 'approve' : 'shadow', target: d.site + ' fixes batch ' + d.batch_id,
  action: state === 'started' || state === 'failed' ? 'start SEO apply fixes' : 'record answer on fixes batch',
  reason: 'Monday SEO report: one named yes per batch (CLAUDE.md rule 2)',
  result: { lost: 'blocked', no: 'blocked', shadow: 'recommended', started: 'success', failed: 'failed' }[state],
  evidence: JSON.stringify({ run_url: d.run_url, auto_changes: d.auto_changes, row_id: d.row_id }),
  before: 'waiting', after: state === 'lost' ? 'not changed' : d.status, approved_by: d.approved_by || '', approved_at: d.status === 'yes' ? d.answered_at : '',
  error: err,
};
const out = [{ json: { chat_id: d.chat_id, text: mine, log } }];
if (theirs) for (const chat of d.others || []) out.push({ json: { chat_id: chat, text: theirs } });
return out;
