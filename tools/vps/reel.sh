#!/usr/bin/env bash
# The ONE way a reel's Claude session on the VPS runs reel code (Harsh, 25 Oct 2026: "use claude on VPS"): the reel Python
# (~/dtj/reel-venv: opencv, LaMa, Whisper, playwright), from services/reel-factory, at low CPU priority so n8n stays fast.
# .claude/vps-settings.json allows only "bash tools/vps/reel.sh ..." for reel code, so what runs is exactly this list:
#   bash tools/vps/reel.sh job <stage> --job <dir> [...]        python -m reel_factory.job (new refs lint ... edit result)
#   bash tools/vps/reel.sh remake <tool> [args]                 tools/remake/<tool>.py: measure_motion recut fixpack clean_brand fetch reference
#   bash tools/vps/reel.sh sparkle <raw.mp4> <clean.mp4>        Flow's sparkle removed (reel_factory.watermark.Remover)
#   bash tools/vps/reel.sh slop <script.json> [--style <style.json>]
#   bash tools/vps/reel.sh check                                what is ready (venv, Chrome on 9222, fonts)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${DTJ_REEL_PYTHON:-$HOME/dtj/reel-venv/bin/python}"
RF="$ROOT/services/reel-factory"
run() { cd "$RF" && exec nice -n 10 "$PY" "$@"; }
[ -x "$PY" ] || { echo "reel python missing: $PY (run tools/vps/setup_reel.sh)"; exit 2; }
cmd="${1:-}"; shift || true
case "$cmd" in
  job) run -m reel_factory.job "$@" ;;
  remake)
    tool="${1:-}"; shift || true
    case "$tool" in
      measure_motion|recut|fixpack|clean_brand|fetch|reference) run "tools/remake/$tool.py" "$@" ;;
      *) echo "unknown remake tool: $tool"; exit 2 ;;
    esac ;;
  sparkle)
    [ $# -eq 2 ] || { echo "usage: reel.sh sparkle <raw.mp4> <clean.mp4>"; exit 2; }
    run -c 'import json, sys; from reel_factory.watermark import Remover; print(json.dumps(Remover().clip(sys.argv[1], sys.argv[2])))' "$1" "$2" ;;
  slop) run -m reel_factory.slop "$@" ;;
  watch) run -m reel_factory.watch "$@" ;;
  check)
    "$PY" -c "import cv2, numpy, simple_lama_inpainting; print('reel python ok')" 2>&1 | tail -1
    python3 -c "import json, urllib.request; print('reel chrome ok:', json.load(urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=5))['Browser'])" 2>&1 | tail -1
    fc-list 2>/dev/null | grep -qi "noto sans gujarati" && echo "fonts ok" || echo "fonts MISSING (fonts-noto-core)" ;;
  *) echo "usage: reel.sh job|remake|sparkle|slop|check ..."; exit 2 ;;
esac
