# DTJ Agency Automation - Runbook v2

Owner: Harsh / Digital Tushar Joshi (DTJ). Status: planning, written 5 October 2026.
This is the full plan. `CLAUDE.md` is the short rulebook an AI session reads first; this file holds the detail.
Items marked **[VERIFY]** are assumptions that must be checked before they are built on.

---

## 0. Goal and principles

**Goal:** run the repeatable parts of the agency (audits, store builds, reporting, monitoring, ad guard, inventory guard, sales follow-up) with as little manual work as possible, without risking client money, accounts or data.

**Principles**
1. **Controls live in the systems, not in the prompt.** Permissions, scopes, branch protection, caps and a kill switch enforce the rules. A prompt only asks.
2. **Numbers come from code; the AI explains them.** Every figure is computed by code, stored with its source and query, and the AI may only interpret it. No source, no claim.
3. **Reversible before irreversible.** Start read-only, then reversible actions, then anything that spends money or is client-visible, and only with approval.
4. **Shadow first.** Every action runs in recommend-only mode before it is allowed to act.
5. **Everything is logged.** Every automated action records what, why, before/after, and who or what approved it.
6. **One source of truth per metric,** with a written definition (same discipline as the creative audit: one denominator, one grain, reconciled).
7. **Plain language for clients.** Reports speak founder language, not engineer language.

---

## 1. Operating model

### 1.1 Risk ladder (what the system may do)

| Tier | Meaning | Examples | Rule |
|---|---|---|---|
| 0 | Read only | Audits, scraping public pages, pulling reports, analysis | Automatic |
| 1 | Reversible, low risk | Pause an ad set, add a label or note, create a draft | Automatic with caps, a cooldown and a log |
| 2 | Spends money, changes client-visible things, or contacts people | Publish an ad, increase budget, push a theme, send a message, create a store | **A human approves each action** |
| 3 | Destructive or irreversible | Delete data, remove access, drop tables, force-push | **Forbidden.** Blocked by permissions, not by instructions |

### 1.2 Rollout modes (per client and per automation)
- **Shadow:** it only writes a recommendation (what it would do and why). Minimum two weeks.
- **Approve:** it prepares the action; a person clicks approve in Slack or the dashboard.
- **Auto (Tier 1 only):** it acts within caps. Tier 2 never becomes automatic.
Moving up a mode needs the exit criteria in section 12.

### 1.3 Kill switch and caps
- A single flag (`AUTOMATION_ENABLED`) in the config store stops all automations immediately. Each automation also has its own flag.
- Per client: maximum actions per day, maximum budget change per 24 hours, protected campaigns that are never touched.
- Dry-run flag on every service: log what would happen, change nothing.

---

## 2. Architecture

### 2.1 Components
| Component | Job | Notes |
|---|---|---|
| **Orchestrator (n8n)** | Triggers, schedules, connects services, human approvals, alerts | Thin. No business logic buried in nodes. |
| **Services (code)** | Audit, store builder, ad guard, Amazon guard, report generator | Versioned, tested, run as small jobs or APIs. |
| **Data warehouse (BigQuery)** | Single source of truth for metrics and the action log | Per-client datasets. |
| **Secrets vault** | API keys and tokens, one set per client | Never in files, nodes, HTML or chat. |
| **Config store** | Per-client thresholds, caps, protected items, mode, kill switch | Read by every service. |
| **Approval queue** | Pending Tier 2 actions with evidence | Slack message with approve/reject, plus a table. |
| **Observability** | Logs, run IDs, heartbeats, cost, dashboards | Alerts on silent failure. |

### 2.2 Repository layout (this folder)
```
dtj-agency-automation/
  CLAUDE.md            short rules for AI sessions
  RUNBOOK.md           this document
  .claude/settings.json  permission rules that enforce the boundaries
  .env.example         names of variables only, never values
  services/            audit/, store-builder/, ad-guard/, amazon-guard/, reports/
  n8n/                 exported workflows (version controlled)
  schemas/             JSON Schemas: webhooks, brand config, actions
  evals/               golden test sets for AI outputs
  docs/                decisions, client playbooks, incident notes
```

### 2.3 Environments
`dev` (own test stores and test data) -> `staging` (copy of a real client setup, no spend) -> `production`. Nothing reaches production without passing staging. n8n workflows live in git and are promoted, never edited live.

### 2.4 Per-client isolation
Separate credentials, separate BigQuery dataset, separate config. A bug in one client's automation cannot read or change another's data.

