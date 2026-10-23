// The brand copy (Harsh, 21 Oct 2026: "all this steps must be done in the telegram bot"; he chose "A new DTJ Store Builder app").
//
// A brand's public products, collections and policy pages go into a store through DTJ Store Builder, a separate DTJ app with only
// the permissions this needs (read/write products, publications, legal policies); the seven block apps keep none. Like DTJ's
// original apps it lives in DTJ's organization, so a store of that organization (a dev store) gets a fresh key from the client
// credentials grant on every call and nothing is stored; Shopify itself refuses a store outside the organization, or one where the
// app is not installed.
//
// POST /copy, signed like /licence (the laptop's CONTROL_KEY, or the Telegram bot's BOT_KEY from n8n), JSON with ts and op:
//   target  {shop}                 read only: name, currency, password page, Online Store channel, empty policies, every handle
//   plan    {job, shop, plan}      keep the laptop's plan (provision/brand_copy.py make_plan) for this job; nothing reaches the store
//   step    {job, approved_by}     copy the next few items (n8n calls it again until "finished"); the Approve tap's name goes in
//   status  {job}                  how far it is, no Shopify call
//   uploads {shop, files}          Shopify's one-time upload addresses for up to 50 pictures (stagedUploadsCreate): the laptop sends
//                                  the bytes of a client's Drive picture or a ChatGPT picture there, and a plan names its resourceUrl;
//                                  nothing in the store changes (22 Oct 2026, the new-store branch)
//   activate {shop, handles, approved_by}  a DRAFT product goes ACTIVE and onto the Online Store, nothing else about it changes
//                                  (Harsh, 22 Oct 2026: "all the products will stay active none of them will be kept as draft");
//                                  at most 12 a call, the rest come back in "left"
//   product {shop, handle}         read only: one product's text, prices, variants and media, for the page builder when the store's
//                                  pages are behind its password (23 Oct 2026: the first VPS page run could not read a dev store)
//   pages {shop, pages, approved_by} new pages only (About, Contact, FAQ: a store handed over ready to sell, Harsh 22 Oct 2026); a
//                                  handle the store has is left as it is; body HTML without scripts, frames or event handlers
//   menu  {shop, handle, items, approved_by}  the store's "main-menu" or "footer" set to these links (home, all products, a
//                                  collection, a page, a policy, search); the menu's old links are kept in the audit row
// Pages and menus need the app's online_store_pages / online_store_navigation scopes (a new Store Builder version: Harsh's yes).
// Only the mutations below can be sent, with inputs rebuilt from a list of allowed fields. It never deletes: a handle the store has
// is skipped, a policy is written only where the store's own is empty, activate changes the status only. Every call that writes is
// one audit row.
import { Refuse, audit, call, orgAccess } from "./worker.js";

export const COPY_API = "2026-10";  // the fields below were read from this version's schema (21 Oct 2026)
const SHOP_RE = /^[a-z0-9][a-z0-9-]*\.myshopify\.com$/;
const JOB_RE = /^[a-z0-9][a-z0-9-]{1,40}$/;
const HANDLE_RE = /^[a-z0-9À-￿][a-z0-9À-￿_-]{0,254}$/i;
const FRESH_SECONDS = 300;
const UNITS_PER_STEP = 8;  // one call stays far below a Worker's 50 outside calls: a product is 3 (exists?, create, publish)
const POLICY_TYPES = new Set(["REFUND_POLICY", "SHIPPING_POLICY", "PRIVACY_POLICY", "TERMS_OF_SERVICE"]);
const LIMITS = { products: 2500, collections: 40, variants: 2048, files: 250 };
const UPLOADS_PER_CALL = 50;
const UPLOAD_MAX_BYTES = 20 * 1024 * 1024;
const UPLOAD_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
const ACTIVATE_MAX = 250;
const ACTIVATE_PER_CALL = 12;  // 3 outside calls a product (find, status, publish) + the key and the channel: far below 50

