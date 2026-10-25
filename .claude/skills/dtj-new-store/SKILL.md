---
name: dtj-new-store
description: Build and design a WHOLE Shopify store from one link sent to DTJ's Telegram bot, for a redesign or a brand-new store. The link is the store to build in (a dev store, elevate, or a client's own store); the bot first asks "redesign or new store", then where the products come from (already in the store; the brand's current website, WordPress or any other, scraped; a Google Drive folder; or sample products with ChatGPT pictures) and the few things it needs (whose store, the client's name, what to design, which products, prices, any offer), adds the products ACTIVE with pictures, collections and policy pages, makes the draft copy of the theme, adds the DTJ apps, collects or makes the brand's logo, colours, fonts and banners, and designs the header and footer, home, collection and product pages into the draft. Every action that needs a yes waits for its own Approve tap in Telegram. Use it whenever someone sends or pastes a store link and wants a brand's store built or designed, says "build the brand's store", "copy this brand into the store", "migrate from WordPress", "new store from scratch", "products from the Drive folder", "sample products", "design the whole store", "new store from this link", "handle the new store request", or when a "Store Factory: New Store" run waits for Claude Code, even if they don't name the skill. Not for one product page (dtj-pdp-factory) or adding a shop only (dtj-add-shop).
---

# A brand's whole store from one link

Harsh, 21 Oct 2026: "i just share the brand store link and it starts designing the store and it asks the specific questions it
needs along with the app installation", then "it didnt asked me the brand link it has to create the shopify store of it". So: **the
link sent is the store to build in**; the job asks for **the brand's own link** and copies that brand into it. His choices that day:
- the store to build in is whatever store he sends;
- copy products with pictures and prices, collections, logo, colours and fonts, and the policy pages;
- (22 Oct 2026, replacing "drafts on an open store") **every product goes in ACTIVE, never as a draft**;
- every yes is an **Approve tap in Telegram**, one per action (one for the whole copy);
- the store is reached with **his collaborator login**, not a Theme Access password;
- every part is designed by default, and the product-page count is asked per store.

Harsh, 22 Oct 2026, the whole flow: "it starts and asks if it is a redesign or new store development". A **redesign** keeps the
brand's own products: already in this store (nothing is added), or scraped from the website it moves from (Senso: WordPress). A
**new store** gets its products from a **Google Drive folder** (layout: `references/drive-folder.md`), or, when there are none yet,
as **sample products** whose pictures, and the home page banners, are made with ChatGPT's image model.

Read `CLAUDE.md` first. This skill is the order of work. Each part is done by its own skill, unchanged, except where that skill says
"ask the person for the approval code": here that is always `store_job.py approve` (an Approve tap) instead.

## Rules
- **One Approve tap per action**, never a code typed at the laptop and never one tap for two actions:
  - `store_job.py draft` (the draft copy) and `copy` (the products: copied, from the Drive folder, or the samples);
  - `apps` (the app copies);
  - `approve` for the header, the footer and the collection page;
  - `pages` (About, Contact, FAQ) and `menus` (the main menu and the footer).

  Skip = the action stays undone; say so at the end. The tapper's name goes into `--approved-by "<name> (Telegram Approve)"`.
- **The copy never changes or deletes what the store has:**
  - a product or collection whose handle exists is skipped;
  - a policy is written only where the store's own is empty;
  - prices are the brand's numbers, what a person typed, or a sample price from the niche's range (tag `dtj-sample-price`;
    Harsh, 22 Oct 2026), never converted; with none of these, 0.00 with the tag `dtj-price-needed`, still ACTIVE;
  - every product goes in ACTIVE; on a store without a password page the Approve tap says they are visible at once.
