// The brand copy through DTJ Store Builder (src/copy.js). A stand-in Shopify answers every call: nothing reaches a store or Cloudflare.
// Run: node --test test/*.test.js
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import worker from "../src/worker.js";
import { cleanProduct, cleanPlan } from "../src/copy.js";

const SHOP = "royal-demo.myshopify.com";
const ORIGIN = "https://dtj-install-catcher.example.workers.dev";
const BUILDER_SECRET = "shpss_test_store_builder";

class FakeKV {
  constructor() { this.data = new Map(); }
  async get(k) { return this.data.has(k) ? this.data.get(k) : null; }
  async put(k, v) { this.data.set(k, v); }
  async delete(k) { this.data.delete(k); }
}

const env = (extra = {}) => ({ APPS: "{}", VAULT_KEY: Buffer.alloc(32, 7).toString("base64"), CONTROL_KEY: "control-key", BOT_KEY: "b".repeat(40),
  BUILDER_CLIENT_ID: "builder-client-id", ORG_SECRET_DTJ_STORE_BUILDER: BUILDER_SECRET, VAULT: new FakeKV(), ...extra });

// a stand-in store: products / collections by handle, policies, a password page, and every GraphQL call recorded
function fakeStore({ password = true, products = ["old-product"], policies = { REFUND_POLICY: "", SHIPPING_POLICY: "Ours." }, failHandles = [] } = {}) {
  const s = { products: new Map(products.map((h, i) => [h, `gid://shopify/Product/${i + 1}`])), collections: new Map(), policies: { ...policies },
    published: [], sent: [], n: 100, password, failHandles: new Set(failHandles) };
  s.fetch = async (url, init = {}) => {
    const u = new URL(url);
    if (u.host !== SHOP) return new Response("other host", { status: 404 });
    if (u.pathname === "/") {
      return new Response(s.password ? '<form method="post" action="/password">' : "<html>shop</html>", { status: 200 });
    }
    if (u.pathname === "/admin/oauth/access_token") {
      const b = JSON.parse(init.body);
      if (b.client_secret !== BUILDER_SECRET || b.grant_type !== "client_credentials") return Response.json({ error: "invalid_client" }, { status: 401 });
      return Response.json({ access_token: "shpat_builder" });
    }
    if (!u.pathname.endsWith("/graphql.json")) return new Response("not found", { status: 404 });
    assert.equal(init.headers["X-Shopify-Access-Token"], "shpat_builder");
    const { query, variables } = JSON.parse(init.body);
    const name = query.match(/^(query|mutation) (\w+)/)[2];
    s.sent.push({ name, variables });
    const pol = Object.entries(s.policies).map(([type, body]) => ({ type, body }));
    const data = {
      Target: () => ({ shop: { name: "Royal Demo", currencyCode: "INR", myshopifyDomain: SHOP, shopPolicies: pol },
        publications: { nodes: [{ id: "gid://shopify/Publication/9", name: "Online Store" }, { id: "gid://shopify/Publication/8", name: "Point of Sale" }] } }),
      ProductHandles: () => ({ products: { nodes: [...s.products.keys()].map((handle) => ({ handle })), pageInfo: { hasNextPage: false, endCursor: null } } }),
      CollectionHandles: () => ({ collections: { nodes: [...s.collections.keys()].map((handle) => ({ handle })), pageInfo: { hasNextPage: false, endCursor: null } } }),
      Exists: () => ({ productByIdentifier: s.products.has(variables.handle) ? { id: s.products.get(variables.handle) } : null }),
      CollectionExists: () => ({ collectionByIdentifier: s.collections.has(variables.handle) ? { id: s.collections.get(variables.handle) } : null }),
      Policies: () => ({ shop: { shopPolicies: pol } }),
      CopyCollection: () => { const id = `gid://shopify/Collection/${++s.n}`; s.collections.set(variables.collection.handle, id); return { collectionCreate: { collection: { id, handle: variables.collection.handle }, userErrors: [] } }; },
      CopyProduct: () => {
        if (s.failHandles.has(variables.input.handle)) return { productSet: { product: null, userErrors: [{ field: ["input"], message: "Bad input" }] } };
        const id = `gid://shopify/Product/${++s.n}`; s.products.set(variables.input.handle, id);
        return { productSet: { product: { id, handle: variables.input.handle }, userErrors: [] } };
      },
      Publish: () => { s.published.push(variables.id); return { publishablePublish: { userErrors: [] } }; },
      SetPolicy: () => { s.policies[variables.shopPolicy.type] = variables.shopPolicy.body; return { shopPolicyUpdate: { shopPolicy: { type: variables.shopPolicy.type }, userErrors: [] } }; },
    }[name];
    if (!data) return Response.json({ errors: [{ message: `unexpected ${name}` }] });
    return Response.json({ data: data() });
  };
  return s;
}

