#!/usr/bin/env bash
# The reel watcher at one gate (skill dtj-reel-watcher; Harsh 25 Oct 2026: "a watcher ... as me or better me or an expert in
# video production"):  bash tools/vps/watcher.sh <a0|g0|g1|g2|g3|g4|g5> <job dir> [round]
# 1. measured checks: reel_factory.watch <gate> -> <job>/watch/<gate>.json (+ g2_pairs.jpg / sheets)
# 2. judge 1: a FRESH Claude session (no maker transcript, read-only settings .claude/watcher-settings.json)
# 3. judge 2: Codex (GPT, another model family: judges grading their own family's work score it too kindly) with the pictures
# 4. merge: the stricter verdict wins, blocking issues and ideas from both -> <job>/watch/<gate>.verdict.json, one line printed
# A judge that is not installed or not logged in is skipped and named in the verdict (never a made-up opinion).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
gate="${1:-}"; job="${2:-}"; rnd="${3:-1}"
case "$gate" in a0|g0|g1|g2|g3|g4|g5) ;; *) echo '{"error": "gate must be a0 g0 g1 g2 g3 g4 g5"}'; exit 2 ;; esac
[ -d "$job" ] || { echo "{\"error\": \"no job folder: $job\"}"; exit 2; }
job="$(cd "$job" && pwd)"; W="$job/watch"; mkdir -p "$W"
PY="${DTJ_REEL_PYTHON:-$HOME/dtj/reel-venv/bin/python}"; [ -x "$PY" ] || PY="python3"
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$PATH"

# 1. measured
case "$gate" in g1|g2|g3|g4) (cd "$ROOT/services/reel-factory" && nice -n 10 "$PY" -m reel_factory.watch "$gate" --job "$job" > "$W/$gate.measured.txt" 2>&1) ;; esac

SKILL="$ROOT/.claude/skills/dtj-reel-watcher"
RUBRIC=$(ls "$SKILL/references/" | grep -i "rubric-$gate-" | head -1); [ "$gate" = "a0" ] && RUBRIC="audience-intelligence.md"
ASK="You are the reel watcher (skill dtj-reel-watcher). Gate: $gate, round $rnd. Job folder: $job.
Read $SKILL/SKILL.md, then $SKILL/references/$RUBRIC and $SKILL/references/golden-set.md, then the job's files the rubric names
and $W/$gate.json if it exists (measured numbers). You did not make this work; judge only what is in front of you. Answer with
ONE JSON object exactly as SKILL.md says (gate, round, judge, score, verdict, blocking, issues, ideas, for_person) and nothing else."

# 2. Claude, fresh
if command -v claude >/dev/null 2>&1; then
  (cd "$ROOT" && env -u ANTHROPIC_API_KEY timeout 1800 claude -p --output-format json --permission-mode dontAsk \
     --settings "$ROOT/.claude/watcher-settings.json" <<<"$ASK" > "$W/$gate.claude.raw" 2>"$W/$gate.claude.err")
else echo '{"skipped": "claude not installed"}' > "$W/$gate.claude.raw"; fi

# 3. Codex, with the pictures of this gate
imgs=()
for f in "$W/g2_pairs.jpg" "$W"/sheet_*.jpg "$job"/checks/*_4fps.jpg; do [ -s "$f" ] && imgs+=(-i "$f"); done
if command -v codex >/dev/null 2>&1; then
  tmp=$(mktemp -d /tmp/dtj-watch-XXXXXXXX)
  (cd "$tmp" && timeout 900 codex exec --skip-git-repo-check -s read-only "${imgs[@]}" -- \
     "$(printf '%s\n\nRUBRIC:\n%s\n\nGOLDEN SET:\n%s\n\nMEASURED:\n%s\n\nUse judge "codex". Answer ONLY the JSON object.' \
        "$(sed -n '/^## Your answer/,/^## Calibration/p' "$SKILL/SKILL.md")" "$(cat "$SKILL/references/$RUBRIC")" \
        "$(cat "$SKILL/references/golden-set.md")" "$(cat "$W/$gate.json" 2>/dev/null | head -c 20000)")" \
     > "$W/$gate.codex.raw" 2>&1 < /dev/null)
  rm -rf -- "$tmp"
else echo '{"skipped": "codex not installed"}' > "$W/$gate.codex.raw"; fi

# 4. merge
(cd "$ROOT/services/reel-factory" && "$PY" -m reel_factory.watch merge --job "$job" --of "$gate" --round "$rnd")
