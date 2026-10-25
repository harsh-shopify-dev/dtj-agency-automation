#!/usr/bin/env bash
# One picture made by Codex (OpenAI's command-line tool, logged in with DTJ's ChatGPT account) on DTJ's VPS, the way
# ~/work/run-ref.sh makes them (Harsh, 22 Oct 2026: "we will use chatgpt cli which will be hosted on our hostinger vps ... where
# you have to upload the referennce images of our products"). Used by services/store-builder/provision/ai_images.py: directly on
# the VPS (the "codex" way) or over ssh from a laptop (the "vps" way).
#     bash tools/vps/codex_image.sh --prompt-file <txt> --out <png> [--ref <photo of our product> ...] [--timeout 600]
# Prints one JSON line: {"ok": true, "path": <out>, "seconds": N} or {"ok": false, "error": "..."}; exit 0 / 1.
# CODEX_HOME picks the Codex account (default ~/.codex). Works in its own /tmp/dtj-codex-* folder and removes only that.
# Every path is made absolute first: Codex runs inside that folder, where a relative path finds nothing (23 Oct 2026, brief 12:
# three pictures failed with "Please reattach the product photo" after a --ref ../../.work/... passed the check here).
set -uo pipefail
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"

fail() { python3 -c 'import json, sys; print(json.dumps({"ok": False, "error": sys.argv[1][:400]}))' "$1"; exit 1; }

prompt="" out="" timeout=600 refs=()
while [ $# -gt 0 ]; do
  case "$1" in
    --prompt-file) [ -n "${2:-}" ] && prompt="$(realpath -m -- "$2")"; shift 2 ;;
    --out) [ -n "${2:-}" ] && out="$(realpath -m -- "$2")"; shift 2 ;;
    --ref) ref=""; [ -n "${2:-}" ] && ref="$(realpath -m -- "$2")"
           [ -s "$ref" ] || fail "reference photo missing: ${2:-}"; refs+=(-i "$ref"); shift 2 ;;
    --timeout) timeout="${2:-600}"; shift 2 ;;
    *) fail "unknown argument: $1" ;;
  esac
done
[ -s "$prompt" ] || fail "no prompt file"
[ -n "$out" ] || fail "no --out"
command -v codex >/dev/null || fail "codex is not installed for $(id -un)"

work=$(mktemp -d /tmp/dtj-codex-XXXXXXXX) || fail "no temp folder"
trap 'rm -rf -- "$work"' EXIT
start=$(date +%s)
(cd "$work" && timeout "$timeout" codex exec --skip-git-repo-check -s workspace-write "${refs[@]}" -- "$(cat "$prompt")" \
  > "$work/run.log" 2>&1 < /dev/null)
code=$?
sid=$(grep -m1 'session id:' "$work/run.log" | awk '{print $3}')
img=""
[ -n "$sid" ] && img=$(ls -t "${CODEX_HOME:-$HOME/.codex}/generated_images/$sid"/*.png 2>/dev/null | head -1)
[ -n "$img" ] || fail "no picture from codex (exit $code): $(tail -3 "$work/run.log" | tr '\n' ' ')"
cp "$img" "$out" || fail "could not save the picture to $out"
python3 -c 'import json, sys; print(json.dumps({"ok": True, "path": sys.argv[1], "seconds": int(sys.argv[2])}))' "$out" "$(( $(date +%s) - start ))"
