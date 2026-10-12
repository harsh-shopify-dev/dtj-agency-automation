# DTJ automation plan: kill switch first, then the agency automation

> **PRIORITY CORRECTION by Harsh (9 Oct 2026), read before the rest of this plan:** the main task is the **store factory** (the Claude API designs each client's store pages from our blocks, adapting to the brand's palette, fonts and shape and following high-converting agency structure) plus the **automated kill switch**. Section 6's order is superseded: page assembly comes FIRST (it is already started in `services/store-builder/page_builder/`), audit-to-pitch and the other automations come later. n8n is glue only. See `docs/HANDOFF.md`, section 'MAIN TASK'.

**Status: DRAFT for Harsh's approval (9 October 2026).** Nothing in this plan is built, deployed, bought or changed until Harsh approves it, and every Tier 2 step still needs his yes on the exact action.
Written by the desktop-app Claude session that now runs the project (Harsh, 9 Oct 2026: "handle the project from here, not claude-a/claude-b").
Every fact has a source (list at the end). Prices are as listed on the vendor page on 9 Oct 2026; "derived" means my arithmetic from listed unit prices. **[VERIFY]** = not proven yet.

---

## 1. The short version

**What I found**
1. **The code is healthy.** 361 tests pass across the four suites (DTJ Blocks 146, DTJ Sections 77, DTJ Sections 2 50, store builder 88) and all three apps pass the library rules. DTJ Sections is close to Shopify's size cap (95.8 KB of 100 KB).
2. **Nothing since 6 Oct is backed up.** 28 commits exist only on this PC, plus 13 changed files that are not committed. GitHub has no `main` branch and no protection. One disk failure loses the whole block library history.
3. **One app secret leaked** (DTJ Sections, in a screenshot on 8 Oct). It must be rotated.
4. **Shopify rule that changes the client plan:** an app with *custom distribution* (what all three of our apps use) "can be installed on multiple stores when those stores belong to the same Plus organization" — in practice **one client store per app**. Our three apps cannot serve many clients as they are. See section 3.
5. **Of the RUNBOOK's 9 automation phases, only the store build (phase 4) has real code.** Phase 0 foundations are partly there (kill switch flag, dry run, action log, approval gate in `services/store-builder/provision/`). Everything else is an empty folder.

**What I recommend**
1. **Week 1: protect what exists** (backups, branch protection, rotate the leaked secret, an automatic test run on every change, fix the gaps in our own safety rules). Small, cheap, and it removes the biggest risks.
2. **Build one small hosted "control service"** that is both the automated kill switch and the shared foundation every later automation needs (action log, Telegram approvals, alerts, heartbeat, master off-switch). One build, two jobs.
3. **Kill switch for your own store first**, from Telegram, with no terminal and no secret ever typed.
4. **Decide how the blocks reach client stores (decision D0) after a short proof**, before building anything for client stores.
5. **Then the agency automation in this order:** audit-to-pitch, page assembly, reporting and monitors, ad guard (shadow first), then intake/billing. Reasons in section 6.

**What I need from you now (the rest can wait):** D0 (how blocks reach clients, after the proof), D5 (where the service runs), and the four week-1 actions only you can do (section 5, K0).

---

## 2. Where things stand (9 Oct 2026)

| Area | State | Source |
|---|---|---|
| Block apps | DTJ Blocks `dtj-blocks-26` (8 blocks), DTJ Sections `dtj-sections-11` (8 sections, 95.8 KB of 100 KB), DTJ Sections 2 `dtj-sections-2-6` (4 sections) | HANDOFF section A 1.1 (8 Oct); sizes re-measured 9 Oct by `check_library.py` |
| Tests | 361 pass (146 / 77 / 50 / 88) | run 9 Oct; store builder needs Pillow, which is not declared in `requirements.txt` (venv run: 2 errors; system Python: all pass) |
| Kill switch today | works on the test store for all three apps; a person runs `tools/dtj-licence` and types each app's secret | HANDOFF A 1.2 |
| Kill switch for clients | impossible today: client credentials "can't reach a store outside your organization" | Shopify docs (client credentials grant) |
| Git | branch `feature/reels-sound-button`, 28 commits not on GitHub, 13 uncommitted files; no `main`, no protection | `git` 9 Oct |
| CI (automatic tests on GitHub) | none (no `.github/`) | repo map 9 Oct |
| Safety rules (`.claude/settings.json`) | blocks push to main, force push, `reset --hard`, `rm -rf`, `bq rm/truncate`, any `--allow-live`, reading `.env`/`secrets/`. **Does not block `shopify theme publish`** although RUNBOOK 3.3 says live theme pushes are blocked | repo map 9 Oct |
| Page builder scripts | `gen_toilova_page.py`, `validate_template.py` were only in another session's temp folder; safety copy now in `.work/rescued/` (not in git) | 9 Oct |
| n8n | your own server (`n8n.srv1969859.hstgr.cloud`, Hostinger); added to Claude as an MCP server, **needs your sign-in**, nothing inspected yet | 9 Oct |
| This session's Shopify login | theme commands and deploys failed here on 6 Oct; a visible-window sign-in fixed it for another store the same day | HANDOFF line 269 |
| Connected here | built-in browser, Chrome, Docs connector, scheduled tasks, `gh` CLI. Not connected: Telegram, Slack, BigQuery, Meta Ads. A Shopify MCP is attached but points at another seller's store: not used | 9 Oct |

