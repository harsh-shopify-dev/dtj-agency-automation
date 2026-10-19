// n8n Code node "Decide the Answer" in "SEO Engine: Weekly Report" (mode: Run Once for All Items).
// A tap on the report's Yes / No (or on the teammate's "Harsh can't be reached" confirm), handed over by the bot's "Who Is It" as
// { row_id, answer: yes | no | yesnr | cancel, by, user_id, chat_id }.
// The rule (CLAUDE.md rule 2): applying the batch is Tier 2. One named yes covers ONE batch: Harsh's, or, when Harsh is not
// reachable, a DTJ teammate's (an active person in dtj_bot_users), recorded as "<name> (Harsh not reachable)". So a teammate's Yes
// first asks them to confirm that Harsh can't be reached. Harsh = the active bot user whose name has the word "Harsh".
// A batch takes one answer: once it is answered, replaced by a newer report or 7 days old, its buttons only explain why not.
// APPLY_ON false (shadow, Harsh's rule "shadow first"): a yes is recorded with its name and nothing is started; Harsh's yes turns it
// on (n8n/seo-engine/README.md). Then a yes starts GitHub's "SEO apply fixes" with this batch's run, the name and the batch id.
// Output: one item, action "record" (to "Save the Answer"), "confirm" (to "Ask Who Approves") or "reply" (to "Send").
const APPLY_ON = false;
const MAX_AGE_DAYS = 7;
const tap = $('Answer from the Bot').first().json || {};  // (this node's own input is the team rows)
const users = $('Load the Team').all().map((i) => i.json).filter((u) => u && u.telegram_user_id && u.active !== false);
const rows = $('Find the Batch').all().map((i) => i.json).filter((b) => b && b.batch_id);
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const chat = String(tap.chat_id || '');
const reply = (text) => [{ json: { action: 'reply', chat_id: chat, text } }];
const me = users.find((u) => String(u.telegram_user_id).trim() === String(tap.user_id || '').trim());
if (!me) return reply('Only the DTJ team can answer the SEO fixes batch.');
const name = String(me.name || tap.by || '').trim();
if (!name) return reply('Your name is missing in the team list (dtj_bot_users), so your answer cannot be recorded. Ask an admin to add it.');
const answer = String(tap.answer || '');
if (!['yes', 'no', 'yesnr', 'cancel'].includes(answer)) return reply('That button is not valid any more.');
const row = rows.find((b) => Number(b.id) === Number(tap.row_id));
if (!row) return reply('I cannot find that fixes batch any more.');
const label = 'batch ' + esc(row.batch_id) + ' (GitHub run ' + esc(row.run_id) + ')';
if (answer === 'cancel') return reply('OK, nothing recorded. The buttons under the report still work.');
if (row.status !== 'waiting') {
  if (row.status === 'yes' || row.status === 'no') {
    return reply('This ' + label + ' was already answered: ' + esc(row.status) + ' by ' + esc(row.answered_by) + ' on '
      + esc(String(row.answered_at).slice(0, 16).replace('T', ' ')) + ' UTC. One answer per batch.');
  }
  return reply('There is nothing to approve in this ' + label + '.');
}
const newest = Math.max(...rows.map((b) => Number(b.id) || 0));
if (Number(row.id) < newest) {
  return reply('This ' + label + ' was replaced by a newer report. Answer the newest one instead; nothing was recorded.');
}
const made = Date.parse(row.made_at || row.received_at || '');
if (!Number.isFinite(made) || Date.now() - made > MAX_AGE_DAYS * 86400000) {
  return reply('This ' + label + ' is more than ' + MAX_AGE_DAYS + ' days old, so the site may have changed. Next Monday\'s report brings a fresh batch.');
}
if (answer !== 'no' && row.can_approve !== true) return reply('There is nothing to approve in this ' + label + '.');

const isHarsh = /\bharsh\b/i.test(name);
if (answer === 'yes' && !isHarsh) {
  return [{ json: { action: 'confirm', chat_id: chat,
    text: 'Applying this ' + label + ' needs Harsh\'s yes. A teammate may say yes only when Harsh cannot be reached.\n\n'
      + 'Is that the case now? Your yes is then recorded as "' + esc(name) + ' (Harsh not reachable)".',
    yes_data: 'seo:yesnr:' + row.id, no_data: 'seo:cancel:' + row.id,
    yes_text: 'Yes, Harsh can\'t be reached', no_text: 'Cancel' } }];
}
const yes = answer !== 'no';
const approvedBy = !yes ? '' : (isHarsh ? name : name + ' (Harsh not reachable)');
const now = new Date().toISOString();
const others = [...new Set(users.filter((u) => String(u.role || '').toLowerCase().trim() === 'admin')
  .map((u) => String(u.telegram_user_id).trim()).filter((id) => id && id !== chat))];
return [{ json: {
  action: 'record', chat_id: chat, others, row_id: Number(row.id), batch_id: row.batch_id, run_id: String(row.run_id),
  run_url: row.run_url, site: row.site, auto_changes: Number(row.auto_changes) || 0,
  status: yes ? 'yes' : 'no', answered_by: name, approved_by: approvedBy, answered_at: now,
  apply_status: yes ? (APPLY_ON ? 'apply requested (result in dtj_action_log)' : 'shadow: recorded, not applied') : 'not applied (no)',
  dispatch: yes && APPLY_ON,
  body: { ref: 'chore/initial-import', inputs: { run_id: String(row.run_id), approved_by: approvedBy, only: '', batch_id: row.batch_id } },
} }];
