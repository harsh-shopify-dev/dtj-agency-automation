# The store factory worker on DTJ's VPS

Harsh, 22 Oct 2026: "the n8n triggers it and same for the claude"; 23 Oct 2026: "there will be a person watching it, its just
because i dont have to tell you here to listen for the call".

**What it does.** n8n leaves every AI step as a waiting run (Store Factory: Page Design, Add Shop, New Store). The worker
(`n8n/store-factory/worker.py`, a service on the VPS) sees each one within about 30 seconds and asks in Telegram, in the chat the
link came from: **"tap Start if you are watching"**. When someone taps it, Claude Code starts on the VPS. That person follows the
job in Telegram: its questions, the Approve taps and the progress bar. Nobody has to tell a laptop session to listen. While a job
waits for a person, the worker checks for the answer itself and wakes Claude when it comes.

**The rules it keeps:**
- **Attended is the default: nothing starts without a person's Start tap.** The tap is recorded with their name, and Claude runs
  on the VPS's own Claude login (ai@dtjgrowth.com), which CLAUDE.md rule 9 allows because a person watches. No API key is needed.
- **Unattended mode** (`DTJ_WORKER_MODE="api"` in the env file) is only if Harsh switches it on. It needs DTJ's Claude API key
  (`ANTHROPIC_API_KEY`) and a spending cap per request (`DTJ_CLAUDE_MAX_USD`), and Claude Code then never reads the login.
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
   - The rest, one at a time, at a hidden prompt: `python tools/vps/set_key.py N8N_MCP_TOKEN` (an n8n MCP token for the worker),
     then the same for `DTJ_ADMIN_CHAT` (the Telegram chat for requests without one, and for failures) and any other key the
     check names. No Claude API key is needed in the default (attended) mode; Claude Code must be logged in once as `ai`.
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
