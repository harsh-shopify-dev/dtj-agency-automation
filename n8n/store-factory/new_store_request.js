// n8n Code node "Request for Claude Code: New Store" in "Store Factory: New Store" (mode: Run Once for All Items).
// The run pauses at the Wait node after this one. A Claude Code session on a DTJ laptop (listen.py watches this workflow too) reads
// `instructions` and does them with the skill dtj-new-store: the store read from its link, the questions and every Approve tap in
// Telegram, the draft copy, the DTJ apps, the brand data and each part chosen (Harsh, 21 Oct 2026: "i just share the brand store link
// and it starts designing the store and it asks the specific questions it needs along with the app installation").
const req = $input.first().json || {};
const link = String(req.link || '').trim();
if (!/^https?:\/\/(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:[/?#][^\s]*)?$/.test(link)) throw new Error('No store link reached this step');
const by = String(req.requested_by || 'an admin').trim().slice(0, 60);
const chat = /^-?[0-9]{3,20}$/.test(String(req.chat_id || '').trim()) ? String(req.chat_id).trim() : '';
const note = String(req.note || '').replace(/\s+/g, ' ').trim().slice(0, 500);
const resumeUrl = $execution.resumeUrl;
const q = (s) => '"' + String(s).replace(/"/g, "'") + '"';
const job = 'python n8n/store-factory/store_job.py';
const lines = [
  'DTJ STORE FACTORY - a whole store from one link: ' + link,
  'You are the AI step: a Claude Code session on a DTJ laptop with a person at it (the Shopify CLI there is logged in to DTJ\'s account).',
  '',
  'REQUEST',
  '- Store link: ' + link + (note ? ' | Note from ' + by + ': ' + note : ''),
  '- Asked by: ' + by + ' (an admin on the DTJ bot) | Telegram chat: ' + (chat || '(none: ask the person at this laptop instead)'),
  '- Every yes comes as an Approve tap in Telegram (Harsh, 21 Oct 2026): one tap for the draft copy, one for the app copies, one '
    + 'for the header, one for the footer, one for the collection page. Product and home pages go to the draft under Harsh\'s standing '
    + 'rule. Nothing is published, the live theme is never written, no store or product is created.',
  '',
  'DO THIS, IN ORDER (from the repo root, D:\\CODE CONTAINERR\\WEB DEV\\dtj-agency-automation)',
  '1. Read CLAUDE.md and the skill dtj-new-store; follow it step by step. Stay on the current git branch.',
  '2. Start: ' + job + ' start --link ' + q(link) + (chat ? ' --chat ' + chat : '') + ' --by ' + q(by),
  '   It reads the store and asks the questions in Telegram. Its JSON line names the job. Exit 3 = waiting for an answer: run it '
    + 'again (it never asks twice); exit 1 = stopped (it says why).',
  '3. The skill\'s steps: the draft copy (store_job.py draft), the apps (store_job.py apps, then add_shop.py in the person\'s terminal), '
    + 'the brand data, then each part chosen, each write after its own Approve tap (store_job.py approve).',
  '4. Answer this n8n run at the end, also when it stopped or is only partly done:',
  '   ' + job + ' finish --job <job> --status "<done | partly done | could not start>" --note "<what is open, in plain words>"',
  '   python n8n/store-factory/reply.py --resume-url "' + resumeUrl + '" --body .work/stores/<job>/answer.json',
  '5. Add a dated entry to docs/HANDOFF.md: the store, what was written where, the samples to replace, what is open.',
  '',
  'RULES',
  '- A write without its Approve tap does not happen; a Skip leaves it undone. One tap covers one action.',
  '- Never invent an offer, price, claim, review or policy: the offer is only the words the person typed; mark samples SAMPLE.',
  '- Never print, paste or store a secret. If something blocks you (the CLI login has no access, the system blocks a command): stop that '
    + 'step, tell the person exactly what to do, and say it in the answer.',
];
return [{ json: {
  claude_code_stage: 'new_store',
  resume_url: resumeUrl,
  instructions: lines.join('\n'),
  request: { link, requested_by: by, telegram_chat_id: chat, note },
} }];
