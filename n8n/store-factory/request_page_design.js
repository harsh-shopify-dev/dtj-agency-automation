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
  (Object.keys(brand).length || Object.keys(facts).length)
    ? '- This brief came from the client form: request.brand and request.facts hold the client\'s answers. Start from them and keep their sources.'
    : '- This brief was started by hand: there are no client answers; the facts come from the store, the brand\'s site and the pictures.',
  '',
  'DO THIS, IN ORDER',
  '1. Work in the repo D:\\CODE CONTAINERR\\WEB DEV\\dtj-agency-automation. Read CLAUDE.md. Load the skill dtj-pdp-factory (the runbook, phases P0-P9) and follow it; dtj-pdp-design-review is its review gate. Stay on the current git branch; do not commit or push unless Harsh asks.',
  '2. Brand data first? Read the brief\'s brand_intake NOW (n8n tool get_data_table_rows, table dtj_client_intake, row id ' + row.id + '): '
    + 'the requester answers in Telegram after this request was written.',
  '   Read its brand_website too: after a Yes the requester sends the brand\'s OWN website (the shop is not always the brand\'s site). '
    + 'When it is set and differs from ' + site + ', collect from it instead, into ../../.work/clients/intake-<its host>.',
  '   - "yes": collect it before anything else (public pages only, a few minutes):',
  '     cd services/store-builder',
  '     python -m page_builder.brand_intake ' + site + ' --client ' + INTAKE + '  (add --drive "DTJ Clients" when this laptop has the DTJ_GDRIVE_* keys, so the team gets a copy)',
  '   - "no": do not collect it again; use an earlier intake in ' + INTAKE + '/intake if there is one.',
  '   - empty: ask the person at this laptop "Collect the brand\'s data first?" and do what they say.',
  '3. Read the product as the store shows it and fetch its pictures (read-only):',
  '   cd services/store-builder',
  '   python -m page_builder.fetch_product --store ' + store + ' --handle ' + handle + ' --client ' + C,
  '   It writes store-product.json and saves every picture in media/ under its STORE file name. Use exactly those names in facts.media[].file.',
  '4. Facts and brand (P2): from store-product.json, the brand intake when there is one (' + INTAKE + '/intake: start from BRAND.md, brand.json and brand-intake.json, every fact with its source; its colours, category and price tier are guesses to confirm against the pack and the brand site), the brand\'s own site and what the pictures print, write in ' + C + ': brand.json (with a vibe), facts.json (every fact with a source; fill every gap with modest SAMPLE content whose source starts with "SAMPLE"; never sample medical claims, "clinically proven", competitor names, licences or certifications, prices, discounts or offers), SOURCES.md, content-needed.md. Voice lines per the skill\'s copywriting.md, each marked "DTJ COPY (basis: ...)". If a look reference is named, open its site and measure its colours before choosing yours (design-principles.md 13).',
  '5. Design-only run (writes run/copy-request.json; touches no store):',
  '   python -m page_builder.ship_draft --client ' + C + ' --design-only --template-suffix ' + suffix + regArg,
  '   Then answer run/copy-request.json into ' + C + '/copy-answer.json (its rules are inside the request).',
  '6. Build, check and write the DRAFT in one command:',
  '   python -m page_builder.ship_draft --client ' + C + ' --store ' + store + ' --theme ' + theme + ' --template-suffix ' + suffix + regArg,
  '   Exit 0 = written to the draft. Exit 2 = a gate failed: read "note" in run/ship-result.json, fix brand.json / facts.json (never hand-edit template.json) and run again, at most 3 rounds. Exit 1 = could not build: read run/ship-build-*.log.',
  '7. Check the real page (P9): open preview_url from run/ship-result.json in the browser at 390 px and 1280 px. Every DTJ section shows, pictures load, no sideways scroll. If not, fix and repeat step 6.',
  '8. Answer this n8n run, also when the page could not be written (the brief row then records why):',
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
    status: row.status, problems: row.problems || '', brand, facts,
    picture_links: parse(row.picture_links_json, []), logo_link: row.logo_link || '',
  },
} }];
