---
name: dtj-brand-intake
description: Collect everything public about a client's store before a redesign (pictures and videos of up to 20 products, logo, collections, policies, fonts, theme colours, a palette proposal and a readable BRAND.md) and put it in DTJ's Google Drive, from Claude Code, from GitHub Actions or from the Telegram bot's /intake. Also the one-time setup of the Drive login, the GitHub secrets and the bot's GitHub key, and how to switch the Drive to another Gmail. Use it whenever someone says "brand intake", "scrape the store", "get all the client's images", "download their products and videos", "collect the brand details", "a client wants a redesign", "put it in the drive", "/intake", "the intake did not arrive", or "change the Drive email", even when they don't name the skill.
---

# Brand intake (a client's public store into DTJ's Google Drive)

Harsh, 19 Oct 2026: "a scraper which will scrape all the product images max to only 20 products ... and a file that contains the
details of the brand and brand color palette so when a client comes for a redesign then we just get all the data and then start
designing", then "uploads to the google drive", "no workspace, go with a dedicated dtj gmail and github actions".

**Result:** a Drive folder `DTJ Clients / <brand> / Brand intake <date>` holding `BRAND.md` (start here), `brand-intake.json`
(every fact with its source), a draft `brand.json` for the page builder, `palette.png`, `products.png`, `images/` and `videos/`.

## What it does and never does
- Reads **public pages only**: the store's `products.json`, each product's `.js` (pictures and videos), `collections.json`, the
  policy pages, the home page and the theme stylesheet. It never signs in and never writes to the store.
- **At most 20 products**: the first 20 the store lists. Videos are fetched as a 720p copy, at most 400 MB in all. YouTube and
  Vimeo videos are listed as links, not downloaded.
- **No personal data**: emails and phone numbers are not collected.
- **Colours, category and price tier are guesses.** BRAND.md lists every guessed field. A person confirms the brand colour and
  the accent before any design (the palette method: `.claude/skills/dtj-pdp-factory/references/colour-and-vibe.md`).
- **Nothing is invented.** Missing or template policy text is reported as such, never filled in.
- The Drive app has the `drive.file` permission only. It sees and changes nothing in the Drive except the folders it made.

## Page design asks first
When a page starts, the person is asked whether to collect the brand's data first (Harsh, 19 Oct 2026):
- **Telegram:** after a product link, the bot's "Got it" is followed by "collect the brand's data first?" with **Yes, collect it
  first** / **No, design now**. The tap is saved on the brief (`dtj_client_intake.brand_intake`). After a Yes the bot asks "Which
  website is the brand's own?" (a reply box): the person replies with the address, or `same` when the shop is the brand's site.
  The address is saved as `dtj_client_intake.brand_website` (a demo shop like Elevate with Harsh carries other brands' products).
- **Claude Code:** the designer reads that answer when it starts (step 2 of the Page Design request) or, with no answer, asks the
  person at the laptop; a page started straight in Claude Code (`dtj-pdp-factory` P2, `dtj-home-page`) asks too.
- Yes runs the intake on the designer's laptop into `.work/clients/intake-<host>/intake` (one folder per website, every page of
  that brand uses it), with `--drive "DTJ Clients"` when the laptop has the Drive keys. The design starts from it.

## Three ways to run it (pick the first that fits)

**1. From Telegram (anyone on the bot):** `/intake freesoul.com`. The bot asks GitHub to run the "Brand intake" workflow. The
run sends the Drive link back to the same chat, within a few minutes. Nothing runs on anyone's laptop.
While it runs, one message in the chat shows a live progress bar (stage, "product 14 of 20", "file 80 of 151", time so far) and
ends with "Done in N"; the Drive-link message says how long it took (`page_builder/progress.py`). Bot-started runs only.
**Stopping one:** the progress message has a **Stop** button, and `/stop` lists every intake running now with its own Stop
button (anyone on the bot). The bot cancels only a run of the "Brand intake" workflow that is still going (`stop_plan.js`); files
already in Drive stay there, and the chat says it was stopped.

**2. From Claude Code, cloud run** (nothing kept on this laptop):
```
gh workflow run brand-intake.yml --repo harsh-shopify-dev/dtj-agency-automation -f store=freesoul.com -f requested_by="<name>"
gh run list --repo harsh-shopify-dev/dtj-agency-automation --workflow brand-intake.yml --limit 1
gh run watch <run id> --repo harsh-shopify-dev/dtj-agency-automation --exit-status
```
The Drive link is in the run's summary page: `gh run view <run id> --repo harsh-shopify-dev/dtj-agency-automation`, or in
Actions on github.com.

**3. From Claude Code, local run** (when you are about to design from it and want the files here too):
```
cd services/store-builder
python -m page_builder.brand_intake https://freesoul.com --client ../../.work/clients/<client> --drive "DTJ Clients"
```
- Leave out `--drive` when this laptop has no `DTJ_GDRIVE_*` keys. The files stay in `.work/clients/<client>/intake/`, which
  git ignores.
- Exit codes: 0 = done; 1 = the site could not be read, or the Drive upload failed (the reason is printed).
- A re-run reuses files it already has. The Drive skips files the folder already holds.

**After any run, tell the person:**
1. the Drive link;
2. the brand, how many products, pictures and videos it found;
3. the brand colour and the accent it proposes, with their sources (from BRAND.md);
4. every guessed field and every policy problem;
5. what to confirm before design.

Never present a guessed colour, category or price tier as a fact.

