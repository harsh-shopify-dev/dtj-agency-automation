# SEO engine map (checked against the code, 19 Oct 2026)

Engine: `services/seo-engine/seo_engine/` (data in `seo_engine/data/`, prompts in `seo_engine/prompts/`). Run engine commands
from `services/seo-engine/`. Tests: `python -m unittest discover -s tests` (52 tests; needs `jsonschema`, not `anthropic`).

## Contents
1. Commands  2. Files a run writes  3. JSON shapes  4. Settings and tiers  5. GitHub workflows  6. Functions without a CLI
7. Data files  8. Skill scripts

## 1. Commands
| Command | Cost | What it does |
|---|---|---|
| `python -m seo_engine.run_weekly` | free (fetches the live sitemap, max 80 pages) | site check, fixes batch, city grid, report |
| `... --live` | Claude + DataForSEO, if the keys exist (a missing key skips that step with a note) | + keyword plan (if missing or 28+ days old), AI-assistant probe, page of the week |
| `... --live --refresh-keywords` | DataForSEO, capped by `DFS_MAX_USD` | rebuild the keyword plan now |
| `... --out PATH --max-pages N --probe-limit N` | | defaults `.work/seo`, 80, 10 |
| `python -m seo_engine.apply_batch --batch <fixes.json> --approved-by "<name>" [--only c001,c004]` | Tier 2 | apply the `auto` changes |
| `python -m seo_engine.apply_batch --undo <applied-*.json> --approved-by "<name>"` | Tier 2 | put the old values back |

`apply_batch` refuses without a name, with the kill switch off or with dry run on. It skips a change when the live page no
longer shows the "before" value, skips alt text that already exists, saves an undo value per field, and checks the live page
up to 3 times, 20 s apart. Statuses: `verified`, `not visible yet`, `skipped`, `failed`. Undo reverses only verified / not
visible yet.

## 2. Files a run writes
Dated folder `.work/seo/<YYYY-MM-DD UTC>/`: `scan.json`, `fixes.json`, `aeo.json`, `city_matrix.json`, `report.md` (always);
`keyword_plan.json` (when refreshed); `top3.json` (with DataForSEO and a topic); `draft.json` (with a topic); `draft.html`
(gate passed); `applied-<batch_id>.json` (written by apply_batch).
Root `.work/seo/`: `actions.jsonl` (action log), `state.json` (`written` topic ids, `last_kind`), `keyword_plan.json`,
`city-pages/<topic>.txt` (for the doorway-page similarity check).
The GitHub run uploads `.work/seo/` as artifact `seo-report` (kept 90 days); applied batches as `seo-applied` (365 days).

## 3. JSON shapes
- **fixes.json**: `id` ("fix-YYYY-MM-DD"), `made_at`, `site`, `source`, `changes[]`, `notes[]`, `counts{auto, blocked, manual}`.
  Change: `cid`, `kind` (`noindex`, `meta_description`, `seo_title`, `alt_text`, `site_jsonld`, `manual`), `url`, `before`,
  `after`, `reason`, `how` (`auto`|`blocked`|`manual`), plus `blocks[]`, `media_id`/`src` (alt text), `rule`/`pages` (manual).
- **scan.json**: `site`, `scanned_at`, `pages_in_sitemap`, `pages[]` (url, status, title, description, robots, canonical, h1,
  questions, schema_types, words, img_total, img_no_alt, …), `findings[]` (severity high|medium|low, rule, page, evidence,
  fix), `counts`, `source`.
- **keyword_plan.json**: `made_at`, `source`, `filters`, `ideas`, `kept`, `rejected{reason: n}`, `cost_usd`, `clusters[]`
  (id, slug, type `tide` = blog / `boat` = service or city page, main, keywords[], volume_sum, avg_kd, max_cpc, priority,
  place, tier, service, grouped_by_google, meets_target, top_urls).
- **aeo.json**: dry run `{mode: "dry-run", planned[], results: []}`; live adds `summary{asked, answered, dtj_named, dtj_cited,
  by_engine{…}, top_cited_sites}`. Each result: question, place, engine, status, answer, dtj_named, dtj_cited, cited_hosts.
  Named = the answer contains "Digital Tushar Joshi", "DTJ" or the domain; cited = a source on digitaltusharjoshi.com (decided by code).
- **draft.json**: topic_id, status (`not-run`, `passed`, `blocked`, `refusal`, `cut-off`, `api-error`, `bad-json`), model,
  usage, cost_usd, gate{ok, blocks, warnings, words}, article.
- **article** (`writer.SCHEMA`): title, slug, meta_description, short_answer, sections[{heading, paragraphs[]}],
  faq[{question, answer}], facts_used[], internal_links[{url, anchor}], sources[{url, title}].
