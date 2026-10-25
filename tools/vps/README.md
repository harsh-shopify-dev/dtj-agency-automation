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
6. Pictures: Codex (already on the VPS, logged in with DTJ's ChatGPT account; `tools/vps/codex_image.sh`). Nothing to do
   unless Codex says it is logged out (then: codex login, once, as ai).
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

## Reel machine (Harsh, 25 Oct 2026: reels are made on this VPS)
**What it is.** A Chrome on a virtual screen (`:99`) with its own profile (`~/dtj/chrome-reel`). Claude drives it like a
person (real clicks, through the Playwright MCP) over Chrome's DevTools port, which listens on `127.0.0.1:9222` only. A
remote view of that screen (noVNC on `127.0.0.1:6080` only) lets a person sign in once and watch a run. Pictures come from
Codex (above), so only Google Flow needs a sign-in. Three user services: `dtj-xvfb`, `dtj-reel-chrome`, `dtj-novnc`. All reel
work runs in `dtj-reel.slice`: at most 1.5 of the 2 cores and lower priority (`Nice=10`), so n8n always keeps half a core.
Start a reel job inside it: `systemd-run --user --slice=dtj-reel.slice --nice=10 -p OOMScoreAdjust=500 -- <command>`.

**Set it up once.**
1. As root: `bash /home/ai/dtj-agency-automation/tools/vps/setup_reel.sh --apt` (the virtual screen, the remote view,
   Chrome, fonts, ffmpeg and the libraries the caption renderer's Chrome needs; `ai` has no sudo).
2. As `ai`: `bash ~/dtj-agency-automation/tools/vps/setup_reel.sh` (the reel Python with CPU torch in `~/dtj/reel-venv`, the
   caption renderer's `npm ci`, then it starts the three services). `--check` only reports. After `su - ai` the script sets
   `XDG_RUNTIME_DIR` itself; for your own `systemctl --user` commands run `export XDG_RUNTIME_DIR=/run/user/$(id -u)` first.

**Sign in to Google Flow (a person, once; nobody types a password for you).**
1. On your laptop, open a tunnel and keep that window open: `ssh -L 6080:localhost:6080 root@srv2048145.hstgr.cloud`
2. In your laptop's browser open http://localhost:6080/vnc.html?autoconnect=1&resize=scale. You see the reel Chrome.
3. In that Chrome, open https://labs.google/fx/tools/flow and sign in with DTJ's Google account yourself (2-step code too).
   Open a Flow project once to check it works, then close the browser tab on your laptop (not the reel Chrome) and the tunnel.
The sign-in stays in `~/dtj/chrome-reel`. Port 6080 and 9222 are never opened to the internet: always use the tunnel.

**Every day.** `bash tools/vps/setup_reel.sh --check` (all ok?). `curl -s http://127.0.0.1:9222/json/version` (Chrome answers).
If someone closed the reel Chrome: `systemctl --user start dtj-reel-chrome`. Logs: `journalctl --user -u dtj-reel-chrome -n 50`.
Flow logged out: repeat the sign-in above.
