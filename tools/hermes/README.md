# Hermes Agent -> DTJ reel factory (phase 1, 26 Oct 2026)

Harsh: "set up hermes for reels". Hermes Agent (Docker container `hermes-agent-ozha-hermes-agent-1`, data in
`/docker/hermes-agent-ozha/data`, profile **ugc_generation_automation** with its own Telegram bot) is a front door for the reel
factory. It runs ONE command, `dtj`, and relays the answer. Nothing about how reels are made changes:

Telegram (Hermes bot) -> Hermes skill `dtj-reels` -> `dtj` (container) -> ssh, forced command -> `tools/hermes/dtj.py --ssh` (VPS,
user `ai`) -> the reel bot's live code nodes decide (team list, daily limit, refusals) -> "Reel Factory: New Reel" -> worker.py ->
"tap Start" in @dtj_reels_bot -> Claude Code (attended, rule 9) with the skills dtj-ugc-reel and dtj-reel-watcher -> Approve taps in
@dtj_reels_bot -> the result.

| File | Where it is installed | What |
|---|---|---|
| `dtj.py` | runs from this repo on the VPS | the command; `python -m unittest tools/hermes/test_dtj.py` |
| `hermes_dtj.sh` | `<profile>/dtj/dtj` (mode 755) | the container side: sends the sender (Hermes's HERMES_SESSION_* values) and the request on stdin; `dtj photo <path>` sends a photo the person sent to Hermes (kept 30 minutes as their product picture, `~ai/dtj/hermes/photos/<user>/`) |
| `skills/dtj-reels/SKILL.md` | `<profile>/skills/dtj/dtj-reels/SKILL.md`, owned by root, read-only for Hermes | when and how Hermes uses `dtj` |
| key | `<profile>/dtj/id_ed25519` (+ `known_hosts`) | its line in `/home/ai/.ssh/authorized_keys` is `command="... tools/hermes/dtj.py --ssh",restrict` |

`<profile>` = `/docker/hermes-agent-ozha/data/profiles/ugc_generation_automation` on the VPS (`/opt/data/profiles/...` inside the
container). The profile's `config.yaml` has `skills.write_approval: true`, so a skill Hermes writes itself waits for review.

Safety:
- The key runs nothing but `dtj.py --ssh` (no shell, no forwarding); `dtj.py` only starts New Reel or answers.
- Who may ask: Hermes's Telegram allowlist AND an active person in n8n's `dtj_bot_users` (the bot's own check).
- Every call is logged on the VPS in `~ai/dtj/hermes/dtj.log`.
- The sender is Hermes's session value, not model text. A model could still forge it by running ssh by hand, but only as another
  active teammate, and the Start/Approve taps still come from that person's own @dtj_reels_bot chat.

Phase 2 (the Hermes migration spec, docs/superpowers/specs/2026-10-26-hermes-agent-migration-design.md): the Start / Approve /
question buttons move into the Hermes bot; until then they stay in @dtj_reels_bot. `/refs` and `/audience` follow the reel bot
(off until "Reel Factory: Find References" is published).