### 2.5 Action log (audit trail)
A table written for every automated or approved action:
`run_id, client_id, automation, tier, mode, target (ad set / SKU / theme), action, reason, evidence (query + values), before, after, approved_by, approved_at, result, error`.
No action without a row.

---

## 3. Security and access

### 3.1 Secrets
- Use the vault / n8n credentials / environment variables. Never in code, workflow JSON, prototypes or chat.
- Rotate on a schedule and when a person leaves. Revoke client access on offboarding.
- `.env.example` lists names only.

### 3.2 Least-privilege access (the real "hard boundaries")
| Platform | Grant | Do not grant |
|---|---|---|
| BigQuery | Dataset-level reader and writer roles (read, insert, update) | `bigquery.tables.delete`, dataset delete, owner roles |
| Shopify Admin API | Only the scopes each job needs (products read/write, themes read/write on dev) | No scope that allows deleting products or stores; no live theme publish for automation |
| GitHub | Fine-grained token for named repos; **branch protection on `main` requires a pull request and review** | Admin, force push, direct push to `main` |
| Meta / Google Ads | Read for reporting; a separate narrowly scoped credential for Tier 1 pause actions | Budget or publish rights for automation |
| Amazon SP-API / Ads | Read inventory; ads pause/resume for product ads | Create or edit campaigns, billing |
| Slack | Post to the alert channel | Read private channels |

### 3.3 Claude Code settings
`.claude/settings.json` denies the commands that must never run (direct push to `main`, force push, `rm -rf`, live theme pushes, BigQuery delete/truncate, reading `.env`). These are a second layer; the first layer is the credentials above. **[VERIFY]** run `/permissions` once to confirm the rules load.

### 3.4 Unattended AI use
Anthropic's consumer terms prohibit automated access to the service except through an API key. **Any scheduled or unattended AI step must use the Claude API with an API key and usage billing, not a Claude subscription login.** Interactive Claude Code at a keyboard is fine. Budget for API cost from the start and set spend caps.

### 3.5 Data protection
Customer data (names, emails, phone, addresses) is collected only when needed, stored per client, retained for a stated period, and never pasted into AI prompts unless required. See section 11.

---

## 4. Data layer

### 4.1 Datasets (per client)
`raw_meta`, `raw_google`, `raw_shopify`, `raw_amazon`, `raw_ga4`, `clarity`, `curated` (cleaned metrics), `actions` (the action log), `audits`.

### 4.2 Metric dictionary
One written definition per metric with grain, window, attribution and source. Examples: spend, purchases (selected action), attributed purchase value (Meta-attributed, not store revenue), store revenue, new vs returning, contribution margin, break-even ROAS, blended ROAS (MER), CPA, link CTR, frequency (deduplicated at its own grain, never summed). Reconcile platforms against the store and record gaps instead of hiding them.

### 4.3 Ingestion
Scheduled pulls, every raw row stored with query, window, UTC extraction time and pagination status. Re-runs are idempotent (same window gives the same rows). Late-arriving conversions are expected: treat the last 3 to 7 days as immature.

---

## 5. Workflows

Each workflow lists: trigger, inputs, steps, guardrails, tier, success measure, failure handling.

### Phase 0 - Foundations (build first)
- Repo, branch protection, environments, vault, config store with kill switch, logging with run IDs, action-log table, alert channel, `.claude/settings.json`, schema validator library, dead-letter queue.
- **Done when:** a dummy automation runs end to end in dev, writes an action-log row, can be stopped by the kill switch, and a malformed payload lands in the dead-letter queue.

### Phase 1 - Client intake and access
- **Trigger:** signed proposal / paid invoice. **Tier:** 0 to 1.
- Steps: onboarding form (brand, goals, margins, targets, shipping and returns facts, protected campaigns); secure access links (OAuth or collaborator invites) for Shopify, GA4, Clarity, Meta, Google Ads, Amazon; checklist of what is connected; per-client config created; kill switch default off.
- Guardrail: collect the minimum access; read-only first.
- **Done when:** a new client reaches "connected and verified" with no manual copy-pasting of credentials.

### Phase 2 - Read-only intelligence (reporting and monitors)
- **Trigger:** schedules (daily pulls, weekly report). **Tier:** 0.
- Services: data pulls into BigQuery; weekly client report in the DTJ format; monitors that raise alerts only: tracking health (pixel and server events, GA4), price or offer mismatch between ads and landing pages, out-of-stock products still advertised, creative fatigue signals, budget pacing, sudden spikes or drops, broken links and pages.
- Guardrails: alert text states evidence and confidence; no action taken.
- **Done when:** a weekly report generates unattended for two clients and monitors alert correctly on seeded test problems.