---

## 3. Decision D0: how the blocks reach client stores (new, decides the kill-switch design)

**The facts (Shopify docs, 9 Oct 2026)**
- Custom distribution: an app goes to one store, or to several stores of one Plus organization; the method "can't be changed later"; custom apps can't use Shopify's app billing.
- For a client store outside our organization, a non-embedded app gets its token with the **authorization code grant** (merchant approves, Shopify redirects to our server, we verify `hmac` + `state` + shop name, swap the code for a token). Custom apps may keep **non-expiring offline tokens** (expiring tokens are mandatory only for public apps).
- App-data metafields (our licence flag) can't be changed by merchants or other apps.

**The options**

| | A. One set of apps per client (custom distribution) | B. One set of apps for everyone (public distribution, limited visibility = unlisted) | C. No app: sections in the client's theme |
|---|---|---|---|
| Apps to run | 3 per client (3 x N) | 3 total | 0 |
| Shopify review | none | **app review needed** [VERIFY requirements] | none |
| Kill switch | our server gets a token per client app at install (OAuth) **or** we release a "switched-off" version of that client's apps (no client token stored at all) [VERIFY release reaches installed stores] | our server gets a token per store at install (OAuth); flag as today | none (contract only) |
| Billing | our invoices (Razorpay etc.) | [VERIFY] public apps may have to charge through Shopify's billing; if so, unpaid = Shopify cancels, which can drive the licence automatically | our invoices |
| Upkeep | every release x N clients; 3 deploy tokens per client, each expiring after 1/3/6 months | one release for all | theme updates per client |
| Speed to first client | fast (no review) | slow (review) | fastest |
| IP protection | source stays with Shopify; kill switch | same | none |

