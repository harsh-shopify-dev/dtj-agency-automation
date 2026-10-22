# The store factory worker on DTJ's VPS

Harsh, 22 Oct 2026: "everything will be automated ... i would suggest that the n8n triggers it and same for the claude".

**What it does.** n8n leaves every AI step as a waiting run (Store Factory: Page Design, Add Shop, New Store). The worker
(`n8n/store-factory/worker.py`, a service on the VPS) takes each one within about 30 seconds and runs Claude Code on it with
nobody at a computer. People still answer the questions and tap Approve in Telegram. While a job waits for a person, the worker
checks for the answer itself, with no Claude and no cost, and wakes Claude when the answer comes.

**The rules it keeps:**
- **Claude runs on DTJ's Claude API key** (`ANTHROPIC_API_KEY`), never on the subscription login. CLAUDE.md rule 9 and
  Anthropic's terms require this for anything that runs alone.
- **Each request has a spending cap** (`DTJ_CLAUDE_MAX_USD`, Harsh's number); nothing starts without one.
- **Claude may only run what `.claude/vps-settings.json` allows.** It never gets the Shopify CLI itself, publishing, git pushes,
  the vault or network tools. Store changes go through DTJ's own tools: draft themes only, and every store write after its
  Approve tap.
- **Three failures in a row stop new starts.** The admin chat hears each failure in Telegram.
- **Reel requests are not taken yet.** They join after a person has watched the first live reel run (it spends Flow credits).
- **Deploying the install service stays with a person** (`deploy.py` is not allowed). DTJ-own stores stop there and say so in
  Telegram.

## Set it up once (Harsh, as the user `ai`, in your own SSH session)
1. Log in to the VPS and become `ai`: `su - ai`.
2. Get the repo, if it is not there yet:
   `git clone https://github.com/harsh-shopify-dev/dtj-agency-automation ~/dtj-agency-automation`.
3. Run `bash ~/dtj-agency-automation/tools/vps/setup_worker.sh --check`. It lists what is ready and what is missing, by name
   only.
4. Put in the keys:
   - From the vault: `python tools/team-setup/vault.py pull --env-file ~/.config/dtj/worker.env`. Bitwarden asks for your master
     password in a hidden prompt; type nothing after it ends.
   - The rest, one at a time, at a hidden prompt: `python tools/vps/set_key.py ANTHROPIC_API_KEY`, then the same for
     `DTJ_CLAUDE_MAX_USD` (the most one request may spend), `N8N_MCP_TOKEN` (an n8n MCP token for the worker),
     `DTJ_ADMIN_CHAT` (the Telegram chat that hears failures) and any other key the check names.
5. The Shopify login for themes: run `shopify theme list --store <a DTJ store>.myshopify.com` once and finish the login with
   DTJ's collaborator account in your browser.
6. ChatGPT for the pictures: the reel factory's Chrome on port 9222 (`services/reel-factory/setup_vps.sh`), logged in to
   chatgpt.com once.
7. Run `bash ~/dtj-agency-automation/tools/vps/setup_worker.sh`. It installs what is missing and starts the service. Once, as
   root: `loginctl enable-linger ai`, so the worker keeps running after you log out.
8. **Stop every laptop listener** (`listen.py`). Two takers would both take the same request.

## Every day
- `python n8n/store-factory/worker.py --status` shows each run: running, waiting for a person, done (with Claude Code's own cost
  figure), or failed (with why).
- `journalctl --user -u dtj-worker -f` shows the worker's live log; per-run logs are in `.work/worker/<run>.log`, with resume
  links hidden.
- `python n8n/store-factory/worker.py --retry <run>` takes a failed request again. It also lifts a stop after 3 failures.
- To update: `git -C ~/dtj-agency-automation pull`, then `systemctl --user restart dtj-worker`.
