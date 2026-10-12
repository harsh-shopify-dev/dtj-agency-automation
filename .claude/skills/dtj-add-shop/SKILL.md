---
name: dtj-add-shop
description: Add a new shop to DTJ's store factory end to end, so product pages can be built for it within hours. Covers a client's store (their own copies of DTJ's three apps, installed through the install service) and a store inside DTJ's own Shopify organization (DTJ's original apps). Claude runs every scripted step and stops only where a person must click in Shopify. Use it whenever someone says "add a new shop", "new client store", "onboard a store", "build the store", "set up <store> for pages", "connect our apps to <store>", "put <store> on the switch", or "the shop is not set up for page design", even when they don't name the skill.
---

# Add a new shop (a few hours, mostly waiting for the client)

When this is done, the shop:
- appears in the bot's `/shops` with its DTJ apps **ON**;
- has a **draft theme**, a **Theme Access** password and a row in **dtj_stores**.

Pages are then made the normal way: a product link to the bot, then "listen for the telegram call".

Claude runs every scripted step. People do only the clicks that Shopify reserves for them. Read `CLAUDE.md` first. In
particular, a "yes" comes from Harsh or, when he isn't reachable, any teammate, by name. The deploy and the app release each need
one; collect them in one message. Background: `docs/TEAM-GUIDE.md` Part E and `services/install-catcher/README.md`.

## Rules
- Secrets only through hidden prompts or the vault: `tools\team-setup\save-dtj-app-secrets.ps1`, opened with `run_in_terminal`
  so the person types there. Never in chat.
- Never touch the live theme. Pages only go to the draft.
- The store's ORIGINAL `.myshopify.com` address is the one that counts: the handle in `admin.shopify.com/store/<handle>`. A
  renamed store keeps sending the original (9 Oct 2026: `test-store-harsh-dtj` is really `qaxv3r-8g`).
- Run Shopify CLI commands (`shopify app config link`, `shopify app deploy`) in the person's terminal with `run_in_terminal`.
  Claude's own shell may hold a different Shopify login: it got 403 "not a member of the requested organization", per HANDOFF.

## S0. Collect in ONE message (ask only for what is missing)
1. **The shop's admin link** (`admin.shopify.com/store/<handle>`) gives the original address.
2. **Whose store:**
   - **(A) a client's store** (most clients);
   - **(B) a store inside DTJ's own Shopify organization**, such as a dev store DTJ created.
3. **Names:**
   - the client's display name, for the app names (for example "Royal Dosa");
   - a short name for files: lowercase letters, digits and dashes, default the handle;
   - the shop's website addresses;
   - the brand name and brand website.
4. **The client's store owner:** who can click Install in the store admin (path A).

Then check it isn't already set up: not in the catcher list (`/shops`) and not in dtj_stores (`setup_n8n.py`). If it is, say so
and stop.

## Path A: a client's store (outside DTJ's organization), 1 to 3 hours
1. **Person (DTJ, Dev Dashboard): collaborator access.** In the Dev Dashboard, Stores, request collaborator access to the client's
   store; the client approves. A collaborator can duplicate themes. Installing the apps, however, must be done by the store
   **owner**: a collaborator login gets "The installation link for this app is invalid".
2. **Person (DTJ, Dev Dashboard): three empty apps.** Create `DTJ Blocks - <Name>`, `DTJ Sections - <Name>` and `DTJ Sections 2 -
   <Name>`.
   - **Tell Claude the three Client IDs.** They aren't secret.
   - **Save the three secrets.** Claude opens this in the person's terminal:
     `powershell -ExecutionPolicy Bypass -File tools\team-setup\save-dtj-app-secrets.ps1 -Client <short name>`.
     It refuses anything that isn't `shpss_` + 32 hex characters.
3. **Claude: register the copies.** Run
   `python services/install-catcher/tools/add_client.py --shop <original>.myshopify.com --label "<Name>" --name <short name>
   --worker https://dtj-install-catcher.ultimateecomwithharsh.workers.dev --blocks-id <id> --sections-id <id> --sections2-id <id>`
4. **Claude, with yes #1: deploy the install service.**
   `cd services/install-catcher` then `CLOUDFLARE_ACCOUNT_ID=530794c3825d1c37ba7f8af33b6415df python tools/deploy.py --dry-run`,
   then the same command without `--dry-run`. `/health` must show 3 more apps.
5. **Claude, with yes #2: release the three copies.** Run in the person's terminal:
   1. For each folder (`block-library`, `block-library-sections`, `block-library-sections-2`), link the copy:
      `shopify app config link --path services/<folder> --client-id <id> --file-name shopify.app.<short>.toml --force --no-input`
   2. Run `add_client.py` again, so our settings win.
   3. Release it: `shopify app deploy --path services/<folder> --config <short> --allow-updates --message "<short> copy"`
   4. Right after the releases: `python services/install-catcher/tools/client_registry.py --client <short>`.
6. **Person (DTJ): the install links.** In each new app, Distribution, Custom distribution, enter the client's original
   `.myshopify.com`, then copy the install link. Send the three links to the **store owner**. They open each one while logged in
   as owner and click Install. The page should say "DTJ is connected".
7. **Claude: confirm.**
   - Run `/status <name>` through the bot test (pinned sends, as in dtj-factory-setup S4): it should show **ON** for all three.
   - Run `client_registry.py --client <short>` again. Its exit code is 0 once the handles are filled in.

## Path B: a store in DTJ's own organization (DTJ's original apps), about 30 minutes
1. **Person (DTJ, Dev Dashboard): install the originals.** Install DTJ Blocks, DTJ Sections and DTJ Sections 2 on the store.
   Check the apps' Client IDs: `5952b612…`, `c10a9d90…` and `a257890d…`.
2. **Claude: register the store.** Run `python services/install-catcher/tools/add_client.py --org --shop <original>.myshopify.com
   --label "<Name>" --name <short>`.
   - The originals' secrets are already in the vault; they reach this laptop through `vault.py pull`.
   - Then, **with yes #1**, deploy as in A4.
3. **Claude: switch the apps on.** A freshly installed app has its switch "not set", so its blocks are hidden. Send `/on <name>`
   through the bot test, or ask a teammate to send it in Telegram and tap Yes.
   - Confirm with `/status <name>`: ON for all three.
4. **Claude: the block-address file.** Copy `services/store-builder/page_builder/clients/elevate-with-harsh.json` to
   `clients/<short>.json`, change `store`, and update `_comment`. The original apps share their handles and uuids.

## Both paths: the shop's own setup
1. **Draft theme** (person with store access): Online Store, Themes, then on the live theme click ..., then Duplicate. Note the
   new theme's number (in its Customize link). Never publish it.
2. **Theme Access** (store owner): install Shopify's Theme Access app and create a password for each designer.
   - Each designer saves it: `setup-team-pc.ps1` asks for `DTJ_THEME_ACCESS_<SHOP>` in a hidden prompt.
   - Harsh or Tushar also keeps it in the vault: `vault.py push DTJ_THEME_ACCESS_<SHOP>`.
3. **The shops list (Claude): add the row to dtj_stores.** Use `mcp__n8n__add_data_table_rows`. Find the table and project ids
   with `setup_n8n.py`. The columns:
   - `store_name`, `myshopify_domain` (the original address);
   - `other_domains` (comma-separated), `draft_theme_id`;
   - `client_registry` = `page_builder/clients/<short>.json`;
   - `brand_name`, `brand_website`, `reference_brands`, `store_notes`;
   - `active` = true.

   Then `python n8n/store-factory/setup_n8n.py --save-stores` so the seed in git matches.
4. **Prove it (Claude):**
   - `python tools/team-setup/check_setup.py`: the draft theme is unpublished, and the Theme Access password works;
   - the bot test `/shops`: the shop shows ON.
5. **Save it (Claude):** commit on a branch and open a pull request. Commit `wrangler.toml`, the `shopify.app.<short>.toml`
   files, `clients/<short>.json` and `stores.seed.json`. Add a HANDOFF entry.
6. **First page:** someone sends a product link to the bot, and a designer says "listen for the telegram call".

## What can go wrong
| You see | Why | Do |
|---|---|---|
| "The installation link for this app is invalid" | opened as a collaborator | the store OWNER opens it |
| The catcher refuses the install (403, "another store") | the copy was registered with the renamed address | `add_client.py --name <short> --shop <ORIGINAL>`, deploy again |
| `/status` says "not set (blocks hidden)" | the switch was never turned on | `/on <name>` and tap Yes |
| A DTJ app line says "outside DTJ's Shopify organization" | path B on a client's store | use path A |
| `client_registry.py` exit 2 "pending" | the client hasn't installed yet | run it again after step A6 |
