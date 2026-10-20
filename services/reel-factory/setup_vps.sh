#!/usr/bin/env bash
# Set up the reel VPS (Ubuntu 22.04/24.04 with a desktop: Chrome, ChatGPT and Flow need a real, logged-in browser window).
#   bash services/reel-factory/setup_vps.sh          install everything (asks for sudo)
#   bash services/reel-factory/setup_vps.sh --check  only report what is there
# After it: open the reel Chrome with  ~/dtj/reel-chrome.sh  and a PERSON signs in once to Google (Flow) and ChatGPT in it.
# No password or key is ever typed by this script or stored by it.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HOME/dtj/reel-venv"
CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1

have() { command -v "$1" >/dev/null 2>&1; }
report() {
  for t in ffmpeg ffprobe node npx google-chrome; do printf '%-14s %s\n' "$t" "$(have "$t" && echo ok || echo MISSING)"; done
  printf '%-14s %s\n' "reel python" "$([ -x "$VENV/bin/python" ] && echo ok || echo MISSING)"
  [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import torch, whisper, cv2, simple_lama_inpainting, playwright; print('python libs   ok; GPU:', torch.cuda.is_available())" || true
  printf '%-14s %s\n' "captions" "$([ -d "$HERE/captions-remotion/node_modules" ] && echo ok || echo 'MISSING (npm ci)')"
}
if [ $CHECK = 1 ]; then report; exit 0; fi

sudo apt-get update
sudo apt-get install -y ffmpeg python3-venv python3-pip curl git fonts-noto-core
if ! have node || [ "$(node -v | cut -c2- | cut -d. -f1)" -lt 22 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs
fi
if ! have google-chrome; then
  curl -fsSLo /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo apt-get install -y /tmp/chrome.deb && rm /tmp/chrome.deb
fi

mkdir -p "$HOME/dtj"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
if have nvidia-smi; then "$VENV/bin/pip" install torch --index-url https://download.pytorch.org/whl/cu128
else echo "No NVIDIA GPU: CPU torch (Whisper and LaMa will be slow: minutes per clip)"; "$VENV/bin/pip" install torch --index-url https://download.pytorch.org/whl/cpu; fi
"$VENV/bin/pip" install -r "$HERE/requirements.txt"
(cd "$HERE/captions-remotion" && npm ci)

cat > "$HOME/dtj/reel-chrome.sh" <<'EOF'
#!/usr/bin/env bash
# The reel Chrome: its own profile (Google + ChatGPT stay signed in), reachable by reel_factory on 127.0.0.1:9222 only.
exec google-chrome --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1 --user-data-dir="$HOME/dtj/chrome-reel" \
  --no-first-run --start-maximized https://flow.google.com/ https://chatgpt.com/ "$@"
EOF
chmod +x "$HOME/dtj/reel-chrome.sh"
report
echo "Next: run ~/dtj/reel-chrome.sh on the VPS desktop and sign in to Google (Flow) and ChatGPT once, by hand."
