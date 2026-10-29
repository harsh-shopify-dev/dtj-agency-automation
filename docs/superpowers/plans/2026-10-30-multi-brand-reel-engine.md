# Multi-brand reel engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One shared n8n "Reel Engine" (Champfuel pattern) plus a small "Reel: <Brand>" workflow per brand that make a reel from a
brand's brief and per-style references: Gemini script, Codex pictures, a person's change loop, Flow clips, Claude QC and edit.

**Architecture:** A new stdlib-HTTP service `services/reel-engine` (Docker box `reel-engine:8091` beside `brand-engine`, same image
and login folders) runs one stage per call. n8n only orders stages, loops on the person's answer and saves to Drive. Stage code
reuses `services/reel-factory` (lint, checks, edit, watermark) and its Telegram side `n8n/reel-factory/reel_job.py`.

**Tech Stack:** Python 3.11 stdlib (`http.server`, `subprocess`, `unittest`), Gemini CLI, Codex CLI, Claude Code CLI, Playwright
over CDP (Flow), n8n Workflow SDK via the n8n MCP server, Node for Code-node tests.

**Spec:** `docs/superpowers/specs/2026-10-30-multi-brand-reel-engine-design.md`

## Global Constraints
- A person is watching every run: the engine refuses `stage` calls for a run without `watcher` set (rule 9).
- Claims: every number/result word in a script must be in the brand's `facts.md` (reuse `reel_factory.job.lint_script`).
- Flow: Omni Flash, 9:16, 2 takes per scene, product never moved inside a clip, start frame picked by asset id.
- Final: 1080x1920, 30 fps, -14 LUFS, TP -1.5, 48 kHz stereo AAC; captions at the bottom mark (~69%).
- One reel run at a time in the box; a second call gets `{"ok": false, "busy": true}`.
- No secrets in code, workflow JSON or logs; logins only through the mounted folders (`HOME`, `CODEX_HOME`, `/gemini-home`, `/claude-home`).
- Nothing posted; nothing deleted (every picture/clip version kept under the run folder).
- **Deviation from the spec, decided here:** the person's taps are read by polling (`review` stage, every 60 s from n8n) through the
  existing `reel_job.py` + `dtj_bot_answers`, instead of a new resume-link path in the Hermes plugin. Same result, no plugin change.

## Review Focus
1. Person answers "3, 5: diya too small" -> only scenes 3 and 5 are redrawn; other scene files untouched (test in Task 4).
2. A CLI prints a sign-in/quota page instead of output -> stage answers `needs_person: true`, never "ok" (test in Task 3).
3. Brand with fewer than 3 references for the style -> the niche library is used; none at all -> clear refusal (test in Task 2).
4. n8n retries a stage call that already finished -> the stage returns the saved result, no second Flow spend (test in Task 2).
5. Gemini returns script JSON wrapped in prose or code fences -> parsed; invalid JSON -> one retry then a plain error (test in Task 3).

---

### Task 1: Feasibility checks on the VPS (no code kept, no money spent)

**Files:** Create: `docs/ugc-reels/2026-10-30-engine-checks.md` (results only)

- [ ] **Step 1:** In `n8n-brand-engine-1` (Hostinger Terminal or `ssh ai@187.126.122.133` + `docker exec`), with `HOME=/gemini-home`:
  `gemini -m gemini-3.1-pro -p "Describe shot by shot: @/tmp/ref.mp4"` on one reference reel. Pass = a shot list with times.
- [ ] **Step 2:** Same box, `HOME`/`CODEX_HOME` as brand-engine: `codex exec` asking GPT Image for one 9:16 scene with a product photo
  attached. Pass = a PNG with our pack recognisable.
