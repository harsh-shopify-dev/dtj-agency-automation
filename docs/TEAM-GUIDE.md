# DTJ Page Designer: team guide

This guide is for anyone in the team, technical or not. Follow it top to bottom and you will be able to make a full product page
for any shop that has our apps, without Harsh and without Harsh's computer.

There are two kinds of team members:

| You are a... | You do | You need |
|---|---|---|
| **Requester** | Send a product link to the Telegram bot and get the preview link back | **Only Telegram.** Skip Part A completely: read "Get access to the bot" below, then Part C |
| **Designer** | Also run Claude Code on your laptop when a page is waiting | Telegram **and** the laptop setup in Part A (once) |

**Get access to the bot (everyone):** in Telegram, search **@DtjPageDesignerBot**, open it, press **Start** (or send "hi").
It replies with your number. Send that number to Harsh and say whether you are a requester or a designer. Once he adds you,
the bot works for you.

- **Part A** sets up a designer's laptop. You do it **once** (about 45 minutes).
- **Part B** explains how everything works. Read it once; it makes the rest easy.
- **Part C** is what you do **every time** you make a page (one message, then about 15 to 20 minutes of waiting).
- **Part D** is what to do with the finished page.
- **Part E** is for Harsh: adding a new shop.
- **Part F** lists problems and their fixes. **Part G** explains the words.


---

## Part A. Set up a designer's laptop (once; requesters skip this)

### What you need before you start

| You need | Where it comes from |
|---|---|
| A Windows laptop, with internet | Your own |
| The Claude login | Harsh |
| An invite to the project on GitHub (an email from GitHub) | Harsh adds you on GitHub |
| A login for n8n (an email from n8n) | Harsh invites you to n8n |
| One "Theme Access" password per shop (an email from Shopify) | Harsh or the shop owner sends it from Shopify (see A6) |

You will copy two kinds of secrets in this setup: an **n8n token** and **Theme Access passwords**. Treat them like bank
passwords: **never** paste them into a chat (not even Claude), an email, WhatsApp, a document or a screenshot. The setup
script asks for them in a hidden box and keeps them inside your Windows settings, nowhere else.

### A1. Install Claude
1. Open https://claude.ai/download and download **Claude for Windows**.
2. Install it and sign in with the Claude login.
3. Leave it open. We use its **Code** tab later.

### A2. Open PowerShell
PowerShell is the blue (or black) window where you type commands.
1. Press the **Windows key**, type **PowerShell**, and click **Windows PowerShell**.
2. To run a command from this guide: copy it, click inside PowerShell, right-click to paste, press **Enter**.
3. Wait until the line ends with `>` again before typing the next command.

### A3. Install Git (the tool that downloads the project)
Paste this and press Enter:
```
winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
```
When it says it is done, **close PowerShell and open it again** (A2), so it can see Git.

> If PowerShell says `winget` is not recognised: open the **Microsoft Store**, search **App Installer**, install or update it,
> then try again.

### A4. Download the project
Paste these three lines, one at a time, pressing Enter after each:
```
cd $HOME
git clone https://github.com/harsh-shopify-dev/dtj-agency-automation.git
cd dtj-agency-automation
```
A GitHub window opens the first time: **sign in with the GitHub account Harsh invited**. Then paste:
```
git checkout feature/store-factory-install-catcher
```
The project is now in the folder `dtj-agency-automation` inside your user folder (for example `C:\Users\riya\dtj-agency-automation`).

### A5. Get your n8n token
1. Open the invite email from n8n and set your password. The n8n address is https://n8n.srv2048145.hstgr.cloud
2. In n8n, click **Settings** (bottom left), then the **MCP** section (called "MCP Access" or "Instance-level MCP", depending on
   the version).
3. Create or copy your **access token**. Keep the page open: you paste it in A7.
4. Cannot find it? Ask Harsh. Do not ask him to send you his own token.

### A6. Get the Theme Access password for each shop
Harsh (or the shop owner) does this in Shopify: **Apps > Theme Access > Create password**, with your name and email. You get an
email from Shopify with a link: open it and copy the password. The link works **once**, so keep the page open until A7 is done.
If the link has expired, ask for a new password.

### A6b. DTJ's key vault (Bitwarden), if Harsh gave you access
DTJ keeps the shared passwords in a company Bitwarden vault (docs/ACCESS-AND-KEYS.md). If you have an invitation:
1. Accept it from your email and set up your Bitwarden account (choose a strong master password and remember it; nobody can
   recover it for you).
