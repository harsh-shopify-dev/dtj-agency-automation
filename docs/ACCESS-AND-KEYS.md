# Access and keys: who owns what, and how a new person gets in

Harsh, 12 Oct 2026: "if another developer moves in and I leave the company, how will they get those keys? Keep everything central
so anyone can use it, even someone non-technical."

This page lists every account and key the store factory needs: where each one lives today, who can issue it again, and what
breaks if it is lost. **It never holds a secret value**: only names and places. Anything marked **[unknown]** must be filled in
by Harsh.

## In short
- **Most keys can be issued again** by whoever owns the company account they come from: Shopify, Cloudflare, Telegram, n8n.
  So two things matter:
  1. every account is owned by **the company (DTJ)**, with **at least two owners**;
  2. the few keys that cannot be issued again sit in **one company password vault**.
- **Only one key is truly irreplaceable today: the install service's vault key** (`DTJ_CATCHER_VAULT_KEY`). If it is lost,
  every client has to install our apps again. Today it exists only on Harsh's laptop and, write-only, in Cloudflare.
- **A non-technical person never needs a key:**
  - a **requester** only needs Telegram;
  - a **designer** needs a laptop set up once (`tools/team-setup/setup-team-pc.ps1`) and their own n8n login;
  - an **admin** switches apps from Telegram.

## Who needs what

| Role | What they use | Keys on their laptop |
|---|---|---|
| Requester (sends product links) | Telegram, a row in `dtj_bot_users` | none |
| Admin (app switch) | Telegram, role `admin` in `dtj_bot_users` | none |
| Designer (runs Claude Code) | the shared Claude account, their own n8n login, this repo | their own `N8N_MCP_TOKEN`, one Theme Access password per shop |
| Developer | everything below | all the keys below |

## Accounts (each must belong to the company and have at least two owners)

| Account | What runs there | Today | If the only owner leaves | What to do |
|---|---|---|---|---|
| **GitHub** | the code (this repo) | `github.com/harsh-shopify-dev/dtj-agency-automation`, a personal account | nobody can merge, add people or rescue the code | create a DTJ GitHub organization, move the repo there (Settings > Transfer), two owners |
| **n8n** | the 3 automations, the tables, the bot's credentials | `n8n.srv2048145.hstgr.cloud` on a Hostinger server; owner **[unknown]** | nobody can add users or fix workflows | the n8n owner and the Hostinger account in the company's name; a second n8n admin |
| **Cloudflare** | the install service (the app switch) | account with the workers.dev name `ultimateecomwithharsh`; owner **[unknown]** | the switch cannot be changed or redeployed | add a DTJ owner as Super Administrator now. Later, give the service a company web address, so a move never changes the address that every client app points at |
| **Shopify Dev Dashboard organization** | DTJ's original apps and every client copy, with their secrets | organization **[unknown]**: Harsh to confirm which account owns the apps | no releases and no new clients | the organization owned by DTJ, at least two owners |
| **Telegram bot** `@DtjPageDesignerBot` | the bot | created from Harsh's Telegram account | nobody can change the bot or get a new token | transfer the bot to a company owner in @BotFather (the bot's settings; **[verify]** the exact menu), and keep the token in the vault |
| **Claude** | the design sessions | the team's shared account | (already shared) | keep at least two admins |
| **Each shop's Theme Access** | designers writing to draft themes | one password per person, per shop | that person's password stops working | the shop owner issues new ones (Part E of the team guide) |

## Keys

| Key (Windows user variable) | Where it lives today | Who can issue it again | If it is lost |
|---|---|---|---|
| `DTJ_CATCHER_VAULT_KEY` | Harsh's laptop; Cloudflare (cannot be read back) | **nobody** | **every client reinstalls the apps.** Must go into the company vault first. |
| `DTJ_CATCHER_CONTROL_KEY` | Harsh's laptop; Cloudflare | a developer (new key, then deploy) | make a new one |
| `DTJ_CATCHER_BOT_KEY` | Harsh's laptop; Cloudflare; the n8n credential "DTJ Catcher Bot Key" | a developer (new key, deploy, paste it into the n8n credential) | make a new one |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | Harsh's laptop | any Cloudflare admin of the account | make a new token |
| `DTJ_SECRET_<CLIENT>_BLOCKS` / `_SECTIONS` / `_SECTIONS2` | Harsh's laptop; Cloudflare | any member of the Shopify organization (the app's page, or `shopify app env show`) | read it again |
| `DTJ_BLOCKS_CLIENT_SECRET`, `DTJ_SECTIONS_CLIENT_SECRET`, `DTJ_SECTIONS2_CLIENT_SECRET` (DTJ's original apps) | not saved yet (`tools/team-setup/save-dtj-app-secrets.ps1`) | the same | read it again |
| `DTJ_THEME_ACCESS_<SHOP>` | each designer's laptop | the shop's Theme Access app | ask for a new one |
| `N8N_MCP_TOKEN` | each person's laptop | each person, in n8n | make your own |
| Telegram bot token | the n8n credential "DTJ Page Bot" | the bot's owner, in @BotFather | get a new one, paste it into the credential |
| n8n's own encryption key | the n8n server | the server's owner | every n8n credential has to be made again |

## When someone leaves (checklist)
1. **n8n:** remove their user. In `dtj_bot_users`, set `active` = false on their row.
2. **Ownership:** take them off GitHub, Cloudflare, the Shopify organization and the Hostinger account. Check that the accounts
   table above still shows two owners for each.
3. **Keys they held:**
   - Make new ones: `DTJ_CATCHER_CONTROL_KEY`, `DTJ_CATCHER_BOT_KEY` (then update the n8n credential), their Cloudflare token.
   - Have the shops revoke their Theme Access passwords.
   - If they ran the Telegram bot: get a new bot token in @BotFather.
4. **`DTJ_CATCHER_VAULT_KEY` cannot be changed today:** the stored store keys are locked with it. A new key would need a
   re-encryption step, which is not built yet. This is the reason it must live in the company vault and nowhere else.
5. Update this page.

## The plan (each step needs Harsh's decision)
1. **A company password vault** (for example Bitwarden or 1Password), owned by DTJ, with Harsh as admin.
   - It holds: the three catcher keys, the Cloudflare token, the Shopify app secrets, the Telegram bot token, and one shared
     item per shop for Theme Access.
   - Never in git, never in chat.
2. **The setup script reads from the vault**, so a new person signs in to the vault once instead of pasting every password.
3. **Accounts moved to the company:** GitHub organization, Cloudflare owner, Shopify organization owners, the n8n and Hostinger
   owner, the Telegram bot.
