// n8n Code node "Report Messages" in "SEO Engine: Weekly Report" (mode: Run Once for All Items).
// After "Save the Batch" (the new dtj_seo_batches row, whose id the buttons carry): for each admin, the full report as a file and
// a short message in plain words with the fixes and, when there is something to approve, the Yes / No buttons.
// The buttons say seo:yes:<row id> / seo:no:<row id>; the bot's "Who Is It" hands a tap to this workflow's answer lane.
// Output: items of kind "file" (Send the Report File), "ask" (Ask Yes or No) or "text" (Send).
const APPLY_ON = false;  // must equal APPLY_ON in answer_plan.js (the tests check): false = shadow, a yes is recorded, nothing applied
const plan = $('Plan the Report').first().json;
const saved = $input.first().json || {};
const r = plan.report;
const row = plan.row;
const rowId = Number(saved.id);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const KIND = { meta_description: 'Google description', seo_title: 'Google title', noindex: 'Hide from Google', alt_text: 'Image alt text',
  site_jsonld: 'Business details for Google and AI' };
if (!Number.isInteger(rowId) || rowId < 1) return [];

const page = (url) => {
  const u = String(url || '');
  const site = String(r.site || '').replace(/\/+$/, '');
  return u.startsWith(site) ? (u.slice(site.length) || '/') : u;
};
const cut = (s, n) => { const t = String(s == null ? '' : s); return t.length > n ? t.slice(0, n - 1) + '…' : t; };
const day = String(r.made_at).slice(0, 10);
const c = r.batch.counts;
const auto = r.batch.changes.filter((x) => x.how === 'auto');
const kind = row.can_approve ? 'ask' : 'text';

function build(show) {
  const L = [];
  L.push('<b>DTJ search report, ' + esc(day) + '</b>');
  L.push('Website check: ' + r.scan.pages + ' pages. ' + r.scan.high + ' to fix now, ' + r.scan.medium + ' soon, ' + r.scan.low + ' later.');
  if (!r.scan.complete) L.push('\n⚠️ <b>This check is incomplete:</b> ' + esc(r.scan.warning || 'part of the site was not read') + '.');
  L.push('');
  L.push('<b>Fixes waiting for one yes</b> (batch ' + esc(r.batch.id) + ')');
  L.push(c.auto + ' ready to apply, ' + c.blocked + ' stopped by the checks, ' + c.manual + ' for a person.');
  for (const x of auto.slice(0, show)) {
    const offices = String(x.after || '').replace(/^business details for Google and AI:?\s*/i, '');
    const what = x.kind === 'noindex' ? '' : (x.kind === 'site_jsonld' ? (offices ? ': ' + esc(cut(offices, 120)) : '')
      : ' → "' + esc(cut(x.after, 160)) + '"');
    L.push('• ' + esc(x.cid) + ' ' + esc(KIND[x.kind] || x.kind) + ', ' + esc(cut(page(x.url), 80)) + what);
  }
  if (auto.length > show) L.push('• and ' + (auto.length - show) + ' more in the file.');
  if (r.batch.manual.length) L.push('For a person: ' + r.batch.manual.length + ' task(s), listed in the file.');
  L.push('');
  L.push('Full report: the file above, or <a href="' + esc(r.run_url) + '">GitHub run ' + esc(r.run_id) + '</a>.');
  L.push('');
  if (row.can_approve) {
    L.push('<b>Yes</b> applies these ' + c.auto + ' change(s) to the live site; each one is skipped if its page changed since the check, '
      + 'and every change can be undone. One yes covers this batch only. Harsh says yes; when he cannot be reached, a teammate, by name.');
    L.push(APPLY_ON ? 'A yes starts "SEO apply fixes" on GitHub at once.'
      : 'For now (test mode) your answer is only recorded: nothing is applied from here yet.');
  } else if (c.auto === 0) {
    L.push('Nothing to approve this week.');
  } else {
    L.push('No Yes button this week: the check missed part of the site. Run "SEO weekly" again on GitHub (Actions) and a new report comes here.');
  }
  return L.join('\n');
}
let show = 15;
let text = build(show);
while (text.length > 4000 && show > 0) text = build(--show);

const file = Buffer.from(String(r.report_md), 'utf8').toString('base64');
const out = [];
for (const chat of plan.admins) {
  out.push({ json: { kind: 'file', chat_id: chat, caption: 'DTJ search report ' + day + ' (batch ' + r.batch.id + ', run ' + r.run_id + ')' },
    binary: { data: { data: file, mimeType: 'text/markdown', fileName: 'dtj-seo-report-' + day + '.md', fileExtension: 'md' } } });
  out.push({ json: { kind, chat_id: chat, text: cut(text, 4096), yes_data: 'seo:yes:' + rowId, no_data: 'seo:no:' + rowId,
    yes_text: 'Yes, apply these ' + c.auto, no_text: 'No, not this batch' } });
}
return out;