2. In the next step the setup script asks "Has Harsh given you access to DTJ's Bitwarden vault?". Type **Y**, sign in, and it
   copies your shop passwords for you, so you skip A6.

### A7. Run the setup script
In PowerShell (still in the `dtj-agency-automation` folder, see A4), paste:
```
powershell -ExecutionPolicy Bypass -File tools\team-setup\setup-team-pc.ps1
```
What you will see, step by step:
1. **Programs.** If something is missing (Python, Node.js, Chrome), it lists it and asks you to type **Y**. Type `Y` and press Enter.
   If it then says to open a NEW window: close PowerShell, open it again, run `cd $HOME\dtj-agency-automation` and the command above again.
2. **Shopify CLI and Python packages.** Nothing to do; wait.
3. **Connect Claude Code to n8n.** Nothing to do.
4. **Your secret settings.** For each one, it shows its name and where it comes from, then a box.
   - **N8N_MCP_TOKEN**: paste the n8n token from A5.
   - **DTJ_THEME_ACCESS_...**: one per shop; paste that shop's password from A6.
   - **Nothing appears while you paste. That is normal.** Just paste (right-click) and press Enter. It then says
     "Saved ... (N characters)".
5. **Readiness check.** A list of lines starting with `[ OK ]` or `[FIX ]`.

### A8. Restart, then check
1. **Close Claude and PowerShell completely**, then open them again. (They only see the new settings after a restart.)
2. In PowerShell:
   ```
   cd $HOME\dtj-agency-automation
   python tools\team-setup\check_setup.py
   ```
3. Every line should say `[ OK ]` and the last line **"Ready to design pages."**
   A `[FIX ]` line has an arrow under it that says exactly what to do. Do it, then run the check again.
   The check only reads: it never changes anything on a shop.

### A9. Open the project in Claude Code (once)
1. In Claude, open the **Code** tab.
2. Choose the folder `dtj-agency-automation` (in your user folder).
3. If Claude asks whether to use the **n8n** server for this project, choose **Allow**.

### A10. Let Claude check everything (any time)
In Claude (Code tab, this folder) type:
```
set up the store factory
```
Claude checks this laptop, n8n (the tables, the three automations and their passwords) and the app switch on every shop. It only
reads, and it tells you in plain words anything you must do (for example "run the setup script" or "ask Harsh to publish"). It
never asks you to type a password into the chat. At the end it says **"Ready. Say 'listen for the telegram call'"**.

Your laptop is ready.

### Keeping the project up to date
When Harsh says there is an update, in PowerShell:
```
cd $HOME\dtj-agency-automation
git pull
```

---

## Part B. How everything works

### The picture

```
 YOU (Telegram)            n8n (the conveyor belt)                          CLAUDE CODE (the designer, on a laptop)
 ──────────────            ───────────────────────                          ───────────────────────────────────────
 product link  ─────►  0. Store Factory: Telegram Bot ("Who is this? Allowed?")
 (to the bot)                    │
                                 ▼
                       1. Store Factory: New Page
                          "Which shop is this?"  (looks in dtj_stores)
                          saves a work order     (dtj_client_intake)
                          replies "Got it" (the bot tells you, and tells the designers
                                 │        "a page is waiting")
                                 ▼
                       2. Store Factory: Page Design
                          writes the task list
                          WAITS (up to 3 days) ◄──── you say: "handle the Claude Code trigger in n8n"
                                                           │
                                                           ▼
                                                     Claude reads the task list and:
                                                     reads the product and its pictures
                                                     reads the brand's website
                                                     writes the facts and the words
                                                     builds the page, runs 11 design checks
                                                     writes it to the shop's DRAFT theme
                                                     checks the real page (phone + computer)
                          checks Claude's answer ◄──── reports back
                          records the result:
                          status, preview link,
                          checks, samples
 preview link  ◄────────  and sends it to you on Telegram
```

### The pieces