let store;
beforeEach(() => { store = fakeStore(); globalThis.fetch = store.fetch; });

const ts = () => Math.floor(Date.now() / 1000);
const signed = (body, key = "control-key") => {
  const raw = JSON.stringify({ ts: ts(), ...body });
  return new Request(`${ORIGIN}/copy`, { method: "POST", body: raw, headers: { "X-DTJ-Signature": createHmac("sha256", key).update(raw).digest("hex") } });
};
const fromBot = (body, key = "b".repeat(40)) => new Request(`${ORIGIN}/copy`, { method: "POST", body: JSON.stringify({ ts: ts(), ...body }), headers: { "X-DTJ-Bot-Key": key } });
const send = async (e, req) => { const res = await worker.fetch(req, e); return { status: res.status, body: await res.json() }; };

const product = (handle, extra = {}) => ({ title: `T ${handle}`, handle, status: "ACTIVE", descriptionHtml: "<p>x</p>",
  productOptions: [{ name: "Size", position: 1, values: [{ name: "S" }, { name: "M" }] }],
  variants: [{ optionValues: [{ optionName: "Size", name: "S" }], price: "499.00", inventoryItem: { tracked: false } },
    { optionValues: [{ optionName: "Size", name: "M" }], price: "599.00", compareAtPrice: "699.00", inventoryItem: { tracked: false } }],
  files: [{ originalSource: "https://cdn.shopify.com/a.jpg", contentType: "IMAGE", alt: "a", filename: "a.jpg" }], ...extra });
const PLAN = { brand: "https://glowco.com", status: "ACTIVE", target: { store: SHOP, online_store: "gid://shopify/Publication/9" },
  products: [product("glow-serum"), product("night-cream"), product("old-product")],
  collections: [{ handle: "skin", title: "Skin", description_html: "<p>All</p>", products: ["glow-serum", "night-cream", "not-planned"] }],
  policies: [{ type: "REFUND_POLICY", body: "<p>7 days</p>", source: "https://glowco.com/policies/refund-policy" },
    { type: "SHIPPING_POLICY", body: "<p>3 days</p>" }] };

test("target reads what the store has, through DTJ Store Builder's own key, and changes nothing", async () => {
  const e = env();
  const r = await send(e, signed({ op: "target", shop: SHOP }));
  assert.equal(r.status, 200);
  assert.deepEqual(r.body, { store: SHOP, name: "Royal Demo", currency: "INR", password: true, online_store: "gid://shopify/Publication/9",
    empty_policies: ["REFUND_POLICY"], products: ["old-product"], collections: [] });
  assert.ok(store.sent.every((c) => !["CopyProduct", "CopyCollection", "Publish", "SetPolicy"].includes(c.name)));
});

test("without the app set up, a bad key or an old request: refused", async () => {
  assert.equal((await send(env({ BUILDER_CLIENT_ID: "" }), signed({ op: "target", shop: SHOP }))).status, 503);
  assert.equal((await send(env(), signed({ op: "target", shop: SHOP }, "wrong-key"))).status, 401);
  assert.equal((await send(env(), fromBot({ op: "target", shop: SHOP }, "short"))).status, 401);
  const old = JSON.stringify({ ts: 1000, op: "status", job: "x" });
  const res = await worker.fetch(new Request(`${ORIGIN}/copy`, { method: "POST", body: old, headers: { "X-DTJ-Signature": createHmac("sha256", "control-key").update(old).digest("hex") } }), env());
  assert.equal(res.status, 400);
  assert.equal((await send(env(), signed({ op: "target", shop: "evil.com" }))).status, 400);
});

