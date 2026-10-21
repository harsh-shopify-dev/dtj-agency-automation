---
name: dtj-header-footer
description: Design a client store's HEADER and FOOTER (the announcement bar, the header with logo, menu and cart, the footer with sign-up, menus, policies and social icons; on every page of the store) from the brand's colour palette, with real store-wide facts only, and prepare the DRAFT theme write for a person's yes. Removes Horizon's placeholders (Welcome to our store, the "exclusive deals" promise, social links to bare facebook.com / instagram.com, Powered by Shopify), places the brand's colours with checked contrast, shows a before / after preview on the real draft and checks the real page after the write. Use it whenever someone says "header", "footer", "announcement bar", "top bar", "nav bar", "menu bar", "the top of the store", "the bottom of the store", "design the header and footer", "brand colours in the header", or "remove Powered by Shopify", even if they don't name the skill. Not for page content (home: dtj-home-page, product: dtj-pdp-factory, collection: dtj-collection-page) and not for editing the store's menus (navigation links live in Shopify admin and need the person's yes).
---

# DTJ header and footer: the brand's palette on every page

Harsh, 21 Oct 2026: "what left is the header and footer design, the header and footer will be designed according to the color palette".

What that means here:
- **The theme's own parts, only re-dressed.** Horizon's header and footer are two group files (`sections/header-group.json`,
  `sections/footer-group.json`). The builder starts from the files AS THEY ARE on the draft and changes only colours, words, social links
  and a few switches; every section, block and id stays (`page_builder/assemble_chrome.py`).
- **The palette decides the colours, the placement is fixed** (`CHROME_COLOURS`): announcement bar on the brand's deep colour with light
  words; header on the page colour with the text colour and a thin border; cart count in the button colours; footer and its bottom strip on
  the brand's deep colour (Horizon turns the words light by itself); sign-up button in the button colours. Every pair is checked at 4.5:1.
- **Real words only.** Announcement lines come from `chrome.json` (store-wide promises: shipping, payment, returns, each with its source)
  or, when it has none, the home facts' announcements. Marked SAMPLE lines go only to a draft (the write then needs `--allow-samples`).
  No line at all = the bar is switched OFF, never "Welcome to our store". Social icons only for the brand's real pages (with where they
  were found); Horizon's placeholder links are emptied. The footer's "Get exclusive deals and early access" promise becomes a modest line.
- **Tier 2 every time.** These two files are on every page, and Harsh's standing draft rule covers product and home pages only: a person
  approves each file's code, draft theme only, never the live theme.

## Design rules (21 Oct 2026 study of 23 strong D2C home pages; `references/study.md`)
| Measured | What the builder does |
|---|---|
| Announcement bar on top: 17 of 23; dark or brand-coloured: 13; about 41 px tall | the brand's deep colour, light words, 10 px above and below a 14 px line |
| Header on white: 21 of 23; sticky: 17; logo left: 12, centred: 4 | the page colour, sticky always, the theme's own logo / menu positions kept |
| Footer dark or brand-coloured: 15 of 23; white or light: 7 | the brand's deep colour, the theme picks light words |
| Sign-up in the footer: 16; social links: 21; payment icons: 4 | the theme's sign-up kept (button in the brand's button colours); social links only when the brand's real pages are known: collect them (H1), most strong stores show them |
Colours come from the brand's palette (Harsh, 19 Oct: "every brand has their own color palette"), never a fixed set.

## Steps
### H0. Orient
Read `CLAUDE.md` and the latest `docs/HANDOFF.md`. Confirm the store's ORIGINAL `.myshopify.com` address, the DRAFT theme id, the client
folder (`.work/clients/<client>/` with `brand.json`; `home-facts.json` and `chrome.json` optional). The Theme Access password must be in the
Windows variable `DTJ_THEME_ACCESS_<STORE HANDLE>` (check by NAME only). **Gate:** all known, or one precise question.

