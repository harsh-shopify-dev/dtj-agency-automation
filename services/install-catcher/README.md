# DTJ install catcher

A Cloudflare Worker that catches a client store's install of its own copies of our three apps, keeps the store key encrypted and
switches the DTJ licence (`dtj.licence` on our app installation) on, and later off or on again for the kill switch.
Design and the facts behind it: [docs/install-catcher-design.md](../../docs/install-catcher-design.md).

```
src/worker.js        the Worker (routes /start, /callback, /webhooks, /licence, /health and a weekly key refresh)
test/worker.test.js  node --test test/*.test.js      (a stand-in Shopify; 15 tests)
tools/add_client.py  writes a client's 3 app-copy files (shopify.app.<client>.toml) and registers them in wrangler.toml;
                     --org registers a store in DTJ's own organization (DTJ's original apps, no files)
tools/deploy.py      creates the storage once, sets the secrets from Windows variables (stdin only), deploys, checks /health
test/test_tools.py   python -m unittest discover -s services/install-catcher/test -p "test_*.py"   (a stand-in wrangler; 21 tests)
```

## One-time setup (Harsh)
1. Cloudflare: free account; open **Workers & Pages** once and pick a `workers.dev` subdomain.
2. **My Profile > API Tokens > Create Token > "Edit Cloudflare Workers"**; save it as the Windows user variable `CLOUDFLARE_API_TOKEN`.
   Send the **Account ID** (not secret); it is saved as `CLOUDFLARE_ACCOUNT_ID`.

## Per client
1. Harsh creates 3 empty apps in the Dev Dashboard (`DTJ Blocks - <Client>`, `DTJ Sections - <Client>`, `DTJ Sections 2 - <Client>`),
   sends the 3 Client IDs and saves the 3 Client secrets as `DTJ_SECRET_<CLIENT>_BLOCKS` / `_SECTIONS` / `_SECTIONS2`
   (`<CLIENT>` = the store's .myshopify.com name in capitals, dashes as underscores).
2. `python services/install-catcher/tools/add_client.py --shop <store>.myshopify.com --label "<Client>" --worker <catcher url> --blocks-id .. --sections-id .. --sections2-id ..`
3. `python services/install-catcher/tools/deploy.py --dry-run`, then (with Harsh's yes) `python services/install-catcher/tools/deploy.py`.
4. For each app folder: `shopify app config link --path services/<folder> --client-id <id> --file-name shopify.app.<client>.toml --force --no-input`
   (pulls the remote app; re-run add_client afterwards so our settings win), then
   `shopify app deploy --path services/<folder> --config <client> --allow-updates --message "<client> copy"`.
5. Harsh: each new app > Distribution > **Custom distribution** > the client's .myshopify.com > open the install link logged in to
   that store > Install. The catcher shows "DTJ is connected" and the licence is on.
6. Check: `POST /licence {"app": "<client>-blocks", "state": "status", "ts": <now>}` signed with `DTJ_CATCHER_CONTROL_KEY` answers `active`.

## A store in DTJ's own Shopify organization (DTJ's original apps)
A dev store in our organization (for example elevate-with-harsh) runs DTJ Blocks / Sections / Sections 2 themselves, not copies.
The catcher reaches it with the original app's client credentials grant (a fresh 24-hour token per call, nothing stored; Shopify
allows this only for stores in the app's own organization).
1. Once, Harsh: `powershell -ExecutionPolicy Bypass -File tools\team-setup\save-dtj-app-secrets.ps1` (saves
   `DTJ_BLOCKS_CLIENT_SECRET`, `DTJ_SECTIONS_CLIENT_SECRET`, `DTJ_SECTIONS2_CLIENT_SECRET`, never shown).
2. `python services/install-catcher/tools/add_client.py --org --shop <store>.myshopify.com --label "<Name>"`
3. `python services/install-catcher/tools/deploy.py` (puts each original secret once as `ORG_SECRET_DTJ_...`), then `/status <name>` in the bot.

## The switch's directory
`POST /licence {"state": "list", "ts": <now>}` (signed, or the bot's key) answers every shop the catcher reaches with its apps
(no secrets, no Shopify call). The Telegram bot's `/shops`, `/status`, `/on` and `/off` find shops in this list.

## Rules
- A store key is never printed, logged, returned or sent to n8n. Client secrets and the vault key are Worker secrets.
- The only write the catcher can make in a store is `metafieldsSet` for `dtj.licence` on our own app installation; our copies ask for no scopes.
- `DTJ_CATCHER_VAULT_KEY` is the only way to read stored keys: never replace it (deploy.py refuses), never share it.