const Q = {
  target: "query Target { shop { name currencyCode myshopifyDomain shopPolicies { type body } } publications(first: 20) { nodes { id name } } }",
  products: "query ProductHandles($after: String) { products(first: 250, after: $after) { nodes { handle } pageInfo { hasNextPage endCursor } } }",
  collections: "query CollectionHandles($after: String) { collections(first: 250, after: $after) { nodes { handle } pageInfo { hasNextPage endCursor } } }",
  exists: "query Exists($handle: String!) { productByIdentifier(identifier: { handle: $handle }) { id } }",
  collectionExists: "query CollectionExists($handle: String!) { collectionByIdentifier(identifier: { handle: $handle }) { id } }",
  policies: "query Policies { shop { shopPolicies { type body } } }",
  password: "query Password { onlineStore { passwordProtection { enabled } } }",
  productStatus: "query ProductStatus($handle: String!) { productByIdentifier(identifier: { handle: $handle }) { id status } }",
  oneProduct: "query OneProduct($handle: String!) { productByIdentifier(identifier: { handle: $handle }) { handle title descriptionHtml vendor productType tags status options { name } variants(first: 100) { nodes { title price compareAtPrice availableForSale } } media(first: 50) { nodes { mediaContentType alt preview { image { url width height } } ... on MediaImage { image { url width height } } ... on Video { sources { url } } } } } }",
  publications: "query Publications { publications(first: 20) { nodes { id name } } }",
  pageHandles: "query PageHandles { pages(first: 250) { nodes { id handle } } }",
  menus: "query Menus { menus(first: 50) { nodes { id handle title isDefault items { title type url items { title } } } } }",
  policyIds: "query PolicyIds { shop { shopPolicies { id type url } } }",
};
const M = {
  product: "mutation CopyProduct($input: ProductSetInput!) { productSet(input: $input, synchronous: true) { product { id handle } userErrors { field message code } } }",
  collection: "mutation CopyCollection($collection: CollectionCreateInput!) { collectionCreate(collection: $collection) { collection { id handle } userErrors { field message } } }",
  publish: "mutation Publish($id: ID!, $input: [PublicationInput!]!) { publishablePublish(id: $id, input: $input) { userErrors { field message } } }",
  policy: "mutation SetPolicy($shopPolicy: ShopPolicyInput!) { shopPolicyUpdate(shopPolicy: $shopPolicy) { shopPolicy { type } userErrors { field message } } }",
  stage: "mutation Stage($input: [StagedUploadInput!]!) { stagedUploadsCreate(input: $input) { stagedTargets { url resourceUrl parameters { name value } } userErrors { field message } } }",
  activate: "mutation Activate($product: ProductUpdateInput!) { productUpdate(product: $product) { product { id status } userErrors { field message } } }",
  page: "mutation AddPage($page: PageCreateInput!) { pageCreate(page: $page) { page { id handle } userErrors { field message } } }",
  menu: "mutation SetMenu($id: ID!, $title: String!, $items: [MenuItemUpdateInput!]!) { menuUpdate(id: $id, title: $title, items: $items) { menu { id handle } userErrors { field message } } }",
};
const PAGES_MAX = 6;
const MENU_HANDLES = new Set(["main-menu", "footer"]);
const MENU_MAX = 12;
const POLICY_HANDLES = { "refund-policy": "REFUND_POLICY", "shipping-policy": "SHIPPING_POLICY", "privacy-policy": "PRIVACY_POLICY",
  "terms-of-service": "TERMS_OF_SERVICE" };
const UNSAFE_HTML = /<\s*(script|iframe|object|embed|form|style)\b|\bon[a-z]+\s*=|javascript:/i;
const SENDABLE = new Set([...Object.values(Q), ...Object.values(M)]);

export function builder(env, shop) {
  if (!SHOP_RE.test(shop || "")) throw new Refuse(400, "shop must be <name>.myshopify.com");
  if (!env.BUILDER_CLIENT_ID || !env.ORG_SECRET_DTJ_STORE_BUILDER) throw new Refuse(503, "DTJ Store Builder is not set up on the install service yet");
  return { shop, client_id: env.BUILDER_CLIENT_ID, secret: env.ORG_SECRET_DTJ_STORE_BUILDER, grant: "org" };
}