test("the plan is rebuilt field by field: an id, a missing price or a non-https picture never reach Shopify", () => {
  assert.equal(cleanProduct(product("x", { id: "gid://shopify/Product/1" }), "ACTIVE"), null);  // would update an existing product
  assert.equal(cleanProduct(product("x", { variants: [{ optionValues: [], price: "" }] }), "ACTIVE"), null);
  const p = cleanProduct(product("x", { files: [{ originalSource: "http://x/a.jpg" }, { originalSource: "https://x/b.jpg", contentType: "VIDEO" }],
    secret: "nope", variants: [{ optionValues: [{ optionName: "Size", name: "S" }], price: "10", compareAtPrice: "5", inventoryPolicy: "CONTINUE" }] }), "DRAFT");
  assert.equal(p.status, "DRAFT");
  assert.equal(p.secret, undefined);
  assert.deepEqual(p.files.map((f) => [f.originalSource, f.contentType]), [["https://x/b.jpg", "IMAGE"]]);
  assert.deepEqual(p.variants[0], { optionValues: [{ optionName: "Size", name: "S" }], price: "10", inventoryItem: { tracked: false } });
  const plan = cleanPlan(PLAN, SHOP);
  assert.deepEqual(plan.collections[0].products, ["glow-serum", "night-cream", "old-product"].filter((h) => h !== "old-product").concat([]));
  assert.throws(() => cleanPlan({ ...PLAN, target: { store: "other.myshopify.com" } }, SHOP));
});

test("the whole copy: kept, then step by step (collections first), each product joined to its collection and published", async () => {
  const e = env();
  const kept = await send(e, signed({ op: "plan", job: "royal-demo", shop: SHOP, plan: PLAN }));
  assert.deepEqual(kept.body, { job: "royal-demo", products: 3, collections: 1, policies: 2, refused: [], status: "ACTIVE" });
  assert.equal((await send(e, fromBot({ op: "step", job: "royal-demo" }))).status, 400);  // no approver, no write
  let last;
  for (let i = 0; i < 5; i++) {
    last = (await send(e, fromBot({ op: "step", job: "royal-demo", approved_by: "Riya (Telegram Approve)" }))).body;
    if (last.finished) break;
  }
  assert.equal(last.finished, true);
  assert.deepEqual(last.done, { collections: 1, products: 2, policies: 1, skipped: 2, failed: 0 });  // old-product and the store's own policy
  const created = store.sent.filter((c) => c.name === "CopyProduct");
  assert.deepEqual(created.map((c) => c.variables.input.handle), ["glow-serum", "night-cream"]);
  assert.deepEqual(created[0].variables.input.collections, [store.collections.get("skin")]);
  assert.equal(store.sent.findIndex((c) => c.name === "CopyCollection") < store.sent.findIndex((c) => c.name === "CopyProduct"), true);
  assert.equal(store.published.length, 3);
  assert.equal(store.policies.SHIPPING_POLICY, "Ours.");  // the store's own policy is never replaced
  assert.equal(store.policies.REFUND_POLICY, "<p>7 days</p>");
  const audit = [...e.VAULT.data.keys()].filter((k) => k.startsWith("audit:")).map((k) => JSON.parse(e.VAULT.data.get(k)));
  assert.ok(audit.every((a) => a.approved_by === "Riya (Telegram Approve)" && a.via === "telegram bot"));
  assert.equal((await send(e, signed({ op: "plan", job: "royal-demo", shop: SHOP, plan: PLAN }))).status, 409);  // started: plan fixed
  assert.equal((await send(e, signed({ op: "status", job: "royal-demo" }))).body.finished, true);
});

test("a draft copy is never published, a failed product is reported and 3 failures in a row stop the copy", async () => {
  store = fakeStore({ password: false, failHandles: ["a", "b", "c", "d"] });
  globalThis.fetch = store.fetch;
  const e = env();
  const plan = { ...PLAN, status: "DRAFT", collections: [], policies: [], products: ["a", "b", "c", "d"].map((h) => product(h)) };
  await send(e, signed({ op: "plan", job: "j1", shop: SHOP, plan }));
  const r = (await send(e, fromBot({ op: "step", job: "j1", approved_by: "Harsh" }))).body;
  assert.equal(r.finished, true);
  assert.match(r.stopped, /3 product copies failed in a row/);
  assert.equal(r.done.failed, 3);
  assert.deepEqual(store.published, []);
});