### Phase 3 - Website audit and pitch generator (lead-facing)
- **Trigger:** webhook with `{lead_url, niche}` (validated against a JSON Schema). **Tier:** 0, with a Tier 2 step for sharing.
- Steps:
  1. Capture the public page: screenshots (mobile and desktop), HTML, request list, theme and app detection. Respect robots.txt and rate limits. **[VERIFY]** the site's terms for each lead.
  2. Score against the checklist (rating under title, icon bullets, price anchoring, variant offers, testimonial under buy button, upsell, visual description, sticky buy bar, review app, analytics, trust items, speed, India essentials) and compute the uplift range from editable assumptions.
  3. Produce the founder-language report (HTML and PDF) with mockups from our ready-made blocks.
  4. Prototype (optional): a private, password-protected, no-index preview built from **our** blocks and neutral placeholders. Do not publish a lead's logos, photos or copy on a public URL.
  5. A person reviews, then sends.
- Guardrails: no fabricated numbers; every claim cites a check ID; uplift figures carry the planning-assumption disclaimer until replaced by our own test results.
- **Existing work:** `GOMINT/store-builder/audit` (capture, scoring, founder layer, HTML/PDF report, block mockups). Known gaps: pack-selector detection, lazy-loaded images, speed measurement. See section 13.
- **Done when:** 20 real stores audited, detector accuracy measured against a hand-checked sample, and reports approved by Harsh without major edits.

### Phase 4 - Store build pipeline (blueprint builder and provisioning)
- **Trigger:** signed-off audit and payment confirmation. **Tier:** 2 for anything on the client's store.
- Inputs: brand config (colours, fonts, logo, tone, offers, shipping and returns, niche), product sheet, image folder. Schema-validated.
- Steps:
  1. Choose the blueprint per page type (home, collection, product, cart, FAQ, about) from the niche and audit findings.
  2. Generate the template files from blueprint plus content (`blueprint.py` already proves a lossless round trip).
  3. AI drafts text for each content slot from the brand config only. Facts it does not have become `[[TODO]]` markers, never invented.
  4. Create the store or use the client's (**[VERIFY]** whether the Shopify Partner API can create development stores programmatically; if not, make creation a one-click manual step).
  5. Push the master theme and templates to an **unpublished** theme with narrow pushes. Create products through the Admin API (create and update only).
  6. Upload graphics supplied by the team into the image slots; missing ones stay as neutral placeholders with a to-do list.
  7. Automated QA: Theme Check, Lighthouse, mobile and desktop screenshots, link checks, test-mode checkout in Playwright on the dev store (never real payments), visual comparison against the blueprint.
  8. Human review of the draft theme, then the client approves. A person publishes.
- Guardrails: never touch a live theme from automation; patches to the theme go to a draft and are reviewed; payment webhook is signature-verified and idempotent so one payment makes one store.
- **Existing work:** the Tattva - Dev theme and its `cg-` blocks (section 13).
- **Done when:** one real brand goes from brief to a reviewed draft theme in the target time (2 to 6 hours of elapsed work, excluding graphics and client wait time).

### Phase 5 - Ad guard (Meta, then Google)
- **Trigger:** schedule (hourly evaluation, daily decisions). **Tier:** 1 for pause, 2 for everything that spends.
- **Principle:** pausing is reversible; scaling, duplicating and publishing spend money and are approval-only.
- Starting rules (tune per client in the config store):
  - **Eligibility:** ad set older than 3 days, out of the learning phase, not tagged `protected`, no change in the last 72 hours.
  - **Enough data:** spend in the window at least 2 to 3 times the target CPA (or a rupee minimum), and enough clicks or impressions to be meaningful.
  - **Pause condition:** ROAS below the client's **break-even ROAS** (derived from contribution margin) by a set margin over 7 days with the 72-hour trend confirming, and blended ROAS across channels not offsetting it. A fixed "1.5" is a placeholder; real thresholds come from margin.
  - **Caps:** at most 3 pauses per account per day; budget changes at most 20% per 24 hours; never delete.
  - **Maturity:** treat the last 3 to 7 days of conversions as incomplete before concluding.
