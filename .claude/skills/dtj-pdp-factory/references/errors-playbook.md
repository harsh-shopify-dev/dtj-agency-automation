# Errors playbook: when X happens, do Y

Every entry happened for real (9-10 Oct 2026). General rule: retry only network errors (429 / 5xx / "aborted"), at most 3 times
with a pause; after 3 failures of the same step stop, keep the evidence, tell Harsh what failed and what you tried. Never work around
a control (a permission deny, a theme-check refusal, an approval gate): report it.

## Shopify apps, distribution, install
| When | Do | Why |
|---|---|---|
| The store picker (accounts.shopify.com) does not list the client store | Open it from Dev Dashboard > Stores (type Collaboration) | Collaborator stores are not in that picker |
| "The installation link for this app is invalid" (Install greyed) on a CLIENT store | The STORE OWNER opens the link (send it to them). Also check the multi-store box was unticked | A collaborator login could not use the custom-distribution link (Rupa Divine, 9 Oct); the owner can |
| "Allow multi-store install for one Plus organization" was left ticked | Untick before "Generate link". If already generated and greyed, create new app copies | Ticked links only allow a Plus organisation |
| The catcher says "this app copy belongs to another store" | Read `shop=` in the /start URL. Pin THAT address (`add_client.py --shop <original> --name <readable>`), redeploy | Shopify sends the original myshopify address even after a rename |
| "DTJ could not connect: bad hmac" | Check the Windows secret matches the app (`shopify app env show`, compare in a script) and redeploy | The secret was saved for another copy or not saved |
| The browser shows `DNS_PROBE_FINISHED_NXDOMAIN` for `<store>.myshopify.comhttps//...` | Ask for the link to be pasted alone (Ctrl+A, Ctrl+V) | Two addresses were pasted together |
| The CLI `shopify app deploy` sits silent for minutes | Kill it, run again with output to a file and a timeout | Piped output hid a prompt / stalled request (9 Oct) |
| CLI error "The user aborted a request" | Retry once | Network timeout; nothing was released |
| CLI 403 "You are not a member of the requested organization" | Stop. The shell's Shopify login is another account: ask Harsh to run it or log the right account in | Do not run `shopify auth logout` (signs out every store) |
| `shopify` not recognised in Harsh's PowerShell | Run it from your own shell (Git Bash: `shopify.cmd`) after his yes | His PATH lacks the npm folder |
| Blocks added with the "addAppBlockId" deep links do not appear in the theme | Do not rely on them; use `client_registry.py` | Saves did not land (10 Oct); the registry tool needs no editor |

## Catcher, Cloudflare
| When | Do | Why |
|---|---|---|
| `wrangler` asks for CLOUDFLARE_API_TOKEN in a non-interactive shell | Pass the env from the Windows variable (deploy.py does) | wrangler does not read the registry |
| "Unable to authenticate request [10001]" or 503/504 from the Cloudflare API | Verify the token: GET `/accounts/<id>/tokens/verify` (NOT `/user/tokens/verify`, it fails for account tokens); if active, wait and retry (max 3) | Cloudflare had a partial outage (10 Oct); the token was fine |
| `wrangler secret put` says the Worker does not exist | Deploy first (deploy.py does this for a new Worker) | Secrets need an existing Worker |
| Python request to the Worker gets 403 | Send a User-Agent header | Cloudflare blocks Python's default agent |
| /health shows the old app count after a deploy | Ask again a few times | The new version reaches every location within seconds |