- [ ] **Step 3:** From the box, `curl http://host.docker.internal:9222/json/version` (add `extra_hosts: host.docker.internal:host-gateway`
  only after Harsh's yes). Pass = Chrome answers.
- [ ] **Step 4:** `free -m` and `docker stats --no-stream` while Chrome has Flow open. Write the numbers and the chosen `mem_limit`.
- [ ] **Step 5:** Write the four results (pass/fail + exact command) in the doc; commit. A fail in 1 or 2 switches that model in
  Task 3 to the browser route (`reel_factory.chatgpt_cli` / Gemini in Chrome); the stage interface stays.

### Task 2: Engine core: brands, runs, HTTP server

**Files:**
- Create: `services/reel-engine/engine/{__init__,brands,runs,server}.py`, `services/reel-engine/README.md`
- Test: `services/reel-engine/tests/test_core.py`

**Interfaces (produces):**
- `brands.Brand(root: Path, name: str)`: `.brief -> str`, `.facts -> str`, `.products -> list[Path]`,
  `.references(style: str, niche_root: Path) -> list[Path]` (brand's own if >= 3, else plus `Niches/<niche>/<style>/`; raises
  `NoReferences` when empty), `.style_card_path(style) -> Path`, `.niche -> str` (from `brand.json`).
- `runs.Run(root: Path, brand: str, run: str)`: `.dir`, `.state -> dict`, `.save()`, `.done(stage) -> dict | None`,
  `.record(stage, result: dict)`.
- `server.handle(body: dict, ctx) -> tuple[int, dict]`; `POST /stage`, `GET /outputs?brand&run`, `POST /files?brand&path` (binary in,
  for the Drive sync). `ctx.stages: dict[str, Callable[[Run, Brand, dict], dict]]`, `ctx.lock`.

- [ ] **Step 1: Tests:** `test_refs_fall_back_to_niche` (2 own + niche 3 -> 5), `test_refs_none_raises`, `test_stage_retry_returns_saved`
  (a stage recorded `done` is not called again; the saved dict is returned with `"cached": true`), `test_busy_when_locked`
  (`{"ok": False, "busy": True}`, 409), `test_refuses_without_watcher` (400, `"watcher"` in error), `test_files_path_cannot_escape`
  (`../x` -> 400).
- [ ] **Step 2:** `python -m unittest discover services/reel-engine/tests` -> FAIL (no module).
- [ ] **Step 3:** Implement. Folder layout: `<root>/brands/<brand>/{brand.json,brief.md,facts.md,products/,references/<style>/,style-cards/}`,
  `<root>/runs/<brand>/<run>/state.json`. Port from `REEL_ENGINE_PORT` (default 8091).
- [ ] **Step 4:** Tests PASS. **Step 5:** Commit `reel-engine: brands, runs, stage server`.

### Task 3: Model wrappers (Gemini, Codex, Claude)

**Files:** Create `services/reel-engine/engine/models.py`; Test `services/reel-engine/tests/test_models.py`

**Interfaces (produces):** `gemini(prompt: str, files: list[Path], run=subprocess.run) -> str`;
`gemini_json(prompt, files, run=...) -> dict` (strips fences/prose, one retry, else `ModelError`);
`codex_image(prompt: str, refs: list[Path], out: Path, run=...) -> Path`; `claude_json(prompt: str, files: list[Path], run=...) -> dict`.
All raise `NeedsPerson` when output matches a sign-in/quota/captcha pattern (`login|sign in|quota|rate limit|captcha|verify`), set
`HOME` per tool from env (`GEMINI_HOME`, `CODEX_HOME`, `CLAUDE_HOME`), timeout 900 s.

- [ ] **Step 1: Tests** with a fake `run`: `test_json_in_fences_parsed`, `test_bad_json_retried_once_then_error` (fake called twice),
  `test_signin_text_is_needs_person`, `test_codex_image_missing_file_is_error`, `test_env_home_per_tool`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement (exact CLI flags from Task 1's doc). **Step 4:** PASS. **Step 5:** Commit.

### Task 4: Stages

**Files:** Create `services/reel-engine/engine/stages.py`, `services/reel-engine/playbooks/{ugc,cinematic,founder}.md`,
`services/reel-engine/GEMINI.md`; Test `services/reel-engine/tests/test_stages.py`

**Interfaces:** consumes Tasks 2-3, `reel_factory.job.lint_script(script, facts) -> list[str]`, `reel_factory.flow_cli.clip(...)` (Task 5),
`reel_factory.edit.render(plan) -> dict`, `n8n/reel-factory/reel_job.py` commands. Produces stage names and results:
- `take {request, style, watcher}` -> `{run, scenes: 0}`
- `style_card` -> `{card: path, cached: bool}` (rebuilt when any reference is newer than the card)
- `script` -> `{script: path, scenes: n}`; script.json uses reel-factory's shape plus `scenes[].image_prompt`; lint errors -> `ok: false`
- `pictures {only?: [ids]}` -> `{pictures: {id: path}, redrawn: [ids]}`; Claude score < 7/10 -> redraw, max 2 per scene
- `review {gate: "pictures"|"final", round}` -> `{waiting: true}` | `{approved: true, by}` | `{approved: false, by, note, scenes: [ids], about: "words"|"pictures"|"edit"}`
- `clips {only?}` -> `{clips: {id: path}, needs_look: [ids]}`; `edit` -> `{final: path, seconds}`; `result` -> reply_body shape.

- [ ] **Step 1: Tests** (fake models, fake reel_job): `test_change_note_redraws_only_named_scenes` (scenes 3,5 new mtime; 1,2,4 unchanged),
  `test_note_about_words_routes_to_script`, `test_lint_failure_stops_script`, `test_style_card_reused_when_refs_unchanged`,
  `test_review_waiting_until_answer`, `test_clips_needs_look_after_3_rounds`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement; playbooks written from `docs/ugc-reels/` lessons (one page each). **Step 4:** PASS.
- [ ] **Step 5:** Commit `reel-engine: stages and style playbooks`.

### Task 5: `flow_cli` (Flow like `chatgpt_cli`)

**Files:** Create `services/reel-factory/reel_factory/flow_cli.py`; Test `services/reel-factory/tests/test_flow_cli.py`

**Interfaces (produces):** `clip(image: Path, prompt_file: Path, out_dir: Path, seconds: int = 8, takes: int = 2, cdp=CDP_DEFAULT,
attach=None) -> tuple[int, dict]` -> `{"ok": true, "files": [...], "credits": int|None, "seconds": float}`; exit 1 + `needs_person`
on `flow.NeedsPerson`, exit 2 when Chrome does not answer. CLI: `python -m reel_factory.flow_cli clip --image --prompt-file --out
[--seconds 8] [--takes 2]`. Uses `Flow.settings("ingredients", "9:16", takes, seconds=...)`, `upload`, `attach(asset_id)`,
`generate`, `video_url`, `download`; refuses `seconds` not in (4, 6, 8, 10); each saved clip's first frame compared with `image`.

- [ ] **Step 1: Tests** (fake Flow, like `test_chatgpt_cli.py`): `test_ok_json`, `test_bad_seconds_refused`, `test_needs_person`,
  `test_chrome_down_exit_2`, `test_attaches_by_asset_id_not_position`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit `reel-factory: flow_cli`.

### Task 6: n8n workflows

**Files:** Create `n8n/reel-engine/{deploy_engine.py,engine.workflow.json,brand.workflow.json,sync.workflow.json,tables.json}`,
Code nodes `n8n/reel-engine/{route_answer,group_files}.js`; Test `n8n/reel-engine/test_engine_nodes.py`

- **Reel Engine** (Execute Workflow Trigger): stage HTTP nodes named exactly `0 [NO AI] Take request`, `1 [GEMINI] Style card`,
  `2 [GEMINI] Script + scenes`, `3 [CHATGPT + CLAUDE] Scene pictures`, `4 [PERSON] Approve script + pictures` (HTTP `review` ->
  `Answered?` -> Wait 60 s loop), `Route answer` (Code: words -> 2, pictures -> 3 with `only`), `5 [FLOW + CLAUDE] Clips`,
  `6 [CLAUDE] Edit`, `7 [PERSON] Approve final`, `8 [NO AI] Save to Drive` (list outputs -> Drive folder -> upload, Champfuel's
  groups-of-2 pattern, never executeOnce on the upload), `Record` (dtj_reel_jobs), `Tell the requester`. HTTP: 1 h timeout, 3 retries.
- **Reel: <Brand>** template: `When called by Hermes` / `Run now` -> `Run settings` (brand, style default, language, drive folder)
  -> `Reel Engine` (wait). `deploy_engine.py --brand <slug>` creates one; tables row in `dtj_brands_reels`.
- **Reel: Sync brand from Drive**: lists the brand's Drive folder, downloads new files, `POST /files`.
- [ ] **Step 1: Tests:** `route_answer.js`: words note -> `{next: "script"}`, `"3, 5: ..."` -> `{next: "pictures", only: ["s3","s5"]}`,
  final-gate note -> `{next: "edit"}`; `group_files.js` 5 files -> 3 groups.
- [ ] **Step 2:** FAIL. **Step 3:** Implement; deploy script follows `n8n/reel-factory/deploy_reel.py` (`--dry-run`, read back, export).
- [ ] **Step 4:** PASS; `deploy_engine.py --dry-run` prints valid SDK code (n8n `validate_workflow`). **Step 5:** Commit.
- [ ] **Step 6 (Harsh's yes):** deploy unpublished; publish after the first live run.

### Task 7: Telegram (Hermes) `/reel <brand> <style> <brief>`

**Files:** Modify `tools/hermes/dtj.py` (`handle` route), `tools/hermes/skills/dtj-reels/SKILL.md`; Test `tools/hermes/test_dtj.py`
- [ ] Tests: `test_reel_brand_runs_brand_workflow` (finds "Reel: <Brand>" by `dtj_brands_reels.workflow_id`, passes style + brief +
  user), `test_unknown_brand_lists_brands`, `test_unknown_style_lists_styles`. FAIL -> implement -> PASS -> commit.

### Task 8: Box on the VPS + dry run

**Files:** Create `services/reel-engine/compose-snippet.yml`, `services/reel-engine/tests/test_dry_run.py`; Modify `docs/ugc-reels/HANDOFF-ai-ugc.md`
- [ ] **Step 1:** `test_dry_run`: whole stage sequence with fake models/Flow/reel_job on a fixture brand -> `final` exists, state shows
  every stage once, a change round redraws only named scenes.
- [ ] **Step 2:** Compose snippet: `reel-engine` service, image `n8n-royal-dosa:latest`, volumes `./reel-engine:/app`, `rd_claude_auth:/claude-home`
  (or `claude_auth`, from Task 1), `/home/ai/.codex`, `/home/ai/codex-accounts`, `/home/ai/gemini-home`, `./reel-engine-data:/data`,
  `extra_hosts`, `mem_limit` from Task 1. Edit the server's compose by SSH, never the Hostinger editor's Deploy (its YAML check fails).
- [ ] **Step 3 (Harsh's yes):** add the box; `curl reel-engine:8091/outputs` from `n8n-n8n-1`.
- [ ] **Step 4 (Harsh's yes, spends Flow credits):** one cinematic reel for one brand, watched; write credits used and results in the handoff.
- [ ] **Step 5:** Commit, push, PR.
