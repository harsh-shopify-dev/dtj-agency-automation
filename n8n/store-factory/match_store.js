// n8n Code node "Match the Store" in "Store Factory: New Page" (mode: Run Once for All Items).
// Finds the shop a product link belongs to in the stores table (dtj_stores: one row per shop, set up once by Harsh) and builds the
// brief row for dtj_client_intake. Every refusal is a plain sentence the person (or the Telegram bot) can show as it is.
const req = $('Take the Request').first().json;
const stores = $input.all().map((i) => i.json).filter((s) => s && s.myshopify_domain);
const fail = (message) => [{ json: { ok: false, message } }];
const link = String(req.product_link || '').trim();
if (!link) return fail('Please send the product link: open the product on the shop\'s website and copy the address from the top of the browser.');

// read the link with plain text matching: n8n's Code sandbox has no URL() (seen in test execution 330, 12 Oct 2026)
const parts = /\s/.test(link) ? null : link.match(/^(?:https?:\/\/)?([^/?#]+)([^?#]*)/i);
const host = parts ? parts[1].toLowerCase().replace(/:\d+$/, '').replace(/^www\./, '') : '';
if (!/^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(host)) {
  return fail('That does not look like a link. Open the product on the shop\'s website and copy the address from the top of the browser.');
}
if (host === 'admin.shopify.com' || host.endsWith('.admin.shopify.com')) {
  return fail('That is a Shopify admin link. In the product page of the admin, click "View" (or open the shop) and send the link of the product on the shop\'s own website.');
}
const m = parts[2].match(/\/products\/([a-z0-9][a-z0-9-]*)/i);
if (!m) return fail('That link is not a product page. A product link has /products/ in it, like https://myshop.com/products/my-product');
const handle = m[1].toLowerCase();

const norm = (d) => String(d || '').trim().toLowerCase().replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/.*$/, '');
const store = stores.find((s) => [s.myshopify_domain, ...String(s.other_domains || '').split(',')].map(norm).filter(Boolean).includes(host));
// a shop that is not connected (or only half) gets the steps to connect it, not "ask Harsh" (Harsh, 23 Oct 2026: "if i provide a
// new store link which isnt connected a step by step follow up shows up on how to set up"); the bot sends these as HTML
const shopLink = host.endsWith('.myshopify.com') ? 'https://' + host : 'the store\'s Shopify address (in its admin the link reads admin.shopify.com/store/&lt;name&gt;: send https://&lt;name&gt;.myshopify.com)';
const steps = (what) => what + '\n\n<b>To connect it, step by step:</b>\n'
  + '1. Send me ' + shopLink + ' (the store, not a product). I ask a few questions here: tap <b>Redesign an existing brand</b> > '
  + '<b>Already in this store</b>, then <b>Only product pages</b>.\n'
  + '2. I make the draft copy of its theme after your <b>Approve</b> tap (the live store does not change).\n'
  + '3. I send <b>7 Install buttons</b> for DTJ\'s apps: the store owner (or you, logged in to its admin) taps each one and presses Install.\n'
  + '4. I design the product pages you pick into the draft and send the preview links. After that, product links of this shop work here too.\n'
  + 'Only adding the shop, no design yet? An admin sends: <code>/addshop ' + (host.endsWith('.myshopify.com') ? host : '&lt;name&gt;.myshopify.com')
  + ' Client Name</code>';
if (!store) return fail(steps('The shop ' + host + ' is not set up for page design yet.'));
if (!/^page_builder\/clients\/[a-z0-9-]+\.json$/.test(String(store.client_registry || ''))) return fail(steps((store.store_name || host) + ' has no app copies saved yet.'));
if (!/^[0-9]{6,20}$/.test(String(store.draft_theme_id || ''))) return fail(steps((store.store_name || host) + ' has no draft theme saved yet.'));
if (store.active === false) return fail('Page design is paused for ' + (store.store_name || host) + '. Ask Harsh.');

const note = String(req.note || '').trim();
return [{ json: {
  ok: true,
  store_name: store.store_name || norm(store.myshopify_domain),
  handle,
  row: {
    submitted_at: new Date().toISOString(),
    status: 'new',
    store_domain: norm(store.myshopify_domain),
    theme_id: String(store.draft_theme_id),
    brand_name: String(store.brand_name || ''),
    product_title: '',
    product_url: 'https://' + host + '/products/' + handle,
    brand_website: String(store.brand_website || ''),
    reference_brands: String(store.reference_brands || ''),
    client_registry: String(store.client_registry),
    template_suffix: ('dtj-' + handle).slice(0, 48).replace(/-+$/, ''),
    notes: [note, store.store_notes ? 'About this shop: ' + store.store_notes : ''].filter(Boolean).join(' | '),
    problems: '',
    problem_count: 0,
    brand_json: '{}',
    facts_json: '{}',
    picture_links_json: '[]',
    raw_json: JSON.stringify({ source: 'Store Factory: New Page', product_link: link, note, requested_by: req.requested_by }),
    requested_by: String(req.requested_by || ''),
    telegram_chat_id: String(req.chat_id || ''),
  },
} }];
