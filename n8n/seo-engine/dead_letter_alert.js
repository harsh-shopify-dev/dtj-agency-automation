// n8n Code node "Dead Letter Alert" in "SEO Engine: Weekly Report" (mode: Run Once for All Items).
// After "Keep in Dead Letter" saved a report that failed its signature or schema check (CLAUDE.md rule 8: nothing else runs for
// it): tell the admins once, in plain words, with the reason and where it is kept. No Yes button, no batch.
// Output: items { chat_id, text } for "Send".
const plan = $('Plan the Report').first().json;
const kept = $input.first().json || {};
const esc = (s) => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const text = 'The Monday SEO report reached n8n but did not pass its checks, so it was not shown and nothing can be approved from it.\n\n'
  + 'Why: ' + esc(plan.dead.reason) + '\n'
  + 'Kept in the data table dtj_dead_letter' + (kept.id ? ' (row ' + esc(kept.id) + ')' : '') + '. '
  + 'The report itself is safe in the GitHub run (Actions > SEO weekly). Ask Claude Code to look at it.';
return (plan.admins || []).map((chat) => ({ json: { chat_id: chat, text } }));