## When it fails
| What you see | Why | Fix |
|---|---|---|
| Bot: "the GitHub key in n8n is missing or not allowed" (401/403) | n8n's Bearer Auth credential "DTJ GitHub Actions" is missing, expired or lacks Actions write | Setup step 6, then `setup_n8n.py --apply` |
| Bot: "cannot find the Brand intake workflow" (404) | the workflow file is not on the default branch `chore/initial-import` yet | merge the PR (Harsh's yes) |
| Bot: "did not finish", with a run link | the store could not be read (not a Shopify store, password page, blocked) or Drive refused | open the run's log; for Drive `invalid_grant`: redo setup step 4 (the login was revoked) |
| Local: "not set up on this laptop: DTJ_GDRIVE_... missing" | this laptop has no Drive login | `python tools/team-setup/vault.py pull`, or run it in the cloud (way 2) |
| Fewer than 20 products | the store has fewer, or hides `products.json` | say so; never fill the gap |

## One-time setup (Harsh, about 15 minutes; Claude prepares every command)
The Drive belongs to **dtjharshsharma@gmail.com** (Harsh's choice, 19 Oct 2026). Claude never sees a key: every value goes
from a Google or GitHub page into the vault or a hidden prompt, then through pipes.

1. **Google app.** Open https://console.cloud.google.com/ signed in as dtjharshsharma@gmail.com.
   - Create a project named `DTJ Brand Intake`.
   - APIs & Services > Library > **Google Drive API** > Enable.
2. **Consent screen.** Google Auth Platform (or "OAuth consent screen"):
   - Branding: app name `DTJ Brand Intake`, support email dtjharshsharma@gmail.com.
   - Audience: **External**, then **Publish app** (status "In production"). In "Testing", Google ends the login after 7 days.
     The app asks only for `drive.file`, which needs no Google review.
   - Data access: add the scope `.../auth/drive.file`.
3. **Client.** Clients > Create client > Application type **Desktop app**, name `DTJ Brand Intake laptop` > Create >
   **Download JSON**. Keep the file in Downloads. Delete it after step 4: it is a key.
4. **Sign in once**, in Harsh's OWN PowerShell, from the repo folder:
   ```
   cd services\store-builder
   python -m page_builder.drive_upload --authorize --client-file "$env:USERPROFILE\Downloads\client_secret_<...>.json"
   ```
   - Google's page opens. Sign in as dtjharshsharma@gmail.com and allow.
   - The script saves `DTJ_GDRIVE_CLIENT_ID`, `DTJ_GDRIVE_CLIENT_SECRET` and `DTJ_GDRIVE_REFRESH_TOKEN` in the Windows user
     settings without showing them.
   - Google may say "Google hasn't verified this app": choose Advanced > Go to DTJ Brand Intake. It is DTJ's own app.
5. **Back up and send to GitHub** (same PowerShell):
   ```
   python tools\team-setup\vault.py push DTJ_GDRIVE_CLIENT_ID DTJ_GDRIVE_CLIENT_SECRET DTJ_GDRIVE_REFRESH_TOKEN
   python tools\team-setup\github_secrets.py push
   python tools\team-setup\github_secrets.py
   ```
   - `push` sends the three Drive keys and `DTJ_TELEGRAM_BOT_TOKEN` to the repo's Actions secrets.
   - The last command must say "all set".
6. **The bot's GitHub key** (for `/intake`):
   - On github.com: Settings > Developer settings > Personal access tokens > **Fine-grained tokens** > Generate new token.
     - Name `DTJ n8n brand intake`, the longest expiry offered.
     - Repository access: only `harsh-shopify-dev/dtj-agency-automation`.
     - Permissions: **Actions: Read and write**. Nothing else.
   - Copy the token straight into a new Bitwarden Login item named `DTJ_GITHUB_ACTIONS_TOKEN` (Developers collection; the token
     goes in the password field).
   - Then run `python tools\team-setup\vault.py pull`.
   - Note the expiry date in `docs/ACCESS-AND-KEYS.md`.
7. **Go live (each needs Harsh's yes, one at a time):**
   1. merge the branch into `chore/initial-import`, so GitHub can run the workflow;
   2. `python n8n/store-factory/deploy_telegram_bot.py --dry-run` shows the changes, then without `--dry-run` it adds `/intake`
      to the bot's DRAFT (the published bot keeps working unchanged);
   3. `python n8n/store-factory/setup_n8n.py --apply` creates the n8n credential "DTJ GitHub Actions" from this laptop's key and
      attaches it;
   4. one real `/intake` test, by Harsh or with his yes;
   5. publish the bot's new version (`setup_n8n.py --publish --only "Store Factory: Telegram Bot"`).

## Switching the Drive to another Gmail later
1. Repeat step 1 (or share the existing Google project with the new Gmail).
2. Repeat steps 3 to 5, signing in with the new Gmail in step 4.
3. Run `github_secrets.py push` again; GitHub replaces the old values.

Nothing else changes: the workflow, the bot and the code read the same three names. Old intakes stay in the old Drive. Move them
by sharing the `DTJ Clients` folder with the new Gmail, or with Google Takeout.

## Files
- `services/store-builder/page_builder/brand_intake.py`: the reading, the colours, BRAND.md and `--drive`.
- `services/store-builder/page_builder/drive_upload.py`: the Google sign-in (`--authorize`) and the upload.
- Tests: `tests/test_brand_intake.py`, `tests/test_drive_upload.py`.
- `.github/workflows/brand-intake.yml`: the cloud run. It answers in Telegram itself and keeps no client files on GitHub.
- `n8n/store-factory/bot_read.js`, `bot_route.js`, `intake_started.js`, `deploy_telegram_bot.py` (`intake_ops`): `/intake`.
- `tools/team-setup/github_secrets.py`: copies the workflow's keys into GitHub. `vault.py` keeps them in Bitwarden.
- Keys and owners: `docs/ACCESS-AND-KEYS.md`.
