---
name: dtj-factory-setup
description: Set up and run DTJ's store factory from this repo, end to end and by itself. Setup installs what this laptop needs, fills its keys from DTJ's Bitwarden vault, builds or repairs the whole n8n side (data tables, the shops list, the three "Store Factory" workflows, the bot's credentials), and checks the install service and the Telegram app switch on every shop. Listen then waits for page requests sent to the Telegram bot and designs each one. Use it whenever someone says "set up the store factory", "set up the automation", "set everything up", "is everything ready", "new laptop", "new n8n", "listen for the telegram call", "listen for page requests", "start listening", "wait for the bot" or "stop listening". Use it even when they don't name the skill.
---

# DTJ store factory: set up by itself, then listen

Harsh, 12 Oct 2026: "as soon as we run the skill, the skill sets up everything on its own; only designing pages and developer jobs
remain". So:
- **Setup** does every step itself, in order, without asking. It stops only for the four things no tool can do (see "When to stop").
  It ends by proving the setup with read-only checks.
- **Listen** then waits for page requests sent to the Telegram bot (@DtjPageDesignerBot) and designs each one.

What stays with people afterwards: designing pages (Listen, or "handle the Claude Code trigger in n8n") and **developer jobs**:
app releases, adding a client's app copies, changes to the install service or the workflows. How the parts fit together is in
`docs/TEAM-GUIDE.md` Part B; the accounts and keys are in `docs/ACCESS-AND-KEYS.md`.

## Rules that never bend (CLAUDE.md, and why)
- **Secrets never pass through Claude.** Keys come from DTJ's Bitwarden vault through `tools/team-setup/vault.py`, which a person
  runs in their own terminal; the tools read them from the Windows user settings and send them only where they belong. Never ask
  for a secret in chat, and never put one in a file, a command line or a log. `.claude/settings.json` blocks Claude from `bw get`,
  `bw list`, `bw export`, `bw login` and `bw unlock`.
- **Read-only checks and building missing pieces need no permission.** The following need a yes for that action, every time,
  from Harsh or, when he isn't reachable, any teammate by name (CLAUDE.md rule 2):
  publishing an n8n workflow, deploying the install service, adding an admin to the bot, switching a shop's apps. `--apply` never
  deletes and never publishes.
- **Pages only ever go to a DRAFT theme** (`page_builder.ship_draft` / `push_page`).
- **Telegram numbers and people's names stay in n8n's tables.** Never in git, files or chat. The tools print counts only.

## When to stop (the only four)
1. **A password only the person knows** (their Bitwarden master password, their personal n8n token). Open the command in the
   person's own terminal with the `run_in_terminal` tool (if this session has it), so they only type there. Otherwise give them
   the one command to paste into their PowerShell.
2. **Creating an account**, first time only, Harsh: the DTJ Bitwarden organization, a person's n8n login, the Telegram bot. Accounts
   are made by people, never by Claude.
3. **A yes for a shared change.** Collect them all and ask ONCE, in one message with a numbered list (for example "publish
   Store Factory: Telegram Bot; add Riya as admin"). Then do exactly those.
4. **A Telegram number:** the person messages @DtjPageDesignerBot, which replies with their number.

Everything else: do it, then report.

## Setup

### S0. Orient (read, do not ask)
Read `CLAUDE.md`, the newest entry of `docs/HANDOFF.md`, `docs/TEAM-GUIDE.md` Part B and `docs/DTJ-CONTEXT.md`.

### S1. This laptop's programs (Claude runs it)
`powershell -ExecutionPolicy Bypass -File tools/team-setup/setup-team-pc.ps1 -Auto` (forward slashes: the Bash tool is Git Bash)
- Run it with the Bash tool's `run_in_background: true`; it can take several minutes.
- It installs whatever is missing without questions: Git, Python, Node.js, Chrome, the Shopify CLI, the Bitwarden CLI and the
  Python packages. It connects Claude Code to n8n. It asks for no secret.
- Windows may show an administrator prompt for an install: tell the person to click Yes.

### S2. This laptop's keys (the person types one password)
`python tools/team-setup/check_setup.py`. If keys are missing:
1. Open the full setup in the person's terminal with `run_in_terminal`, title "DTJ setup":
   `powershell -ExecutionPolicy Bypass -File tools\team-setup\setup-team-pc.ps1`
2. Tell them, in this order:
   - answer **Y** to "access to DTJ's Bitwarden vault?";
   - sign in with their email and master password, typed only in that terminal;
   - paste their personal n8n token when asked. They get it in n8n: Settings > MCP Access. No n8n login yet? Harsh invites them.
3. Watch with `read_terminal` until it prints the readiness check, then run `check_setup.py` again.
- The tools in this folder read keys straight from the Windows settings, so Setup goes on without a restart. Claude Code's own
  n8n connection (the `mcp__n8n__*` tools) needs a restart if the n8n token was new: say so at the end.
- No vault access yet: the same script asks for each key in a hidden prompt instead. Tell Harsh to add the person to the vault
  (docs/ACCESS-AND-KEYS.md).

### S3. n8n (Claude runs it; builds whatever is missing)
1. `python n8n/store-factory/setup_n8n.py`: the read-only checklist (tables and their columns, the shops list, the people (counts
   only), the three workflows, code equal to git, credentials, published state).
2. If it isn't READY, run `python n8n/store-factory/setup_n8n.py --apply`, then the check again. `--apply`:
   - creates missing tables and workflows from the exports in git (on a brand-new server too);
   - restores the shops list from `n8n/store-factory/stores.seed.json` into an empty dtj_stores table;
   - copies code that differs;
   - creates the bot's two credentials from the keys the vault put on this laptop (`DTJ_TELEGRAM_BOT_TOKEN`,
     `DTJ_CATCHER_BOT_KEY`, `N8N_API_KEY`);
   - attaches the credentials.
3. Left over after `--apply`, and their fixes:
   - **"not published / draft not live":** add "publish <names>" to the one question (stop 3). After the yes:
     `python n8n/store-factory/setup_n8n.py --publish`.
   - **"no admin":** the person messages the bot to get their number (stop 4). Then add "add <name> as admin" to the one question.
     After the yes: `python n8n/store-factory/setup_n8n.py --add-admin <number> --name "<name>"`. The number goes only into that
     command and n8n, never into chat replies or files.
   - **A credential it cannot create** (a key missing on this laptop): it names the key. Harsh puts that key in the vault, the
     person runs `vault.py pull`, and you run `--apply` again.
   - **A structural difference** (a node or connection) that `--apply` cannot repair: run the matching
     `n8n/store-factory/deploy_*.py`. That's a developer job, so say so.
4. The n8n address comes from `.mcp.json`. A move to a new server means changing that one address; then S3 builds the rest.

### S4. The switch and the shops (read-only)
1. Install service: `curl -s -A dtj-setup/1 https://dtj-install-catcher.ultimateecomwithharsh.workers.dev/health` should answer
   `{"ok":true,...}`.
2. The bot end to end, without anyone getting a message: `mcp__n8n__test_workflow` on "Store Factory: Telegram Bot" with this pin
   data:
   - `Telegram Message`: an update with `text: "/shops"` from an admin of dtj_bot_users, in a private chat. Read the admin's number
     with `get_data_table_rows` and use it only in this call.
   - `Send`, `Ask to Confirm` and `Answer the Button`: each `[{"json": {"ok": true}}]`.

   Then read that run's **Licence Report** node: every shop the switch reaches, with each app ON / OFF / not installed, plus the
   page shops that are not on the switch yet.
3. Any page shop not on the switch: adding it is a developer job (TEAM-GUIDE Part E step 1: `add_client.py`, or `add_client.py
   --org` plus `tools\team-setup\save-dtj-app-secrets.ps1`, then deploying the install service with Harsh's yes). Report it;
   don't start it.

### S5. The one question, then the report
If S3 or S4 left yeses to collect, ask them now in one message. Do exactly what was approved, then run the checks of S3 and S4
again. Finish with a short table:
- the laptop;
- the keys (names only);
- n8n: tables, shops, people (counts), workflows, credentials, published;
- the switch: each shop and its state;
- what is left, and who does it (a developer job, or Harsh).

If everything passed, end with: **"Ready. Say 'listen for the telegram call' and keep this window open."** Add "restart Claude
first" if the n8n token was new in S2.

## Listen

A small watcher, `n8n/store-factory/listen.py`, runs in the background and wakes this session when a request is waiting in n8n:
a "Store Factory: Page Design" run paused at "Wait for Claude Code: Page Design", or (since 21 Oct 2026) a "Store Factory: Add Shop"
run paused at "Wait for Claude Code: Add Shop" (an admin's `/addshop`). This session does it exactly as CLAUDE.md's "n8n hand-offs"
section says, answers n8n, and goes back to waiting.

**Only while a person is at this laptop.** Harsh's rule is that Claude Code answers the factory's AI steps only while a human is in
the loop. Unattended running must use the Claude API with an API key (CLAUDE.md rule 9). So the watcher stops itself after 8 hours
(12 at most), never runs overnight, and only one laptop listens at a time; two would design the same page twice.

L1. **Ready?** `python n8n/store-factory/setup_n8n.py` must pass; if it doesn't, run Setup first.
    `python n8n/store-factory/listen.py --status` shows how many requests are already waiting.
L2. **Start.** Run `python n8n/store-factory/listen.py --hours 8` with the Bash tool's `run_in_background: true`. Tell the person in
    one line: "Listening for page requests until <time>. Keep this window open; only this laptop should listen."
L3. **When it exits:**
    - **Exit 0 with one JSON line** (`execution_id`, ...): handle that run.
      1. `get_workflow_execution` with that id, `includeData: true` and `nodeNames: ["Request for Claude Code: Page Design"]`; when
         the line says `"workflow": "Store Factory: Add Shop"`, the node is "Request for Claude Code: Add Shop".
      2. Do everything in its `instructions`, in order; they call the factory skills and `ship_draft` (a page), or add_shop.py and
         the skill dtj-add-shop (a shop).
      3. Answer through `n8n/store-factory/reply.py` exactly as the instructions say.
      4. Tell the person in three lines: the shop, the product, and the result (preview link, checks, samples); for a shop: how many
         of the 7 apps are installed and what is still open.
      5. Go back to L2, unless the person has said stop.
    - **Exit 1:** wrong arguments; fix the command.
    - **Exit 2:** n8n could not be reached 3 times in a row. Say what failed and stop. This follows CLAUDE.md's self-healing rule:
      after 3 failures, stop and report.
    - **Exit 3:** the time limit was reached. Say so, and offer to start again.
L4. **A request that cannot be finished** still gets an answer through `reply.py`, with the failure status its instructions name.
    That way the person who asked hears back, and the run does not wait 3 days. Say why, then keep listening.
    If you stopped halfway without answering, run `python n8n/store-factory/listen.py --forget <execution id>` so the request is
    offered again.
L5. **"stop listening":** stop the background watcher (TaskStop) and confirm. Requests that come in later wait in n8n (up to 3 days)
    until someone listens again or says "handle the Claude Code trigger in n8n".

Never do these in listen mode: publish anything, deploy, switch a shop's apps, touch a live theme, or message people on Telegram
yourself (n8n does that). The one exception is an Add Shop request: the admin's `/addshop` is the yes for exactly what its
instructions list (add_shop.py's app releases, the install service deploy, its progress bar and Install buttons in that chat).
Handle one request at a time.
