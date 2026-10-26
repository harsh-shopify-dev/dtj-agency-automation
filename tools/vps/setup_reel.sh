#!/usr/bin/env bash
# Turn DTJ's VPS into the reel machine (Harsh, 25 Oct 2026: the reel worker runs on the current VPS): a Chrome on a virtual
# screen (:99) that Claude drives over CDP on 127.0.0.1:9222, a remote view of that screen for the one-time sign-in
# (noVNC on 127.0.0.1:6080 only, reached through an SSH tunnel), the reel Python (CPU torch) and the caption renderer.
#     bash tools/vps/setup_reel.sh --apt      the system packages: run ONCE as root (the user ai has no sudo)
#     bash tools/vps/setup_reel.sh            as ai: install what is missing and start the three services
#     bash tools/vps/setup_reel.sh --check    as ai: only say what is ready and what is missing
# Safe to run again. It never signs in anywhere and never stores a password: a person signs in to Google Flow themself
# (tools/vps/README.md, "Reel machine"). Reel work runs in dtj-reel.slice (CPUQuota=150%, Nice=10) so n8n keeps a core.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="${DTJ_REPO:-$(cd "$HERE/../.." && pwd)}"
REEL="$REPO/services/reel-factory"
VENV="$HOME/dtj/reel-venv"
UNIT_DIR="$HOME/.config/systemd/user"
UNITS=(dtj-reel.slice dtj-xvfb.service dtj-reel-chrome.service dtj-novnc.service)
# Ubuntu 24.04 names (t64). The libs are what Remotion's headless Chrome needs (remotion.dev/docs/miscellaneous/linux-dependencies).
APT_PKGS=(xvfb x11vnc novnc websockify fonts-noto-core fonts-noto-extra ffmpeg python3-venv
          libnss3 libdbus-1-3 libatk1.0-0t64 libatk-bridge2.0-0t64 libcups2t64 libgbm1 libxkbcommon0 libxrandr2 libxfixes3
          libxcomposite1 libxdamage1 libpango-1.0-0 libcairo2 libasound2t64)
CHROME_DEB=https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

if [ "${1:-}" = "--apt" ]; then
  [ "$(id -u)" = 0 ] || { echo "--apt installs system packages: run it as root"; exit 1; }
  apt-get update
  apt-get install -y "${APT_PKGS[@]}"
  if ! command -v google-chrome >/dev/null; then   # Google's own package (it also adds Google's apt source for updates)
    tmp="$(mktemp -d)"
    curl -fsSLo "$tmp/chrome.deb" "$CHROME_DEB"
    apt-get install -y "$tmp/chrome.deb"
    rm -rf "$tmp"
  fi
  echo "System packages done. Now as ai: bash $REPO/tools/vps/setup_reel.sh"
  exit 0
fi

if [ "$(id -un)" = "root" ]; then
  echo "Run this as the user ai, not root (root only runs --apt): su - ai, then bash tools/vps/setup_reel.sh"
  exit 1
fi
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"   # su - ai does not set it; systemctl --user needs it
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1
missing=()
ok() { echo "  ok    $1"; }
todo() { echo "  TODO  $1"; missing+=("$1"); }

echo "1. System packages (root: bash $REPO/tools/vps/setup_reel.sh --apt)"
apt_missing=()
for p in "${APT_PKGS[@]}"; do
  [ "$(dpkg-query -W -f='${db:Status-Status}' "$p" 2>/dev/null)" = installed ] || apt_missing+=("$p")
done
command -v google-chrome >/dev/null || apt_missing+=(google-chrome-stable)
if [ ${#apt_missing[@]} -eq 0 ]; then
  ok "all ${#APT_PKGS[@]} packages + $(google-chrome --version)"
else
  todo "as root: bash $REPO/tools/vps/setup_reel.sh --apt (missing: ${apt_missing[*]})"
fi

echo "2. Reel Python ($VENV, CPU torch) and the caption renderer"
py_ok() { [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import torch, whisper, cv2, simple_lama_inpainting, playwright" 2>/dev/null; }
npm_ok() { [ -d "$REEL/captions-remotion/node_modules" ]; }
if ! { py_ok && npm_ok; } && [ $CHECK_ONLY = 0 ] && [ ${#apt_missing[@]} -eq 0 ]; then
  bash "$REEL/setup_vps.sh" --no-apt   # the reel service's own installer: venv, torch, requirements.txt, npm ci
fi
if py_ok; then ok "python libs ($("$VENV/bin/python" -c 'import torch; print("torch", torch.__version__)'))"; else todo "reel python: bash $REEL/setup_vps.sh --no-apt"; fi
if npm_ok; then ok "captions-remotion node_modules"; else todo "captions: cd $REEL/captions-remotion && npm ci"; fi

echo "3. Services (systemd --user, in dtj-reel.slice)"
if [ $CHECK_ONLY = 0 ] && [ ${#apt_missing[@]} -eq 0 ]; then
  mkdir -p "$UNIT_DIR" "$HOME/dtj/chrome-reel"
  for u in "${UNITS[@]}"; do cp "$HERE/$u" "$UNIT_DIR/$u"; done
  systemctl --user daemon-reload
  systemctl --user enable --now dtj-xvfb.service dtj-reel-chrome.service dtj-novnc.service
  sleep 5   # Chrome needs a moment before it answers on 9222
fi
for u in "${UNITS[@]}"; do
  if [ ! -f "$UNIT_DIR/$u" ]; then todo "$u not installed"
  elif ! cmp -s "$HERE/$u" "$UNIT_DIR/$u"; then todo "$u is older than the repo's: run this without --check"
  elif [ "${u##*.}" = slice ] || systemctl --user is-active --quiet "$u"; then ok "$u"
  else todo "$u not running: journalctl --user -u $u -n 30"; fi
done
[ "$(loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null)" = yes ] && ok "linger on (services run without a login)" \
  || todo "as root, once: loginctl enable-linger $(id -un)"

echo "4. Reachable from the VPS only"
if v="$(curl -sf --max-time 5 http://127.0.0.1:9222/json/version)"; then
  ok "Chrome DevTools on 127.0.0.1:9222 ($(echo "$v" | grep -o '"Browser": *"[^"]*"' | cut -d'"' -f4))"
else
  todo "Chrome DevTools does not answer on 127.0.0.1:9222"
fi
if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:6080/vnc.html)" = 200 ]; then
  ok "noVNC on 127.0.0.1:6080"
else
  todo "noVNC does not answer on 127.0.0.1:6080"
fi
public="$(ss -Hltn 2>/dev/null | awk '{print $4}' | grep -E ':(9222|6080|59[0-9][0-9])$' | grep -vE '^(127\.0\.0\.1|\[::1\]):' || true)"
if [ -z "$public" ]; then ok "nothing of it listens on a public address"; else todo "LISTENING PUBLICLY, stop it now: $public"; fi

echo "5. Result"
if [ ${#missing[@]} -gt 0 ]; then
  echo "  ${#missing[@]} item(s) above. Fix them and run this again."
  exit 3
fi
echo "  reel machine ready. A person signs in to Google Flow once through the remote view (tools/vps/README.md, Reel machine)."
