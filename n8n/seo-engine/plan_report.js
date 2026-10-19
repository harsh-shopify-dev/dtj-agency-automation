// n8n Code node "Plan the Report" in "SEO Engine: Weekly Report" (mode: Run Once for All Items).
// After "Check the Report": who gets it, the row for dtj_seo_batches, the action-log row, or the dead letter.
// Who gets it: the active admins in dtj_bot_users (the people who may give a Tier 2 yes: Harsh, or a teammate when he is not
// reachable). A Yes button only when there is something to apply AND the website check read the whole site (report.py says
// "run the check again before saying yes" otherwise).
// The same GitHub run twice (a retried send) is sent once: a run already in dtj_seo_batches gives no output.
// Output: one item, action "save" (row, report, admins, log) or "dead_letter" (dead, admins, log), or nothing.
const checked = $('Check the Report').first().json || {};  // (this node's own input is the batch rows)
const users = $('Load Bot Users').all().map((i) => i.json).filter((u) => u && u.telegram_user_id && u.active !== false);
const batches = $('Load Batches').all().map((i) => i.json).filter((b) => b && b.batch_id);
const admins = [...new Set(users.filter((u) => String(u.role || '').toLowerCase().trim() === 'admin')
  .map((u) => String(u.telegram_user_id).trim()))];
const now = new Date().toISOString();
const log = (fields) => ({ ts: now, run_id: '', client_id: 'dtj', automation: 'seo-engine-n8n', tier: 0, mode: 'shadow', target: '',
  action: '', reason: '', result: 'success', evidence: '', before: '', after: '', approved_by: '', approved_at: '', error: '', ...fields });

if (!checked.ok) {
  return [{ json: {
    action: 'dead_letter', admins,
    dead: { received_at: now, source: 'SEO Engine: Weekly Report', reason: String(checked.reason || 'unknown').slice(0, 500),
      raw: String(checked.raw || '').slice(0, 20000), replayed: '' },
    log: log({ target: 'Monday SEO report', action: 'receive weekly report', reason: 'CLAUDE.md rule 8: signature and schema first',
      result: 'blocked', error: String(checked.reason || '').slice(0, 500) }),
  } }];
}

const r = checked.report;
if (batches.some((b) => String(b.run_id) === r.run_id)) return [];

const c = r.batch.counts;
const canApprove = c.auto > 0 && r.scan.complete === true;
const row = {
  batch_id: r.batch.id, run_id: r.run_id, run_url: r.run_url, report_date: String(r.made_at).slice(0, 10), made_at: r.made_at,
  site: r.site, status: canApprove ? 'waiting' : 'not asked', can_approve: canApprove, auto_changes: c.auto,
  blocked_changes: c.blocked, manual_tasks: c.manual, pages_checked: r.scan.pages, check_complete: r.scan.complete,
  sent_to: admins.length, received_at: now, answered_by: '', approved_by: '', answered_at: '', apply_status: '',
};
return [{ json: {
  action: 'save', row, report: r, admins,
  log: log({ run_id: r.run_id, target: r.site + ' fixes batch ' + r.batch.id, action: 'send weekly report to the bot',
    reason: 'Monday SEO report: one named yes per batch', result: canApprove ? 'recommended' : 'success',
    evidence: JSON.stringify({ run_url: r.run_url, counts: c, pages: r.scan.pages, complete: r.scan.complete, admins: admins.length }) }),
} }];