| Piece | What it is | Plain words |
|---|---|---|
| **The shop** | A Shopify store with our 3 apps installed and a **draft theme** | The draft theme is a private copy of the shop's design. Shoppers never see it until Harsh publishes it. |
| **n8n** | https://n8n.srv2048145.hstgr.cloud | The conveyor belt. It holds the work orders and passes them from one step to the next. |
| **dtj_stores** (a table in n8n) | One row per shop | The shop's addresses, its draft theme, its app copies, its brand website. Set up once by Harsh. |
| **dtj_client_intake** (a table in n8n) | One row per page request | The work order: which product, who asked, and later the result and the preview link. |
| **dtj_bot_users** (a table in n8n) | One row per person allowed to use the bot | Their Telegram number, name and role (requester, designer, admin). |
| **@DtjPageDesignerBot** | The Telegram bot | The easiest front door: send it a product link, it sends you back the preview link. Admins can also switch a shop's DTJ apps off and on with it. |
| **The install service** | https://dtj-install-catcher.ultimateecomwithharsh.workers.dev | Keeps the on/off switch of every client's copy of our 3 apps. The bot asks it with its own key. |
| **Claude Code** | Claude's **Code** tab, opened in the project folder | The designer. It follows the project's rules and the task list. |
| **The project folder** | `dtj-agency-automation` on your laptop | The rules, the design knowledge and the tools Claude uses. |

### Automation 0: "Store Factory: Telegram Bot" (the messenger)

| Box in n8n | What it does |
|---|---|
| **Telegram Message** | Receives every message sent to the bot. |
| **Read the Message** | Ignores group chats. Refuses anything that looks like a password (asks you to delete it). Finds the first link; the rest of the message is your note. |
| **Load Bot Users** / **Load Shops** / **Who Is It** | Checks you are in dtj_bot_users. If not, it replies with your number to send to Harsh. Then decides what you asked for: a page, an admin command (Part E, "Switch a shop's apps"), or just an answer. |
| **What to Do** | Sends the request down the right path: a page, an admin's switch command, or a plain answer. |
| **Ask for the Shop List** / **Pick the Shop** / **What Next** | For a switch command: asks the install service which shops it can reach, finds the one you named (by name, `.myshopify.com` address or website), then asks the service about it, shows the confirm buttons, or explains what is wrong. |
| **Ask New Page** | Gives the link and your note to automation 1 and waits for its answer (about a second). |
| **Write the Answers** / **Send** | Tells you "Got it ..." and tells every designer "New page waiting ... type: handle the Claude Code trigger in n8n". |
| **Ask to Confirm** | For /off and /on: sends "Switch OFF ...?" with a **Yes** and a **Cancel** button. Nothing is switched yet. |
| **Is It a Button?** / **Answer the Button** | When an admin taps a button, tells Telegram the tap arrived (so the button stops spinning). |
| **Licence Calls** / **Ask the Switch** | Asks the install service about each DTJ app of the shop (or of every shop, for /shops), or switches them, with the bot's own key (the n8n credential **DTJ Catcher Bot Key**). |
| **Licence Report** | Turns the 3 answers into one message: each app ON or OFF, and "(checked)" when the service confirmed the change. Other admins are told too. |

### Automation 1: "Store Factory: New Page" (the front door, about 1 second)

| Box in n8n | What it does |
|---|---|
| **What to Design (edit me)** | Where you paste the product link and a note (Part C). |
| **From Another Workflow** | The same front door, used by the Telegram bot. |
| **Take the Request** | Tidies the link and the note. |
| **Load Stores** | Reads the shops table (dtj_stores). |
| **Match the Store** | Finds the shop the link belongs to. If anything is wrong it explains it in one sentence (wrong kind of link, shop not set up, no draft theme). |
| **Matched?** | Yes: go on. No: go to **Not Started** (nothing is saved). |
| **Save Brief** | Saves the work order in dtj_client_intake. |
| **Start Page Design** | Starts automation 2 and does not wait for it. |
| **Started** | Your answer: "Got it: designing ..." and what to do next. |

### Automation 2: "Store Factory: Page Design" (the design desk)

| Box in n8n | What it does |
|---|---|
| **When a Brief Is Ready** | Automation 1 starts it with the work order's number. |
| **Load Brief** | Reads that work order. |
| **Request for Claude Code: Page Design** | Writes the complete, numbered task list for Claude, including where to answer. |
| **Wait for Claude Code: Page Design** | Pauses. It waits up to 3 days for you to run Claude Code. |
| **Claude Code Reply: Page Design** | Checks Claude's answer (a page marked "written" must come with a real preview link). |
| **Record Page Design** | Writes the result on the work order: status, preview link, checks passed, number of samples. |
| **Tell the Requester** / **Send Result** | If the request came from Telegram: sends the person the preview link and the number of samples (or why it was not finished). |