- **applied-<id>.json**: batch_id, site, approved_by, approved_at, results[{cid, kind, url, after, status, why?, undo_value, …}], counts.
- **actions.jsonl** row: ts, run_id, client_id "dtj", automation "seo-engine", tier, mode, target, action, reason, result
  (recommended|dry_run|blocked|success|failed), optional evidence/before/after/approved_by/error. Secrets are redacted.

## 4. Settings and tiers (`config.py`, environment variables only)
| Variable | Default | |
|---|---|---|
| `AUTOMATION_ENABLED` | off | kill switch |
| `SEO_DRY_RUN` | on | |
| `SEO_MODE` | `shadow` | `approve` lets new pages become WordPress drafts |
| `SEO_SITE` | `https://digitaltusharjoshi.com` | |
| `WP_USER`, `WP_APP_PASSWORD` | none | a WordPress **Editor**'s application password |
| `ANTHROPIC_API_KEY` | none | the writer, the alt-text step, the Claude probe |
| `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` | none | keywords, Google top 10, ChatGPT/Perplexity/Gemini answers |
| `DFS_MAX_USD` | 3.00 | DataForSEO cap per run (adds up the cost each answer states) |
| `OPENAI_API_KEY` | none | pictures only (skill script `blog_image.py`; not used by the engine) |

`cfg.decide(tier, approved_by)`: Tier 0 always. Tier 1 (WordPress draft) = kill switch on + dry run off + `SEO_MODE=approve`.
Tier 2 (live-site batch) = a named approver + kill switch on + dry run off. Tier 3 never.
`SEO_LIVE` is a GitHub variable only (turns into `--live`).

## 5. GitHub workflows
- `seo-weekly.yml`: Monday 03:30 UTC (09:00 IST), runs the tests then `run_weekly`; input `refresh_keywords`. Runs only from the
  default branch `chore/initial-import`.
- `seo-apply.yml`: inputs `run_id`, `approved_by` (required), `only`, `undo`. Takes the newest fixes.json (or applied-*.json
  for undo) from that run's artifact. `gh workflow run seo-apply.yml -f run_id=<id> -f approved_by="<name>"`.

## 6. Functions without a CLI
- `keywords.keep(k, seeds) -> (bool, reason)`, `page_type(k)`, `place_of`, `service_of`, `priority`, `build_plan(client, seeds)`.
- `dataforseo.Client(cap_usd=None)`: `.keyword_ideas(seeds, location_code=2356, limit=300)`, `.serp(keyword,
  location_name=None)`, `.llm_answer(engine, question, city=None)`, `.spent`.
- `serp_skeleton.build(dfs, keyword, place)`: top-3 outline + an in-memory fingerprint for the copy check.
- `writer.build_request(topic, pages)`, `writer.write_article(...)` (client=None = dry run), `writer.to_html(article)`.
- `gates.check(article, kind=, fingerprint=)` → ok, blocks, warnings, words; `gates.check_snippet(text, max_len=)` for one line.
- `wordpress.create_draft(cfg, title, slug, html, excerpt, kind="posts"|"pages")`: refuses a slug already in use, sets status
  draft, never publishes, sends no featured image. No media upload exists anywhere.
- `aeo_probe.probe(questions, client, limit, dfs)`.

## 7. Data files (`seo_engine/data/`)
- `facts.json`: `brand`, `facts[{id, status approved|needs_source, text, source}]`, `unknown[]` (fees, minimum spend, contract,
  response time, office address, RTO/COD fixing, …). Only `approved` facts may be used.
- `local_proof.json`: per city (Rajkot, Ahmedabad, Surat, Vadodara): office, clients[], reviews[], photos[]. A city page needs a
  client with `consent: true` and a `result`, plus an office, review or photo. All client lists are empty today.
- `seeds.json`: 6 services, places (local Rajkot/Ahmedabad, state Gujarat/Surat/Vadodara, national India), 14 founder pains,
  `must_contain_one`, `exclude_words`.
- `topics.json`: 6 article topics (id, slug, question, pain, words_they_use, link_to) and 10 AI-probe questions.
- `rules.json`: block and warn patterns, link hosts, article/city length and shape limits, official source hosts.

## 8. Skill scripts (`.claude/skills/dtj-seo/scripts/`)
| Script | Free? | |
|---|---|---|
| `keyword_check.py rows.json --source "…" [--out]` | yes | engine filters on rows from DataForSEO or OpenSEO |
| `page_brief.py --topic <id> \| --keyword … [--keywords …] [--out]` | yes | the writer's exact brief + OVERLAP warnings (queued topics, existing pages) |
| `page_gate.py article.json --out <dir> [--top3 URLs] [--images-dir] [--topic-id] [--kind city] [--wordpress] [--log] [--state]` | yes (draft = Tier 1) | gate, HTML, preview, images.md (pending pictures marked, not blocking), topic marked written, optional WordPress draft |
| `blog_image.py --slug --role --prompt --alt --out [--model] [--dry-run \| --via browser \| --record FILE]` | API route costs | one checked picture + sidecar |