- Creative refresh: a low CTR flag needs a minimum number of impressions and a comparison against the account benchmark and frequency. The system **drafts** new creative; a person approves; Meta ad-policy and brand claims are checked (especially spiritual and food or health claims).
- Every proposed action writes an action-log row with its evidence.
- **Done when:** two weeks of shadow recommendations match a human media buyer's decisions at an agreed rate, then approve mode for a month, then auto-pause only.

### Phase 6 - Creative pipeline
- Briefs from performance data (hooks, angles, formats that worked), AI-assisted drafts (copy and static layouts from templates), human review and approval, naming and tagging so results trace back to the brief. Fatigue refresh uses a controlled test (change one thing at a time). **Tier 2** for publishing.

### Phase 7 - Amazon inventory guard (only for clients on Amazon)
- **Trigger:** every 30 to 60 minutes, plus notifications where available. **[VERIFY]** SP-API report freshness and rate limits before choosing the interval.
- Steps: fetch inventory by SKU; compute run rate and days of cover; compare with **supplier lead time plus a buffer** (not a fixed 14 days).
- Action (Tier 1): pause the **product ads for that SKU** (not whole campaigns) when cover falls below the pause level; resume only when cover rises above a higher resume level (a gap prevents flip-flopping). Log every change.
- **Done when:** a seeded low-stock SKU pauses and resumes correctly in a test account.

### Phase 8 - Sales, CRM and billing
- Lead capture into a CRM, WhatsApp-first follow-up for Indian leads (approved templates and consent), audit report as the hook, proposal and contract templates, GST invoices and payment reminders, onboarding trigger (Phase 1). Messaging is Tier 2 (approved templates only).

---

## 6. Self-healing protocol

**Automatic (safe classes):**
- 429 / 5xx: retry with exponential backoff and jitter, up to 3 times.
- 401 / expired token: refresh credentials, then retry once.
- Idempotent replays from the dead-letter queue.

**Propose only (needs approval):**
- Schema changes, mapping fixes, workflow edits. The AI writes the patch on a **branch**, runs it in staging against the saved failing payload, and opens a pull request with the diff and test result. A person merges and promotes.

**Always:**
- Circuit breaker: after 3 consecutive failures of the same step, stop that automation, keep the payload, and alert Slack with the error, attempted fixes and the run ID.
- Never edit a production workflow directly; never disable a safety check to make a run pass.
- Every healing attempt is logged.

---

## 7. Webhooks and payload handling
1. Verify the sender's signature (HMAC or provider method) and timestamp.
2. Validate the body against its JSON Schema in `schemas/`.
3. Check the idempotency key; ignore duplicates.
4. Malformed or unverifiable payload goes to the dead-letter queue with the raw body and the reason. Nothing downstream runs.
5. Replay from the queue is manual or via the safe automatic classes above.

---

## 8. AI usage policy
- Use the Claude API (API key, billed usage) for anything unattended. Cap spend per run and per day.
- Structured outputs against a schema; reject and retry malformed output.
- Numbers are computed by code and passed to the AI as facts; the AI cannot invent or alter them. Every statement cites a source ID or check ID.
- Prompts are versioned in git. A golden test set in `evals/` runs before any prompt or model change.
- Client-facing text and creative are reviewed by a person.
- Customer personal data is excluded from prompts unless essential.
- Fallbacks: if the model errors or is uncertain, the step returns "needs human" instead of guessing.

---

## 9. Observability
- Structured logs with `run_id` and `client_id`.
- Dashboards: automations run, success rate, actions by tier, approvals pending, AI cost per client, data freshness.
- **Heartbeats:** every scheduled job reports in; a missing heartbeat raises an alert (silent failure is the main risk).
- Weekly review of the action log: what the system did, what humans overrode, what to tune.

---

## 10. Testing and QA
- Unit tests for calculations and rules (threshold edge cases).
- Contract tests for each external API (detect schema drift early).
- Playwright for page capture and test-mode checkout; visual comparison for store builds.
- Staging runs on a copy of a real client setup with spend disabled.
- Seeded-problem tests: deliberately create a bad ad set, a low-stock SKU, a broken pixel, and confirm the right alert or action.
- Detector accuracy for the website audit measured against hand-labelled stores.

---

## 11. Compliance (confirm with a qualified professional)
- **India's DPDP Act 2023:** collect only what is needed, state the purpose, keep it per client, honour deletion requests.
- **Shopify protected customer data rules** apply to any customer fields read through the API.
- **Meta and Google ad policies:** especially claims for health, food and spiritual products; keep an approved-claims list per client.
- **Scraping:** respect robots.txt and site terms; do not republish a prospect's images, logos or copy publicly.
- **Outreach:** use consented channels and approved WhatsApp templates; honour opt-outs.
- **Finance:** GST invoicing and records.
- **AI provider terms:** unattended use through the API only (section 3.4).

