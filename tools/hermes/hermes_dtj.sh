#!/bin/sh
# `dtj` inside Hermes Agent's container (profile ugc_generation_automation): sends one request to DTJ's VPS over ssh, with a key whose
# authorized_keys line can only run tools/hermes/dtj.py --ssh (tools/hermes/README.md). The sender is Hermes's own session values
# (HERMES_SESSION_USER_ID / _USER_NAME / _PLATFORM, set by the gateway for the Telegram user who wrote), not words the model typed.
#     dtj <remake|reel|refs|audience|status|help> [request text ...]
# Prints the VPS's one JSON line ({"ok", "say"}): relay "say" to the person word for word.
D="$(dirname "$0")"
[ $# -ge 1 ] || set -- help
sub="$1"; shift
{ printf '%s\n' "${HERMES_SESSION_USER_ID:-}" "${HERMES_SESSION_USER_NAME:-}" "${HERMES_SESSION_PLATFORM:-}" "$sub"; printf '%s\n' "$*"; } |
  ssh -i "$D/id_ed25519" -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$D/known_hosts" -o ConnectTimeout=15 \
    ai@"${DTJ_VPS_HOST:-172.16.3.1}"
