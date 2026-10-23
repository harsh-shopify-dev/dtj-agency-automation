#!/usr/bin/env bash
# Set up the store factory worker on DTJ's VPS (Harsh, 22 Oct 2026: "everything will be automated ... the n8n triggers it and same
# for the claude"). Run it as the user ai in your own SSH session; safe to run again (it only adds what is missing).
#     bash tools/vps/setup_worker.sh            check and set up, then start the worker if every key is there
#     bash tools/vps/setup_worker.sh --check    only say what is ready and what is missing
# It never prints a key. Keys go into ~/.config/dtj/worker.env (owner-only), see tools/vps/README.md.
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"  # claude and codex live there for ai (the service's PATH has them too)

REPO="${DTJ_REPO:-$HOME/dtj-agency-automation}"
ENV_FILE="$HOME/.config/dtj/worker.env"
UNIT_DIR="$HOME/.config/systemd/user"
# attended (the default, Harsh 23 Oct 2026: a person watches every run in Telegram) needs no Claude API key: the VPS's own Claude
# login runs it. DTJ_WORKER_MODE="api" in the env file = unattended, which needs the API key and the spend cap too.
NEEDED=(N8N_MCP_TOKEN DTJ_TELEGRAM_BOT_TOKEN DTJ_ADMIN_CHAT DTJ_CATCHER_CONTROL_KEY)
OPTIONAL=(DTJ_GDRIVE_CLIENT_ID DTJ_GDRIVE_CLIENT_SECRET DTJ_GDRIVE_REFRESH_TOKEN OPENAI_API_KEY)
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1
missing=()
ok() { echo "  ok    $1"; }
todo() { echo "  TODO  $1"; missing+=("$1"); }

if [ "$(id -un)" = "root" ]; then
  echo "Run this as the user ai, not root: su - ai, then bash tools/vps/setup_worker.sh"
  exit 1
fi

echo "1. The repo ($REPO)"
if [ -d "$REPO/.git" ]; then
  [ $CHECK_ONLY = 1 ] || git -C "$REPO" pull --ff-only --quiet || echo "  (git pull failed: local changes? leaving the repo as it is)"
  ok "repo at $(git -C "$REPO" log --oneline -1)"
else
  todo "clone it: git clone https://github.com/harsh-shopify-dev/dtj-agency-automation $REPO (needs GitHub access for ai)"
fi

echo "2. Python"
if [ -x "$REPO/.venv/bin/python" ]; then
  ok "venv $("$REPO/.venv/bin/python" --version)"
elif [ $CHECK_ONLY = 0 ] && [ -d "$REPO" ]; then
  python3 -m venv "$REPO/.venv" && ok "venv made"
else
  todo "python3 -m venv $REPO/.venv"
fi
if [ $CHECK_ONLY = 0 ] && [ -x "$REPO/.venv/bin/pip" ]; then
  "$REPO/.venv/bin/pip" install --quiet -r "$REPO/services/store-builder/requirements.txt" playwright && ok "packages installed"
fi

echo "3. Programs"
for prog in node npm claude; do
  if command -v "$prog" >/dev/null; then ok "$prog $("$prog" --version 2>/dev/null | head -1)"; else todo "install $prog"; fi
done
if command -v shopify >/dev/null || [ -x "$HOME/.npm-global/bin/shopify" ]; then
  ok "Shopify CLI"
elif [ $CHECK_ONLY = 0 ] && command -v npm >/dev/null; then
  npm config set prefix "$HOME/.npm-global" && npm install -g --silent @shopify/cli @bitwarden/cli && ok "Shopify CLI and Bitwarden CLI installed"
else
  todo "npm install -g @shopify/cli @bitwarden/cli (with npm prefix ~/.npm-global)"
fi

echo "4. Keys in $ENV_FILE (names only)"
mkdir -p "$(dirname "$ENV_FILE")" && touch "$ENV_FILE" && chmod 600 "$ENV_FILE"
if grep -q '^DTJ_WORKER_MODE="api"' "$ENV_FILE"; then
  echo "  mode: api (unattended): the Claude API key and the spend cap are needed too"
  NEEDED+=(ANTHROPIC_API_KEY DTJ_CLAUDE_MAX_USD)
else
  echo "  mode: attended (a person taps Start in Telegram and watches): the VPS's own Claude login runs it"
  if [ -f "$HOME/.claude/.credentials.json" ]; then ok "Claude Code is logged in for $(id -un)"; else todo "log in to Claude Code once as $(id -un): claude, then /login"; fi
fi
for k in "${NEEDED[@]}"; do
  if grep -q "^$k=" "$ENV_FILE"; then ok "$k"; else todo "$k: python tools/vps/set_key.py $k (or the vault pull below)"; fi
done
for k in "${OPTIONAL[@]}"; do
  grep -q "^$k=" "$ENV_FILE" && ok "$k" || echo "  -     $k (optional)"
done

echo "5. Pictures (Codex, logged in with DTJ's ChatGPT account: tools/vps/codex_image.sh)"
if command -v codex >/dev/null; then
  ok "codex $(codex --version 2>/dev/null | tail -1)"
else
  todo "install codex for $(id -un) (npm install -g @openai/codex) and log in once: codex login"
fi

echo "6. The service"
if [ ${#missing[@]} -gt 0 ]; then
  echo "  not started: ${#missing[@]} item(s) above. Fix them and run this again."
  exit 3
fi
if [ $CHECK_ONLY = 1 ]; then
  echo "  everything is ready (--check: nothing started)"
  exit 0
fi
mkdir -p "$UNIT_DIR"
cp "$REPO/tools/vps/dtj-worker.service" "$UNIT_DIR/dtj-worker.service"
systemctl --user daemon-reload
systemctl --user enable --now dtj-worker.service
ok "dtj-worker started: journalctl --user -u dtj-worker -f (to watch), python n8n/store-factory/worker.py --status"
echo "  Once, as root, so it keeps running after you log out: loginctl enable-linger ai"
echo "  Stop every laptop listener now: two takers would take the same request."
