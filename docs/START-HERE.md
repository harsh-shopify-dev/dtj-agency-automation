# Start here: DTJ's store factory (share this page with the team)

This is how DTJ makes Shopify product pages, and keeps its apps on or off on every shop, without depending on one person.
What you need depends on your job: **most people only need Telegram.**

## 1. Everyone: the Telegram bot (2 minutes)
1. In Telegram, open **@DtjPageDesignerBot** and send `/start`.
2. It replies with your number. Send that number to Harsh. If Harsh doesn't answer, send it to any teammate who already uses the
   bot: they tell Claude "add <your name> to the bot, number <number>".
3. You now have **full access**:
   - **A product page:** send a product link from the shop's website, with a note if you like. The bot sends the preview link back
     when the page is ready.
   - **Change a finished page by chatting:** after the bot's "page ready" message, just type what to change in plain words (for
     example "make the hero headline about protein"). Claude on DTJ's server changes the page's draft and answers in the same chat
     with the new preview link. Changes beyond the page's draft (the product, the store's settings, the live theme) need your yes
     in the chat first.
   - **A whole store:** send the store's own link (no /products/ in it); the bot asks redesign or new store and the rest.
   - **The app switch:** `/shops` lists every shop and its DTJ apps; `/status <shop>` shows one; `/off <shop>` and `/on <shop>`
     switch them, after you tap a confirm button.

## 2. Designers: a laptop that designs the pages (once, about 30 minutes)
Ask Harsh, or a teammate with access, for:
- the DTJ **Claude** login (the team's shared account);
- an invite to the **GitHub** repo `harsh-shopify-dev/dtj-agency-automation` (make a free GitHub account first);
- an **n8n** login (n8n: Settings > Users > Invite);
- the **Theme Access password** for each shop you'll design for. It is sent with a Bitwarden Send link, never in chat or email.

Then:
1. `docs/TEAM-GUIDE.md` Part A, steps A1 to A4: install Claude and Git, and download the project.
2. Open Claude, the **Code** tab, in the folder `dtj-agency-automation`, and type:
   ```
   set up the store factory
   ```
   Claude installs everything. Type passwords **only** in the terminal tab it opens, never in the chat, and type nothing there
   after it says "Done".
3. To design pages, type either of these:
   - `listen for the telegram call`: Claude designs every request that comes in while you're at the laptop;
   - `handle the Claude Code trigger in n8n`: one page.

## 3. A developer taking over the technical side
1. **Bitwarden:** Tushar or Harsh adds you to the **DTJ** organization. The free plan has 2 members, so the person leaving is
   swapped out.
2. Do section 2. The setup then fills **every** key from the vault.
3. **Read:**
   - `docs/ACCESS-AND-KEYS.md`: every account and key, and the leave checklist;
   - the newest entry of `docs/HANDOFF.md`: what is open right now.
4. **Get added to:** the GitHub repo (as admin), Cloudflare (DTJ's account), n8n (owner), Hostinger and the Shopify Dev Dashboard
   organization that owns DTJ's apps.

## 4. If Harsh doesn't answer: who decides
- **No yes needed:**
  - the bot;
  - designing pages into a shop's **draft** theme;
  - the app switch (it has its own confirm button).
- **A yes from Harsh, or from any teammate when Harsh isn't reachable** (Harsh, 12 Oct 2026). Tell Claude:
  "Harsh isn't reachable, I approve <the action>", with your name. One yes covers one action. These need it:
  - deploying the install service;
  - releasing app updates;
  - creating a store;
  - publishing an n8n workflow;
  - anything that changes what a shop's customers see live.
- **Never, whoever asks:** deleting things, force-pushing code, putting passwords or keys in a chat.

## 5. "We need a store ready in a few hours"
- **The shop is already set up** (it's in `/shops`): send product links to the bot, and a designer types
  `listen for the telegram call`. It takes about 20 minutes a page.
- **A brand-new shop:** in Claude (Code tab, this folder) type `add a new shop`, and it walks through every step (the skill
  `dtj-add-shop`).
  - Plan for **1 to 3 hours** for a client's store. Most of it is waiting for the client.
  - From the client you need two things: **collaborator access** for DTJ, and the **store owner** available to click three
    install links.
  - A store inside DTJ's own Shopify organization takes about 30 minutes.

## Who to ask
Harsh first. If he isn't reachable, Tushar. If neither is, any teammate on the bot: the rules above let you continue.
