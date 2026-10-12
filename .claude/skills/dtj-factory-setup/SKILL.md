---
name: dtj-factory-setup
description: Set up and run DTJ's store factory from this repo, end to end. Setup checks this laptop, builds or repairs the n8n side (the data tables, the three "Store Factory" workflows, their credentials), and checks the install service and the Telegram app switch on every shop. Listen then waits for page requests sent to the Telegram bot and designs each one. Use it whenever someone says "set up the store factory", "set up the automation", "set everything up", "is everything ready", "new laptop", "new n8n", "listen for the telegram call", "listen for page requests", "start listening", "wait for the bot" or "stop listening". Use it even when they don't name the skill.
---

# DTJ store factory: set up, then listen

This skill has two jobs:
- **Setup** gets this laptop, n8n and the app switch ready, and proves it with read-only checks. Run it on every new laptop, after a
  pull that changed `n8n/store-factory/`, or when something looks broken.
- **Listen** waits for page requests that people send to the Telegram bot (@DtjPageDesignerBot), and designs each one. Once setup
  has passed, the person only has to say "listen for the telegram call".

How the parts fit together is in `docs/TEAM-GUIDE.md` Part B; read it once if this is a new session.

## Rules that never bend (CLAUDE.md, and why)
- **Secrets never pass through Claude.** Tokens, passwords and keys are typed into hidden prompts in the person's own PowerShell, or
  pasted by the person into n8n's credential screens. Never ask for one in chat, and never put one in a file, a command line or a log.
  The tools here check secrets by name and length only.
- **Every check in Setup is read-only and needs no permission.** Anything that changes a shared system needs Harsh's yes for that
  action, every time: publishing an n8n workflow, deploying the install service, switching a shop's apps, adding people to the bot.
  `--apply` only builds missing pieces and copies code from git; it never deletes or publishes anything.
- **Pages only ever go to a DRAFT theme** (`page_builder.ship_draft` / `push_page`). Never a live theme.
- **Telegram numbers (people) and shop rows live only in n8n's tables, not in git.** Read them when a step needs them, and never
  copy them into files or chat.

## Setup

Run the steps in order. When a step needs the person, stop, tell them exactly what to click or run (numbered, plain words), then
check again once they say "done".

### S0. Orient
Read `CLAUDE.md`, the newest entry of `docs/HANDOFF.md`, and `docs/TEAM-GUIDE.md` Part B. Then say in one line what this setup is:
a designer's laptop, Harsh's laptop, or a new n8n server.

### S1. This laptop
`python tools/team-setup/check_setup.py`
- Programs or secrets missing: the person runs this in their own PowerShell, in the project folder. It installs what is missing and
  asks for each secret in a hidden prompt:
  `powershell -ExecutionPolicy Bypass -File tools\team-setup\setup-team-pc.ps1`
  Then they close and reopen Claude, so it sees the new settings, and you run the check again.
- Keys come from DTJ's Bitwarden vault when the person has access: the setup script asks, or they run
  `python tools/team-setup/vault.py pull` in their own PowerShell. Claude never runs `bw` itself: reading the vault is blocked
  in `.claude/settings.json`, and only the person can type their master password.
- `vault.py status` (run by the person) warns if `DTJ_CATCHER_VAULT_KEY` exists only on one laptop: point them to
  docs/ACCESS-AND-KEYS.md, "The company vault".
- "draft theme ... is live": the shop's draft was published. Harsh duplicates the live theme and puts the new number in dtj_stores
  (TEAM-GUIDE Part E step 2).

### S2. n8n
1. `python n8n/store-factory/setup_n8n.py`: a read-only checklist covering the data tables, the three workflows (published, live =
   draft, code equal to git), and the credentials. "Cannot connect" usually means N8N_MCP_TOKEN or `.mcp.json` is missing: back
   to S1. The n8n address comes from `.mcp.json`, so a new server is one edit there.
2. Anything missing or different: `python n8n/store-factory/setup_n8n.py --apply`, then check again. On a brand-new server this
   builds the tables and all three workflows from the exports in git. A structural difference it reports but cannot repair is fixed
   with the matching `n8n/store-factory/deploy_*.py`.
3. A missing **credential** can only be made by a person (n8n never shows a secret to these tools, on purpose):
   - Telegram API **DTJ Page Bot**: the bot token from @BotFather. In n8n: Overview > Credentials > Create credential > Telegram API,
     paste, save.
   - Header Auth **DTJ Catcher Bot Key**: Name `X-DTJ-Bot-Key`. On Harsh's laptop, copy the Value without showing it:
     `[Environment]::GetEnvironmentVariable('DTJ_CATCHER_BOT_KEY','User') | Set-Clipboard`. Paste it into Value (Ctrl+A, then
     Ctrl+V), save, then clear the clipboard: `Set-Clipboard -Value ' '`.
   After "done", run `--apply` again (it attaches them), then check.
