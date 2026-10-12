// n8n Code node "Page Brief (edit for each run)" in "Store Factory: Page Design" (mode: Run Once for All Items).
// Harsh edits ONLY the object below, then presses "Execute workflow". No passwords, tokens or keys belong here.
const brief = {
  store_domain: 'qaxv3r-8g.myshopify.com',          // the store's ORIGINAL .myshopify.com address (the Test Store keeps qaxv3r-8g)
  theme_id: '167627423941',                          // a DRAFT (unpublished) theme's id, never the live theme
  product_url: 'https://test-store-harsh-dtj.myshopify.com/products/PUT-THE-HANDLE-HERE', // the product, already created on the store
  brand_name: '',                                    // as the brand writes it
  brand_website: '',                                 // the brand's own site or product page (facts, voice, pictures)
  reference_brands: '',                              // brands whose LOOK you like, e.g. 'Minimalist' (their site is measured first)
  client_registry: 'page_builder/clients/test-store-harsh-dtj.json', // the store's DTJ app copies (one file per store)
  notes: '',                                         // anything else: what is confirmed, what to avoid, real offers or rating source
};

// ---- checks (a bad brief stops here, before anything is saved)
const problems = [];
const store = String(brief.store_domain || '').trim().toLowerCase();
if (!/^[a-z0-9][a-z0-9-]*\.myshopify\.com$/.test(store)) problems.push('store_domain must be the original <name>.myshopify.com address');
const theme = String(brief.theme_id || '').trim();
if (!/^[0-9]{6,20}$/.test(theme)) problems.push('theme_id must be the draft theme number');
const m = String(brief.product_url || '').match(/\/products\/([a-z0-9][a-z0-9-]*)/i);
const handle = m ? m[1].toLowerCase() : '';
if (!handle || handle === 'put-the-handle-here') problems.push('product_url must be the product link (…/products/<handle>)');
const registry = String(brief.client_registry || '').trim();
if (!/^page_builder\/clients\/[a-z0-9-]+\.json$/.test(registry)) problems.push('client_registry must look like page_builder/clients/<store>.json');
for (const key of ['brand_website']) {
  const v = String(brief[key] || '').trim();
  if (v && !/^https:\/\//.test(v)) problems.push(key + ' must start with https://');
}
if (problems.length) throw new Error('Page brief not ready: ' + problems.join('; '));

// one template file per product: templates/product.dtj-<handle>.json (letters, digits and hyphens only)
const template_suffix = ('dtj-' + handle).slice(0, 48).replace(/-+$/, '');
return [{ json: {
  submitted_at: new Date().toISOString(),
  status: 'new',
  store_domain: store,
  theme_id: theme,
  brand_name: String(brief.brand_name || '').trim(),
  product_title: '',
  product_url: String(brief.product_url).trim(),
  brand_website: String(brief.brand_website || '').trim(),
  reference_brands: String(brief.reference_brands || '').trim(),
  client_registry: registry,
  template_suffix,
  notes: String(brief.notes || '').trim(),
  problems: '',
  problem_count: 0,
  brand_json: '{}',
  facts_json: '{}',
  picture_links_json: '[]',
  raw_json: JSON.stringify({ source: 'Page Brief (run by hand)', brief }),
} }];