---

## 12. Rollout plan and exit criteria

| Phase | Work | Rough time | Exit criteria |
|---|---|---|---|
| 0 | Foundations | 2 to 3 weeks | Dummy automation passes the Phase 0 test |
| 1 | Client intake | 1 to 2 weeks | New client connected with no credential copy-paste |
| 2 | Read-only intelligence | 3 to 5 weeks | Weekly report unattended for two clients; monitors catch seeded problems |
| 3 | Website audit and pitch | 3 to 4 weeks (builds on existing tool) | 20 stores audited; accuracy measured; reports approved with minor edits |
| 4 | Store build pipeline | 6 to 8 weeks | One real brand reaches a reviewed draft theme in target time |
| 5 | Ad guard | 3 to 4 weeks shadow, then approve, then auto-pause | Recommendations match a media buyer at the agreed rate |
| 6 | Creative pipeline | 3 to 4 weeks | Briefs to approved drafts working for one client |
| 7 | Amazon guard | 2 to 3 weeks (if needed) | Seeded SKU pauses and resumes correctly |
| 8 | Sales, CRM, billing | 3 to 4 weeks | A lead flows from audit to proposal to onboarding |

These times are estimates for planning, not commitments. The order matters more than the weeks; do not skip Phase 0 or shadow mode.

---

## 13. Existing assets and how they plug in
| Asset | Location | Role |
|---|---|---|
| Product page audit tool | `GOMINT/store-builder/audit/` (`audit.py`, `founder_layer.py`, `report_html.py`, `capture_blocks.py`, `uplift_assumptions.json`) | Phase 3 service |
| Blueprint splitter and builder | `GOMINT/store-builder/blueprint.py`, `store-builder/tattva/` | Phase 4 core |
| Custom block library (`cg-` and `gm-`) | Tattva - Dev theme `181085339895`; local copy `GOMINT/tattva-cro-rating-block/` | Phase 4 master theme seed |
| Block mockup images | `GOMINT/store-builder/audit/assets/blocks/` | Audit reports |
| Handoff notes and rules | `GOMINT/CLAUDE.md`, `GOMINT/HANDOFF.md` | Working conventions to carry over |

Known gaps: missing blocks (four-icon benefits, pack cards with "Most popular", trust row); detector accuracy on pack selectors and lazy-loaded images; speed numbers from this machine are unreliable (confirm with Google's tools); the uplift numbers are planning assumptions until replaced by our own test results.

---

## 14. Open decisions and things to verify
1. Can the Shopify Partner API create development stores programmatically? **[VERIFY]**
2. Which MCP servers are available and maintained (n8n, GitHub, browser automation, BigQuery)? Prefer well-maintained ones or our own thin scripts. **[VERIFY]**
3. Where n8n is hosted (cloud or self-hosted), who backs it up, and how workflows are promoted between environments.
4. Whether Amazon is in scope now (affects Phase 7).
5. Client-level targets: break-even ROAS, target CPA, margins, protected campaigns.
6. Claude API budget and per-run caps.
7. Who approves Tier 2 actions, and the target response time.
8. Data retention periods and deletion process.

---

## Appendix A - Environment variables (names only)
`CLAUDE_API_KEY`, `SHOPIFY_PARTNER_TOKEN`, `SHOPIFY_ADMIN_TOKEN_<CLIENT>`, `GITHUB_TOKEN`, `BIGQUERY_PROJECT`, `BIGQUERY_CREDENTIALS_PATH`, `META_ACCESS_TOKEN_<CLIENT>`, `GOOGLE_ADS_*`, `AMAZON_SP_*`, `SLACK_WEBHOOK_ALERTS`, `N8N_API_KEY`, `AUTOMATION_ENABLED`.

## Appendix B - Action matrix (summary)
| Action | Tier | Mode needed |
|---|---|---|
| Pull reports, run audits, scrape public pages | 0 | Auto |
| Pause ad set within caps | 1 | Shadow, then approve, then auto |
| Pause product ads for a low-stock SKU | 1 | Same |
| Create draft creative or draft theme | 1 | Auto (draft only) |
| Publish ad, change budget, push or publish a theme, send a message, create a store | 2 | Always human approval |
| Delete anything, force-push, drop tables, remove access | 3 | Forbidden |
