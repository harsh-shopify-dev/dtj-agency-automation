# DTJ Heroes (fourth theme app extension)

Why it exists: the home page hero and showcase sections get their own app so they can be released and licensed on their own, and because DTJ Sections 2 already holds 6 blocks.
Design and limits: `docs/block-library-design.md`; state and history: `docs/HANDOFF.md`.

**Status (12 Oct 2026): app created and linked (client id 6d250bd5...), release `dtj-heroes-3` is active with all 4 blocks. NOT installed on any store yet and no licence flag set (blocks show nothing until it is `active`).**

## Blocks (5; 94 KB of 100 KB: this app is FULL, the next block goes in a new app)
| Block (file `dtj-<id>`) | Editor name | Notes |
|---|---|---|
| `hero-banner` | DTJ Hero Banner | one block, three layouts chosen by the **Layout** setting. **V1 Banner**: full-width picture with the text on it over a side fade (badge, heading with accent words, subheading, boxed star rating with partial stars, up to 4 ticked points, button); phones = picture on top melting into the text, or the text on the picture's lower edge. **V2 Split**: picture on one side (left or right, fill or show whole), a rounded text panel on the other with heading, paragraph, ticked points, a review quote card and button; phones = picture then panel. **V3 Cover**: the whole picture with the text low on it over a bottom fade (heading with a forced line break, paragraph, one tick point, button with arrow); phones = text on the picture with picture space kept above it. Built from the Supersenior promo hero (`dtj-hero-promo`) and three screenshots from Harsh (12 Oct 2026). The Supersenior code was NOT ported (it uses Horizon-only constructs); this is a rewrite. |

| `video-reviews` | DTJ Video Reviews | a centre-focus carousel of tall review cards (up to 6): the centre card is full size, its neighbours are smaller and tucked behind it, the outer pair fades (desktop shows 5 or 3, phones show the centre with the neighbours peeking in). Each card: picture, optional video, name with an optional verified tick, one line, a link. A video file loads ONLY when a visitor presses play (it replaces the picture in place, with a close button). Heading and subheading above, arrows at the sides (optional on phones), swipe, arrow keys, optional autoplay (only while on screen, never while a video plays, never with reduced motion). Built from Harsh's Sternify screenshot "Uber 1000+ Menschen vertrauen uns". **Page-friendly by design:** all sizing is CSS (container query units), the 5 KB script only moves a `data-d` attribute and measures nothing, only transform and opacity animate, pictures are lazy with width/height and a 4-size srcset, the section skips rendering while off screen (`content-visibility`), the first paint is correct without the script. |

| `feature-cards` | DTJ Feature Cards | a badge pill, a heading, a rounded centre picture with up to 3 soft feature cards on each side (round icon, capitals title, text; 22 built-in icons) and a button under the picture. The button is a regular rounded or square rectangle, never an oval (Harsh, 12 Oct 2026). Phones: picture, then the cards (one or two per row), then the button. Plain grid and flex, no script; the tint uses `color-mix` inside `@supports`, so older browsers get a clean outline instead. Built from Harsh's SONA "Designed For The Modern Bathroom" screenshot; it is the Feature Showcase layout (DTJ Sections 2) restyled, kept as its own block so the home page sections live in this app. |

| `feature-tiles` | DTJ Feature Tiles | heading, paragraph, a button and up to 6 small icon tiles (28 built-in icons: tooth, sliders, hourglass, signal, battery with bolt, shield with drop and more) on one side, a rounded picture on the other (left or right; on desktop the picture fills the height of the text column). Rectangular button (rounded or square, never an oval). Phones: picture above or below the text, tiles 1, 2 or 3 per row. Plain grid, no script. Built from Harsh's SONA "Precision Quiet Design" screenshot. |

| `compare-showcase` | DTJ Compare Showcase | words on the left (small line, heading with accent words, paragraph, up to 4 ticked points, button), a centre product picture and a comparison table card with one highlighted column (up to 7 rows; an empty cell is a tick or a cross, typed words replace them; our column can show a logo). Two variations: **Spotlight** (serif heading, ticks and button; picture hidden on phones; serif brand name in the table header) and **Gradient** (bold heading with an italic accent; picture shown on phones). Sizes copy the reference sections and never grow past them: content max 1400 px, table card 535 px with 58 px rows and 35/32.5/32.5 columns on desktop; full width up to 400 px with 46 px rows and 46/27/27 columns on phones (measured in a real browser at 1917 and 367 px: card 535x429 and 347x327, no sideways scroll). A real HTML table (caption, column and row headers), no script. Built from Harsh's Happy Place and Bris screenshots (13 Oct 2026). |

