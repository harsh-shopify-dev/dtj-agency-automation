#!/bin/sh
# `dtj` inside Hermes Agent's container (profile ugc_generation_automation): sends one request to DTJ's VPS over ssh, with a key whose
# authorized_keys line can only run tools/hermes/dtj.py --ssh (tools/hermes/README.md). The sender is Hermes's own session values
# (HERMES_SESSION_USER_ID / _USER_NAME / _PLATFORM, set by the gateway for the Telegram user who wrote), not words the model typed.
#     dtj <remake|reel|refs|audience|status|help> [request text ...]
#     dtj photo <the saved image path Hermes gave for a photo the person sent>   (it becomes a product picture for 30 minutes)
# Prints the VPS's one JSON line ({"ok", "say"}): relay "say" to the person word for word.
D="$(dirname "$0")"
[ $# -ge 1 ] || set -- help
sub="$1"; shift
send() {
  ssh -T -i "$D/id_ed25519" -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$D/known_hosts" -o ConnectTimeout=15 \
    ai@"${DTJ_VPS_HOST:-172.16.3.1}"
}
head4() { printf '%s\n' "${HERMES_SESSION_USER_ID:-}" "${HERMES_SESSION_USER_NAME:-}" "${HERMES_SESSION_PLATFORM:-}" "$sub"; }
if [ "$sub" = photo ]; then
  f="$1"
  if [ ! -f "$f" ] || [ "$(wc -c < "$f")" -gt 10000000 ]; then
    echo '{"ok": false, "say": "I could not read that photo. Please send it again (as a photo, under 10 MB)."}'; exit 1
  fi
  { head4; base64 < "$f" | tr -d '\n'; printf '\n'; } | send
else
  { head4; printf '%s\n' "$*"; } | send
fi