- Product and home pages go to the draft without a tap (Harsh's standing draft rule): `ship_draft` and `ship_home`.
- Draft only. Never the live theme, never publish, never create a store, never assign a template to a product.
- The offer is exactly what the person typed, or none. Never invent offers, claims, reviews or policies. Sample products, prices
  and descriptions are allowed for a store build and always tagged (`dtj-sample`, `dtj-sample-price`, `dtj-sample-text`).
- **Hand over a store that is ready to sell** (Harsh, 22 Oct 2026: "if anything is missed by me you will cover it"): `finish`
  writes `.work/stores/J/handover.md` (what is in the store, every sample to replace, the owner's own settings) and sends the
  short part to Telegram.
- **Everything the person does happens in Telegram** (Harsh, 21 Oct 2026): taps, typed answers, the Install buttons. Never ask
  them to type a command on the laptop.
- **Themes use the laptop's Shopify CLI login.** If a command answers that it has no access, stop that step and tell the person in
  Telegram: the store owner accepts DTJ's collaborator request (with Themes). If the system blocks a command, say so in Telegram and
  in the answer; never work around it.
- Never print, paste or store a secret.

## Steps (from the repo root; `J` = the job name, the store's handle)
1. **Questions.** `python n8n/store-factory/store_job.py start --link "<store link>" --chat <chat> --by "<name>"`
   - It reads the store (its original .myshopify.com address, live theme, products, collections). Then it asks in Telegram:
     1. **redesign or new store**;
     2. where the products come from (then: should ChatGPT make pictures? banners, extra product pictures, or none):
        - redesign: "Already in this store" (nothing is added), or "On its current website": the person sends the link. A Shopify
          brand is read from its catalogue; any other website from the product pages its sitemap lists (name, features, pictures;
          Senso). A link that cannot be read is asked for again (3 in a row stop);
        - new store: "Yes: I'll send a Google Drive folder": the folder is read at once (`provision/drive_assets.py`, no login: it
          must be shared "Anyone with the link"); the bot says what it found and the problems (a product without pictures or a
          price). A folder that cannot be read is asked for again (3 stop). Or "No: make sample products": the brand's name, what
          the store sells, how many (3, 6, 9 or 12);
     3. whose store;
     4. the client's name (client stores);
     5. the theme question, when the store does not run Horizon;
     6. what to design;
     7. which products, from the brand's best sellers (the Drive folder's order; for samples: all, the first 3 or 6);
     8. the offer.
   - Exit 3 = waiting for an answer: run the same command again. Answers are kept and nothing is asked twice; only taps given after
     a question was sent count.
   - Exit 1 = stopped (wrong store, a brand site that is not Shopify, nothing chosen): finish with "could not start".
   - `store_job.py status --job J` shows the plan.
1a. **The competitor study** (Harsh, 23 Oct 2026: "an option for competitor website analysis and a block that asks what to focus
   on"). Skip it when the plan's `competitors.how` is "no".
   1. **The links.** Take `competitors.links` (the person's), or find 5 yourself when `how` is "find": D2C brands of the same
      niche that grow on Meta ads, never the category's giants. Write one line per brand on why it was picked.
   2. **Read them**, read only, from `services/store-builder`:
      `python -m provision.niche_assets <links> --out ../../.work/stores/J/niche --niche "<one line>"`. You get each brand's
      banners, best sellers, prices, colours and a contact sheet. Open their home and product pages too
      (WebFetch / built-in browser) for copy, layout and trust.
   3. **Write `.work/stores/J/study.md`.** One `#` heading per focus the person picked, named exactly: Pictures,
      Copywriting, Colour palette and fonts, Layout and sections, Offers and pricing, Trust. When the person typed what to look
      at (`competitors.note`), add a `# Your request` heading that answers it first. Under each:
      - what the best of them do, with an example and which brand;
      - what WE do, in our own words and from our own facts.

      Never copy their text, claims, offers, reviews or pictures. Prices go only into the price range for sample prices
      (step 1b).
   4. `python n8n/store-factory/store_job.py study --job J --file .work/stores/J/study.md`. It keeps the study with the job
      and sends its short form to Telegram. It refuses a study that is missing a picked focus.
   5. The later steps use it:
      - the palette and fonts: header, footer and every page;
      - the layout: home and product pages;
      - the copywriting: tone and headlines;
      - the pictures: the `style` of step 1b;
      - the trust: which real proof to show.

1b. **The assets: research, sample details, pictures** (Harsh, 22 Oct 2026: "ensuring you dont generate bad results you will
   search top 5 competitors in that brand niche ... analyze all the brands assets and then plan the images and then create the
   images using chatgpt where you have to upload the referennce images of our products"). Run it whenever the plan says
   `pictures` is not "none", or products lack a price or description, or the store is a samples store.
   1. **Pick 5 competitors** (web search): D2C brands of the same niche that grow on Meta ads, never the category's giants (for a
      tea brand like Senso: Blue Tea India and its peers, never Wagh Bakri, Red Label or Taj). Check each in Meta's Ad Library when
      you can reach it; write one line per brand on why it was picked.
   2. **Read them** (read only): `python -m provision.niche_assets <5 links> --out ../../.work/stores/J/niche --niche "<one line>"`
      from `services/store-builder`. It downloads each brand's banners and 2-3 best-seller pictures and prices, writes
      `niche.json` (with the niche's price range) and one contact sheet per brand. Their pictures are for study only: never
      uploaded to the picture maker, never put in the store.
   3. **Study and plan**: look at every contact sheet; write `style` (a few lines: light, background, props, colours, framing that
      the best of them share, and how ours will look). Plan each picture: our product photos as `refs` (the Drive folder's or the
      brand's own), one product per picture, no words on it.
   4. **Write `.work/stores/J/assets.json`** (you are the AI step):
      ```
      {"research": "<.work/stores/J/niche/niche.json>", "style": "<the study>",
       "products": [{"title", "description", "collection", "price", "compare_at_price", "pictures": [1-3 prompts]}],
       "pictures": [{"for": "<handle>", "prompt", "refs": ["<our photo>"], "kind": "lifestyle" | "product"}],
       "banners": [{"prompt", "refs": ["<our photo>"]}],
       "sample_prices": {"<handle>": {"price", "compare_at_price"}}, "descriptions": {"<handle>": "<text>"}}
      ```
      - `products` only for a samples store, exactly the count asked: realistic, modest products for what the store sells.
      - **Sample prices are allowed** (Harsh, 22 Oct 2026: "you can add any price, compare price, etc. because we will change it
        later"): use `provision.niche_assets.sample_price(niche["prices"], rank, count)`, so they sit in the niche's real range.
        They are tagged `dtj-sample-price`; sample descriptions `dtj-sample-text`; sample products `dtj-sample`. Every one is in the
        handover list.
      - Never a claim (clinically, certified, cures, %, reviews, stars, best seller, No. 1: refused), an offer, a competitor's name
        or a real person.
      - `pictures` (extra product pictures) only for a Drive store with "Banners and extra product pictures"; banners whenever the
        answer allows and the store has none.
   5. `python n8n/store-factory/store_job.py assets --job J --file .work/stores/J/assets.json`. It refuses pictures without the
      research (3+ brands read) and the study; makes each picture once (`provision/ai_images.py`: the ChatGPT command on DTJ's VPS
      `DTJ_IMAGE_VPS`, else OpenAI's API with `OPENAI_API_KEY`, else a local logged-in ChatGPT), with our photos uploaded as
      references; adds ChatGPT's product pictures after the brand's own; keeps the sample prices for the prices question.
   6. Look at every picture it made before going on. A picture that changed our product, added words or looks fake: delete that
      file and run `assets` again (only missing pictures are made again).
2. **Draft copy.** `python n8n/store-factory/store_job.py draft --job J`. One Approve tap, then the live theme is duplicated as
   "DTJ Draft <date>" (unpublished; read back to check). When the person added Horizon instead, that theme is used.
3. **The products** (the brand copy; skipped when the products are already in this store). It runs in Telegram and n8n only (Harsh, 21 Oct 2026: "all this steps must
   be done in the telegram bot"); the laptop never writes to the store here.
   - It goes through **DTJ Store Builder**, the one DTJ app that may add products, collections and policy pages; the block apps
     never can. A store needs it installed once: Dev Dashboard > Apps > DTJ Store Builder > Install app > the store. The job asks
     the person in Telegram the first time and goes on by itself once it is installed.
   - Run `python n8n/store-factory/store_job.py copy --job J`. It does four things:
     1. When products have no price, it asks in Telegram: "Use the sample prices" (when step 1b made them), "I'll type the
        prices" (lines `name = price`; typed wins, samples fill the rest) or "Leave them at 0.00".
     2. It reads the brand's public store (or, for a Drive folder or samples, takes the products this laptop holds and sends their
        pictures to Shopify's own staged upload through Store Builder, `provision/staged_upload.py`), and what the store has
        through the install service (read only). It writes `.work/stores/J/copy/plan.json` and keeps the plan on the install
        service for this job.
     3. It sends the Approve tap with what will be created, e.g. "17 products (197 pictures, 58 variants), 29 collections, 2 policy
        pages, as ACTIVE", plus the notes (currency, an open store).
     4. **The tap itself starts n8n's Store Factory: Brand Copy**, which calls the install service step by step (`POST /copy`,
        `src/copy.js`) and tells the person when it is done. The job only watches the progress and returns when n8n says finished:
        exit 0 done, 1 stopped, 3 still going (run the same command again to keep watching).
   - What it never does: change or delete anything the store has (existing handles are skipped, a policy is written only where the
     store's own is empty), convert or guess a price, add a product as a draft.
   - Products an older copy left as drafts (before 22 Oct 2026): `store_job.py activate --job J --approved-by "<name> (<where
     they said yes>)"` switches only those drafts to ACTIVE and shows them on the Online Store, nothing else (a person's named yes).
4. **Apps.** `python n8n/store-factory/store_job.py apps --job J`. One Approve tap, then it prints the command:
   - a client's store: `add_shop.py ... --approved-by "<name> (Telegram Approve)" --theme <draft id>`. Run it in the person's
     terminal (`run_in_terminal`, read with `read_terminal`) and follow the skill dtj-add-shop, "One command" (the install links from
     the Dev Dashboard, the 7 Install buttons for the store OWNER). The installs can take hours: carry on with step 5 meanwhile;
   - DTJ's own store: register it (`add_client.py --org --shop <store> --label "<Name>" --name J`), deploy the install service
     (`tools/deploy.py`; it needs the 7 original apps' secrets on this laptop: read from the Dev Dashboard with `shopify app env
     show`, saved in Windows variables, never shown), write `page_builder/clients/J.json` (elevate's, store changed), then
     `python n8n/store-factory/store_job.py installs --job J`: one Telegram message with 7 Install buttons (Shopify's own install
     page; an install is always a person's tap), and each app switched on as soon as it is installed (Harsh, 22 Oct 2026:
     "Install buttons in Telegram"). No `/on` needed.
5. **Brand data** (no store change).
   - `store_job.py step --job J intake`.
   - Then from `services/store-builder`: `python -m page_builder.brand_intake <the BRAND's link> --client
     ../../.work/clients/intake-<brand host>`. Add `--drive "DTJ Clients"` when this laptop has the DTJ_GDRIVE_* keys.
   - It gives the logo, colours and fonts that the header, footer and pages use.
   - A new store: the Drive folder's "1 Brand" (logo, Brand details: colours, fonts, about, contact) is the brand data; nothing to
     scrape. A samples store has no logo: the header shows the store name, and you propose a palette for what it sells, marked
     "DTJ proposal" for the client to confirm.
   - The banners (`brand.banners` in `.work/stores/J/job.json`: the Drive folder's or ChatGPT's) go to the store's Files with
     `page_builder.store_files` and into the home page's hero and banner sections; ChatGPT's are samples to replace.
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
        `fetch_product --store <the brand's .myshopify.com> --handle <handle>`. A website, Drive or samples product: its facts are
        in `.work/stores/J/job.json` (`brand.products`: title, description, pictures; samples are all SAMPLE content).
     2. Write the facts, then the design-only run.
     3. `ship_draft --store <store> --theme <draft> --template-suffix dtj-<handle> --client-registry page_builder/clients/<store handle>.json`
     4. `store_job.py step --job J products --done <n> --total <all>`.
     - Use the offer from the plan word for word, or none.
   - **About, Contact and FAQ pages and the menus** (part "pages"; Harsh, 22 Oct 2026: "we have to handover a product ready
     shopify store"). These go through DTJ Store Builder and need its pages and navigation permissions. Those come in a new app
     version, which needs Harsh's yes; until then the step says in Telegram that it is refused and stays open in the handover.
     1. Write `.work/stores/J/pages.json`:
        `{"pages": [{"handle", "title", "body_html", "template_suffix", "sample"}]}`
        - **About us** (`about-us`): the brand's own story, from its website or the Drive "Brand details" About. A samples store
          gets a short sample text marked `"sample": true`.
        - **Contact** (`contact`, `"template_suffix": "contact"`): the theme's contact form. Add only the brand's real email,
          phone and address; if it has none, add nothing.
        - **FAQ** (`faq`): what shoppers ask in this niche, answered only from the brand's facts and its real policies. Shipping,
          returns or payment terms the brand has not stated are left out, never made up.
        - No claims, offers or reviews.
     2. `store_job.py pages --job J --file .work/stores/J/pages.json`. It has its own Approve tap. It adds new pages only; a page
        the store already has stays as it is.
     3. `store_job.py menus --job J`. One Approve tap sets both menus:
        - main menu: Home, Shop all, up to 5 collections, About us, Contact;
        - footer: About us, Contact, FAQ, Search and the 4 policies.

        A link the store does not have is left out. The old menus are kept in the install service's audit row.
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
| "not a Shopify store and shows no price for some products" | a website brand (Senso: WordPress) | expected: the prices question when copying; the rest go in ACTIVE at 0.00 tagged dtj-price-needed |
| "I could not read that folder" | the Drive folder is not shared "Anyone with the link", or not in the layout | the person fixes it and sends the link again; `references/drive-folder.md` |
| assets: "no way to make pictures" | no OpenAI key on this laptop and no ChatGPT Chrome | save `OPENAI_API_KEY` (Harsh's key, Windows variable / vault), or run on the reel VPS |
| assets: "the samples file is refused" | a price, a claim word or the wrong count in assets.json | rewrite the file without it |
| the theme question | the live theme is not Horizon (Dawn: product pages only) | the person adds Horizon, or product pages only |
| draft: "no access to ... themes" | the CLI login is not a collaborator of the store yet | the owner accepts DTJ's collaborator request; log in once |
| copy: "install DTJ Store Builder" | the app is not on the store yet | the person installs it once (Dev Dashboard); the job goes on by itself |
| copy: "DTJ Store Builder is not set up" | the install service has no Store Builder key yet | `tools/store_builder.py create`, then deploy the install service (Harsh's yes) |
| copy note: "open to the public" | the store has no password page | the products are visible and buyable at once: the tapper decides |
| a write refused: app block missing | the DTJ apps are not installed yet | wait for the installs (step 6) |
| exit 3 again and again | nobody answers in Telegram | tell the person at the laptop which question waits |