**My recommendation:** run a 1-2 day **distribution proof** (phase K1) before choosing. Provisionally:
- **B is the long-term answer** if its review rules are acceptable (one app set, standard install, possibly Shopify-handled billing).
- **A is the stop-gap** for a paying client before B is approved. The control service design is the same for A and B: only "how we get the token" differs.
- **C stays** for the bulk pack sections in the master theme (Harsh's earlier decision).

---

## 4. The control service (kill switch + shared foundation)

**In plain words:** a small program that runs all the time on a server. It keeps the app secrets and store tokens in a locked vault, talks to Shopify and Telegram, asks you before any Tier 2 action, double-checks every change by reading it back, writes every action to a log, and alerts you if it stops working. The same program later carries approvals and alerts for the ad guard, reports and audits.

```
You (Telegram)            Shopify (install, uninstall webhooks)       Billing (later, shadow first)
     |  secret header            |  HMAC-signed                            |  signed webhook
     v                           v                                         v
 +------------------------------ control service (Python) -----------------------------------+
 |  allow-list -> policy (tiers, confirm taps, caps, AUTOMATION_ENABLED, dry run)            |
 |  -> executor (metafieldsSet only) -> read-back check -> action log -> reply + alert       |
 +-----------+---------------------------+------------------------------+--------------------+
             |                           |                              |
     secret store                 token vault (encrypted)        uptime monitor (heartbeat)
  (app secrets, bot token,     store x app -> token             alert to your Telegram
   encryption key)
```

**Reuse, don't rewrite** (all exist and are tested): `tools/licence.py` (token, read, set, log; only `metafieldsSet` allowed), `provision/config.py` (master off-switch, dry run, modes, tier gate), `provision/actionlog.py` (schema-checked log, secrets scrubbed), `provision/gql.py` (operation allow-list, retries with backoff, rate-limit aware), `provision/run.py` (`CircuitBreaker`: stop after 3 failures), `tests/test_licence_tool.py` (`FakeShopify` for offline tests).
**Three fixes first:** licence log rows don't match `schemas/action.schema.json` (missing run id, client id, mode, reason); its mutation check is a regex (use the parser in `gql.py`); its API version is hard-coded `2026-07` (still supported, but read it from config).

**Telegram (facts from the Bot API docs):** webhook with a secret header `X-Telegram-Bot-Api-Secret-Token` (we reject anything without it); confirm/cancel buttons (`callback_data` up to 64 bytes); `chat.type` tells private chats from groups (we answer private chats from allow-listed user ids only); a bot can delete a message in a private chat within 48 hours (so a pasted secret gets deleted and you get a "rotate it" warning); about 1 message per second per chat. Proposed commands: `/status`, `/hide <store>`, `/show <store>`, `/hideall <store>`, `/panic` (asks twice), `/pending`, `/help`.

**Shopify webhooks:** `app/uninstalled` declared in each `shopify.app.toml`; verify `X-Shopify-Hmac-SHA256` (HMAC-SHA256 of the raw body with the app secret); drop duplicates by `X-Shopify-Webhook-Id`; Shopify allows 5 seconds and retries 8 times over 4 hours. Add the three privacy webhooks too ([VERIFY] whether custom distribution requires them; cheap to add).

### Where it runs (decision D5)

| Option | Compute (listed / derived) | Database | Secret store | India region | Notes |
|---|---|---|---|---|---|
| **Google Cloud Run** (recommended) | 1 always-on minimum instance, 1 vCPU / 0.5 GiB idle: about **$9.86/month** before free tier (derived) | Firestore free quota (1 GiB, 50k reads/day) or Cloud SQL db-f1-micro about **$7.67/month** (derived, Iowa price; Mumbai price [VERIFY]) | Secret Manager: first 6 secret versions free, then $0.06/version/month | **Yes, Mumbai** | managed, India region, secrets built in |
| Render | Starter **$7/month** | Postgres basic **$6/month** | environment groups (encrypted at rest per a Render article) | No (Singapore) | simplest |
| Fly.io | about **$2.78/month** in Singapore for 256 MB (derived) | managed Postgres **$38/month** (or a small volume) | secrets vault (values can't be read back) | No (Singapore) | cheapest compute, pricey database |
| Your Hostinger server (where n8n runs) | already paid [VERIFY plan and location] | self-run | self-run | [VERIFY] | cheapest, but you patch, back up and secure it yourself, and an n8n break-in would sit next to the token vault |

**Recommendation:** Google Cloud Run in Mumbai with Secret Manager, Firestore to start: roughly **$10-18 per month** (derived from the listed prices above, before free-tier credits). Heartbeat: **Healthchecks.io free** (20 checks, Telegram alerts included). Keep n8n on Hostinger as the scheduler and glue, not as the vault.

---

## 5. Phased plan (each phase needs your approval to start; Tier 2 steps inside still need your yes each time)

Sizes are relative (S/M/L), not promises.

| Phase | What | Exit criteria (done when) | Size |
|---|---|---|---|
| **K0 Protect what exists** | **You:** create `main` on GitHub + protection (PR + review, no force push); rotate the DTJ Sections secret; sign this session's Shopify CLI in (visible-window method, you do the browser step); sign n8n in. **Me (after your yes on each exact command):** commit the 13 changed files on a feature branch, push, open the pull request; add CI (GitHub Actions: the four test suites, library rules, Theme Check, secret scan), declare the Python dependencies (Pillow, python-liquid, jsonschema); move the two rescued scripts into `services/store-builder/page_builder/` with tests; propose a deny rule for `shopify theme publish` and live pushes (you approve settings changes). | Everything on GitHub; CI green on the PR; secret rotated; `shopify theme list` works from this session | S |
| **K1 Distribution proof** | Answer D0's [VERIFY] items with real tests: what happens when a merchant outside our org installs a non-embedded custom app (does Shopify send them to our server so we can run the authorization code grant?); does a new app version reach installed stores without the merchant doing anything; public-app review rules (billing, embedded UI, privacy webhooks). Needs a store **outside our organization** (decision D9). Read-only plus one throwaway test app. | Written answers with sources; you pick A, B or a mix | S |
| **K2 Service skeleton, dry run only** | `services/control-service/`: app registry (3 apps, client ids, secret *names*), config, action log, master off-switch, health endpoint, heartbeat, dead-letter queue, dry run on every action, fake-Shopify tests, CI. Deployed to the chosen host with no real secrets yet. | RUNBOOK Phase 0 "done when": a dummy action runs end to end, writes a log row, is stopped by the off-switch, a malformed payload lands in the dead-letter queue | M |
| **K3 Own-store kill switch** | `licence.py` logic as a library; client-credentials tokens minted on the server (secrets from the secret store); status / hide / show for all three apps with read-back; nightly drift check. | On `elevate-with-harsh`: hide and show all three apps from the service; storefront page source loses / regains `class="dtj-b` (also closes the open "flag off" check) | M |
| **K4 Telegram, approve mode** | Bot (you create it with BotFather; the token goes straight into the secret store, never into chat), allow-list, confirm buttons with expiry, alerts, break-glass doc (the terminal script stays). | You hide/show the test store from your phone; an unknown user gets no reply and triggers an alert; an old confirm button does nothing | M |
| **K5 Client installs** (per D0) | Install callback (authorization code grant: verify hmac, state, shop; check granted scopes), token vault, default licence on install (D4), uninstall webhook, onboarding checklist item "kill switch connected and verified". | A store outside our org installs, can be hidden/shown from Telegram, uninstall is detected | L |
| **K6 Billing rules in shadow** | billing webhook relay (n8n), rules with grace period and reminder ladder; **messages only** ("I would hide store X"). | 2 weeks of shadow output reviewed by you with zero wrong cases (RUNBOOK 1.2) | M |
| **K7 Release automation** | CI deploys with Shopify **App Automation Tokens** (one per app, created in the Dev Dashboard, expire after 1, 3 or 6 months; the old Partner CLI tokens can no longer be created); a Telegram "release?" button; the active version is read back after every deploy. Token expiry alerts. | A release is one approved tap, with the version check posted back | M |
| **K8 Auto mode (optional, later)** | billing rule acts for real, only for stores you authorised in writing (D1). | your written approval + RUNBOOK section 12 criteria | S |

Order: K0 and K1 can run in parallel; K2-K4 give you the Telegram switch for your own store; K5 waits for D0.

---

## 6. The wider automation: what exists, and what to automate next

| RUNBOOK phase | Exists today | Next step I recommend |
|---|---|---|
| 0 Foundations | kill switch flag, dry run, modes, tier gate, schema-checked action log, retries, circuit breaker (`provision/`) | delivered by K2 (one shared service) |
| 1 Client intake | nothing | later: onboarding form + access checklist, after K5 shows how installs work |
| 2 Reporting and monitors | nothing (`services/reports/` empty) | after K2: read-only pulls on a schedule (n8n), a metric dictionary, weekly report; needs BigQuery (not connected) and read access per client |
| 3 Audit and pitch | old tool in `GOMINT/store-builder/audit/` (no tests); `import_catalog.py` | **next after K4**: move the audit tool into the repo with tests, the `{lead_url, niche}` webhook + schema, a hand-checked accuracy set in `evals/`. Read-only, brings in leads |
| 4 Store build | provisioning service, 3 block apps, rescued page builder | page assembly from a product sheet (the Toilova generator pattern), QA automation (headless screenshots, overflow checks, Theme Check), all pushes still approved |
| Screenshot-to-block | done by hand many times (build, rules, tests, render) | Claude API with an API key and spend caps; a human reviews the visual diff before any deploy |
| 5 Ad guard | nothing | only after phase 2 data and your break-even numbers; shadow for 2+ weeks (RUNBOOK) |
| 6 Creative | nothing | later |
| 7 Amazon guard | nothing | only if Amazon is in scope (RUNBOOK open decision 4) |
| 8 Sales, CRM, billing | nothing | billing feed first, because it powers K6 |

**n8n's role:** schedules, webhook relays and simple glue only; workflows exported to git (RUNBOOK 2.1). No business logic or secrets in workflow JSON. Unattended AI steps use the Claude API with an API key, never a subscription login.

---

## 7. Decisions for you (my recommendation in brackets)

- **D0 How blocks reach clients:** A, B or C (section 3). [decide after the K1 proof; provisionally B long-term, A as stop-gap]
- **D1 Automatic hiding** ever allowed? RUNBOOK says Tier 2 never becomes automatic. [no for now: Telegram button only; revisit after K6 shadow]
- **D2 Who may press the button?** [only you; `/panic` and `/hideall` ask twice]
- **D3 Service down:** storefronts keep their last state because the flag lives in Shopify. [accept]
- **D4 New install default:** `inactive` until paid, or `active` for a trial? [inactive; commercial call is yours]
- **D5 Hosting:** [Google Cloud Run, Mumbai]
- **D6 Billing source:** Razorpay / Stripe / invoices / Shopify billing (if B)? [your call]
- **D7 Secret store:** [follows D5: Google Secret Manager]
- **D8 Client contract wording** for the licence and kill switch [needs a qualified professional]
- **D9 A test store outside our organization** for K1/K5 (a second Shopify account/org you control). [needed for the proof]
- **D10 Telegram bot:** you create it with BotFather; the token goes only into the secret store. [needed for K4]

---

## 8. Not proven yet ([VERIFY]) and how we will check

1. After a merchant outside our org installs a non-embedded custom app, are they sent to our server so we can run the authorization code grant? (docs silent; only forum posts) -> K1 test.
2. Which scope, if any, writing the app-installation metafield needs (docs silent; our tool works today) -> K1/K5 test.
3. Are privacy webhooks required for custom distribution? (docs only say App Store apps) -> add them anyway.
4. Public distribution review requirements (Shopify billing, embedded UI) -> read the current requirements in K1.
5. Does a new app version reach installed stores without merchant action (matters for option A's "switched-off release")? -> K1 test.
6. Cloud SQL / Firestore prices and availability in Mumbai -> pricing calculator in K2.
7. Hostinger server plan, location and spare capacity -> you or the n8n check.
8. Telegram webhook retry behaviour -> Bot API docs / test in K4.
9. Store-builder tests need Pillow, not declared -> fixed in K0.

---

## 9. Main risks

| Risk | Mitigation |
|---|---|
| Losing work (nothing since 6 Oct on GitHub) | K0 first |
| Hiding a paying client by mistake | confirm taps, read-back check, instant `/show`, shadow first, no automatic hiding (D1) |
| Token vault leak | encryption with a separate key, minimal scopes, only `metafieldsSet` allowed, rotation drill |
| Telegram account takeover | allow-list, Telegram 2-step verification, confirm buttons with expiry, alerts, the terminal break-glass |
| Distribution choice is permanent per app | prove first (K1); never create a client app before D0 |
| Deploy tokens expire (1-6 months) | expiry alerts from the service (K7) |
| Secrets pasted into chat again | bot deletes and warns; CI secret scan; hidden prompts in the terminal tool |

---

## 10. Sources (read 9 Oct 2026)

Shopify: client credentials grant `shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant`; authorization code grant `.../access-tokens/authorization-code-grant`; distribution `shopify.dev/docs/apps/launch/distribution` and `.../distribution/select-distribution-method`; offline tokens `.../access-tokens/offline-access-tokens` and changelog "expiring offline access tokens required for public apps April 1 2026"; app installation metafields `shopify.dev/docs/api/admin-graphql/latest/objects/AppInstallation`, `shopify.dev/docs/apps/build/metafields`; privacy webhooks `shopify.dev/docs/apps/build/compliance/privacy-law-compliance`; webhooks `shopify.dev/docs/apps/build/webhooks/subscribe/get-started`, `.../subscribe/https`; App Automation Tokens `shopify.dev/docs/apps/build/dev-dashboard/app-automation-tokens` and changelog "app deployment in CI/CD is now available for all apps"; versioning `shopify.dev/docs/api/usage/versioning`; rate limits `shopify.dev/docs/apps/build/apis/graphql-admin/rate-limits`.
Telegram: `core.telegram.org/bots/api`, `core.telegram.org/bots/faq`, `core.telegram.org/bots/webhooks`.
Hosting and tools: `cloud.google.com/run/pricing`, `cloud.google.com/sql/pricing`, `cloud.google.com/firestore/pricing`, `cloud.google.com/secret-manager/pricing`, `render.com/pricing`, `render.com/docs/regions`, `docs.fly.io/about/pricing`, `docs.fly.io/mpg`, `docs.fly.io/apps/secrets`, `docs.railway.com/reference/pricing/plans`, `healthchecks.io/pricing`, `healthchecks.io/integrations/telegram`, `uptimerobot.com/pricing`, `betterstack.com/pricing`, `neon.com/pricing`, `supabase.com/pricing`.
Repo facts: test runs, `git`, `check_library.py` and a read-only repo map on 9 Oct 2026; `docs/HANDOFF.md` section A (8 Oct).