async function gql(shop, token, query, variables) {
  if (!SENDABLE.has(query)) throw new Refuse(500, "only the brand copy's own queries may be sent");
  const res = await call(`https://${shop}/admin/api/${COPY_API}/graphql.json`, {
    method: "POST", headers: { "Content-Type": "application/json", "X-Shopify-Access-Token": token },
    body: JSON.stringify({ query, variables: variables || {} }),
  });
  const body = await res.json().catch(() => ({}));
  if (res.status !== 200 || body.errors) {
    const why = (body.errors || []).map((e) => e.message).join("; ").slice(0, 200) || `HTTP ${res.status}`;
    throw new Refuse(502, `Shopify refused it: ${why}`);
  }
  return body.data;
}

const userErrors = (payload) => (payload?.userErrors || []).map((e) => `${(e.field || []).join(".")}: ${e.message}`).join("; ");

// ------------------------------------------------------------------------------------------------ the plan, rebuilt field by field
const str = (v, max) => (v == null ? undefined : String(v).slice(0, max));
const money = (v) => (/^\d{1,9}(\.\d{1,4})?$/.test(String(v ?? "")) ? String(v) : null);

export function cleanProduct(p, status) {
  if (!p || !HANDLE_RE.test(p.handle || "") || !String(p.title || "").trim() || "id" in p) return null;
  const options = (p.productOptions || []).slice(0, 3).map((o, i) => ({
    name: str(o.name, 255), position: i + 1, values: (o.values || []).slice(0, 255).map((v) => ({ name: str(v.name, 255) })) }));
  const variants = [];
  for (const v of (p.variants || []).slice(0, LIMITS.variants)) {
    const price = money(v.price);
    if (price === null) return null;  // no price, no product: never a guessed one
    const one = { optionValues: (v.optionValues || []).slice(0, 3).map((o) => ({ optionName: str(o.optionName, 255), name: str(o.name, 255) })),
      price, inventoryItem: { tracked: false } };
    if (money(v.compareAtPrice) !== null && Number(v.compareAtPrice) > Number(price)) one.compareAtPrice = money(v.compareAtPrice);
    if (v.sku) one.sku = str(v.sku, 255);
    variants.push(one);
  }
  if (!variants.length || !options.length) return null;
  const files = (p.files || []).slice(0, LIMITS.files).filter((f) => /^https:\/\//.test(String(f.originalSource || "")))
    .map((f) => ({ originalSource: str(f.originalSource, 2000), contentType: "IMAGE", alt: str(f.alt || "", 512), filename: str(f.filename || "", 255) || undefined }));
  const out = { title: str(p.title, 255), handle: p.handle, status, descriptionHtml: str(p.descriptionHtml || "", 65000),
    productOptions: options, variants, files };
  if (p.vendor) out.vendor = str(p.vendor, 255);
  if (p.productType) out.productType = str(p.productType, 255);
  if (Array.isArray(p.tags) && p.tags.length) out.tags = p.tags.slice(0, 250).map((t) => str(t, 255));
  return out;
}

export function cleanPlan(plan, shop) {
  if (!plan || typeof plan !== "object") throw new Refuse(400, "plan must be an object");
  if (plan.target?.store !== shop) throw new Refuse(400, "the plan was made for another store");
  const status = plan.status === "ACTIVE" ? "ACTIVE" : "DRAFT";
  const products = [], refused = [];
  for (const p of (plan.products || []).slice(0, LIMITS.products)) {
    const c = cleanProduct(p, status);
    if (c) products.push(c); else refused.push(String(p?.handle || "?").slice(0, 80));
  }
  const handles = new Set(products.map((p) => p.handle));
  const collections = (plan.collections || []).slice(0, LIMITS.collections).filter((c) => HANDLE_RE.test(c?.handle || "") && String(c.title || "").trim())
    .map((c) => ({ handle: c.handle, title: str(c.title, 255), descriptionHtml: str(c.description_html || "", 65000),
      products: (c.products || []).filter((h) => handles.has(h)) }));
  const policies = (plan.policies || []).filter((p) => POLICY_TYPES.has(p?.type) && String(p.body || "").trim())
    .map((p) => ({ type: p.type, body: str(p.body, 200000), source: str(p.source || "", 300) }));
  const online = /^gid:\/\/shopify\/Publication\/\d+$/.test(plan.target?.online_store || "") ? plan.target.online_store : null;
  return { status, online_store: online, brand: str(plan.brand || "", 300), products, collections, policies, refused };
}

// ------------------------------------------------------------------------------------------------ the operations
async function target(env, body) {
  const cfg = builder(env, body.shop);
  const token = await orgAccess(cfg);
  const data = await gql(cfg.shop, token, Q.target);
  const handles = async (query, field) => {
    const found = [];
    let after = null;
    for (let i = 0; i < 20; i++) {
      const page = (await gql(cfg.shop, token, query, { after }))[field];
      found.push(...page.nodes.map((n) => n.handle));
      if (!page.pageInfo.hasNextPage) break;
      after = page.pageInfo.endCursor;
    }
    return found.sort();
  };
  // the password page: Shopify's own setting first; the storefront only when the app may not read it (22 Oct 2026: the storefront
  // check called dtj-testing "open to the public" although it shows its password page)
  let password;
  try {
    password = Boolean((await gql(cfg.shop, token, Q.password)).onlineStore?.passwordProtection?.enabled);
  } catch {
    const front = await call(`https://${cfg.shop}/`, { redirect: "follow" }).catch(() => null);
    const page = front ? await front.text().catch(() => "") : "";
    password = Boolean(front && ((front.url || "").includes("/password") || /action="\/password"/.test(page)));
  }
  // a policy the store has never set is not in shopPolicies at all: it is as empty as a blank one (22 Oct 2026, dtj-testing)
  const filled = new Set(data.shop.shopPolicies.filter((p) => String(p.body || "").trim()).map((p) => p.type));
  return {
    store: data.shop.myshopifyDomain, name: data.shop.name, currency: data.shop.currencyCode, password,
    online_store: (data.publications.nodes.find((p) => p.name === "Online Store") || {}).id || null,
    empty_policies: [...POLICY_TYPES].filter((t) => !filled.has(t)).sort(),
    products: await handles(Q.products, "products"), collections: await handles(Q.collections, "collections"),
  };
}

async function keepPlan(env, body) {
  if (!JOB_RE.test(body.job || "")) throw new Refuse(400, "job must be lowercase letters, digits and dashes");
  builder(env, body.shop);
  const old = JSON.parse((await env.VAULT.get(`copy:${body.job}`)) || "null");
  if (old && old.approved_by && !old.finished) throw new Refuse(409, "this copy has started already: its plan cannot change");
  const clean = cleanPlan(body.plan, body.shop);
  const state = { job: body.job, shop: body.shop, ...clean, done: { collections: {}, products: {}, policies: [] }, skipped: [],
    failed: {}, approved_by: null, finished: false, stopped: null, streak: { kind: "", n: 0 }, planned_at: new Date().toISOString() };
  await env.VAULT.put(`copy:${body.job}`, JSON.stringify(state));
  return { job: body.job, products: clean.products.length, collections: clean.collections.length, policies: clean.policies.length,
    refused: clean.refused, status: clean.status };
}

const counts = (s) => ({
  done: { collections: Object.keys(s.done.collections).length, products: Object.keys(s.done.products).length, policies: s.done.policies.length,
    skipped: s.skipped.length, failed: Object.keys(s.failed).length },
  total: { collections: s.collections.length, products: s.products.length, policies: s.policies.length },
  finished: s.finished, stopped: s.stopped, status: s.status, approved_by: s.approved_by,
});

async function step(env, body, via) {
  const by = String(body.approved_by || "").trim().slice(0, 100);
  if (!by) throw new Refuse(400, "approved_by is required: a copy writes to the store");
  const raw = await env.VAULT.get(`copy:${body.job || ""}`);
  if (!raw) throw new Refuse(404, "no copy plan for this job");
  const s = JSON.parse(raw);
  if (s.finished) return counts(s);
  s.approved_by = s.approved_by || by;
  const cfg = builder(env, s.shop);
  const token = await orgAccess(cfg);
  const publishTo = s.status === "ACTIVE" && s.online_store ? [{ publicationId: s.online_store }] : [];
  let units = UNITS_PER_STEP;
  const fail = (kind, key, why) => {
    s.failed[`${kind}:${key}`] = String(why).slice(0, 300);
    s.streak = s.streak.kind === kind ? { kind, n: s.streak.n + 1 } : { kind, n: 1 };
    if (s.streak.n >= 3) s.stopped = `3 ${kind} copies failed in a row (last: ${String(why).slice(0, 200)})`;
  };
  const ok = (kind) => { if (s.streak.kind === kind) s.streak = { kind, n: 0 }; };
  const open = (kind, key) => !(key in (kind === "collection" ? s.done.collections : s.done.products)) && !s.failed[`${kind}:${key}`]
    && !s.skipped.includes(`${kind}:${key}`);

  for (const c of s.collections) {
    if (units <= 0 || s.stopped) break;
    if (!open("collection", c.handle)) continue;
    units -= 1;
    try {
      if ((await gql(s.shop, token, Q.collectionExists, { handle: c.handle })).collectionByIdentifier) { s.skipped.push(`collection:${c.handle}`); continue; }
      const made = (await gql(s.shop, token, M.collection, { collection: { title: c.title, handle: c.handle, descriptionHtml: c.descriptionHtml } })).collectionCreate;
      if (userErrors(made)) { fail("collection", c.handle, userErrors(made)); continue; }
      if (publishTo.length) await gql(s.shop, token, M.publish, { id: made.collection.id, input: publishTo });
      s.done.collections[c.handle] = made.collection.id;
      ok("collection");
    } catch (err) { fail("collection", c.handle, err.message); }
  }
  const member = {};
  for (const c of s.collections) for (const h of c.products) if (s.done.collections[c.handle]) (member[h] ||= []).push(s.done.collections[c.handle]);
  for (const p of s.products) {
    if (units <= 0 || s.stopped) break;
    if (!open("product", p.handle)) continue;
    if (s.collections.some((c) => open("collection", c.handle))) break;  // collections first, so a product joins them as it is made
    units -= 1;
    try {
      if ((await gql(s.shop, token, Q.exists, { handle: p.handle })).productByIdentifier) { s.skipped.push(`product:${p.handle}`); continue; }
      const made = (await gql(s.shop, token, M.product, { input: { ...p, collections: member[p.handle] || [] } })).productSet;
      if (userErrors(made)) { fail("product", p.handle, userErrors(made)); continue; }
      if (publishTo.length) await gql(s.shop, token, M.publish, { id: made.product.id, input: publishTo });
      s.done.products[p.handle] = made.product.id;
      ok("product");
    } catch (err) { fail("product", p.handle, err.message); }
  }
  const productsLeft = s.products.some((p) => open("product", p.handle));
  const policiesLeft = s.policies.filter((p) => !s.done.policies.includes(p.type) && !s.failed[`policy:${p.type}`] && !s.skipped.includes(`policy:${p.type}`));
  if (!s.stopped && units > 0 && !productsLeft && policiesLeft.length) {
    const current = (await gql(s.shop, token, Q.policies)).shop.shopPolicies;
    for (const pol of policiesLeft) {
      if (units <= 0) break;
      units -= 1;
      if (String((current.find((c) => c.type === pol.type) || {}).body || "").trim()) { s.skipped.push(`policy:${pol.type}`); continue; }
      try {
        const set = (await gql(s.shop, token, M.policy, { shopPolicy: { type: pol.type, body: pol.body } })).shopPolicyUpdate;
        if (userErrors(set)) { fail("policy", pol.type, userErrors(set)); continue; }
        s.done.policies.push(pol.type);
      } catch (err) { fail("policy", pol.type, err.message); }
    }
  }
  const left = s.collections.some((c) => open("collection", c.handle)) || s.products.some((p) => open("product", p.handle))
    || s.policies.some((p) => !s.done.policies.includes(p.type) && !s.failed[`policy:${p.type}`] && !s.skipped.includes(`policy:${p.type}`));
  s.finished = Boolean(s.stopped) || !left;
  await env.VAULT.put(`copy:${s.job}`, JSON.stringify(s));
  const out = counts(s);
  await audit(env, { app: "dtj-store-builder", shop: s.shop, action: `brand copy step (${s.job})`, result: s.stopped ? "stopped" : "success",
    approved_by: s.approved_by, via, ...out.done, finished: s.finished });
  return out;
}

// a picture's upload address: the file name is rebuilt (letters, digits, dot, dash, underscore), the type and size are checked
export function cleanUpload(f) {
  const mimeType = String(f?.mimeType || "").toLowerCase();
  const size = Number(f?.fileSize);
  const filename = String(f?.filename || "").replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^[-.]+/, "").slice(-120);
  if (!UPLOAD_TYPES.has(mimeType) || !Number.isInteger(size) || size <= 0 || size > UPLOAD_MAX_BYTES || !filename) return null;
  return { filename, mimeType, fileSize: String(size), resource: "IMAGE", httpMethod: "POST" };
}

