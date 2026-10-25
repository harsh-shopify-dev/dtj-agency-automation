// n8n Code node "Request for Claude Code: Page Design" in "Store Factory: Page Design" (mode: Run Once for All Items).
// The run pauses at the Wait node after this one. A Claude Code session on Harsh's PC (possibly a FRESH one that knows nothing about
// the project) finds this waiting run, reads `instructions` and does everything in it: research, design, checks, the DRAFT write,
// the answer to resume_url. Harsh's choice (9 Oct 2026): Claude Code is the AI step while he is in the loop, not the Claude API.
const row = $input.first().json;
if (!row || !row.id) throw new Error('No brief row (dtj_client_intake id) reached this step');
const parse = (s, fallback) => { try { return JSON.parse(s || ''); } catch (e) { return fallback; } };
const brand = parse(row.brand_json, {});
const facts = parse(row.facts_json, {});
const urlHandle = (String(row.product_url || '').match(/\/products\/([a-z0-9][a-z0-9-]*)/i) || [])[1] || '';
const handle = (urlHandle || (facts.product && facts.product.handle) || '').toLowerCase();
if (!handle) throw new Error('The brief has no product (product_url or facts.product.handle)');
const store = String(row.store_domain || '').toLowerCase();
const theme = String(row.theme_id || '');
const suffix = row.template_suffix || ('dtj-' + handle).slice(0, 48).replace(/-+$/, '');
const registry = row.client_registry || '';
const folder = ('n8n-' + row.id + '-' + handle).slice(0, 60).replace(/-+$/, '');
const C = '../../.work/clients/' + folder;
const resumeUrl = $execution.resumeUrl;
// the brand intake (19 Oct 2026): the requester answers "collect the brand's data first?" in Telegram AFTER this request is written,
// so Claude Code reads the brief's brand_intake column when it starts. The data goes to a folder per website, shared by every page.
const site = row.brand_website || ((String(row.product_url || '').match(/^https?:\/\/[^/]+/i) || [])[0]) || ('https://' + store);
const host = String(site).replace(/^https?:\/\//i, '').replace(/^www\./i, '').replace(/[/?#].*$/, '').toLowerCase();
const INTAKE = '../../.work/clients/intake-' + host;
const regArg = registry ? ' --client-registry ' + registry : ' --client-registry <the file in page_builder/clients/ whose "store" is ' + store + '>';
// the progress bar (Harsh, 20 Oct 2026: "in the telegram bot also add the progress bar for page designing"): a request from the bot
// carries the requester's chat; the designer's session edits ONE Telegram message at every step (page_builder/progress.py). A brief from
// the client form has no chat, so these lines are left out.
const chat = String(row.telegram_chat_id || '').trim();
const PROG = 'python -m page_builder.progress page ';
const PSTATE = ' --state ' + C + '/progress.json';
const prog = (what) => chat ? ['   Progress bar (Telegram; run it from services/store-builder; it never stops the work): ' + PROG + what + PSTATE] : [];

const lines = [
  'DTJ STORE FACTORY - design the WHOLE product page for this brief and write it into the DRAFT theme.',
  'You are the AI step: a Claude Code session on Harsh\'s PC. Nobody has briefed you; everything you need is below and in the repo.',
  '',
  'BRIEF',
  '- Brief row: id ' + row.id + ' in the n8n data table dtj_client_intake',
  '- Brand: ' + (row.brand_name || brand.brand_name || '(not given: take it from the product and the brand site)'),
  '- Store: ' + store + ' (the ORIGINAL .myshopify.com address) | Draft theme: ' + theme,
  '- Product: ' + (row.product_url || ('https://' + store + '/products/' + handle)) + ' (handle ' + handle + ')',
  '- Page file: templates/product.' + suffix + '.json (a NEW template for this product; the theme\'s product.json is never touched)',
  '- Brand\'s own site: ' + (row.brand_website || '(not given: search for it; only the brand\'s own pages count as sources)'),
  '- Look references: ' + (row.reference_brands || '(none)'),
  '- App copies on this store: ' + (registry ? 'services/store-builder/' + registry : '(not given: find it in services/store-builder/page_builder/clients/)'),
  '- Asked by: ' + (row.requested_by || 'Harsh') + ' | Notes: ' + (row.notes || '(none)'),
  '- Brand data first (brand_intake): ' + (row.brand_intake || 'not answered yet when this request was written: read it in step 2'),
  '- Upload the brand\'s pictures (upload_assets): ' + (row.upload_assets ? row.upload_assets + (row.upload_assets_by ? ', by ' + row.upload_assets_by : '') : 'not answered yet: read it in step 2'),
  (Object.keys(brand).length || Object.keys(facts).length)
    ? '- This brief came from the client form: request.brand and request.facts hold the client\'s answers. Start from them and keep their sources.'
    : '- This brief was started by hand: there are no client answers; the facts come from the store, the brand\'s site and the pictures.',
  '',
  'DO THIS, IN ORDER',
  '1. Work in the repo D:\\CODE CONTAINERR\\WEB DEV\\dtj-agency-automation. Read CLAUDE.md. Load the skill dtj-pdp-factory (the runbook, phases P0-P9) and follow it; dtj-pdp-design-review is its review gate. Stay on the current git branch; do not commit or push unless Harsh asks.',
  ...prog('start --chat ' + chat + ' --title "Page design: ' + handle + '"'),
  '2. Brand data first? Read the brief\'s brand_intake NOW (n8n tool get_data_table_rows, table dtj_client_intake, row id ' + row.id + '): '
    + 'the requester answers in Telegram after this request was written.',
  ...prog('step --stage brief'),
  '   Read its brand_website too: after a Yes the requester sends the brand\'s OWN website (the shop is not always the brand\'s site). '
    + 'When it is set and differs from ' + site + ', collect from it instead, into ../../.work/clients/intake-<its host>.',
  '   - "yes": collect it before anything else (public pages only, a few minutes):',
  ...prog('step --stage intake'),
  '     cd services/store-builder',
  '     python -m page_builder.brand_intake ' + site + ' --client ' + INTAKE + ' --product "<the product\'s name as its pack says it>"  (add --drive "DTJ Clients" when this laptop has the DTJ_GDRIVE_* keys, so the team gets a copy; --product finds its pictures on any site, also a non-Shopify one)',
  '   - "no": do not collect it again; use an earlier intake in ' + INTAKE + '/intake if there is one.',
  '   - empty: ask the person at this laptop "Collect the brand\'s data first?" and do what they say.',
  '   Then read upload_assets and upload_assets_by (the third Telegram answer, after the website):',
  '   - "yes": put the intake\'s product pictures into the store\'s Files; that tap is the person\'s approval for this one upload:',
  '     python -m page_builder.store_files --store ' + store + ' --folder <the intake folder>/intake/images/products --approved-by "<upload_assets_by> (Telegram, brief ' + row.id + ')"',
  '     (the intake ran on GitHub, so its folder is only in Drive? first: python -m page_builder.drive_upload --download "DTJ Clients/<brand>/Brand intake <date>" <the intake folder>/intake)',
  '     Then use the names in its store-files.json as facts.media[].file (roles such as lifestyle, pack, serve), point story, story_2, final_push and ugc image_role at them, and keep a picture of another pack version out of the buy box.',
  '   - "no" or empty: upload nothing; the store already has its pictures.',
  // the same follow-ups as a whole store (Harsh, 23 Oct 2026: "here it should also show ChatGPT generates and that competitor flow
  // message follow ups")
  ...(chat ? [
    '2b. The page\'s own questions in Telegram: ChatGPT pictures, a competitor study and what it should focus on (from the repo root):',
    '   python n8n/store-factory/page_questions.py --brief ' + row.id + ' --chat ' + chat,
    '   Exit 3 = waiting for the person: run it again (it never asks twice). It prints {"pictures", "pictures_by", "competitors": {"how", "links", "focus", "note"}}.',
    '   - competitors.how is not "no": the study, before step 4 (skill dtj-new-store, step 1a): the person\'s links, or 5 D2C brands of this niche that grow on Meta ads (never the giants); from services/store-builder: python -m provision.niche_assets <links> --out ' + C + '/niche --niche "<one line>"; read their home and product pages too. Progress bar before you start it: ' + (chat ? PROG + 'step --stage study' + PSTATE : '(none)') + '. Write ' + C + '/study.md: one "#" heading per focus (Pictures, Copywriting, Colour palette and fonts, Layout and sections, Offers and pricing, Trust) and "# Your request" when there is a note. Then from the repo root: python n8n/store-factory/page_questions.py --brief ' + row.id + ' --study ' + '.work/clients/' + folder + '/study.md (it sends the short form to Telegram). Use the study in steps 4-6; never copy their text, claims, offers or pictures.',
    // the gallery method (Harsh, 23-24 Oct 2026: square product pictures that explain the product like a pro D2C brand; the busy
    // first set was "AI SLOP"), made WHILE the facts and the copy are written ("i want such tasks to go parallely")
    '   - pictures is "make": follow references/product-gallery.md in the skill dtj-pdp-factory (6 square gallery pictures: what it is, why this one, the numbers, what\'s inside, how to use, lifestyle; one photo per picture section; ONE subject per photo on a flat brand-colour backdrop, nothing floating, the empty space named; the words are set later by code).',
    '     WORK IN PARALLEL: right after step 3, write ' + C + '/gallery/plan.json (refs: step 3\'s pack photo in media/; "ref": true when our product is in the photo; "transparent": true for a cut-out on a see-through background) and start every photo in the background, from services/store-builder:',
    '     python -m provision.gallery_photos --plan ' + C + '/gallery/plan.json --out ' + C + '/gallery/photos --detach' + (chat ? ' --progress ' + C + '/progress.json' : ''),
    '     It returns at once (Codex on the VPS, 3 at a time, about 2 minutes each)' + (chat ? ' and moves the Telegram bar itself' : '') + '. Do steps 4 and 5 (facts, brand, copy) meanwhile; do not wait for the photos.',
    '     Before step 6: python -m provision.gallery_photos --plan ' + C + '/gallery/plan.json --out ' + C + '/gallery/photos --wait. Look at every photo against the quality gate in product-gallery.md (one subject, no clutter, the product exactly as the pack, appetising, no words); remake the ones that fail with --only <names> --detach, then --wait again (at most 3 tries each).',
    '     Then the words: write ' + C + '/gallery/compose.json (layouts pack, top, numbers, tiles, stack, bottom; every line from facts.json) and run python -m provision.gallery_compose --spec ' + C + '/gallery/compose.json --facts ' + C + '/facts.json --out ' + C + '/gallery/final. Look at the 6 finished pictures next to the study\'s reference brand: busier or cheaper looking = redo it.',
    '     Upload the finished gallery and the section photos: python -m page_builder.store_files --store ' + store + ' --folder <the folder> --approved-by "<pictures_by> (Telegram, brief ' + row.id + ' pictures)". Put the section photos in facts.media (roles lifestyle, story_2, final_push; keys role, file and alt only). Putting the 6 first in the product\'s own gallery changes the product: say in the reply that they are in the store\'s Files, ready for a person\'s yes.',
  ] : []),
  '3. Read the product as the store shows it and fetch its pictures (read-only):',
  ...prog('step --stage product'),
  '   cd services/store-builder',
  '   python -m page_builder.fetch_product --store ' + store + ' --handle ' + handle + ' --client ' + C,
  '   It writes store-product.json and saves every picture in media/ under its STORE file name. Use exactly those names in facts.media[].file.',
  '4. Facts and brand (P2): from store-product.json, the brand intake when there is one (' + INTAKE + '/intake: start from BRAND.md, brand.json and brand-intake.json, every fact with its source; its colours, category and price tier are guesses to confirm against the pack and the brand site), the brand\'s own site and what the pictures print, write in ' + C + ': brand.json (with a vibe), facts.json (every fact with a source; fill every gap with modest SAMPLE content whose source starts with "SAMPLE"; never sample medical claims, "clinically proven", competitor names, licences or certifications, prices, discounts or offers), SOURCES.md, content-needed.md. Voice lines per the skill\'s copywriting.md, each marked "DTJ COPY (basis: ...)". If a look reference is named, open its site and measure its colours before choosing yours (design-principles.md 13).',
  ...prog('step --stage facts'),
  '5. Design-only run (writes run/copy-request.json; touches no store):',
  '   python -m page_builder.ship_draft --client ' + C + ' --design-only --template-suffix ' + suffix + regArg,
  '   Then answer run/copy-request.json into ' + C + '/copy-answer.json (its rules are inside the request).',
  '6. Build, check and write the DRAFT in one command:',
  ...prog('step --stage build --done <this round: 1, 2 or 3> --total 3'),
  '   python -m page_builder.ship_draft --client ' + C + ' --store ' + store + ' --theme ' + theme + ' --template-suffix ' + suffix + regArg,
  '   Exit 0 = written to the draft. Exit 2 = a gate failed: read "note" in run/ship-result.json, fix brand.json / facts.json (never hand-edit template.json) and run again, at most 3 rounds. Exit 1 = could not build: read run/ship-build-*.log.',
  '7. Check the real page (P9): open preview_url from run/ship-result.json in the browser at 390 px and 1280 px. Every DTJ section shows, pictures load, no sideways scroll. If not, fix and repeat step 6.',
  ...prog('step --stage check'),
  '8. Answer this n8n run, also when the page could not be written (the brief row then records why):',
  ...(chat ? ['   Progress bar, FIRST, from services/store-builder (the result message follows it): ' + PROG + 'done' + PSTATE + '   (page not written: ' + PROG
    + 'stopped --note "<why, in plain words>"' + PSTATE + ')'] : []),
  '   python n8n/store-factory/reply.py --resume-url "' + resumeUrl + '" --body ' + '.work/clients/' + folder + '/run/ship-result.json',
  '   (run it from the repo root; if you stopped before step 6, send a small JSON file instead: {"page_status": "could not build", "note": "<why>"})',
  '9. Add a dated entry to docs/HANDOFF.md (what was built, the preview link, the samples to replace, anything open). Tell Harsh in plain words: the preview link, the SAMPLE list, what needs his action.',
  '',
  'RULES',
  '- Draft theme only: never the live theme, never --allow-live, never publish a theme. ship_draft writes the draft under Harsh\'s standing rule (no approval code for drafts).',
  '- Never put a password, token or key in a file or in chat; the tools read the Theme Access password from a Windows user variable.',
  '- Do not invent prices, offers, claims, reviews or policies. Mark unknowns.',
  '- If something blocks you (no Theme Access password, the theme is live, the product does not exist, the store is password-protected): stop, answer n8n with "could not build" and the reason (step 8), and tell Harsh exactly what he must do.',
];

return [{ json: {
  claude_code_stage: 'page_design',
  resume_url: resumeUrl,
  instructions: lines.join('\n'),
  request: {
    row_id: row.id, brand_name: row.brand_name || brand.brand_name || '', store_domain: store, theme_id: theme, handle,
    product_url: row.product_url || '', template_suffix: suffix, client_registry: registry, client_folder: '.work/clients/' + folder,
    brand_website: row.brand_website || '', reference_brands: row.reference_brands || '', notes: row.notes || '',
    brand_intake: row.brand_intake || '', intake_folder: INTAKE.replace('../../', ''),
    upload_assets: row.upload_assets || '', upload_assets_by: row.upload_assets_by || '',
    status: row.status, problems: row.problems || '', brand, facts,
    telegram_chat_id: chat,
    picture_links: parse(row.picture_links_json, []), logo_link: row.logo_link || '',
  },
} }];
