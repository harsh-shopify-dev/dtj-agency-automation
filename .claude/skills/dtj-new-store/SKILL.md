---
name: dtj-new-store
description: Design a WHOLE client store from the one link a person sends DTJ's Telegram bot (https://brand.com, no /products/ in it). Reads the store, asks the person the few questions it needs in Telegram (whose store, the client's name, what to design, which products, any offer), takes an Approve tap in Telegram before every action that needs a yes, makes the draft copy of the live theme with the laptop's own Shopify login (DTJ's collaborator access), adds the DTJ app copies (add_shop.py), collects the brand data, then designs the header and footer, home page, collection page and product pages into the draft. Use it whenever someone sends or pastes a store's own link and wants the store designed, says "design the whole store", "do the full store", "new store from this link", "handle the new store request", or when a "Store Factory: New Store" run waits for Claude Code, even if they don't name the skill. Not for one product page (dtj-pdp-factory) or adding a shop only (dtj-add-shop).
---

# A whole store from one link

Harsh, 21 Oct 2026: "i just share the brand store link and it starts designing the store and it asks the specific questions it needs
along with the app installation". His choices that day: every part by default (header and footer, home, collection, product pages);
how many product pages is asked per store; every yes is an **Approve tap in Telegram**; the store is reached with **his collaborator
login**, not a Theme Access password.

Read `CLAUDE.md` first. This skill is the order of work; each part is done by its own skill, unchanged except where it says "ask the
person for the approval code": here that is always `store_job.py approve` (an Approve tap) instead.

## Rules
- **One Approve tap per action** (`store_job.py approve` / `draft` / `apps`), never a code typed at the laptop and never one tap for two
  actions: the draft copy, the app copies, the header, the footer, the collection page. Skip = that action stays undone; say so at the
  end. The tap's name goes into `--approved-by "<name> (Telegram Approve)"` (store_job.py prints it as `APPROVED_BY=...`).
- Product and home pages go to the draft without a tap (Harsh's standing draft rule): `ship_draft` / `ship_home`.
- Draft only. Never the live theme, never publish, never create a store or a product, never assign a template to a product.
- The offer is exactly what the person typed, or none. Never invent prices, offers, claims, reviews or policies; samples are SAMPLE.
- The Shopify CLI runs with the laptop's login. If a command answers that it has no access, stop that step and tell the person: the
  store owner accepts DTJ's collaborator request (with Themes), then they run `shopify theme list --store <store>` once in their own
  terminal and log in. If the system blocks a command (app release, theme write), give the person the exact command for their own
  PowerShell; never work around it.
- Never print, paste or store a secret.

## Steps (from the repo root; `J` = the job name printed by start)
1. **Questions.** `python n8n/store-factory/store_job.py start --link "<link>" --chat <chat> --by "<name>"`
   It reads the store (its original .myshopify.com address, live theme, products in best-selling order, collections) and asks in
   Telegram: whose store; the client's name (client stores); the theme question when the store does not run Horizon; what to design;
   which products (options sized to the store: "All N" for a small one); the offer. Exit 3 = waiting for an answer: run the same
   command again (answers are kept, nothing is asked twice). Exit 1 = stopped (wrong store, nothing chosen): finish with
   "could not start". `store_job.py status --job J` shows the plan.
2. **Draft copy.** `python n8n/store-factory/store_job.py draft --job J` - Approve tap, then the live theme duplicated as
   "DTJ Draft <date>" (unpublished; read back to check). When the person added Horizon instead, that theme is used.
3. **Apps.** `python n8n/store-factory/store_job.py apps --job J` - Approve tap, then it prints the command:
   - a client's store: `add_shop.py ... --approved-by "<name> (Telegram Approve)" --theme <draft id>`. Run it in the person's terminal
     (`run_in_terminal`, read with `read_terminal`) and follow the skill dtj-add-shop, "One command" (the install links from the Dev
     Dashboard, the 7 Install buttons for the store OWNER). The installs can take hours: carry on with step 4 meanwhile.
   - DTJ's own store: the skill dtj-add-shop, path B.
4. **Brand data** (no store change): `store_job.py step --job J intake`, then from `services/store-builder`:
   `python -m page_builder.brand_intake <link> --client ../../.work/clients/intake-<host>` (add `--drive "DTJ Clients"` when this
   laptop has the DTJ_GDRIVE_* keys).
5. **Wait for the apps.** The pages use DTJ's blocks, so the parts below start when `add_shop.py --shop <store> --status` shows all 7
   installed (or path B is done). If the session must end first: `finish --status "partly done"` with what is open.
6. **Each part chosen**, in this order, each with `store_job.py step --job J <part>` and, after a write, `store_job.py record --job J
   --part "<part>" --preview <preview link>`. The client folder is `.work/clients/J` (one per product: `.work/clients/J-<handle>`).
   - **Header and footer** (skill dtj-header-footer, `run_chrome --store <store> --theme <draft>`). Then one tap each:
     `store_job.py approve --job J --key ok_header --text "Write the header of <name>: <what changes>. Preview: <before/after link>"`,
     `push_page --out .../chrome-run/header --approve <its code> --approved-by "<APPROVED_BY>"`; then the same with `ok_footer`.
   - **Home page** (skill dtj-home-page, `ship_home --sections auto`): no tap (standing rule).
   - **Collection page** (skill dtj-collection-page, `run_collection --store --theme`): `store_job.py approve --key ok_collection`, then
     `push_page --out .../collection-run --approve <code> --approved-by "<APPROVED_BY>"`.
   - **Product pages**, one per product in the plan (skill dtj-pdp-factory, as a page request does it: `fetch_product`, facts, the
     design-only run, then `ship_draft --store <store> --theme <draft> --template-suffix dtj-<handle> --client-registry
     page_builder/clients/<store handle>.json`): no tap (standing rule). Use the offer from the plan word for word, or none.
     `store_job.py step --job J products --done <n> --total <all>`.
7. **Finish and answer n8n:** `store_job.py finish --job J --status "done" | "partly done" | "could not start" --note "<open items>"`,
   then `python n8n/store-factory/reply.py --resume-url "<resume_url>" --body .work/stores/J/answer.json`.
8. **HANDOFF:** a dated entry in `docs/HANDOFF.md`: the store, the draft theme, every page written with its preview, the taps (who),
   what was skipped, the samples to replace, what is open (installs, menus, a Horizon theme to add).

## What can go wrong
| You see | Why | Do |
|---|---|---|
| start: "does not look like a Shopify store" | not Shopify, or a password page | ask for the store's .myshopify.com address |
| the theme question | the live theme is not Horizon (Dawn: product pages only) | the person adds Horizon, or product pages only |
| draft: "no access to ... themes" | the CLI login is not a collaborator of the store yet | the owner accepts DTJ's collaborator request; log in once |
| a write refused: app block missing | the DTJ apps are not installed yet | wait for the installs (step 5) |
| exit 3 again and again | nobody answers in Telegram | tell the person at the laptop which question waits |
