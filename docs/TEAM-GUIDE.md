# DTJ Page Designer: team guide

This guide is for anyone in the team, technical or not. Follow it top to bottom and you will be able to make a full product page
for any shop that has our apps, without Harsh and without Harsh's computer.

- **Part A** sets up your laptop. You do it **once** (about 45 minutes).
- **Part B** explains how everything works. Read it once; it makes the rest easy.
- **Part C** is what you do **every time** you make a page (about 2 minutes of your time, then about 15 to 20 minutes of waiting).
- **Part D** is what to do with the finished page.
- **Part E** is for Harsh: adding a new shop.
- **Part F** lists problems and their fixes. **Part G** explains the words.

> Coming soon: a Telegram bot. You will send the product link to the bot instead of opening n8n. Part C will then get shorter.
> Everything else in this guide stays the same.

---

## Part A. Set up your laptop (once)

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
 YOU                       n8n (the conveyor belt)                          CLAUDE CODE (the designer, on your laptop)
 ───                       ───────────────────────                          ──────────────────────────────────────────
 product link  ─────►  1. Store Factory: New Page
                          "Which shop is this?"  (looks in dtj_stores)
                          saves a work order     (dtj_client_intake)
                          replies "Got it"
                                 │
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
```

### The pieces

| Piece | What it is | Plain words |
|---|---|---|
| **The shop** | A Shopify store with our 3 apps installed and a **draft theme** | The draft theme is a private copy of the shop's design. Shoppers never see it until Harsh publishes it. |
| **n8n** | https://n8n.srv2048145.hstgr.cloud | The conveyor belt. It holds the work orders and passes them from one step to the next. |
| **dtj_stores** (a table in n8n) | One row per shop | The shop's addresses, its draft theme, its app copies, its brand website. Set up once by Harsh. |
| **dtj_client_intake** (a table in n8n) | One row per page request | The work order: which product, who asked, and later the result and the preview link. |
| **Claude Code** | Claude's **Code** tab, opened in the project folder | The designer. It follows the project's rules and the task list. |
| **The project folder** | `dtj-agency-automation` on your laptop | The rules, the design knowledge and the tools Claude uses. |

### Automation 1: "Store Factory: New Page" (the front door, about 1 second)

| Box in n8n | What it does |
|---|---|
| **What to Design (edit me)** | Where you paste the product link and a note (Part C). |
| **From Another Workflow** | The same front door for the Telegram bot (coming soon). |
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

### Step 2. Give it to n8n
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

### Step 3. Let Claude design it
1. Open Claude, the **Code** tab, in the folder `dtj-agency-automation`.
2. Type exactly:
   ```
   handle the Claude Code trigger in n8n
   ```
3. Wait about 15 to 20 minutes. Claude works on its own. If it asks to allow a normal page step, choose **Allow**.
4. At the end Claude gives you the **preview link** and the **list of samples**.

---

## Part D. After the page is made

1. Open the **preview link** on your phone and on a computer. This is the draft: shoppers cannot see it.
2. Read the **samples list**. These are placeholder words or pictures (for example made-up reviews) that must be replaced with
   real ones, or approved by Harsh, before the page goes live.
3. Send Harsh the preview link and the samples list. He decides what goes live and when.
4. The result is also saved in n8n: **Data tables > dtj_client_intake**, the newest row (page_status "written to draft", the
   preview link, how many checks passed, how many samples).

---

## Part E. Add a new shop (Harsh)

A shop can get pages only after these steps, done once:
1. **Our apps:** the client's copies of DTJ Blocks, DTJ Sections and DTJ Sections 2 are installed and switched on (the install
   catcher). Their addresses file exists: `services/store-builder/page_builder/clients/<shop>.json`.
2. **A draft theme:** in the shop's admin, **Online Store > Themes**, on the live theme click **...** > **Duplicate**. Note the
   new theme's number (in its "Customize" link). If a draft is ever published, make a new duplicate: the tools refuse to
   write to a live theme.
3. **Theme Access:** install Shopify's **Theme Access** app on the shop and send a password to each team member (Part A6).
4. **A row in dtj_stores** (n8n > Data tables > dtj_stores): store_name, myshopify_domain (the shop's ORIGINAL
   `.myshopify.com` address), other_domains (every other address of the shop, separated by commas, for example
   `hopenskin.com, www.hopenskin.com`), draft_theme_id, client_registry (`page_builder/clients/<shop>.json`), brand_name,
   brand_website, reference_brands (optional), store_notes (optional), active = true.
5. Each team member runs the setup script again (Part A7): it asks only for the new shop's password. Then the check (A8).

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
| **Preview link** | The address where you can see the draft page. |
