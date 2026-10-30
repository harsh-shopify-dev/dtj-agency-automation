# DTJ reel engine (multi-brand)

One reel automation for every brand and style (UGC, cinematic, founder), built like Champfuel's creative engine: n8n's
**Reel Engine** calls this service once per step; each brand has a small **Reel: <Brand>** workflow. A person watches every run
and approves in Telegram. Nothing is posted. Spec: `docs/superpowers/specs/2026-10-30-multi-brand-reel-engine-design.md`;
VPS checks: `docs/ugc-reels/2026-10-30-engine-checks.md`.

| Step (n8n node) | Tool (login on the VPS host) | What |
|---|---|---|
| 0 [NO AI] Take request | - | checks the brand folder, starts the Telegram thread |
| 1 [GEMINI] Style card | `agy`, Gemini 3.8 Flash High (`/home/ai/gemini-home`) | watches the brand's references of the style once |
| 2 [GEMINI] Script + scenes | `agy` | script in reel-factory's shape; claims checked against `facts.md` |
| 3 [CHATGPT + CLAUDE] Scene pictures | Codex + GPT Image (ChatGPT Plus, `CODEX_HOME`), Claude Code | below 7/10 redrawn (max 2) |
| 4 [PERSON] Approve script + pictures | `n8n/reel-factory/reel_job.py` (reel bot) | Approve, or "3, 5: ..." redraws only those scenes |
| 5 [FLOW + CLAUDE] Clips | `reel_factory.flow_cli` (Flow, Ultra plan, logged-in Chrome), Claude | 2 takes per scene, max 3 rounds; **spends Flow credits** |
| 6 [CLAUDE] Edit | reel-factory `edit` | trims, beats, captions, -14 LUFS |
| 7 [PERSON] Approve final reel | `reel_job.py` | Approve; "2: ..." -> those clips again; any other note ends as "needs a look" with the note |
| 8 [NO AI] Result | - | reel ready / needs a look, file path, credits |

## A brand's folder (on the VPS host)
`/home/ai/reel-engine/brands/<brand>/`: `brand.json` (`{"name", "niche", "product_name", "default_style"}`), `brief.md`, `facts.md`
(the only claims allowed), `products/` (real pack photos), `references/<style>/` (winning reels), optional `music/` (licensed).
Shared niche references: `/home/ai/reel-engine/Niches/<niche>/<style>/` (used when a brand has fewer than 3 of its own).
Fill it with the VPS **File Browser** app or `POST http://172.16.1.1:8091/files?brand=<brand>&path=<relative path>` (body = the file).

## A new brand
1. Make its folder as above.
2. `python n8n/reel-engine/deploy_engine.py --brand <slug> --name "<Brand Name>" --style cinematic` (creates "Reel: <Brand Name>").
3. In Telegram (Hermes): `make <slug> cinematic <what the reel is about>`.

## Run / test
- Tests: `cd services/reel-engine && python -m unittest discover -s tests -t .` (fake models, Telegram and Flow).
- Service: `reel-engine.service` (systemd, user `ai`, port 8091 on 172.16.1.1). `GET /health`, `POST /stage`, `GET /outputs`.
  It needs `/home/ai/.config/dtj/reel-engine.env` holding `DTJ_REEL_BOT_TOKEN` (the Hermes reel bot's token) for the Telegram approvals.
- One reel at a time: a new request is refused in Telegram while another runs (a run quiet for 6 h, stopped by a failure, or
  unanswered for 2 days no longer blocks).
- A failed step answers 422: the n8n run stops at that node and the person is told in Telegram. Fix, then **Retry** the node in n8n.
  Repeating the same call returns the saved answer (no second Flow spend); a new round, note or scene list runs again.

## Not built yet
Drive sync of brand folders and saving finished reels to Drive; a row in `dtj_reel_jobs` per reel.
