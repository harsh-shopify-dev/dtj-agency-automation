# DTJ store factory on Hermes Agent (design, 26 Oct 2026)

## 1. Goal (Harsh's words, 26 Oct 2026)
"Nothing should be operated from here [the laptop], to make the workflow usable for anyone and anywhere without depending on this
device, we have to move to hermes ... hermes learns itself on its own so we will connect this claude to it using the same vps system and
the hermes is also hosted on vps." And: "whatever our automation is capable of must act same in the hermes agent."

Decisions taken in the session:
| Question | Decision |
|---|---|
| How Claude is connected | **B**: Hermes hands every design job to Claude Code on the VPS (its own Claude login); a person taps Start and watches (CLAUDE.md rule 9). No Claude API cost. |
| Hermes's own model | **OpenRouter**, a low-cost model, spend cap set in OpenRouter (about USD 15 a month). |
| n8n | **Stays** behind Hermes: tables, Approve taps, Brand Copy, Store Factory workflows. |
| Who may use the bot | Anyone with bot access (active people in n8n's `dtj_bot_users`) can use everything. |
| Make the theme live | New action, **double confirmation**: tap 1 shows a checklist, tap 2 publishes. Anyone with bot access. |
| Parity | Hermes must do exactly what the automation does today; the laptop is the only thing removed. |

Success = with the laptop switched off, a teammate on a phone builds a whole store from one link (questions, Approve taps, pages,
pictures) and publishes it with the two taps; every parity test in section 7 passes; every secret lives only on the VPS.

## 2. Hermes facts this design rests on (official docs, read 26 Oct 2026)
- Install: `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`; home `~/.hermes`; config `~/.hermes/config.yaml`,
  secrets `~/.hermes/.env`; persona `SOUL.md`; workspace instructions `AGENTS.md`; MIT licence.
- Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS` (numeric ids; no list = everyone denied), `allow_admin_from`,
  `user_allowed_commands`. Questions show inline buttons (with "Other (type answer)"); dangerous commands wait for a typed "yes";
  files go out with `MEDIA:/path` tags (20 MB limit). The gateway owns its bot token (one consumer per token).
- Models: `hermes model` / `/model provider:model`; OpenRouter supported.
- Skills: `SKILL.md` with YAML frontmatter (agentskills.io); `skills.external_dirs` adds folders; `skills.create_dir` sends the
  agent's own new skills elsewhere; `skills.write_approval: true` stages every skill write for review. **The agent can edit any skill
  it can reach**: external folders are not write-protected, so locking needs filesystem permissions.
- Tools: terminal (local/Docker/SSH backends), MCP servers, subagents, a built-in cron scheduler, command approval and a command
  allowlist.

## 3. Architecture (one VPS: srv2048145)
| Part | Runs as | Job |
|---|---|---|
| **Hermes gateway** (new) | Linux user `hermes`, systemd service `hermes-gateway` | The team's Telegram front door. Reads the request, picks the job, starts it through the `dtj` command (below), posts progress, passes free-form change requests to Claude Code word for word. Own model: OpenRouter. |
| **`dtj` command** (new, in this repo: `tools/hermes/dtj`) | called by Hermes | The ONLY thing Hermes may run (command allowlist). Sub-commands map 1:1 to today's capabilities (section 5). It writes jobs to the worker's inbox and reads status; it never touches a store or a theme itself. |
| **DTJ worker** (today's `n8n/store-factory/worker.py`) | user `ai`, service `dtj-worker` | Unchanged role: asks "tap Start if you are watching", runs Claude Code (attended), DTJ_WAIT, progress, page chat. Gains a Hermes inbox source next to the n8n requests. |
| **Claude Code** | user `ai` | Every design job with the repo's skills and tools; `.claude/vps-settings.json` permissions. |
| **n8n** | as today | Tables (`dtj_stores`, `dtj_bot_answers`, `dtj_bot_users`, briefs), Store Factory workflows, Brand Copy, Approve-tap answers. |
| **DTJ bot (existing)** | n8n | Keeps sending and receiving the **Approve / Skip / Start / Stop / question buttons** that store_job.py and the worker send today (their callbacks land in n8n). |

**One bot in the end, in two phases** (Harsh, 26 Oct 2026: "we will built the things in hermes telegram bot once the setup is done").
A Telegram token has one consumer, so:
- **Phase 1, setup:** Hermes on the VPS with its own new bot, its model, the locks, the `dtj` command and the moves off the laptop
  (section 8). The existing DTJ bot keeps the job buttons meanwhile, so nothing that works today stops.
- **Phase 2, one bot:** every button flow the DTJ bot carries today (questions, Start / Stop, Approve / Skip, progress, page chat,
  publish) is rebuilt inside the Hermes bot, each with the same behaviour and a parity test; the answers keep landing in n8n's tables.
  When every flow passes, the DTJ bot's flows are switched off (kept, not deleted) and the team uses only the Hermes bot.

**Locks (Hermes learns, but never rewrites DTJ's rules):**
- The repo is owned by `ai`; user `hermes` gets read-only access (group read, no write) to `.claude/skills`, `CLAUDE.md`, `RUNBOOK.md`.
- `skills.external_dirs: [/home/ai/dtj-agency-automation/.claude/skills]` (read-only by permission), `skills.create_dir:
  /home/hermes/suggestions/skills`, `skills.write_approval: true`.
- Hermes's notes and suggested skills stay in `/home/hermes/suggestions`. Weekly (Hermes cron), Claude Code reviews them and opens a
  pull request for what is worth keeping; Harsh (or a teammate by name) says yes before it becomes a rule.
- Command allowlist: `dtj ...` only. Everything else needs a typed "yes" in Telegram and is refused by the `hermes` user's permissions anyway.

## 4. Data flow of a job
1. A teammate messages Hermes: a store link, a product link, "home page for X", a change, `/addshop`, `/intake`, a reel request, or
   "make the theme live".
2. Hermes checks the sender (allowlist mirrors `dtj_bot_users`, refreshed by `dtj users sync`) and runs the matching `dtj` sub-command.
3. `dtj` starts the same thing n8n starts today (a Store Factory run or a worker inbox job) with the requester's Telegram id and name.
4. The DTJ bot asks the questions and the Start / Approve taps exactly as today; the worker runs Claude Code after Start.
5. `dtj status <job>` lets Hermes answer "how far is it?" from progress.json; finished jobs post their links in both chats.
6. A reply like "make the banner warmer" → `dtj chat <job> "<exact words>"` → page chat (worker) → Claude Code edits the DRAFT → reply.

## 5. Capabilities and their `dtj` sub-commands (parity list)
| Today (n8n bot / laptop) | `dtj` sub-command | Behind it (unchanged) |
|---|---|---|
| Store link → whole store (redesign / new / Drive / samples) | `dtj store <link>` | Store Factory: New Store → worker → skill dtj-new-store |
| Product link → product page | `dtj page <link>` | Store Factory: New Page → worker → dtj-pdp-factory |
| Home page, collection page, header/footer | `dtj home|collection|chrome <store>` | worker → dtj-home-page / dtj-collection-page / dtj-header-footer |
| Page chat (change a built page) | `dtj chat <job> "<text>"` | worker page chat |
| `/addshop` | `dtj addshop <store>` | Store Factory: Add Shop → dtj-add-shop |
| `/intake` | `dtj intake <brand link>` | dtj-brand-intake |
| Reel request | `dtj reel ...` | Reel Factory: New Reel → dtj-ugc-reel |
| Progress / Stop | `dtj status|stop <job>` | progress.json, worker stop |
| **New: make the theme live** | `dtj publish <store>` | section 6 |
| Laptop-only today: store sign-in | `dtj storeauth <store>` | VPS `shopify store auth`; the link goes to the person in Telegram, opened on their device through the VPS callback tunnel (section 8) |
| Laptop-only today: git push / PR | (inside worker jobs) | VPS GitHub key, fine-grained, this repo only; merges still by a person |
| Laptop-only today: install service deploy, app release | `dtj deploy install|app <name>` | runs on the VPS only after a named Approve tap (Tier 2), keys in the VPS env file |

## 6. "Make the theme live" (double confirmation)
- Offered when a store job is finished (and on request `dtj publish <store>`).
- Tap 1 "Make the theme live" → the bot shows the checklist from the store's handover: sample prices still in place, AI pictures,
  store name and currency, payment provider, password page on/off, the theme that will be replaced. Buttons: **Publish now** / Cancel.
- Tap 2 "Publish now" (same person or another person with bot access) → publishes exactly that draft theme (`shopify theme publish`),
  reads back that it is live, logs both taps by name (approved_by "<name> (Telegram Approve, 2 taps)").
- Never removes the password page. The previous live theme stays; an **Undo publish** button republishes it (one tap, logged).
- Needs a CLAUDE.md rule change (rule 2: "a tap never covers a live theme, publishing"): publishing a finished draft by the double tap
  is allowed; editing a live theme's files stays forbidden for automation.

## 7. Testing (parity gate before the switch)
- A second test bot runs Hermes while the old flow keeps working.
- One pass/fail test per row of section 5 on dtj-testing (and a throwaway dev store for publish/undo), run from a phone with the laptop off.
- Unit tests for `dtj` (argument checks, refusing unknown sub-commands, allowlist sync) and the worker's Hermes inbox.
- Switch only when every row passes; then the n8n bot workflow's free-text handling is turned off (kept, not deleted) and the team
  moves to the Hermes bot. Switch back = turn it on again.

## 8. Moving off the laptop (secrets stay on the VPS, never in chat)
- Store sign-ins: `shopify store auth` on the VPS; the callback reaches the VPS through a short-lived tunnel the worker opens; the person
  approves on their own device.
- GitHub: a fine-grained token or deploy key for this repo on the VPS (Harsh creates it; Claude never sees the value).
- Cloudflare (install service) and app-release keys: VPS env file (0600), used only after an Approve tap.
- OpenRouter key: `~/.hermes/.env` (0600), with the spend cap set in OpenRouter.
- The laptop setup script and `listen` mode are retired from the docs once parity holds.

## 9. Errors
Network errors: 3 tries with backoff. The same step failing 3 times: stop, keep the payload, post what failed and what was tried
(Telegram, both bots). Hermes never retries a Tier-2 action by itself. A design job that fails is reported by the worker with its reason.

## 10. Out of scope
Rebuilding n8n's flows inside Hermes; unattended Claude (API key) runs; changing any page design rule.

## 11. Open points for Harsh
1. The new Hermes bot's name (BotFather) and who creates it (the token goes straight into the VPS env file).
2. The OpenRouter account and the exact cap.
3. The GitHub token for the VPS.