async function uploads(env, body, via) {
  const cfg = builder(env, body.shop);
  const files = Array.isArray(body.files) ? body.files : [];
  if (!files.length || files.length > UPLOADS_PER_CALL) throw new Refuse(400, `files must list 1 to ${UPLOADS_PER_CALL} pictures`);
  const input = files.map(cleanUpload);
  const bad = input.map((x, i) => (x ? null : String(files[i]?.filename || i).slice(0, 80))).filter((x) => x !== null);
  if (bad.length) throw new Refuse(400, `not a jpg, png, webp or gif of at most 20 MB: ${bad.slice(0, 5).join(", ")}`);
  const token = await orgAccess(cfg);
  const made = (await gql(cfg.shop, token, M.stage, { input })).stagedUploadsCreate;
  const targets = input.map((x, i) => {
    const t = (made.stagedTargets || [])[i];
    return t && t.url ? { filename: x.filename, url: t.url, resourceUrl: t.resourceUrl, parameters: t.parameters || [] } : { filename: x.filename, url: null };
  });
  await audit(env, { app: "dtj-store-builder", shop: cfg.shop, action: `picture upload addresses (${input.length})`, result: "success", via });
  return { targets, userErrors: userErrors(made) };
}

async function activate(env, body, via) {
  const by = String(body.approved_by || "").trim().slice(0, 100);
  if (!by) throw new Refuse(400, "approved_by is required: activate changes products in the store");
  const cfg = builder(env, body.shop);
  const handles = Array.isArray(body.handles) ? [...new Set(body.handles.map(String))] : [];
  if (!handles.length || handles.length > ACTIVATE_MAX || !handles.every((h) => HANDLE_RE.test(h))) {
    throw new Refuse(400, `handles must list 1 to ${ACTIVATE_MAX} product handles`);
  }
  const token = await orgAccess(cfg);
  const online = ((await gql(cfg.shop, token, Q.publications)).publications.nodes.find((p) => p.name === "Online Store") || {}).id;
  const out = { activated: [], already_active: [], not_found: [], failed: [], left: handles.slice(ACTIVATE_PER_CALL) };
  for (const handle of handles.slice(0, ACTIVATE_PER_CALL)) {
    try {
      const found = (await gql(cfg.shop, token, Q.productStatus, { handle })).productByIdentifier;
      if (!found) { out.not_found.push(handle); continue; }
      if (found.status !== "DRAFT") { out.already_active.push(handle); continue; }  // ACTIVE stays, ARCHIVED is a person's choice
      const set = (await gql(cfg.shop, token, M.activate, { product: { id: found.id, status: "ACTIVE" } })).productUpdate;
      if (userErrors(set)) { out.failed.push({ handle, why: userErrors(set).slice(0, 300) }); continue; }
      if (online) {
        const pub = (await gql(cfg.shop, token, M.publish, { id: found.id, input: [{ publicationId: online }] })).publishablePublish;
        if (userErrors(pub)) { out.failed.push({ handle, why: `active, but not on the Online Store: ${userErrors(pub).slice(0, 250)}` }); continue; }
      }
      out.activated.push(handle);
    } catch (err) { out.failed.push({ handle, why: String(err.message).slice(0, 300) }); }
  }
  if (!online) out.note = "no Online Store channel found: the products are active but not on the storefront";
  await audit(env, { app: "dtj-store-builder", shop: cfg.shop, action: "products made active (status only)", result: out.failed.length ? "partly" : "success",
    approved_by: by, via, activated: out.activated.length, failed: out.failed.length, left: out.left.length });
  return out;
}

