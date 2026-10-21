// n8n Code node "Request for Claude Code: Add Shop" in "Store Factory: Add Shop" (mode: Run Once for All Items).
// The run pauses at the Wait node after this one. A Claude Code session on a DTJ laptop (listen.py watches this workflow too) reads
// `instructions` and does them: add_shop.py makes, links and releases the seven DTJ app copies, the install links come from each copy's
// Distribution page, and the person taps seven Install buttons in Telegram (Harsh, 21 Oct 2026: "one step process from telegram").
const req = $input.first().json || {};
const shop = String(req.shop || '').toLowerCase().trim();
if (!/^[a-z0-9][a-z0-9-]*\.myshopify\.com$/.test(shop)) throw new Error('No store address (<name>.myshopify.com) reached this step');
const label = String(req.label || '').replace(/\s+/g, ' ').trim().slice(0, 60);
if (!label) throw new Error('No client name reached this step');
const by = String(req.requested_by || 'an admin').trim().slice(0, 60);
const chat = /^-?[0-9]{3,20}$/.test(String(req.chat_id || '').trim()) ? String(req.chat_id).trim() : '';
const resumeUrl = $execution.resumeUrl;
const client = shop.split('.')[0];
const q = (s) => '"' + String(s).replace(/"/g, "'") + '"';
const base = 'python services/install-catcher/tools/add_shop.py --shop ' + shop;
const parts = ['blocks', 'sections', 'sections2', 'heroes', 'commerce', 'shop', 'collection'];
const lines = [
  'DTJ STORE FACTORY - add a client shop: the seven DTJ app copies on ' + shop + ' for ' + label + '.',
  'You are the AI step: a Claude Code session on a DTJ laptop where the Shopify CLI is signed in to DTJ\'s Dev Dashboard account.',
  '',
  'REQUEST',
  '- Shop: ' + shop + ' (the ORIGINAL .myshopify.com address) | Client name: ' + label,
  '- Asked by: ' + by + ' (an admin on the DTJ bot) | Telegram chat: ' + (chat || '(none)'),
  '- This /addshop is ' + by + '\'s yes for exactly this: creating, linking and releasing the seven app copies, deploying the install service, '
    + 'and generating the seven install links on the copies\' Distribution pages. Nothing else: no theme write, no live theme, no other shop.',
  '',
  'DO THIS, IN ORDER (from the repo root, D:\\CODE CONTAINERR\\WEB DEV\\dtj-agency-automation)',
  '1. Read CLAUDE.md and the skill dtj-add-shop (its "One command: add_shop.py" part). Stay on the current git branch.',
  '2. Run in the person\'s terminal (terminal tool run_in_terminal: the Shopify CLI there is signed in to DTJ\'s Dev Dashboard; Claude\'s own '
    + 'shell may hold another login), then read it with read_terminal:',
  '   ' + base + ' --label ' + q(label) + (chat ? ' --chat ' + chat : '') + ' --approved-by ' + q(by + ' (Telegram /addshop)'),
  '   It creates, links and releases the copies, saves their keys (never shown) and deploys the install service, with a progress bar in '
    + 'the chat. Exit 3 = waiting for the install links; exit 1 = stopped (read why, fix, run the same command again: it continues).',
  '3. The install links: Shopify makes them ONLY in the Dev Dashboard (no API, no CLI). For each copy (DTJ Blocks / Sections / Sections 2 / '
    + 'Heroes / Commerce / Shop / Collection - ' + label + '): open the app in the built-in browser (dev.shopify.com, organization 141167028), '
    + 'Distribution, Custom distribution, the store ' + shop + ', Generate link, copy it. If the browser is not signed in, ask the person at '
    + 'the laptop; never type a password.',
  '   Record them: ' + base + ' ' + parts.map((p) => '--link ' + p + '=<url>').join(' '),
  '   That run sends ' + by + ' seven Install buttons in Telegram and waits up to 30 minutes for the installs (exit 3 = some still missing: '
    + 'run ' + base + ' again later to keep waiting).',
  '4. Answer this n8n run, also when it stopped (add_shop.py writes the answer file at the end of every run):',
  '   python n8n/store-factory/reply.py --resume-url "' + resumeUrl + '" --body .work/add-shop/' + client + '.answer.json',
  '5. Add a dated entry to docs/HANDOFF.md: the shop, what is done, what is open (its draft theme id and Theme Access password for page writes).',
  '',
  'RULES',
  '- Never print, paste or store a client secret, token or password: add_shop.py moves each key from the CLI into a Windows user variable.',
  '- No theme and no store change here: an install is the store owner\'s own tap on Shopify\'s page (a collaborator login was refused before).',
  '- If something blocks you (the CLI is not signed in, Shopify refuses an app name or a release): stop, answer n8n (step 4: the answer file '
    + 'says "could not add" and why) and tell the person exactly what to do.',
];
return [{ json: {
  claude_code_stage: 'add_shop',
  resume_url: resumeUrl,
  instructions: lines.join('\n'),
  request: { shop, label, requested_by: by, telegram_chat_id: chat, client },
} }];