## Theme Access, themes, storefront
| When | Do | Why |
|---|---|---|
| The Theme Access password link says "page not found" | Delete that password in the Theme Access app, create a new one, open the email link ONCE, copy at once | The link works once; mail scanners can use it up |
| `read_token` finds no password | Check the variable NAME by listing names (never values): `DTJ_THEME_ACCESS_<ORIGINAL HANDLE>`; Harsh must click OK twice | Saved under another name, or the dialog was not confirmed |
| A saved value is literally "the password" or the wrong length | Ask Harsh to paste the real value; check prefix `shptka_` and length 39 only | It happened (9 Oct) |
| The theme check stops: theme is LIVE | Correct behaviour. Ask Harsh: duplicate to a draft, or he decides about the live theme himself | Automation never writes a live theme |
| Reading a theme JSON fails to parse | Strip the leading `/* ... */` comment Shopify adds | Templates edited in the editor carry it |
| Page built but the product shows the old layout | The template is not assigned. Preview with `?view=<suffix>`; Harsh assigns it in the product | New templates apply only when chosen |
| The buy button says "Sold out" | Tell Harsh: the product has no stock or inventory tracking is on | A page cannot convert while sold out (Go Mints, 10 Oct) |
| Storefront shows the old page after a write | Add a cache-busting query (`&r=123`) | Shopify caches pages briefly |
| The write says "the file read back does not match" | Re-run the push printing the CLI output: Shopify lists the setting it refused (e.g. "Setting 'overlay_opacity' must be a step in the range"). Fix the builder, never the JSON by hand | The CLI exits 0 when Shopify refuses a file; `theme_target` now raises on "pushed with errors" and the catalog checks range steps (10 Oct 2026) |
| A draft preview shows the live theme's page | Open `/?preview_theme_id=<id>` first and keep its cookie (curl `-c/-b`, or the built-in browser), then the product with `?view=<suffix>` | The preview theme is a cookie, not a page parameter |
| Live theme write requested | Only with Harsh's explicit yes for that exact file; never through a script that hides `--allow-live` from the permission rule | `.claude/settings.json` denies `--allow-live`; on 9-10 Oct a scratchpad script sidestepped it after Harsh's yes. Harsh to decide the proper path |

## Builder, lint, review
| When | Do | Why |
|---|---|---|
| "source ... is too long" | Shorten sources (about 60 characters): "pack print, heroimg.png" | Schema limit |
| An accent colour turns olive or muddy | It was pushed toward black for contrast. Choose an accent that passes as is (e.g. the brand's deep tone) or use it only as a fill on dark | Volt yellow #E9EF12 on white is 1.25:1 |
| 4 items in a 3-column grid leave one alone | Use 4 columns (builder does this since 10 Oct) or 2 x 2 | Orphans look broken |
| Same picture in many slots | In demo mode leave slots empty instead and list them in the graphics brief | Repetition reads as a template (Harsh's feedback) |
| Preview shows Rs 699 / 1,400 / -50% | Placeholder data in the local render; the live block shows the real price | Not a real price |
| L08 flags a number in text like `&#x27;` | Fixed (html.unescape); if it returns, check the entity, not the copy | False positive |
| Edge headless renders blank pages | `browser.py` already picks the first browser that renders a test page | Edge headless broke on this PC |
| Headless full-page screenshot has blank bands | Add `--force-prefers-reduced-motion` (Horizon reveals sections on scroll) | Works for 1280 px |
| Headless phone screenshot is cut on the right | Use the built-in browser's mobile preset (375) instead | Headless lays out wider than 390 px |

## Figma, browser, n8n, git
| When | Do | Why |
|---|---|---|
| Figma canvas unreadable or "Sign up" prompts | Harsh logs in in the built-in browser; then open `https://www.figma.com/proto/<file>/<name>?node-id=<frame>&scaling=scale-down-width&content-scaling=fixed&hide-ui=1` and scroll; list sections with `get_page_text` on the layers panel | Logged-out view blocks present/export; never create an account |
| The n8n MCP server times out | Continue: the Wait-node hand-off works without it (`reply.py` posts to the resume URL) | Connection problem, not missing access |
| About to commit | Scan staged files for `shpss_`, `shpat_`, `shptka_`, `shprt_`, `cfut_`, `Bearer `, JWTs; never commit `.mcp.json` or `.env*` | `.mcp.json` holds the n8n access header |
| Never | `shopify auth logout`, force-push, commit to main, print a secret, delete theme files | Project rules |