// a page as the laptop wrote it, rebuilt: a handle, a title, safe HTML, the default or the contact template
export function cleanPage(p) {
  const handle = String(p?.handle || "").toLowerCase();
  const title = String(p?.title || "").trim().slice(0, 255);
  const body = String(p?.body || "");
  const templateSuffix = p?.template_suffix === "contact" ? "contact" : "";
  if (!/^[a-z0-9][a-z0-9-]{0,99}$/.test(handle) || !title || body.length > 100000 || UNSAFE_HTML.test(body)) return null;
  return { handle, title, body, isPublished: true, templateSuffix };
}

async function pages(env, body, via) {
  const by = String(body.approved_by || "").trim().slice(0, 100);
  if (!by) throw new Refuse(400, "approved_by is required: pages appear on the store");
  const cfg = builder(env, body.shop);
  const list = Array.isArray(body.pages) ? body.pages : [];
  const input = list.map(cleanPage);
  if (!list.length || list.length > PAGES_MAX || input.some((x) => !x)) {
    throw new Refuse(400, `pages must list 1 to ${PAGES_MAX} pages, each a handle, a title and HTML without scripts, frames or forms`);
  }
  const token = await orgAccess(cfg);
  const have = new Set((await gql(cfg.shop, token, Q.pageHandles)).pages.nodes.map((n) => n.handle));
  const out = { created: [], skipped: [], failed: [] };
  for (const page of input) {
    if (have.has(page.handle)) { out.skipped.push(page.handle); continue; }  // the store's own page is never changed
    try {
      const made = (await gql(cfg.shop, token, M.page, { page })).pageCreate;
      if (userErrors(made)) out.failed.push({ handle: page.handle, why: userErrors(made).slice(0, 300) });
      else out.created.push(page.handle);
    } catch (err) { out.failed.push({ handle: page.handle, why: String(err.message).slice(0, 300) }); }
  }
  await audit(env, { app: "dtj-store-builder", shop: cfg.shop, action: `pages added (${out.created.join(", ") || "none"})`,
    result: out.failed.length ? "partly" : "success", approved_by: by, via, skipped: out.skipped.length, failed: out.failed.length });
  return out;
}