### What Claude does when you say "handle the Claude Code trigger in n8n"
1. Finds the waiting work order in n8n and reads its task list.
2. Reads the product from the shop and downloads its pictures, under the exact names the shop uses.
3. Reads the brand's own website. If a look you like is named (for example "Minimalist"), it measures that site's colours.
4. Writes the facts (every fact with its source) and the words of the page. Anything it had to make up to fill the design is
   marked **SAMPLE** and listed, so it can be replaced before the page goes live. It never makes up prices, offers, medical
   claims or certificates.
5. Builds the full page (the same 13 sections for every product) and runs every check: words, layout, contrast, and the
   **11 design checks** from Harsh's reviews.
6. Only if every check passes, writes the page into the shop's **draft** theme. It can never write to the live theme.
7. Opens the real page on a phone-size and a computer-size screen and checks it.
8. Reports back to n8n, adds a note to the project log, and tells you the preview link and the list of samples.

### What is safe and what is not
- Pages only ever go into a **draft** theme. Publishing (making it live) is Harsh's decision, always.
- Secrets stay in your Windows settings. Claude never needs them typed into the chat.
- Claude may ask "allow this?" for something unusual. If you are not sure what it means, choose **No** and ask Harsh.
  The normal page steps are already allowed, so you should rarely see this.

---

## Part C. Make a page (every time)

### Step 1. Copy the product link
1. Open the product **on the shop's website** (the page shoppers see), not in the Shopify admin.
   In the Shopify admin you can open it with the **View** button on the product page.
2. Copy the address from the top of the browser. It contains `/products/`, for example
   `https://test-store-harsh-dtj.myshopify.com/products/pore-clarifying-serum-2-salicylic-acid-30ml`

### Step 2. Send it to the bot (the easy way)
1. In Telegram, open **@DtjPageDesignerBot**.
2. Paste the link. If you want, add a note after it in the same message, in plain words. For example:
   `https://hopenskin.com/products/vitamin-c-serum lead with the glow, real rating 4.6 on Judge.me`
3. The bot answers in a few seconds:
   - "Got it: designing ..." means the work order is saved. Designers get a message too.
   - Anything else explains, in one sentence, what to fix (usually the link). Fix it and send again.
4. If you are a **requester**, you are done: the bot sends you the preview link when the page is ready (Part D).
   If you are a **designer**, go to Step 3.

### Step 2 (other way). Give it to n8n by hand
Use this only if Telegram is not available.
1. Open https://n8n.srv2048145.hstgr.cloud and open the workflow **Store Factory: New Page**.
2. Double-click the box **What to Design (edit me)**.
3. Find the line that starts with `const product_link =`. It ends with two small slanted marks `` ` ` `` and a `;`.
   Click between the two marks and paste the link, so it looks like
   ``const product_link = `https://...your link...`;``
4. Optional: on the line `const note =`, write a note between its two marks, in plain words (apostrophes are fine). For example
   ``const note = `Lead with acne marks. Real rating 4.6 from Judge.me. Don't use green.`;``
   Keep the two marks and the `;` at the end of each line.
5. Close the box, press **Ctrl + S** to save, then click **Execute workflow** (bottom of the screen).
6. Click the box at the end that turned green:
   - **Started**: read the message. It says "Got it: designing ...". Go to Step 3.
   - **Not Started**: read the message, fix what it says (usually the link), and try again.

### Step 3. Let Claude design it (designers)
Designers get a Telegram message "New page waiting ..." whenever someone sends a link.
1. Open Claude, the **Code** tab, in the folder `dtj-agency-automation`.
2. Type exactly:
   ```
   handle the Claude Code trigger in n8n
   ```
3. Wait about 15 to 20 minutes. Claude works on its own. If it asks to allow a normal page step, choose **Allow**.
4. At the end Claude gives you the **preview link** and the **list of samples**. The bot also sends the preview link to the
   person who asked.

### Step 3 (hands-free). Let Claude listen for the bot
Instead of starting each page yourself, you can let Claude wait for them while you are at your laptop:
1. In Claude (Code tab, this folder) type:
   ```
   listen for the telegram call
   ```
2. Claude says "Listening for page requests until ...". Keep the window open. Every time someone sends a link to the bot, Claude
   designs that page on its own, sends the preview link back (the bot passes it on), tells you in three lines, and waits for the
   next one.
3. To stop, type `stop listening`. It also stops by itself after 8 hours.
- **Only one laptop listens at a time** (two would design the same page twice). Agree in the team who listens today.
- **Only while you are at the laptop.** Do not leave it listening overnight or while nobody is around: running Claude unattended
  needs a different (paid API) setup that Harsh decides on.

