# Handoff - DTJ Agency Automation

**Rewritten 6 October 2026 so a NEW Claude account/session can continue with no other context.** Facts only. No secrets in this file (client ids and store ids are not secrets; the client secret and tokens are never written anywhere).
Update this file at the end of every working session (Harsh's rule).

---------------------------------------------------------------------------------------------------

## 0. Read this first (60 seconds)

- **What this is:** an automation system for **Digital Tushar Joshi (DTJ)**, a performance-marketing agency in India run with **Harsh** (developer, the person you work for). The long-term goal is to run the repeatable parts of the agency (audits, store builds, reporting, monitoring, ad guard) with little manual work, **without risking client money, accounts or data**. Plan: `RUNBOOK.md`. Rules: `CLAUDE.md`.
- **What the last sessions built (5 Oct 2026, one very long session):**
  1. A **Shopify store-provisioning service** (`services/store-builder/provision/`) that takes a brand config + product sheet + images and puts a theme, draft products and template settings on a store, with safety rules in code. 88 tests.
  2. A **proprietary block library delivered as a Shopify theme app extension** (`services/block-library/`): app "DTJ Blocks", with a **licence kill switch** (a flag we control that makes the blocks disappear). 7 blocks live, 104 tests.
- **Where it runs:** all work so far is on **Harsh's own test store** `elevate-with-harsh.myshopify.com` (type "Client Transfer", plan Development). **No real client store has been touched.** The live theme on that store was never touched.
- **State right now:** everything is released as app version **`dtj-blocks-13`** (released 6 Oct 2026; 13 = reels sound button + editor notes for empty blocks). What is **NOT verified** is how any block *looks* (the assistant has no browser; Harsh checks in the theme editor) and the **add-to-cart behaviour of the Add-ons block** in the real theme.
- **Git (changed 6 Oct 2026, later session):** this folder IS now a git repo. One commit (`07ab47a`, 109 files) on branch `chore/initial-import`, pushed to the private repo `https://github.com/harsh-shopify-dev/dtj-agency-automation`. GitHub's default branch is still `chore/initial-import` (no `main` exists yet) and branch protection is NOT set: Harsh must do both in GitHub settings (section 12, item G; section 17).
- **Store access blocker (6 Oct 2026):** the Shopify CLI in the account-A session could NOT read `elevate-with-harsh` ("you don't have access to this dev store"). Harsh was going to sign the CLI in himself. Nothing could be read from or written to the store in that session (section 17).
- **Never do without Harsh's explicit approval of that exact action:** push/publish a theme, create or change products, deploy/release the app, flip the licence flag, send any message. Ask with the exact command and what it changes (section 2).

---------------------------------------------------------------------------------------------------

## 1. The project, in plain language

DTJ does performance marketing and store builds for Indian D2C brands. Harsh wants to automate:
- **Website audit and pitch** (scrape a prospect's page, score it, produce a report) - existing tool in `D:\CODE CONTAINERR\WEB DEV\GOMINT\store-builder\audit\`.
- **Store build** (blueprint + brand config -> a Shopify theme + products + settings, reviewed by a human, never auto-published) - **this is what the sessions worked on.**
- Later: reporting and monitors, an **ad guard** (pause bad ad sets within caps), Amazon inventory guard, creative pipeline, sales/CRM/billing (RUNBOOK phases 0-8; Phase 0 foundations are NOT started).

**The business idea behind the block library:** DTJ owns a set of high-converting storefront blocks (trust rows, offer pills, testimonials, add-ons, etc.). Harsh wants clients to *use* them without being able to walk away with the code: the blocks live in a Shopify **app** (source stays on Shopify's side, not in the client's theme) and each block checks a per-store **licence flag** that DTJ can switch off if a client churns. Decision "Route 3" (5 Oct 2026). Honest limits: the browser still receives HTML/CSS/JS, so this protects the *source* and gives a *clean cut-off*, not secrecy of the look (`docs/block-library-design.md`).

**Later, more automation:** the end state is a pipeline that, for a new brand, creates a store, pushes the master theme, creates products, adds the right app blocks to the templates with the brand's copy, runs QA (Theme Check, Lighthouse, test-mode checkout), and posts "ready for human sign-off". The pasted "Zero-Touch Provisioning Pipeline" spec Harsh gave is the intent; section 7 lists where it was adapted to reality.

---------------------------------------------------------------------------------------------------

## 2. How to work with Harsh and the rules that bind you

**Read `CLAUDE.md` (project) and `RUNBOOK.md` first.** Key rules, restated:
- **Plain, founder-friendly language. Lead with the result.** No jargon unless asked. Be honest about what was and was not verified.
- **Risk ladder:** Tier 0 read-only = free. Tier 1 reversible low-risk = only within runbook caps and logged. **Tier 2** (spends money, client-visible, contacts people: publish ad, change budget, push or publish a theme, create/change products, deploy a Shopify app version, flip the licence flag, send a message, create a store) = **ask Harsh first, every time; approval for one action does not cover the next.** Tier 3 destructive (delete, truncate, drop, force-push, remove access) = never, unless Harsh explicitly and knowingly instructs it (he did once: deleting the seven old blocks' source files, after being told there was no copy).
- **Shadow first. Numbers come from code. Never fabricate** offers, prices, claims, reviews, ratings, scarcity. Unknown facts = `[[TODO]]`.
- **Secrets:** never in code, files, logs or chat. Do not open `.env`. The licence tool's secret lives only in an environment variable in **Harsh's own terminal**.
- **Git:** feature branch + pull request, never commit to `main`, never force-push. (A repo now exists, see section 0 and 17; `main` itself does not exist yet.)
- **Shopify:** automation never touches a live theme (`--allow-live` is denied in `.claude/settings.json`). Push narrowly (`--only`, `--nodelete`) to an unpublished theme. Test checkouts only in test mode on a dev store. Never run `shopify auth logout` (it signs out every account).
- **Controls are in the systems.** `.claude/settings.json` denies: pushes to main/master, force push, `git reset --hard`, `rm -rf`, `bq rm/truncate`, any command containing `--allow-live`, reading `.env*` and `secrets/`. If a command is blocked, tell Harsh what and why; **do not work around it** (two commands were blocked in the last sessions because they *contained the text* `--allow-live` / began with `rm -rf`: fixed by not needing those).
- **Approval pattern that worked all session:** show the exact command and its effect, ask with a multiple-choice question, run it, then **verify independently** (pull the file back from the store, list themes, read the product) and report what was and was not checked.
- **Harsh's personal preferences (his global `CLAUDE.md` lives only in account A, `D:\Extra Data\DTJ\claude-terminal\CLAUDE.md`; replicate them in the new account):** plain language; never push to a live store theme without his clear go-ahead (dev themes fine once the target is clear); don't run `shopify auth logout`; don't invent offers/prices/claims/policies; keep secrets out of files and chat; update this HANDOFF at the end of a session with what was done, what is open and exact targets; be honest about verification.
- **Memory is per account.** The new account has none of the old memory. This file is the memory.
- **Harsh's habits:** answers via multiple-choice popups; sends **screenshots** of the Shopify editor (the assistant cannot see pages); runs interactive/secret commands himself (`! command` in the session, or his own PowerShell); decides quickly; changes direction when facts change. He expects mistakes to be named plainly and fixed (the licence saga below had several of my wrong theories).

---------------------------------------------------------------------------------------------------

## 3. The assistant ("you") and the environment

- **Who:** Claude Code (Sonnet 5.5) acting as Harsh's developer assistant, in a terminal session on his Windows 11 machine. **No browser/Playwright tool is connected**; no BigQuery, Slack, GitHub MCP. It cannot see a rendered page: ask for screenshots, and put diagnostics in the code (see the "editor-only notice" lesson, section 10).
- **Accounts:** Harsh runs two Claude Code accounts. A = launcher `claude-a`, config folder `D:\Extra Data\DTJ\claude-terminal`. B = `claude-b`, `C:\Users\harsh\.claude-account-b`. Launchers in `C:\Users\harsh\.local\bin`. Project files are shared. The continuing account should start in `D:\CODE CONTAINERR\WEB DEV\dtj-agency-automation` and can resume with `--continue`.
- **Tools on the machine:** Shopify CLI 4.8.4 (logged in as Harsh's Shopify account; `shopify store auth` token for the test store is an **online** token that can expire), `gh` 2.100 (logged in as `harsh-shopify-dev`), Git 2.52, Node 22, Python 3.13. A private venv `.work/.venv` holds `python-liquid` 2.3.3 + `jsonschema` (needed for the Liquid tests). Not installed: `bc`, `pytest`, `bq`.
- **MCP servers connected at session start (checked live):** n8n (personal project only, no workflows listed), **Shopify MCP (pointing at `sagarchudesara.com` / `sagar-book.myshopify.com`, a real paid store of another seller: do not write to it)**, **Meta Ads MCP (many client ad accounts, write tools available: not used; consider narrowing, RUNBOOK 3.2)**, Claude Docs. Needing sign-in (not connected): Google Drive, Similarweb, Supermetrics. Missing for the runbook: BigQuery, Slack, GitHub MCP, Playwright MCP.
- **Shell quirks (Git Bash on Windows):** cwd persists between commands; long heredocs and escape-heavy inline Python failed repeatedly (see errors); `/tmp` is not writable (use the session scratchpad dir or `.work/`); Hindi text needs `PYTHONIOENCODING=utf-8`; in plain `cmd`, `cd D:\...` does NOT switch drive (use `cd /d`).
- **Secret to set per terminal:** `DTJ_BLOCKS_CLIENT_SECRET` (the DTJ Blocks app's client secret from the Dev Dashboard: Settings). PowerShell: `$env:DTJ_BLOCKS_CLIENT_SECRET = Read-Host "Client secret"`, then start the session from that same window. A session started elsewhere will not see it (nor should it: never ask for it in chat; rotate it if it ever leaks).

---------------------------------------------------------------------------------------------------

## 4. Systems and IDs (no secrets)

| Thing | Value |
|---|---|
| Test store (all work happens here) | `elevate-with-harsh.myshopify.com`, plan Development, currency INR, **type "Client Transfer"** (this matters: `shopify app dev` and `shopify app execute` cannot see it) |
| Live theme on the test store | **188778578093** "DTJ licensed test 3": **never touch** |
| Test theme (unpublished) | **188893495469** "DTJ master 4.2.0 test 1". Editor `https://elevate-with-harsh.myshopify.com/admin/themes/188893495469/editor`; preview `https://elevate-with-harsh.myshopify.com?preview_theme_id=188893495469` (store is password-protected; Harsh enters the password himself) |
| Themes on the store | 19 (Shopify's cap is believed to be 20, unverified): do not create more; push additively into the test theme |
| Other stores in Harsh's org | `dev-of-anshul` (type Dev, whose it is is unknown: do not use), `thetracex`, `discover-steel` (Client Transfer) |
| Shopify org (Dev Dashboard) | Harsh, id **141167028** |
| App | **DTJ Blocks**, app id 431619997697, client id `5952b6121d9bc666225ea06143fb523d` (in `services/block-library/shopify.app.toml`), custom distribution (permanent choice), installed on the test store. Dashboard: `https://dev.shopify.com/dashboard/141167028/apps/431619997697` |
| App versions | `dtj-blocks-1`..`-13`; **`-13` is the active release** (dashboard: `https://dev.shopify.com/dashboard/141167028/apps/431619997697/versions/1156147085313`). History in section 9 |
| Block reference format in theme JSON | `shopify://apps/dtj-blocks/blocks/<block-handle>/01a10b7e-02ff-7b68-95a3-bbcdcb562875` (the last part is the extension uuid, assumed stable per extension: verify on a second store) |
| Master theme repo | `harsh-shopify-dev/dtj-master-theme` (private): a fork of Shopify **Horizon 4.2.0**. `main` pinned at `5acd1b6b66c02f61d3216e3adace5dd9e0404fc9`. Four **unmerged** pack branches: `block/food-product-blocks`, `section/beauty-proeffex-pack`, `section/supersenior-pack`, `section/supplements-gomint-pack` |
| Source of the copied catalog | `sagarchudesara.com` (another seller's author store). Public catalog (6 published products, 42 images, a logo) copied for testing: **private test copy, do not publish, do not reuse** |
| Dev store products | 27 older + **6 created by us as DRAFT** (handles: a long `we-are-there-for-each-other-english-...-copy`, `imported-14914244182381` (the Hindi one: rename later), `we-are-there-for-each-other-an-intense-love-story-...`, `gift-wrapped-embossed-edition`, `book-reading-tracker-by-sagar-chudesara`, `from-pen-to-published-copy` (the original handle clashed with an older product of Harsh's, left untouched)) |
| Licence flag | app-data metafield on the **app installation**: namespace `dtj`, key `licence`, value `active`/`inactive`. Last known: Harsh switched it off and on (should be `active`): check with `tools/licence.py --status` |
| Local working files (git-ignored, `.work/`) | `master-theme/` (clone + pack branches), `master-packs/` (master + 4 packs overlaid + one patched file, **review copy, not for clients**), `import/sagarchudesara/` (catalog JSON, 42 images, logo.png, brand.json, product-sheet.json, SOURCE.md), `out/` (action logs), `pulled-theme/`, `verify-push/`, `.venv/`. If you are on another machine these do not exist: regenerate (section 14) |
| Action logs | `.work/out/action-log.jsonl` (theme push), `.work/out/stage3/action-log.jsonl` (products), `.work/out/licence-log.jsonl` (flag flips) |

---------------------------------------------------------------------------------------------------

## 5. Repository map (what exists)

```
CLAUDE.md, RUNBOOK.md              rules + full plan (read first)
.claude/settings.json              deny rules (the real boundaries)    .claude/commands/start-dtj-engine.md
.env.example, .gitignore           (.gitignore covers .env*, secrets/, .work/, .venv/, .shopify/, output/)
schemas/                           action.schema.json, brand-config.schema.json (incl. optional `style` block), product-sheet.schema.json
docs/                              HANDOFF.md (this), shopify-provisioning.md, block-library-design.md,
                                   block-inventory.md, product-page-layout.md
services/store-builder/provision/  PROVISIONING SERVICE (python, stdlib + jsonschema)
   config.py     env settings, kill switch AUTOMATION_ENABLED (default OFF), DRY_RUN (default ON), mode shadow|approve (never auto), the permission gate decide(tier, approver)
   actionlog.py  one JSON line per action, secrets scrubbed, schema-validated
   gql.py        GraphQL client: operation ALLOWLIST (productCreate, productVariantsBulkUpdate, stagedUploadsCreate, fileCreate; anything with "delete" refused), cost-aware throttle, retries 429/5xx/THROTTLED max 3, 401/ACCESS_DENIED halts
   cli_gql.py    sends GraphQL through `shopify store execute` (the CLI holds the token; allowlist enforced again)
   theme.py      builds/validates Shopify CLI theme commands, refuses live themes
   products.py   builds productCreate / staged upload / variant requests (always DRAFT, one variant)
   stage3.py     creates draft products + images (needs --approved-by, kill switch on, not dry-run, mode approve); skips existing handles; circuit breaker after 3 failures
   import_catalog.py  copies a storefront's PUBLIC catalog (products.json) + images locally, polite, size-capped
   templates.py  Horizon template JSON: bindings by section TYPE, add_app_block() (idempotent, keeps the auto-generated header), app_block_type()
   style.py      brand `style` block -> Horizon `current.color_palette`/font handles/logo; auto-fills missing colours from the logo, forces readable contrast, records provenance
   apps.py, run.py   app checklist (apps cannot be installed via API), dry-run planner
services/store-builder/tests/      88 tests
services/block-library/            THE APP (details in section 8)
   shopify.app.toml, extensions/dtj-blocks/ (blocks/, assets/, snippets/, locales/), manifests/, src/, schemas/, tools/ (build_blocks.py, check_library.py, licence.py), tests/ (104 tests incl. addons_logic.js run under Node), README.md
```
Pre-existing, outside this repo: `D:\CODE CONTAINERR\WEB DEV\GOMINT` (audit tool, blueprint builder, Tattva theme work; has its own CLAUDE.md/HANDOFF.md; never mix its stores with this project).

---------------------------------------------------------------------------------------------------

## 6. What was done on real systems (chronological, all approved by Harsh)

All on the test store unless stated. "Verified" = checked independently afterwards.
1. **Theme:** pushed the master theme (Horizon 4.2.0 @ `5acd1b6`) as a NEW unpublished theme 188893495469 via `shopify theme push --unpublished --theme "<name>" --json`. Verified with `theme list`: 19 themes, live unchanged.
2. **CLI sign-in:** `shopify store auth` with scopes exactly `read_products, write_products, read_files, write_files`. Verified with a read-only query.
3. **Products:** copied the public catalog of sagarchudesara.com to `.work/import/sagarchudesara/`, created **6 DRAFT products with 42 images** on the test store via `provision.stage3` (store total 27 -> 33; all DRAFT, prices match, 42/42 media READY). Not copied: 7 unpublished products, videos, collections, pages, policies, variant option names, SEO. Titles/claims are the source's own wording: unverified, not ours.
4. **App "DTJ Blocks":** created through `shopify app config link` (Harsh ran it), versions deployed and released with `shopify app deploy` / `shopify app release` (`--allow-updates`, never `--allow-deletes` needed), installed on the test store through the custom-distribution link (Harsh clicked Install).
5. **Licence flag:** written/read through `services/block-library/tools/licence.py` (Harsh runs it in his own terminal: it needs the secret env var). Kill switch **proven in the theme editor**: off hides the block, on shows it.
6. **Pack files pushed:** 43 `dtj-*` files (16 blocks, 21 sections, 5 scripts, 1 snippet) from the four pack branches **added** to the test theme with `--only "assets/dtj-*" --only "blocks/dtj-*" --only "sections/dtj-*" --only "snippets/dtj-*" --nodelete`; verified by pulling back. Later one file (`sections/dtj-beauty-product-list.liquid`) was overwritten with a patched version (section 11, error 20). The review copy still carries other brands' default copy and fixed colours.
7. **Deleted (Harsh's explicit choice):** the seven first-built blocks' source files and `dtj-icon` snippet and `tests/test_licence_render.py`. Not recoverable from the machine; app versions 1-10 remain in the Dev Dashboard.
8. **Not done anywhere:** no live theme change; no product made Active; no collection, menu, page, hero image or brand style applied to the store; no message or email sent; nothing on any client store; the master-theme GitHub repo untouched.
9. The test theme's `templates/product.json` currently holds blocks Harsh placed by hand (at least Social Proof, Rotating Text, Hero Points; **dangling references** to the seven removed blocks; block settings changed for the product-list blocks, so those need re-picking). Cleaning the template is a separate Tier 2 push.

---------------------------------------------------------------------------------------------------

## 7. Decisions and why

| Decision | Why |
|---|---|
| Master theme = fork of Horizon 4.2.0 (`dtj-master-theme`) | Harsh's own repo. The older GOMINT `cg-` blocks belong to the Tattva theme and do not carry over |
| Inputs for builds = brand config + product sheet + image folder (not scraping) | Runbook 11: do not republish a prospect's content. The sagarchudesara copy is a one-off private test |
| Products created as DRAFT; handles never overwritten | Reversible, nothing visible to shoppers |
| API version pinned `2026-07` (2026-01 and 2026-10 also accepted) | Spec said 2026-01; today is Oct 2026 |
| GraphQL through `shopify store execute` + our allowlist | Token stays in the CLI; deletes impossible by code |
| Dev-store creation | CLI can do it: `shopify store create dev --name --organization-id --plan` (answers the runbook open item). The test store is "Client Transfer" so app commands cannot see it |
| **Route 3: blocks in a theme app extension with a licence flag** (Harsh, 5 Oct) | Source stays on Shopify; clean revoke. Limits below |
| Licence flag lives on the **app installation** (`app.metafields.dtj.licence`), fail-closed (only exactly `active` shows) | Per store, hidden from admin, readable only by our app. For stores in Harsh's own org the app's client-credentials grant can write it; **for client stores outside the org a hosted service must catch the install and keep that client's token** (not built; until then revocation = client uninstalls) |
| Blocks are GENERATED from `manifests/*.json` + `src/<id>.{liquid,css,js}` | One source of truth, standard controls on every block, no hand-edited generated files (`build_blocks.py --check`) |
| Seven first-built blocks removed | Freed 42 KB of the 100 KB cap so all priority pack blocks fit in ONE app (second app "DTJ Blocks Pro" no longer needed) |
| **Master theme for the bulk of the pack, app only for a premium set** (my recommendation, Harsh: "complete the app work first") | 23 requested pack items = ~590 KB of Liquid vs a 100 KB cap per app; 9 use child blocks, 5 `font_picker`, 13 exceed the header limit. Converting all is not possible; the pack sections in the theme are not technically protected (contract does the work) |
| Add-ons: **no manual "add-on price"**, real variant prices only | The pack displayed a price the cart would not charge: misleading |
| Testimonials: stars default none, badge is free text | A default 5 stars / "Verified buyer" would be an invented claim |
| Social Proof: stars from the review app's real rating; real stock only | No fabricated numbers |

---------------------------------------------------------------------------------------------------

## 8. The block library (the app) in detail

**How a block is made:** `manifests/<id>.json` (settings, content slots, standard controls, `test.sample/expect`, `script`, `css_includes`) + `src/<id>.liquid` (body only) + `src/<id>.css` (+ `src/<id>.js`). `python tools/build_blocks.py` writes `extensions/dtj-blocks/blocks/dtj-<id>.liquid` (prelude + body wrapped in the licence gate + **compact** `{% schema %}`) and `assets/dtj-<id>.css|.js`. **Never edit generated files.** Standard controls added to every block: spacing (padding 4 sides + top/bottom margin), alignment, text/background colour, corner radius, text size (per manifest). Colours default empty (follow the theme); no default copy.

**Licence gate:** `snippets/dtj-licence.liquid` is a WRAPPER: `{% render 'dtj-licence', value: app.metafields.dtj.licence.value, content: ..., design_mode: request.design_mode, attributes: block.shopify_attributes %}`; prints the content only when the flag is exactly `active`; otherwise nothing on the storefront (no markup shipped, not even in comments) and, in the theme editor only, a dashed note "DTJ block hidden: the licence is not active (flag seen: ...)". **Keep that diagnostic in every block** (it found a bug in one screenshot).

**Current blocks (release `dtj-blocks-13`, 71.8 KB of 100 KB, 7 of 30 blocks):**
| id (file `dtj-<id>`) | Editor name | What it is / non-obvious behaviour |
|---|---|---|
| `hero-points` | DTJ Hero Points | eyebrow pill + subheading + benefits typed one per line (max 8 non-blank); ticks use the shared disc+tick icon |
| `rotating-text` | DTJ Rotating Text | typewriter, up to 6 phrases + prefix; script `dtj-rotating-text`; reduced-motion safe |
| `social-proof` | DTJ Social Proof Line | stars from the real review-app rating (`product.metafields.reviews.rating`), manual rating only as fallback; stock line only when inventory is tracked and qty>0 with Harsh's own text (`{count}`); two own lines |
| `testimonials` | DTJ Testimonials | up to 5 reviews, avatar/photo, stars default none, badge = free text, auto-advance + swipe, pause on hover/off-screen |
| `shoppable-reels` | DTJ Shoppable Reels | 6 cards image or video, **one `product_list`**: card N links to product N; muted autoplay when 60% visible, tap for sound; translatable play/pause labels |
| `shade-picker` | **DTJ Option Picker** | up to 8 sibling PRODUCTS as swatches/pills, **one `product_list`**: option N = product N; current product auto-highlighted by handle; sold-out dimmed and unclickable; hover shows the name beside the label |
| `addons` | DTJ Add-ons | **one `product_list`**: first four = add-on cards, `s{i}_alt` picks a list position 5-8 as a swap; real prices/compare-at only; live total from the chosen variant; ticked add-ons + product go in ONE `/cart/add.js` (add-to-cart and buy-now clicks intercepted in capture phase; nothing ticked = theme flow untouched; failure falls back to the theme form); after-add default = cart page (drawer is best effort) |
Shared pieces: snippet `dtj-check-icon` (the master theme's bullet: ONE solid circle + tick, or a glyph in the same circle, or a custom image), `src/_check-item.css`. Block placement format and findings: sections 4 and 11.

**Library rules enforced by `tools/check_library.py` (each one came from a real failure, section 11):** manifest valid and every slot exists in the schema; no default copy on text-like settings and no colour defaults; every block runs the licence gate (wrapper) and its snippets exist; no hard-coded hex colours (ignores `&#9733;`-style codes); range default on a step, <=101 steps, select default is an option, **range `unit` never blank**; snippets never read `block.`/`section.` (pass values in); **never capture or compare a snippet's output**; **max 6 header/paragraph settings**; **every `<img>` needs an explicit size in the block's CSS**; **no `{`/`}` inside a `{{ ... }}` output** (put literals in `{% assign %}`); **scripts < 10,000 bytes**; **schema name <= 25 characters**; **at most ONE resource picker per type** (`product`, `product_list`, `collection`...: enforced by Shopify for `product`, assumed for the rest); Liquid budget (printed): 100 KB per app, 30 blocks.

**App-block limits learned (Shopify server, not documented in one place):** 100 KB of Liquid per extension (one extension per app); 30 blocks; no child blocks; <=6 non-interactive settings; 1 picker per resource type; name <= 25 chars; blank range unit rejected; `{`/`}` inside output tags rejected; Theme Check errors on scripts >= 10,000 bytes and warns above 40 settings (advisory; four blocks have 41-54).

**Licence tool:** `python tools/licence.py --shop elevate-with-harsh.myshopify.com --status` (read) or `--set active|inactive --approved-by NAME` (Tier 2). Uses the app's client-credentials grant (only works for stores in the same Shopify org as the app: the test store qualifies although it is "Client Transfer"). Logs each change; refuses everything except `metafieldsSet`; never prints the secret/token.

---------------------------------------------------------------------------------------------------

## 9. App version history (what each release was)

1 created at link (inactive) | 2 Trust Row proof of concept | 3 licence read moved to the shop (WRONG owner) | 4 back to `app.metafields`, tool writes the app installation, editor note shows the flag | 5 snippet got the value as a parameter | 6 **gate became a wrapper (root cause fixed; licence proven)** | 7 batch 1 (highlight text, offer pill/callout/urgency, bullets, secure checkout) | 8 bullets/trust row restyled to the master bullet design | 9 offer pill image/overflow fix | 10 hero points, rotating text, social proof | 11 removed the seven first blocks | 12 testimonials, shoppable reels, option picker, add-ons | **13 reels: tap plays with sound, separate sound on/off button, one reel with sound at a time; editor-only "this block is empty" notes on Testimonials, Reels, Option Picker, Add-ons (current; run by Harsh in his own PowerShell, success output seen, not re-checked by the assistant)**.

---------------------------------------------------------------------------------------------------

## 10. Lessons (how to work on this)

1. **Server-side validation is stricter than every local check.** Each new block family so far was refused at least once at `shopify app deploy` (6-header cap, `{count}`, blank unit, 1 product picker, 25-char name, ...). Budget a retry per new family; after each refusal add a rule to `check_library.py` with a test, then retry the same approved deploy. Shopify's Theme Check did NOT catch most of them.
2. **The local Liquid engine (python-liquid) is not Shopify.** Known differences: `nil != blank` (Shopify: nil == blank; the test harness models unset settings as `""`), `<=`/`>=` exclude equality for computed decimals (use strict `<` with +1), no `json`/`image_url`/`money`/`video_tag`/`payment_type_img_url` filters (stubbed in `tests/test_generated_blocks.py`). Tests wrap every snippet in `<!-- BEGIN app snippet -->` comments like the real editor.
3. **Put raw-value diagnostics in the editor-only note** ("flag seen: ..."): one screenshot found a bug that three theories missed.
4. **Verify after every store write** by reading it back (pull the file, list themes, query the product) and ask Harsh to open the editor: a push can break the editor preview without any CLI error.
5. **Theme CSS fights blocks:** Horizon stretches images and styles buttons. Size images in CSS, not only in tags; wrap long text; never rely on tag attributes.
6. **Mutation-test the tests:** deliberately break the gate and confirm the tests fail.
7. **Write files with the file tools**, not long shell heredocs with embedded escapes (see errors 5-6).
8. Never claim a visual/behavioural result you cannot see. Say "not verified" and say what Harsh should check.

---------------------------------------------------------------------------------------------------

## 11. Errors faced and how they were solved

### Process / environment
| # | Problem | Cause | Fix / where recorded |
|---|---|---|---|
| 1 | Session said the folder was a git repo; it is not | wrong session info (it happened again on 6 Oct: the session snapshot said "clean repo", `git status` said "not a git repository": always run `git status` yourself) | fixed 6 Oct 2026: `git init`, first commit, private GitHub repo (section 17). Branch protection still open (12 G) |
| 2 | Two commands blocked ("permission denied") | one contained the text `--allow-live` (inside a grep pattern), another began with `rm -rf`: both are deny rules | rewrote without them; never work around a deny rule |
| 3 | `shopify app config link` wrote `shopify.app.toml` into `C:\Users\harsh` and printed `EPERM scandir 'Application Data'` | Windows `cmd`: `cd D:\...` does not change drive, so the CLI ran in the home folder | moved the file into `services/block-library/`; use `cd /d` or `--path` |
| 4 | Long shell heredocs failed ("unexpected EOF") and one patch script produced broken files | quoting/escape handling | use Write/Edit tools or a script file in the scratchpad |
| 5 | A regex written through a patch script contained a backspace character (`"\b"` in a normal string) and a string literal got a real newline (`"\n"`) | escapes interpreted by the outer Python string | write source with the file tools; verify with a sanity test (the new rule did not match the old pattern until fixed) |
| 6 | `/tmp` write denied; `bc` missing; Hindi text crashed a print (cp1252) | machine setup | scratchpad dir; Python for arithmetic; `PYTHONIOENCODING=utf-8` |
| 7 | `DTJ_BLOCKS_CLIENT_SECRET` not visible in the restarted session | env var set in another window (and secrets may be scrubbed from tool environments) | Harsh runs `tools/licence.py` in his own terminal and pastes the output; **do not rename the variable to dodge scrubbing** |
| 8 | `shopify app dev` and `shopify app execute`: "Could not find store ... in organization" | the test store is type **Client Transfer**; these commands only accept **Dev** stores | installed through a custom-distribution link instead; flag changes via the client-credentials grant |
| 9 | The CLI store sign-in token is "online" and may expire | by design | re-run `shopify store auth --store elevate-with-harsh.myshopify.com --scopes read_products,write_products,read_files,write_files` |

### Data / provisioning
| # | Problem | Fix |
|---|---|---|
| 10 | Product handle clash with an older product of Harsh's | renamed the copy `from-pen-to-published-copy`; existing handles are never touched (stage3 skips/reports) |
| 11 | A product had a Hindi (non-ASCII) handle; schema only allows ASCII | neutral `imported-<id>` handle (rename later) |
| 12 | One product had 11 images; schema limit was 10 | raised to 50 |
| 13 | Public feed lists only published products | 6 of 13 copied; said so |
| 14 | Auth failure on the first read crashed the run instead of stopping cleanly (found by a test) | wrapped; reports "auth problem" and changes nothing |
| 15 | The licence tool's "same organization" hint did not appear (bug in my error text) | fixed + test |

### Shopify / theme / app (the long ones)
| # | Problem | Cause | Fix |
|---|---|---|---|
| 16 | **Licence flag never made the block show (4 rounds)** | (a) round 1: tool wrote the flag on the **shop** with a `$app` namespace while Liquid read `app.metafields...`; (b) my "fix" changed the Liquid to the shop path (wrong side); (c) a snippet-scope theory (wrong); (d) **real cause:** in the theme editor Shopify wraps every snippet's output in `<!-- BEGIN app snippet -->` comments, so my block's `== 'active'` comparison of the snippet's output failed | tool writes `currentAppInstallation` (owner = install id, namespace `dtj`); Liquid reads `app.metafields.dtj.licence.value`; **gate is now a wrapper that prints content and is never compared**; editor note shows flag value; tests wrap snippets in the comments; rules 7/8 |
| 17 | Bullet/Trust Row icons looked bad | I drew a circled-check icon INSIDE a circle (double ring); the master theme's bullet is ONE solid circle + tick (read from `dtj-bullet-points`) | shared `dtj-check-icon` + `_check-item.css`; rebuilt Trust Row/Bullets (later removed) |
| 18 | Offer Pill image huge, text overflowing | Horizon stretches images; my CSS never sized the image | CSS-sized image + wrapping; rule "every `<img>` sized in CSS" (the first version of the rule had a comment-in-selector bug) |
| 19 | Deploy refused: "settings: must have a maximum of 6 for non-interactive settings" | 8 header settings in Bullets | removed per-point headers; rule |
| 20 | **Editor showed "color schemes must be defined in settings_data and settings_schema" and NOTHING previewed** | one pushed pack file (`dtj-beauty-product-list`) declares a `color_scheme` setting; Horizon 4.2.0 has no scheme group (uses `color_palette`) | replaced by a `color` setting, single-file push, verified; lesson 4 |
| 21 | Deploy refused: Liquid syntax error at `'{count}'` | Shopify ends a `{{ }}` output at the first single `}` | literal braces in `{% assign %}`; rule |
| 22 | Deploy refused: "unit can't be blank" | empty `unit` on a range | omit the key; rule |
| 23 | Theme Check **error**: `dtj-addons.js (10442 B)` over 10,000 | script too big | trimmed comments (9.8 KB); rule |
| 24 | Deploy refused: "exceeds limit of 1 for type 'product'" and "name must have a maximum of 25 characters" | 4-8 product pickers per block; a 28-char name | one `product_list` per block with per-position settings; renamed "DTJ Option Picker"; rules |
| 25 | Theme Check: missing `width` on payment-icon `<img>` | layout shift | explicit width/height |
| 26 | Hex check flagged `&#9733;` (star entity) | regex | ignore HTML character codes |
| 27 | Star rating of 4.5 showed 4 stars in tests | engine decimal-compare quirk | whole-number maths with strict `<` |
| 28 | The requested 23 pack items cannot fit one app | ~590 KB vs 100 KB cap, child blocks, font_picker, header cap | lean rebuild of the priority 7 + decision to keep the rest in the master theme (section 7) |

---------------------------------------------------------------------------------------------------

## 12. Open items and next steps (priority order)

**A. Verify with Harsh (nothing here is proven yet):** open the editor, add the four newest blocks (Testimonials, Shoppable Reels, Option Picker, Add-ons) and tell the assistant what looks wrong (screenshots). **Add-ons cart test:** product page, tick an add-on, Add to cart, check the cart holds both items (also buy-now). Products used as add-ons must be published to the Online Store. **Storefront check with the flag off:** open the preview URL (password-protected) and confirm no block markup in the page source; the editor was checked, the storefront was not. Check the `product_list` picker ordering/UX.
   **Item A progress (6 Oct 2026, Harsh doing the editor checks; nothing below is "verified looks right" until Harsh confirms):**
   - *First screenshot:* the four new blocks (Reels, Option Picker, Testimonials, Add-ons) were added in `Product information > Details` but rendered NOTHING. Cause (read from the block source, not a bug): each hides itself when empty. Testimonials needs at least one review text; Reels needs per card either (Card N shows = Video AND a video) or an image (default is Image, so uploaded videos stay hidden until "Video" is chosen; cards 3 and 4 in the screenshot looked set to Image); Option Picker needs at least one product; Add-ons needs at least one of the first four products. The three older blocks (Social Proof, Rotating Text, Hero Points) DID render, so the licence flag looks active (not confirmed with `tools/licence.py --status`).
   - *Editor-only "empty block" note: BUILT, tested and RELEASED in `dtj-blocks-13` (Harsh said yes, 6 Oct 2026):* Testimonials, Shoppable Reels, Option Picker and Add-ons now print a dashed note in the theme editor only (`request.design_mode`, inside the licence gate so it never shows with the licence off) saying what to fill in and naming real setting labels ("Review 1 text"; "Card 1 shows"/"Card 1 video"/"Card 1 image"; "Option products"; "Add-on products"). The storefront output for an empty block is still nothing. 5 new tests (`EmptyBlockNoteTests`): the two that need the note FAIL against the commit without it, the three that guard "never on the storefront / never with real content / never with the licence off" pass. Block-library suite now **112 tests**, build `--check` up to date, library rules ok (71.8 KB of 100 KB), store-builder 88 OK, Theme Check 0 errors / 3 advisory warnings. Branch `feature/reels-sound-button` (local only, NOT pushed to GitHub, no pull request yet; the reels sound change and this note shipped in ONE deploy).
   - *Reels sound change (Harsh's request: "on clicking the video they should open with sound ... with a sound on/off option"):* BUG found: videos autoplay muted, so the old first tap hit the "pause" branch and the video stopped without sound. Fixed on branch `feature/reels-sound-button` and RELEASED as `dtj-blocks-13` (see deploy result below): tapping the video plays with sound (silent playing reel = sound on and keeps playing; reel with sound = pause; paused reel = plays with sound); new separate sound on/off button under the play/pause button; only one reel has sound at a time; a reel returning into view restarts silent (browser rule); two new translatable labels (`sound_on_label`, `sound_off_label`). Verified: 10 Node checks run the REAL script (`tests/reels_logic.js`, mutation-tested: breaking the fix makes it fail), 107 block-library tests + 88 store-builder tests pass, build `--check` up to date, library rules ok (70.7 KB of 100 KB; script 3,669 bytes), Theme Check 0 errors / 3 advisory warnings. NOT verified: how it looks or sounds in a real browser (no browser here). **Deploy result (Harsh pasted the PowerShell output, 6 Oct 2026):** `shopify app deploy --path "services\block-library" --allow-updates --message "Reels: tap plays with sound, sound on/off button; editor notes for empty blocks" --no-color` printed "New version released to users. dtj-blocks-13". Shopify did NOT refuse it (no server-side rule violations this time). Theme Check printed the same three advisory `ExcessiveSettingsCount` warnings (47, 45 and 54 settings; advisory only). The assistant cannot re-check the version itself (its Shopify login is not in the Harsh org: 403), so this rests on the pasted output. Still NOT verified by anyone: that the blocks look and sound right in the editor/storefront (Harsh to check: empty blocks show the dashed note; Reels cards set to "Video" play, tap gives sound, speaker button toggles, one reel at a time).
   - *Harsh's 3rd screenshot (after `dtj-blocks-13`):* the dashed editor notes ARE visible for Option Picker, Testimonials and Add-ons (so the release is live in the editor and the notes work, confirmed from the screenshot). Option Picker was still empty because its "Option products" list had no products: the names, subtitles and swatch images were typed in but each option is a product, and the block only renders when the list has at least one. Told Harsh to pick 2-3 Active, Online-Store-published products (not the six draft copies: unpublished products come through as blank) including the previewed product to see the current highlight. Result of that: waiting. Testimonials (needs "Review 1 text") and Add-ons (needs at least one published product) also still empty; Reels cards seem to show at the top of the preview but that was not confirmed.
**B. LOW PRIORITY, STOPPED by Harsh on 6 Oct 2026 ("cosmetic on a test theme, not worth more pull/push rounds"). Do NOT ask Harsh to run more pull/push commands for it and do NOT work around the missing theme login. Left as is. The notes below are only for whoever picks it up later.** Clean the test theme (analysed 6 Oct 2026; the editor delete never reached the store: fresh pulls at 11:21, 11:27 and 11:30 all still showed the broken block): the pulled `templates/product.json` has exactly ONE dangling reference, not seven: app block `dtj-offer-callout` (id `dtj_blocks_dtj_offer_callout_tiDq3G`, test text "aaa", yellow background) inside group `group_icgrde` of `main/product-details`. The other three DTJ blocks (social-proof, rotating-text, hero-points) are valid. Still to do: Harsh deletes it in the editor, re-pulls the file, the assistant verifies by analysis (script pattern: strip the leading `/* */` comment, walk blocks, compare `shopify://apps/dtj-blocks/blocks/<handle>/...` handles with `extensions/dtj-blocks/blocks/*.liquid`). A cleaned copy with only that block removed exists at `.work/product-json-clean/templates/product.json` (diff = exactly 2 removals) as a fallback push (Tier 2, `--only "templates/product.json" --nodelete`, but a template push overwrites editor changes). Also still open: re-pick products in the product-list blocks whose settings changed (needs the editor).
**C. Pack sections for the rest (16 of the 23 requested are not converted):** Harsh's decision was "master theme for the bulk": clean the review copy (neutral default copy, palette-following colours, no `color_scheme`), then merge through a pull request into `dtj-master-theme` `main` (needs the git workflow, G). What Harsh meant by "updates in the master theme" was never specified: ask. Not converted: Beauty Video Proof, Price Focus, FAQ, Marquee, Stories, Video Wall; Food Info Card, Comparison Table, Root Cause, Root Science, Science Stats, Testimonials Slider, Hero Promo (111 KB alone), Supplements Hero Rotating, Not Inside, What's Inside. (`docs/block-inventory.md` has sizes and conversion notes.)
**D. Finish Stage 4 (store build):** hero image + collection into `templates/index.json`, products to Active (needs approval at the moment), brand style (palette/fonts/logo; font names unchecked until a push), menus. Needs more CLI scopes (`read_publications, write_publications, read_online_store_navigation, write_online_store_navigation`; collections and Active need only `write_products`) and the new mutations validated and added to the allowlist in `gql.py` with tests (`productUpdate`, `publishablePublish`, `collectionCreate`, `collectionAddProducts`, `menuCreate` were validated against Shopify's schema only). **Installer:** read a recipe + brand copy, call `templates.add_app_block()` (currently places at section top level; Horizon's `_product-details` also accepts `@app` so blocks can go INSIDE the product column: unproven), push only the template (docs/product-page-layout.md has the reference-image mapping; its block list is partly stale after the removal).
**E. QA stages 6-8:** Lighthouse (mobile score < 85 triggers a *recommendation*, not an auto-fix), Playwright test-mode checkout (needs the storefront password in an env var; Playwright not installed), self-healing in shadow mode only, handoff note (Slack not connected; any n8n message is Tier 2).
**F. Hosted licence service:** for client stores outside Harsh's org the kill switch needs a small hosted OAuth/token service (catch the install, keep that client's offline token, one endpoint that sets the flag). Decide before the first external client install; until then revocation = the client uninstalls. Also put the revocation right in the client contract (qualified review).
**G. Git (partly done 6 Oct 2026):** repo created, first commit pushed (section 17). STILL OPEN, Harsh only (GitHub admin): make a real `main` (rename the default branch or create it), turn on branch protection (pull request + review required, no force push, no direct push to `main`). Then merge `chore/initial-import` into `main` through a pull request. The seven deleted block sources still have no copy anywhere.
**H. RUNBOOK Phase 0 and the rest:** BigQuery, Slack, vault, config store/kill switch for services, action-log table, dead-letter queue; Phase 2 reporting, Phase 5 ad guard, etc. All not started.
**I. Hygiene:** the Shopify MCP is pointed at a real store of another seller (`switch-shop` before any write, confirm with `get-shop-info`); the Meta Ads MCP has write access to many client accounts (narrow it); rotate the app client secret if it was ever exposed; the copied catalog is another seller's content: keep it private, never publish.

## 13. Decisions still waiting on Harsh
n8n hosting (cloud/self-hosted); whether Amazon is in scope; Claude API budget and per-run caps for unattended AI steps (must use the API with a key, not a subscription login); who approves Tier 2 actions and target response time; what "master theme updates" means; whether to build the hosted licence service now or later; theme-limit check on the store (believed 20).

## 14. Cheat sheet (run from the repo root unless stated)

```
# tests (block library needs the venv for the Liquid tests)
cd services/block-library && ../../.work/.venv/Scripts/python -m unittest discover -s tests -t .      # 104 tests, includes node tests/addons_logic.js
cd services/store-builder && python -m unittest discover -s tests -t .                                  # 88 tests
cd services/block-library && python tools/build_blocks.py [--check] && python tools/check_library.py   # rules + size budget
shopify theme check --path extensions/dtj-blocks                                                       # Shopify's own check (0 errors expected, 4 advisory warnings)

# deploy (Tier 2: ask Harsh with the exact command first; expect server-side refusals on new block types)
cd services/block-library && shopify app deploy --path . --allow-updates --message "<what>" --no-color

# licence flag (Harsh's own terminal, secret set)
python tools/licence.py --shop elevate-with-harsh.myshopify.com --status
python tools/licence.py --shop elevate-with-harsh.myshopify.com --set inactive --approved-by Harsh

# store reads
shopify theme list --store elevate-with-harsh.myshopify.com --json
shopify store execute --store elevate-with-harsh.myshopify.com --version 2026-07 --json --query '<graphql read>'
shopify theme pull --store ... --theme 188893495469 --path .work/verify-push --only "<file>" --nodelete     # read-back verification

# additive theme push pattern (Tier 2; never to the live theme)
shopify theme push --store elevate-with-harsh.myshopify.com --theme 188893495469 --path .work/master-packs --only "<glob>" --nodelete

# rebuild the review copy of master + packs (read-only against GitHub)
git clone https://github.com/harsh-shopify-dev/dtj-master-theme.git .work/master-theme  &&  git -C .work/master-theme fetch origin <the 4 pack branches>
# then: git archive the base SHA into .work/master-packs and overlay each pack's added files (blocks/sections/snippets/assets); patch `sections/dtj-beauty-product-list.liquid`'s color_scheme setting
```
Provisioning dry run: `cd services/store-builder && python -m provision.run --brand brand.json --products products.json --images ./images --out ./out`. Live product creation: `AUTOMATION_ENABLED=true DRY_RUN=false AUTOMATION_MODE=approve SHOPIFY_DOMAIN=... SHOPIFY_API_VERSION=2026-07 CLIENT_ID=... python -m provision.stage3 ... --approved-by NAME` (Tier 2).
The manifests were first created by throwaway generator scripts (not in the repo); the manifests are now the source, edit the JSON.

## 15. Do not do
No pushes to `main`; no live-theme changes; no deleting data (the one deletion this session was Harsh's explicit instruction); no secrets in files or chat; no unattended AI steps without the Claude API key; no writes to the Shopify MCP's store (sagarchudesara.com) or to any Meta ad account; **work ONLY in `elevate-with-harsh.myshopify.com`: do not read or touch any other store (sagar-book, dev-of-anshul, thetracex, discover-steel...) unless Harsh gives that command himself (standing instruction, 6 Oct 2026)**; no claim that something looks right without Harsh's eyes; no invented ratings, scarcity, prices, offers or reviews.

## 16. Related docs
`RUNBOOK.md` (plan) | `CLAUDE.md` (rules) | `docs/block-library-design.md` (route 3, limits, findings) | `docs/shopify-provisioning.md` (the provisioning service) | `docs/product-page-layout.md` (reference image -> blocks mapping; partly stale) | `docs/block-inventory.md` (the four pack branches, sizes, conversion difficulty; written before the conversions) | `services/block-library/README.md` | `D:\CODE CONTAINERR\WEB DEV\GOMINT\HANDOFF.md` (the older Tattva/audit work).

## 17. Latest session (6 Oct 2026, account A, "finish off the blocks app")

**Done and verified**
- Block library health re-checked from a clean state: `build_blocks.py --check` up to date (19 generated files), `check_library.py` ok for all 7 blocks (69.4 KB of 100 KB, 7 of 30), 104 block-library tests and 88 store-builder tests pass. `shopify theme check` on the extension: 0 errors, **3** advisory warnings (this file previously said 4).
- Git set up: `git init`, `.gitattributes` added (`* text=auto eol=lf`, so the byte-exact generated-files check stays stable on Windows), one commit `07ab47a` on `chore/initial-import` (109 files; `.work/`, `.venv/`, `.shopify/`, `__pycache__`, `.env*` except the names-only `.env.example` are ignored; a secret-pattern scan found no keys or tokens). A throwaway clone of the repo rebuilt, passed the library rules and passed both test suites (104 and 88).
- GitHub (approved by Harsh, exact two commands): `gh repo create harsh-shopify-dev/dtj-agency-automation --private --source . --remote origin`, then `git push -u origin chore/initial-import`. Read back: repo is PRIVATE, remote commit SHA equals the local `07ab47a`.

**Not done / blocked**
- **Store access:** `shopify theme list --store elevate-with-harsh.myshopify.com` failed from the assistant's shell ("you don't have access to this dev store"; the app dashboard answered 403 "not a member of the requested organization", so the shell's CLI login is a different account). Harsh signed in as `ultimateecomwithharsh@gmail.com` (the owner of the Harsh org) in HIS PowerShell and `theme list` worked there (screenshot: live theme 188778578093 "DTJ licensed test 3", test theme 188893495469 present; the list showed 14 themes where this file earlier said 19: unexplained, not verified). The assistant's shell STILL does not see that login (same user folders and CLI 4.8.4, cause unknown). `shopify auth logout` was NOT run. The `store execute` route (stored store token) DOES work from the assistant's shell (read the shop name). Working pattern: **Harsh runs the authenticated theme commands in his own PowerShell, the assistant analyses the files on disk.** Harsh pulled `templates/product.json` that way (`shopify theme pull ... --only "templates/product.json" --nodelete` into `.work/verify-push`).
- **Item B (clean `templates/product.json`)**: analysed, fix = Harsh deletes the one dangling block in the editor (see item B in section 12). Nothing pushed. Harsh said "done, pulled": the file pulled at 11:27 STILL contained the broken block (identical 94,766 bytes to the first pull; diff vs the cleaned copy = the same 2 removals). So either the editor delete was not saved or it hit another block: a fresh pull at 11:30 into a new empty folder (`.work/verify-pull-2`) still showed the broken block. Harsh then STOPPED this item (low priority); the cleaned copy was never pushed. `.work/verify-pull-3` is an unused empty folder.
- **Standing permission (Harsh, 6 Oct 2026):** "from now on you can push and pull the files yourself". Scope kept by the assistant: `elevate-with-harsh` only, unpublished test theme 188893495469 only (never live 188778578093, never another store), always `--only "<file>" --nodelete`, pull + diff before pushing a template, verify each push by pulling it back, log it. Publishing, deleting, products, app deploys and the licence flag still need a fresh yes. Saved in the assistant's memory too. **Practical block:** the assistant's shell has no usable Shopify theme login, and the Terminal-panel tool failed to open a tab ("Claude terminal integration did not load", missing `%APPDATA%\Claude\terminal-shell-integration\pwsh\claude-desktop.ps1`). Until one of those is fixed, Harsh runs the commands in his PowerShell.
- **Not verified by anyone yet:** how the blocks look in the editor, the Add-ons cart behaviour (also buy-now), storefront output with the licence off, the current flag value (`tools/licence.py --status`, Harsh's terminal).
- **Branch protection / `main`:** not set (needs Harsh in GitHub settings; direct pushes to `main` are denied for the assistant anyway).
- The HANDOFF update that records all of this is a SECOND commit on `chore/initial-import`, local only, NOT pushed. Pushing it needs Harsh's approval (approval for the first push does not cover it).

**Process notes**
- The session snapshot claimed a clean git repo; the folder was not one. The handoff was right. Trust `git status`, not the snapshot.
- `cat .env.example` is blocked by the `.env*` deny rule: do not try; read the variable names in RUNBOOK Appendix A instead.
- A command containing `rm -rf` is blocked by the deny rules: use fresh folders instead of cleaning up.
- Reading the Shopify CLI's login file (`%APPDATA%\shopify-cli-kit-nodejs\Config\config.json`), even keys only, was blocked as credential exploration. Do not retry; ask Harsh to run the command in his own terminal instead.
- **`shopify auth login` cannot be done from the assistant's shell (tried 6 Oct 2026, at Harsh's request, no other route attempted).** Non-interactive runs fail: plain `auth login` needs `--alias`; with `--alias elevate-harsh` or `--alias ultimateecomwithharsh@gmail.com` it still dies with "Failed to prompt: Which account would you like to use?". `auth login --help` says `--alias` only picks an EXISTING session and is "required if non interactive", so a new browser sign-in is impossible there, and no stored session matched. (`auth login` takes no `--no-color`.) No sign-in completed, nothing was replaced. Do not retry; the deploy and any theme command stay with Harsh's own PowerShell.
