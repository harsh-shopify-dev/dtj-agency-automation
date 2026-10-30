# Reel engine: checks on the VPS (30 Oct 2026)

| # | Check | Result | Exact command / evidence |
|---|---|---|---|
| 1 | Gemini watches a reel | **Pass, with the Antigravity CLI.** The old Gemini CLI login is refused by Google ("no longer supported for Gemini Code Assist for individuals"). `agy` with the same Google login (`/home/ai/gemini-home`) watched a 31 s reel: 9 shots with times, framing, spoken and on-screen words, in 43 s. This login lists only Gemini 3.8 Flash (High/Medium/Low); no Pro model. | `HOME=/home/ai/gemini-home /home/ai/gemini-home/.local/bin/agy --model gemini-3.8-flash-high -p "@ref.mp4 Open this video with your file viewer (do not run shell commands). ..." --output-format json`, run in the folder holding the file. Without `@file` it tries a shell command and is denied. |
| 2 | Codex draws with our product photo | **Pass by production evidence** (no quota spent): Champfuel's `brand-engine/05_scripts/generate_image.py` makes its ads this way every day. | `codex exec --skip-git-repo-check -s danger-full-access -C <work> -m gpt-6.1-sol --image=<pack.png> -- "<prompt>"` with `CODEX_HOME=/home/ai/codex-accounts/plus-3` (ChatGPT Plus); the picture appears in `$CODEX_HOME/generated_images/<session id>/*.png` |
| 3 | Reach the Flow Chrome | **Pass on the host only.** Chrome listens on `127.0.0.1:9222` (host); the Docker boxes cannot reach it. The host also has ffmpeg, Claude Code, Codex, `agy` and the repo venv with Playwright (`/home/ai/dtj-agency-automation/.venv`). | `curl 127.0.0.1:9222/json/version` -> Chrome 156 |
| 4 | Memory | 7.9 GB total, ~5.5 GB available with Chrome open (Chrome ~1 GB, n8n ~0.6 GB). 2 vCPU. Firewall (ufw) inactive. | `free -m`, `ps -eo rss,comm` |

Decisions from these checks:
- The Gemini steps use `agy` (Gemini 3.8 Flash High), not the old Gemini CLI.
- The engine runs **on the host as the `ai` user** (a systemd service like the reel worker), bound to `172.16.1.1:8091`, the gateway
  of n8n's Docker network, so it is not on the public address. Not a Docker box: Chrome, ffmpeg and Playwright are on the host.
- Codex runs with `OPENAI_API_KEY` removed from its environment, so it can only use the ChatGPT login (never paid API credits).

Left on the VPS from these checks (to remove): `/home/ai/gemini-home/work/check/ref.mp4`, `/tmp/agy.out`, Docker image `curlimages/curl:8.10.1`.