---

## Part D. After the page is made

1. Open the **preview link** (from the bot, or from Claude) on your phone and on a computer. This is the draft: shoppers
   cannot see it.
2. Read the **samples list**. These are placeholder words or pictures (for example made-up reviews) that must be replaced with
   real ones, or approved by Harsh, before the page goes live.
3. Send Harsh the preview link and the samples list. He decides what goes live and when.
4. The result is also saved in n8n: **Data tables > dtj_client_intake**, the newest row (page_status "written to draft", the
   preview link, how many checks passed, how many samples).

---

## Part E. Add a new shop (Harsh)

A shop can get pages only after these steps, done once:
1. **Our apps, on the switch:** either the client's own copies of DTJ Blocks, DTJ Sections and DTJ Sections 2 are installed
   through the install service (`services/install-catcher/tools/add_client.py`), or, for a shop inside DTJ's own Shopify
   organization that runs DTJ's original apps, it is added with `add_client.py --org --shop <shop>.myshopify.com --label "<Name>"`
   (needs DTJ's original app secrets once: `tools\team-setup\save-dtj-app-secrets.ps1`). Then the install service is deployed
   (`services/install-catcher/tools/deploy.py`) and `/shops` in the bot shows the shop. Its addresses file exists:
   `services/store-builder/page_builder/clients/<shop>.json`.
2. **A draft theme:** in the shop's admin, **Online Store > Themes**, on the live theme click **...** > **Duplicate**. Note the
   new theme's number (in its "Customize" link). If a draft is ever published, make a new duplicate: the tools refuse to
   write to a live theme.
3. **Theme Access:** install Shopify's **Theme Access** app on the shop and send a password to each team member (Part A6).
4. **A row in dtj_stores** (n8n > Data tables > dtj_stores): store_name, myshopify_domain (the shop's ORIGINAL
   `.myshopify.com` address), other_domains (every other address of the shop, separated by commas, for example
   `hopenskin.com, www.hopenskin.com`), draft_theme_id, client_registry (`page_builder/clients/<shop>.json`), brand_name,
   brand_website, reference_brands (optional), store_notes (optional), active = true.
5. Each designer runs the setup script again (Part A7): it asks only for the new shop's password. Then the check (A8).

### Add a person to the bot (Harsh)
1. The person messages **@DtjPageDesignerBot** and sends you the number it replies with.
2. In n8n: **Data tables > dtj_bot_users > add a row**: telegram_user_id (that number), name, role (`requester`, `designer`
   or `admin`), active = true.
3. To remove someone, set active = false. Designers and admins get the "New page waiting" messages.
   Only make someone an `admin` if you trust them to switch a client's apps off: admins can do that from their phone.

### Switch a shop's DTJ apps off or on (admins)
Use this when a client stops paying, or to bring their apps back. It switches all 3 DTJ apps (Blocks, Sections, Sections 2) of
that shop at once. Only people with the role `admin` can use it; everyone else gets "Only an admin can ...".

| Send the bot | What happens |
|---|---|
| `/shops` | Every shop the switch reaches, with each DTJ app ON or OFF. Changes nothing. |
| `/status test store` | Each of the shop's 3 apps: ON or OFF. Changes nothing. |
| `/off test store` | The bot asks "Switch OFF all DTJ apps on DTJ Test Store?" with two buttons. Tap **Yes, switch OFF** within 2 minutes, or **Cancel**. |
| `/on test store` | The same, to switch them back on. |

- You can use the shop's name, its `.myshopify.com` address or its website address. If more than one shop matches, the bot
  asks you to be more specific.
- **OFF means every DTJ block disappears from that shop for its shoppers at once**, until someone switches it back on. The
  shop's theme and pages are not changed or deleted.
- After a switch the bot answers each app `ON -> OFF (checked)`. "(checked)" means the service read the switch back and it
  really changed. If a line says "NOT confirmed" or "failed", send `/status` again and tell Harsh.
- Every switch is saved in the install service's log with your name ("via Telegram") and every other admin gets a message.
- **Which shops:** every shop the install service knows, whether or not it gets pages: client shops with their own copies of
  our apps (for example Rupa Divine), and shops inside DTJ's own Shopify organization that run DTJ's original apps (for example
  Elevate with Harsh, once Harsh has added it, Part E). A shop set up for pages but not on the switch yet is named at the end
  of `/shops`.
- What the lines mean: **ON** / **OFF**; **not set (blocks hidden)** = the switch was never set on that shop, so DTJ blocks
  stay hidden until someone sends `/on`; **not installed on the shop** = the shop has not installed that app (or removed it).

---

## Part F. Problems and fixes

| What you see | What it means | What to do |
|---|---|---|
| **Not Started:** "That is a Shopify admin link" | You copied the link from the admin | Open the product on the shop's website (View) and copy that link |
| **Not Started:** "not a product page" | The link has no `/products/` in it | Open the product itself, not a collection or the home page |
| **Not Started:** "is not set up for page design yet" | The shop is not in dtj_stores | Ask Harsh to add it (Part E) |
| **Not Started:** "no draft theme" / "no app copies" / "paused" | The shop's row is incomplete or switched off | Ask Harsh |
| The check says `[FIX ] ... draft theme ... is live` | The draft was published, so it is no longer a draft | Ask Harsh to make a new draft (Part E step 2) and update dtj_stores |
| The check says a password or token is not saved | A secret is missing | Run the setup script again (A7) |
| The check says Shopify refused the design password | The Theme Access password is wrong or was removed | Ask for a new one (A6), then run the setup script with `-Replace` at the end of the command |
| Claude says it cannot see n8n | Claude was opened before the setup, or the n8n server is not allowed | Close Claude completely, open it again in the project folder, choose **Allow** for n8n. Still not working: run the check (A8) |
| Claude says "could not build" | Something stopped the page (Claude explains why) | Send Harsh Claude's message. Nothing was written to the shop |
| Claude asks to allow something unusual | A step outside the normal page steps | If unsure, choose **No** and ask Harsh |
| Nothing happens after "handle the Claude Code trigger in n8n" | No work order is waiting | Do Part C Step 2 first; check the box at the end says **Started** |
| PowerShell: "running scripts is disabled" | Windows blocks scripts by default | Use the exact command in A7 (it starts with `powershell -ExecutionPolicy Bypass`) |
| The bot says "This bot is only for the DTJ team ... send Harsh this number" | You are not on the list yet | Send Harsh the number |
| The bot says "That looks like a password or a key" | Your message looked like a secret | Delete your message (press and hold it, then Delete). Never send passwords to any chat |
| The bot does not answer at all | n8n is down, or you wrote in a group | Write to the bot directly (not in a group). Still nothing after a minute: tell Harsh |
| You sent a link but no preview link came back | Nobody has run Claude Code yet, or the page could not be finished | Ask a designer; the bot tells you if the page was not finished, and why |
| The bot says "That button has expired" | More than 2 minutes passed before you tapped | Send the /off or /on command again |
| The bot says "the bot's key was refused" | The n8n credential **DTJ Catcher Bot Key** does not match the install service | Harsh: open the credential, check Name is `X-DTJ-Bot-Key`, paste the key again (see HANDOFF, 12 Oct) |
| The bot says a shop "is set up for pages, but its DTJ apps are not on the switch yet" | The shop is in dtj_stores but not in the install service | Harsh adds it (Part E step 1) |
| A line says "not installed on the shop" | The shop never installed that app copy, or removed it | The shop owner installs it from the link Harsh sends |
| A line says "outside DTJ's Shopify organization" | DTJ's original app is not installed there, or the shop is not in DTJ's organization | Ask Harsh |

---

## Part G. Words

| Word | Meaning |
|---|---|
| **Draft theme** | A private copy of the shop's design. Changes there are invisible to shoppers until it is published. |
| **Live theme** | The design shoppers see right now. Our tools never change it. |
| **Publish** | Make a draft the live theme. Only Harsh does this. |
| **Sample** | A placeholder (a made-up review, a test picture) that fills the design until the real one arrives. Always listed. |
| **n8n** | The online tool that runs our automations (workflows) and keeps the tables. |
| **Workflow** | A chain of boxes in n8n that runs one after another. |
| **Work order / brief** | One row in dtj_client_intake: one page request. |
| **Theme Access password** | A password from Shopify that lets the tools write to a shop's draft theme. One per shop, per person. |
| **n8n token** | Your personal key that lets Claude talk to n8n. |
| **Requester / designer / admin** | A requester sends links to the bot. A designer also runs Claude Code on a set-up laptop. An admin can also switch a shop's DTJ apps off and on. |
| **App switch** | The on/off switch of a client's copy of our apps. OFF hides every DTJ block on that shop until it is switched back on. |
| **Preview link** | The address where you can see the draft page. |