Settings worth knowing (hero banner): `|` in the heading starts a new line; `*words*` in the heading and rating text mark the accent / bold part; `Automatic` choices follow the layout (accent style, phone alignment, point icon, overlay, text height, phone layout); a separate phone picture is optional; the first hero on a page loads its picture first (`priority`). No default copy and no hard-coded colours are shipped.

Standard controls: top/bottom padding (default 0), side space (default 0: a hero is edge to edge), text and background colour. Every block runs the licence gate.
Put it in a FULL-WIDTH section so it reaches both screen edges.

## First-time setup (Harsh; each step is his or needs his yes)
1. Create the app in the Dev Dashboard (Custom distribution, organization Harsh) named `DTJ Heroes`.
2. `cd "D:\CODE CONTAINERR\WEB DEV\dtj-agency-automation\services\block-library-heroes"` then `shopify app config link` and pick that app. CHECK the path in the prompt ends in `block-library-heroes` (the command rewrites that folder's `shopify.app.toml`).
3. Deploy (Tier 2, approve the exact command): `shopify app deploy --path "services\block-library-heroes" --allow-updates --message "<what>" --no-color`, then `shopify app versions list --path services\block-library-heroes` (the star = active). Expect Shopify to refuse something the local checks cannot see; each refusal becomes a library rule.
4. Install on the test store, then set the licence flag `active` (a fresh install has none, so the block shows nothing, by design).
5. Register the app everywhere the other three are listed, only AFTER step 2 (a placeholder id would break `--app all`): `services/block-library/tools/licence.py` (`APPS`, new env var `DTJ_HEROES_CLIENT_SECRET`), `tools/dtj-licence.ps1`, `services/store-builder/page_builder/registry.json` (the extension uuid appears after the first deploy), the vault and the key script in `tools/team-setup/`, the install catcher (`services/install-catcher`) and the Telegram bot's licence calls (`n8n/store-factory/licence_calls.js`).

## Daily commands (from `services/block-library-heroes`, venv python)
```
python ../block-library/tools/build_blocks.py --root .            # write generated files (add --check to only verify)
DTJ_APP_ROOT=$PWD python ../block-library/tools/check_library.py   # library rules + size budget
DTJ_APP_ROOT=$PWD ../../.work/.venv/Scripts/python -m unittest discover -s tests -t .
shopify theme check --path extensions/dtj-heroes
```
The Shopify CLI on Harsh's PC lives in the Claude desktop app's own npm folder (`C:/Users/harsh/AppData/Local/Packages/Claude_pzs8sxrjxfjjc/LocalCache/Roaming/npm/shopify.cmd`, version 4.9.3), so a normal PowerShell window does not find `shopify`: call it by that full path or install it in a normal window (`npm install -g @shopify/cli`).
Preview (from `services/block-library`, `DTJ_APP_ROOT` pointing at this folder, `PREVIEW_THEME=1`): `python tools/preview_block.py hero-banner out.png "layout=split" "heading=..." "image=FILE:path.jpg:1.5"`; `PREVIEW_WIDTH=1400` for desktop.

## Verified / not verified
Verified (12-13 Oct 2026): 78 unit tests; library rules and size budget; Shopify Theme Check (CLI 4.9.3: only the usual ExcessiveSettingsCount warnings, one per block); headless-browser renders of the hero V1, V2, V3 and the video carousel on desktop (1400 / 1800 px) and phone (390 px) with crops of Harsh's screenshots as stand-in pictures (hero V3 used a plain placeholder: no clean photo was available). Video playback itself (press play, close, stop on slide change) is covered by code reading and the markup tests only: the headless render does not click.
NOT verified: video playback in a real browser, swipe on a real phone, the speed on a real store (no Lighthouse run), a deploy, the theme editor, real product photos, the page speed of a real hero image, tablet widths in a real editor.