### H1. Facts
Collect store-wide lines (the store's shipping, refund and payment pages, the checkout's payment options, COD) into `chrome.json` with a
source each, and the brand's real social pages (its own site footer, its Instagram bio link) with where they were found:
```json
{"announcements": [{"text": "Free shipping above Rs. 499", "source": "shipping policy page, 21 Oct 2026", "link": "/policies/shipping-policy"}],
 "social": {"instagram": {"url": "https://www.instagram.com/<brand>/", "source": "the brand's own site footer, 21 Oct 2026"}},
 "newsletter": {"text": "<the brand's own sign-up line>", "source": "<where>"}}
```
Never a product claim in the bar (it is on every page), never an offer the store does not run. **Gate:** every line and link has a source.

### H2. Build (read-only on the store) and preview
```bash
cd services/store-builder
../../.work/.venv/Scripts/python.exe -m page_builder.run_chrome --client ../../.work/clients/<client> --store <store> --theme <id>
cd ../..
python .claude/skills/dtj-header-footer/scripts/preview_chrome.py --client .work/clients/<client> --store <store> --theme <id>
```
(Git Bash: prefix with `MSYS_NO_PATHCONV=1` when a page path like `/` is passed.) Look at `chrome-preview/*-before-*.png` and
`*-after-*.png`. The preview paints the design over the real page in the browser: close, not exact. **Gate:** build problems 0, every
contrast 4.5:1 or more, no placeholder left in `chrome-report.json`.

Look for repetition before asking: a home page that has its own announcement strip right under the header (`home_announcement`, DTJ
Commerce marquee-band) would show the same lines twice. Say so and offer the fix (the bar carries them on every page; the home strip goes).

### H3. Approval (Tier 2) and write
Show the person the before / after screenshots, the colours with their contrast, what was removed, the SAMPLE lines, the target (store,
draft theme id, the two files) and the two approve codes. On their yes (with the codes, by name):
```bash
cd services/store-builder
../../.work/.venv/Scripts/python.exe -m page_builder.push_page --out ../../.work/clients/<client>/chrome-run/header --approve <code> --approved-by "<name>" [--allow-samples]
../../.work/.venv/Scripts/python.exe -m page_builder.push_page --out ../../.work/clients/<client>/chrome-run/footer --approve <code> --approved-by "<name>"
```
Each refuses a live theme, a changed file (someone edited it in the editor since H2: build again) and a wrong code; each backs up the old
file first and reads the new one back.

### H4. Check the real page
```bash
MSYS_NO_PATHCONV=1 python .claude/skills/dtj-header-footer/scripts/check_chrome_live.py --client .work/clients/<client> --store <store> --theme <id> --paths / /collections/all
```
K1-K5 must pass (lines and colours as designed, every word 4.5:1, no placeholder, no bare social link, no Powered by Shopify, no sideways
scroll). Update `docs/HANDOFF.md`. **Gate:** PASS, or each finding explained with its fix. Undo: push the backup with push_page.

## Not done by this skill (say so plainly)
The store's menus (main menu, footer menu: their links and names live in Shopify admin; a broken item such as "footer-client-services" is
the person's to fix, or Claude's with their yes), the logo picture (theme settings), and the theme's global colours and fonts
(`config/settings_data.json`, never written by the page builder).

## Files
| File | What |
|---|---|
| `services/store-builder/page_builder/assemble_chrome.py` | the design: placement of the palette, words, placeholders, contrast |
| `services/store-builder/page_builder/run_chrome.py` | read-only check of the draft, backups, the two approval files |
| `services/store-builder/page_builder/base/horizon-chrome-parts.json` | Horizon 4.2.0's header / footer settings, for validation |
| `scripts/preview_chrome.py` | before / after screenshots on the real draft (paint only, nothing written) |
| `scripts/check_chrome_live.py` | the real page after the write (K1-K5) |
| `references/study.md` | how 24 strong D2C sites do their header and footer |
