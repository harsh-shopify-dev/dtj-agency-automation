---
name: dtj-new-store
description: Build and design a brand's WHOLE Shopify store from one link sent to DTJ's Telegram bot. The link is the store to build in (a dev store, elevate, or a client's own store); the bot then asks for the brand's own link and the few things it needs (whose store, the client's name, what to design, which products, any offer), copies the brand's products with pictures and prices, its collections and its policy pages into the store, makes the draft copy of the theme, adds the DTJ apps, collects the brand's logo, colours and fonts, and designs the header and footer, home, collection and product pages into the draft. Every action that needs a yes waits for its own Approve tap in Telegram. Use it whenever someone sends or pastes a store link and wants a brand's store built or designed, says "build the brand's store", "copy this brand into the store", "design the whole store", "new store from this link", "handle the new store request", or when a "Store Factory: New Store" run waits for Claude Code, even if they don't name the skill. Not for one product page (dtj-pdp-factory) or adding a shop only (dtj-add-shop).
---

# A brand's whole store from one link

Harsh, 21 Oct 2026: "i just share the brand store link and it starts designing the store and it asks the specific questions it
needs along with the app installation", then "it didnt asked me the brand link it has to create the shopify store of it". So: **the
link sent is the store to build in**; the job asks for **the brand's own link** and copies that brand into it. His choices that day:
- the store to build in is whatever store he sends;
- copy products with pictures and prices, collections, logo, colours and fonts, and the policy pages;
- products go in ACTIVE when the store is behind a password (a dev store), else as drafts;
- every yes is an **Approve tap in Telegram**, one per action (one for the whole copy);
- the store is reached with **his collaborator login**, not a Theme Access password;
- every part is designed by default, and the product-page count is asked per store.

Read `CLAUDE.md` first. This skill is the order of work. Each part is done by its own skill, unchanged, except where that skill says
"ask the person for the approval code": here that is always `store_job.py approve` (an Approve tap) instead.

## Rules
- **One Approve tap per action**, never a code typed at the laptop and never one tap for two actions:
  - `store_job.py draft` (the draft copy) and `copy` (the brand copy);
  - `apps` (the app copies);
  - `approve` for the header, the footer and the collection page.

  Skip = the action stays undone; say so at the end. The tapper's name goes into `--approved-by "<name> (Telegram Approve)"`.
- **The copy never changes or deletes what the store has:**
  - a product or collection whose handle exists is skipped;
  - a policy is written only where the store's own is empty;
  - prices are the brand's numbers, never converted or guessed.
- Product and home pages go to the draft without a tap (Harsh's standing draft rule): `ship_draft` and `ship_home`.
- Draft only. Never the live theme, never publish, never create a store, never assign a template to a product.
- The offer is exactly what the person typed, or none. Never invent prices, offers, claims, reviews or policies; mark samples SAMPLE.
- **Everything the person does happens in Telegram** (Harsh, 21 Oct 2026): taps, typed answers, the Install buttons. Never ask
  them to type a command on the laptop.
- **Themes use the laptop's Shopify CLI login.** If a command answers that it has no access, stop that step and tell the person in
  Telegram: the store owner accepts DTJ's collaborator request (with Themes). If the system blocks a command, say so in Telegram and
  in the answer; never work around it.
- Never print, paste or store a secret.

## Steps (from the repo root; `J` = the job name, the store's handle)
1. **Questions.** `python n8n/store-factory/store_job.py start --link "<store link>" --chat <chat> --by "<name>"`
   - It reads the store (its original .myshopify.com address, live theme, products, collections). Then it asks in Telegram:
     1. **which brand**: the person sends the brand's own link, or taps "This store is the brand" (redesign the store as it is). A
        Shopify brand is read from its catalogue; any other website from the product pages its sitemap lists (name, features,
        pictures; Harsh, 22 Oct 2026, Senso). A link that cannot be read is asked for again;
     2. whose store;
     3. the client's name (client stores);
     4. the theme question, when the store does not run Horizon;
     5. what to design;
     6. which products, from the brand's best sellers, with options sized to its catalogue;
     7. the offer.
   - Exit 3 = waiting for an answer: run the same command again. Answers are kept and nothing is asked twice; only taps given after
     a question was sent count.
   - Exit 1 = stopped (wrong store, a brand site that is not Shopify, nothing chosen): finish with "could not start".
   - `store_job.py status --job J` shows the plan.
2. **Draft copy.** `python n8n/store-factory/store_job.py draft --job J`. One Approve tap, then the live theme is duplicated as
   "DTJ Draft <date>" (unpublished; read back to check). When the person added Horizon instead, that theme is used.
3. **Brand copy** (skipped when the store is the brand). It runs in Telegram and n8n only (Harsh, 21 Oct 2026: "all this steps must
   be done in the telegram bot"); the laptop never writes to the store here.
   - It goes through **DTJ Store Builder**, the one DTJ app that may add products, collections and policy pages; the block apps
     never can. A store needs it installed once: Dev Dashboard > Apps > DTJ Store Builder > Install app > the store. The job asks
     the person in Telegram the first time and goes on by itself once it is installed.
   - Run `python n8n/store-factory/store_job.py copy --job J`. It does three things:
     1. It reads the brand's public store, and what the store has through the install service (read only). It writes
        `.work/stores/J/copy/plan.json` and keeps the plan on the install service for this job.
     2. It sends the Approve tap with what will be created, e.g. "17 products (197 pictures, 58 variants), 29 collections, 2 policy
        pages, as ACTIVE", plus the notes (currency, an open store).
     3. **The tap itself starts n8n's Store Factory: Brand Copy**, which calls the install service step by step (`POST /copy`,
        `src/copy.js`) and tells the person when it is done. The job only watches the progress and returns when n8n says finished:
        exit 0 done, 1 stopped, 3 still going (run the same command again to keep watching).
   - What it never does: change or delete anything the store has (existing handles are skipped, a policy is written only where the
     store's own is empty), convert or guess a price, publish products on an open store (they go in as drafts there).
4. **Apps.** `python n8n/store-factory/store_job.py apps --job J`. One Approve tap, then it prints the command:
   - a client's store: `add_shop.py ... --approved-by "<name> (Telegram Approve)" --theme <draft id>`. Run it in the person's
     terminal (`run_in_terminal`, read with `read_terminal`) and follow the skill dtj-add-shop, "One command" (the install links from
     the Dev Dashboard, the 7 Install buttons for the store OWNER). The installs can take hours: carry on with step 5 meanwhile;
   - DTJ's own store: the skill dtj-add-shop, path B.
5. **Brand data** (no store change).
   - `store_job.py step --job J intake`.
   - Then from `services/store-builder`: `python -m page_builder.brand_intake <the BRAND's link> --client
     ../../.work/clients/intake-<brand host>`. Add `--drive "DTJ Clients"` when this laptop has the DTJ_GDRIVE_* keys.
   - It gives the logo, colours and fonts that the header, footer and pages use.
6. **Wait for the apps.** The pages use DTJ's blocks, so the parts below start when `add_shop.py --shop <store> --status` shows all 7
   installed (or path B is done). If the session must end first, run `finish --status "partly done"` with what is open.
7. **Each part chosen**, in this order. Before each, run `store_job.py step --job J <part>`; after each write, run `store_job.py record
   --job J --part "<part>" --preview <preview link>`. The client folder is `.work/clients/J`, and one per product,
   `.work/clients/J-<handle>`.
   - **Header and footer** (skill dtj-header-footer, `run_chrome --store <store> --theme <draft>`), one tap each:
     1. `store_job.py approve --job J --key ok_header --text "Write the header of <name>: <what changes>. Preview: <before/after link>"`
     2. `push_page --out .../chrome-run/header --approve <its code> --approved-by "<APPROVED_BY>"`
     3. The same with `ok_footer` for the footer.
   - **Home page** (skill dtj-home-page, `ship_home --sections auto`): no tap (standing rule).
   - **Collection page** (skill dtj-collection-page, `run_collection --store --theme`):
     1. `store_job.py approve --key ok_collection`
     2. `push_page --out .../collection-run --approve <code> --approved-by "<APPROVED_BY>"`
   - **Product pages**, one per product in the plan (skill dtj-pdp-factory, as a page request does it). No tap (standing rule).
     1. Copied products keep the brand's handles, so read each from the brand's store, which needs no store password:
        `fetch_product --store <the brand's .myshopify.com> --handle <handle>`.
     2. Write the facts, then the design-only run.
     3. `ship_draft --store <store> --theme <draft> --template-suffix dtj-<handle> --client-registry page_builder/clients/<store handle>.json`
     4. `store_job.py step --job J products --done <n> --total <all>`.
     - Use the offer from the plan word for word, or none.
8. **Finish and answer n8n.**
   1. `store_job.py finish --job J --status "done" | "partly done" | "could not start" --note "<open items>"`
   2. `python n8n/store-factory/reply.py --resume-url "<resume_url>" --body .work/stores/J/answer.json`
9. **HANDOFF.** Add a dated entry to `docs/HANDOFF.md`:
   - the store and the brand;
   - the draft theme;
   - what the copy created;
   - every page written, with its preview;
   - the taps (who) and what was skipped;
   - the samples to replace;
   - what is open (installs, menus, a Horizon theme to add, prices in another currency).

## What can go wrong
| You see | Why | Do |
|---|---|---|
| "I could not read ... as a brand" | the link is neither a Shopify store nor a site with product pages in its sitemap | the bot asks again; 3 in a row stop the job |
| "not a Shopify store and shows no prices" | a website brand (Senso: WordPress) | expected: its products go in as hidden drafts at 0.00 tagged dtj-price-needed; prices are set in Shopify |
| the theme question | the live theme is not Horizon (Dawn: product pages only) | the person adds Horizon, or product pages only |
| draft: "no access to ... themes" | the CLI login is not a collaborator of the store yet | the owner accepts DTJ's collaborator request; log in once |
| copy: "install DTJ Store Builder" | the app is not on the store yet | the person installs it once (Dev Dashboard); the job goes on by itself |
| copy: "DTJ Store Builder is not set up" | the install service has no Store Builder key yet | `tools/store_builder.py create`, then deploy the install service (Harsh's yes) |
| copy note: "products go in as DRAFT" | the store has no password page (open to the public) | expected for a live store; a dev store keeps them ACTIVE |
| a write refused: app block missing | the DTJ apps are not installed yet | wait for the installs (step 6) |
| exit 3 again and again | nobody answers in Telegram | tell the person at the laptop which question waits |