async function menu(env, body, via) {
  const by = String(body.approved_by || "").trim().slice(0, 100);
  if (!by) throw new Refuse(400, "approved_by is required: the menu is on every page of the store");
  const cfg = builder(env, body.shop);
  if (!MENU_HANDLES.has(body.handle)) throw new Refuse(400, "handle must be main-menu or footer");
  const wanted = Array.isArray(body.items) ? body.items : [];
  if (!wanted.length || wanted.length > MENU_MAX) throw new Refuse(400, `items must list 1 to ${MENU_MAX} links`);
  const token = await orgAccess(cfg);
  const found = (await gql(cfg.shop, token, Q.menus)).menus.nodes.find((m) => m.handle === body.handle);
  if (!found) throw new Refuse(404, `the store has no ${body.handle} menu`);
  let pageIds = null, policies = null;
  const items = [], left = [];
  for (const it of wanted) {
    const title = String(it?.title || "").trim().slice(0, 255);
    const handle = String(it?.handle || "").toLowerCase();
    if (!title) { left.push({ title: "?", why: "no title" }); continue; }
    if (it.type === "FRONTPAGE") items.push({ title, type: "FRONTPAGE", url: "/" });
    else if (it.type === "CATALOG") items.push({ title, type: "CATALOG", url: "/collections/all" });
    else if (it.type === "SEARCH") items.push({ title, type: "SEARCH", url: "/search" });
    else if (it.type === "COLLECTION" && HANDLE_RE.test(handle)) {
      const c = (await gql(cfg.shop, token, Q.collectionExists, { handle })).collectionByIdentifier;
      if (c) items.push({ title, type: "COLLECTION", resourceId: c.id, url: `/collections/${handle}` });
      else left.push({ title, why: `no collection ${handle}` });
    } else if (it.type === "PAGE" && HANDLE_RE.test(handle)) {
      pageIds = pageIds || new Map((await gql(cfg.shop, token, Q.pageHandles)).pages.nodes.map((n) => [n.handle, n.id]));
      if (pageIds.has(handle)) items.push({ title, type: "PAGE", resourceId: pageIds.get(handle), url: `/pages/${handle}` });
      else left.push({ title, why: `no page ${handle}` });
    } else if (it.type === "SHOP_POLICY" && POLICY_HANDLES[handle]) {
      policies = policies || (await gql(cfg.shop, token, Q.policyIds)).shop.shopPolicies;
      const pol = policies.find((x) => x.type === POLICY_HANDLES[handle]);
      if (pol && pol.id) items.push({ title, type: "SHOP_POLICY", resourceId: pol.id, url: `/policies/${handle}` });
      else left.push({ title, why: `the ${handle} is empty` });
    } else left.push({ title, why: "not a link this menu may have" });
  }
  if (!items.length) throw new Refuse(400, "none of the links could be made: the menu is left as it is");
  const before = (found.items || []).map((i) => ({ title: i.title, type: i.type, url: i.url, sub: (i.items || []).length }));
  const set = (await gql(cfg.shop, token, M.menu, { id: found.id, title: found.title, items })).menuUpdate;
  if (userErrors(set)) throw new Refuse(502, `Shopify refused the menu: ${userErrors(set).slice(0, 300)}`);
  await audit(env, { app: "dtj-store-builder", shop: cfg.shop, action: `menu ${body.handle} set (${items.length} links)`, result: "success",
    approved_by: by, via, before, after: items.map((i) => ({ title: i.title, type: i.type, url: i.url })) });
  return { menu: body.handle, items: items.map((i) => ({ title: i.title, url: i.url })), left_out: left, before };
}

