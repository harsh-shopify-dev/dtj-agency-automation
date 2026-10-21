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
// Only the four mutations below can be sent, with inputs rebuilt from a list of allowed fields. It never updates or deletes: a
// handle the store has is skipped, a policy is written only where the store's own is empty. Every step is one audit row.
import { Refuse, audit, call, orgAccess } from "./worker.js";

export const COPY_API = "2026-10";  // the fields below were read from this version's schema (21 Oct 2026)
const SHOP_RE = /^[a-z0-9][a-z0-9-]*\.myshopify\.com$/;
const JOB_RE = /^[a-z0-9][a-z0-9-]{1,40}$/;
const HANDLE_RE = /^[a-z0-9À-￿][a-z0-9À-￿_-]{0,254}$/i;
const FRESH_SECONDS = 300;
const UNITS_PER_STEP = 8;  // one call stays far below a Worker's 50 outside calls: a product is 3 (exists?, create, publish)
const POLICY_TYPES = new Set(["REFUND_POLICY", "SHIPPING_POLICY", "PRIVACY_POLICY", "TERMS_OF_SERVICE"]);
const LIMITS = { products: 2500, collections: 40, variants: 2048, files: 250 };

const Q = {
  target: "query Target { shop { name currencyCode myshopifyDomain shopPolicies { type body } } publications(first: 20) { nodes { id name } } }",
  products: "query ProductHandles($after: String) { products(first: 250, after: $after) { nodes { handle } pageInfo { hasNextPage endCursor } } }",
  collections: "query CollectionHandles($after: String) { collections(first: 250, after: $after) { nodes { handle } pageInfo { hasNextPage endCursor } } }",
  exists: "query Exists($handle: String!) { productByIdentifier(identifier: { handle: $handle }) { id } }",
  collectionExists: "query CollectionExists($handle: String!) { collectionByIdentifier(identifier: { handle: $handle }) { id } }",
  policies: "query Policies { shop { shopPolicies { type body } } }",
};
const M = {
  product: "mutation CopyProduct($input: ProductSetInput!) { productSet(input: $input, synchronous: true) { product { id handle } userErrors { field message code } } }",
  collection: "mutation CopyCollection($collection: CollectionCreateInput!) { collectionCreate(collection: $collection) { collection { id handle } userErrors { field message } } }",
  publish: "mutation Publish($id: ID!, $input: [PublicationInput!]!) { publishablePublish(id: $id, input: $input) { userErrors { field message } } }",
  policy: "mutation SetPolicy($shopPolicy: ShopPolicyInput!) { shopPolicyUpdate(shopPolicy: $shopPolicy) { shopPolicy { type } userErrors { field message } } }",
};
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
  const front = await call(`https://${cfg.shop}/`, { redirect: "follow" }).catch(() => null);
  const page = front ? await front.text().catch(() => "") : "";
  const password = Boolean(front && ((front.url || "").includes("/password") || /action="\/password"/.test(page)));
  return {
    store: data.shop.myshopifyDomain, name: data.shop.name, currency: data.shop.currencyCode, password,
    online_store: (data.publications.nodes.find((p) => p.name === "Online Store") || {}).id || null,
    empty_policies: data.shop.shopPolicies.filter((p) => !String(p.body || "").trim()).map((p) => p.type).sort(),
    products: await handles(Q.products, "products"), collections: await handles(Q.collections, "collections"),
  };
}

async function keepPlan(env, body) {
  if (!JOB_RE.test(body.job || "")) throw new Refuse(400, "job must be lowercase letters, digits and dashes");
  builder(env, body.shop);
  const old = JSON.parse((await env.VAULT.get(`copy:${body.job}`)) || "null");
  if (old && old.approved_by) throw new Refuse(409, "this copy has started already: its plan cannot change");
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

export async function copyRoute(request, env, caller, now) {
  const raw = await request.text();
  const via = await caller(request, env, raw);
  let body;
  try { body = JSON.parse(raw); } catch { throw new Refuse(400, "body is not JSON"); }
  if (!Number.isFinite(body.ts) || Math.abs(now() - body.ts) > FRESH_SECONDS) throw new Refuse(400, "the request is too old");
  if (body.op === "target") return target(env, body);
  if (body.op === "plan") return keepPlan(env, body);
  if (body.op === "step") return step(env, body, via);
  if (body.op === "status") {
    const raw2 = await env.VAULT.get(`copy:${body.job || ""}`);
    if (!raw2) throw new Refuse(404, "no copy plan for this job");
    return counts(JSON.parse(raw2));
  }
  throw new Refuse(400, "op must be target, plan, step or status");
}