4. A workflow that is not published, or whose draft differs from live: ask Harsh "publish <names>?". Only after his yes, run
   `python n8n/store-factory/setup_n8n.py --publish`.
5. **Rows:** shops (dtj_stores) and people (dtj_bot_users) are not in git. On a new server Harsh adds the shops (TEAM-GUIDE Part E)
   and the people: each person messages the bot, which replies with their number, and Harsh adds a row.

### S3. The switch and the shops (read-only)
1. Check the bot end to end without anyone getting a message. Run `mcp__n8n__test_workflow` on "Store Factory: Telegram Bot" with this
   pin data:
   - `Telegram Message`: an update with `text: "/shops"` from an admin of dtj_bot_users, in a private chat. Read the admin's number
     with `get_data_table_rows` and use it only in this call.
   - `Send`, `Ask to Confirm` and `Answer the Button`: each `[{"json": {"ok": true}}]`, so no Telegram message goes out.

   Then read that run's **Licence Report** node (`get_workflow_execution` with `includeData` and `nodeNames: ["Licence Report"]`).
   It lists every shop the switch reaches, each DTJ app ON / OFF / not installed, and the page shops that are not on the switch yet.
2. Every shop in dtj_stores should be on the switch. For each one that is not, tell Harsh to follow TEAM-GUIDE Part E step 1:
   `add_client.py` for a client's own app copies, or `add_client.py --org` for a store in DTJ's own Shopify organization. Then the
   install service is deployed, with his yes.
3. A "the bot's key was refused" line means the credential DTJ Catcher Bot Key is wrong: S2 step 3.

### S4. Report
Give a short table: the laptop, the n8n tables, workflows, credentials and publish state, every switch shop with its state, the page
shops not on the switch, and what the person still has to do. If everything passed, end with:
**"Ready. Say 'listen for the telegram call' and keep this window open."**

## Listen

A small watcher, `n8n/store-factory/listen.py`, runs in the background and wakes this session when a page request is waiting in n8n.
A waiting request is a "Store Factory: Page Design" run paused at "Wait for Claude Code: Page Design". This session designs the page
exactly as CLAUDE.md's "n8n hand-offs" section says, answers n8n, and goes back to waiting.

**Only while a person is at this laptop.** Harsh's rule is that Claude Code answers the factory's AI steps only while a human is in
the loop. Unattended running must use the Claude API with an API key (CLAUDE.md rule 9). So the watcher stops itself after 8 hours
(12 at most), never runs overnight, and only one laptop listens at a time; two would design the same page twice.

L1. **Ready?** `python n8n/store-factory/setup_n8n.py` must pass; if it doesn't, run Setup first.
    `python n8n/store-factory/listen.py --status` shows how many requests are already waiting.
L2. **Start.** Run `python n8n/store-factory/listen.py --hours 8` with the Bash tool's `run_in_background: true`. Tell the person in
    one line: "Listening for page requests until <time>. Keep this window open; only this laptop should listen."
L3. **When it exits:**
    - **Exit 0 with one JSON line** (`execution_id`, ...): handle that run.
      1. `get_workflow_execution` with that id, `includeData: true` and `nodeNames: ["Request for Claude Code: Page Design"]`.
      2. Do everything in its `instructions`, in order; they call the factory skills and `ship_draft`.
      3. Answer through `n8n/store-factory/reply.py` exactly as the instructions say.
      4. Tell the person in three lines: the shop, the product, and the result (preview link, checks, samples).
      5. Go back to L2, unless the person has said stop.
    - **Exit 3:** the time limit was reached. Say so, and offer to start again.
    - **Exit 1:** wrong arguments; fix the command.
    - **Exit 2:** n8n could not be reached 3 times in a row. Say what failed and stop. This follows CLAUDE.md's self-healing rule:
      after 3 failures, stop and report.
L4. **A request that cannot be finished** still gets an answer through `reply.py`, with the failure status its instructions name.
    That way the person who asked hears back, and the run does not wait 3 days. Say why, then keep listening.
    If you stopped halfway without answering, run `python n8n/store-factory/listen.py --forget <execution id>` so the request is
    offered again.
L5. **"stop listening":** stop the background watcher (TaskStop) and confirm. Requests that come in later wait in n8n (up to 3 days)
    until someone listens again or says "handle the Claude Code trigger in n8n".

Never do these in listen mode: publish anything, deploy, switch a shop's apps, touch a live theme, or message people on Telegram
yourself (n8n does that). Handle one request at a time.