export async function copyRoute(request, env, caller, now) {
  const raw = await request.text();
  const via = await caller(request, env, raw);
  let body;
  try { body = JSON.parse(raw); } catch { throw new Refuse(400, "body is not JSON"); }
  if (!Number.isFinite(body.ts) || Math.abs(now() - body.ts) > FRESH_SECONDS) throw new Refuse(400, "the request is too old");
  if (body.op === "target") return target(env, body);
  if (body.op === "plan") return keepPlan(env, body);
  if (body.op === "step") return step(env, body, via);
  if (body.op === "uploads") return uploads(env, body, via);
  if (body.op === "activate") return activate(env, body, via);
  if (body.op === "product") {
    const cfg = builder(env, body.shop);
    if (!HANDLE_RE.test(body.handle || "")) throw new Refuse(400, "handle must be a product handle");
    const found = (await gql(cfg.shop, await orgAccess(cfg), Q.oneProduct, { handle: body.handle })).productByIdentifier;
    if (!found) throw new Refuse(404, `no product ${body.handle} in ${cfg.shop}`);
    return { product: found };
  }
  if (body.op === "pages") return pages(env, body, via);
  if (body.op === "menu") return menu(env, body, via);
  if (body.op === "status") {
    const raw2 = await env.VAULT.get(`copy:${body.job || ""}`);
    if (!raw2) throw new Refuse(404, "no copy plan for this job");
    return counts(JSON.parse(raw2));
  }
  throw new Refuse(400, "op must be target, plan, step, status, uploads, activate, product, pages or menu");
}
