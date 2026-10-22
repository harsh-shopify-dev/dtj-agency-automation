// The brand copy through DTJ Store Builder (src/copy.js). A stand-in Shopify answers every call: nothing reaches a store or Cloudflare.
// Run: node --test test/*.test.js
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import worker from "../src/worker.js";
import { cleanProduct, cleanPlan, cleanUpload } from "../src/copy.js";

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
function fakeStore({ password = true, products = ["old-product"], policies = { REFUND_POLICY: "", SHIPPING_POLICY: "Ours." }, failHandles = [],
  passwordQuery = true, statuses = {} } = {}) {
  const s = { products: new Map(products.map((h, i) => [h, `gid://shopify/Product/${i + 1}`])), collections: new Map(), policies: { ...policies },
    published: [], sent: [], n: 100, password, failHandles: new Set(failHandles), statuses: { ...statuses } };
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
      Password: () => (passwordQuery ? { onlineStore: { passwordProtection: { enabled: s.password } } } : null),
      CopyCollection: () => { const id = `gid://shopify/Collection/${++s.n}`; s.collections.set(variables.collection.handle, id); return { collectionCreate: { collection: { id, handle: variables.collection.handle }, userErrors: [] } }; },
      CopyProduct: () => {
        if (s.failHandles.has(variables.input.handle)) return { productSet: { product: null, userErrors: [{ field: ["input"], message: "Bad input" }] } };
        const id = `gid://shopify/Product/${++s.n}`; s.products.set(variables.input.handle, id);
        return { productSet: { product: { id, handle: variables.input.handle }, userErrors: [] } };
      },
      Publish: () => { s.published.push(variables.id); return { publishablePublish: { userErrors: [] } }; },
      SetPolicy: () => { s.policies[variables.shopPolicy.type] = variables.shopPolicy.body; return { shopPolicyUpdate: { shopPolicy: { type: variables.shopPolicy.type }, userErrors: [] } }; },
      Publications: () => ({ publications: { nodes: [{ id: "gid://shopify/Publication/9", name: "Online Store" }] } }),
      ProductStatus: () => {
        const id = s.products.get(variables.handle);
        return { productByIdentifier: id ? { id, status: s.statuses[variables.handle] || "DRAFT" } : null };
      },
      Activate: () => {
        const handle = [...s.products].find(([, id]) => id === variables.product.id)[0];
        if (s.failHandles.has(handle)) return { productUpdate: { product: null, userErrors: [{ field: ["status"], message: "Cannot activate" }] } };
        s.statuses[handle] = variables.product.status;
        return { productUpdate: { product: { id: variables.product.id, status: variables.product.status }, userErrors: [] } };
      },
      Stage: () => ({ stagedUploadsCreate: { stagedTargets: variables.input.map((f, i) => ({ url: "https://shopify-staged-uploads.storage.googleapis.com/",
        resourceUrl: `https://shopify-staged-uploads.storage.googleapis.com/tmp/1/products/${i}/${f.filename}`, parameters: [{ name: "key", value: `tmp/1/${f.filename}` }] })),
        userErrors: [] } }),
    }[name];
    const out = data && data();
    if (!out) return Response.json({ errors: [{ message: data ? "Access denied for onlineStore" : `unexpected ${name}` }] });
    return Response.json({ data: out });
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
    empty_policies: ["PRIVACY_POLICY", "REFUND_POLICY", "TERMS_OF_SERVICE"], products: ["old-product"], collections: [] });  // never set = empty
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
  assert.equal((await send(e, signed({ op: "plan", job: "royal-demo", shop: SHOP, plan: PLAN }))).status, 200);  // finished: a new copy may follow
  const fresh = (await send(e, signed({ op: "status", job: "royal-demo" }))).body;  // the new plan waits for its own Approve tap
  assert.deepEqual([fresh.finished, fresh.approved_by], [false, null]);
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

test("the password page comes from Shopify's own setting, else the storefront; an unfinished copy keeps its plan", async () => {
  store = fakeStore({ password: false });
  globalThis.fetch = store.fetch;
  assert.equal((await send(env(), signed({ op: "target", shop: SHOP }))).body.password, false);
  store = fakeStore({ password: true, passwordQuery: false });  // the app may not read the setting: the storefront decides
  globalThis.fetch = store.fetch;
  assert.equal((await send(env(), signed({ op: "target", shop: SHOP }))).body.password, true);
  const e = env();
  const big = { ...PLAN, collections: [], policies: [], products: Array.from({ length: 12 }, (_, i) => product(`p${i}`)) };
  await send(e, signed({ op: "plan", job: "j2", shop: SHOP, plan: big }));
  await send(e, fromBot({ op: "step", job: "j2", approved_by: "Harsh" }));  // 8 of 12: started, not finished
  assert.equal((await send(e, signed({ op: "plan", job: "j2", shop: SHOP, plan: PLAN }))).status, 409);
});

test("uploads: Shopify's one-time upload addresses for pictures only, the store itself unchanged", async () => {
  const e = env();
  const r = await send(e, signed({ op: "uploads", shop: SHOP, files: [{ filename: "Glow Serum 1.jpg", mimeType: "image/jpeg", fileSize: 123456 },
    { filename: "../banner.png", mimeType: "image/png", fileSize: 99 }] }));
  assert.equal(r.status, 200);
  assert.deepEqual(r.body.targets.map((t) => t.filename), ["Glow-Serum-1.jpg", "banner.png"]);
  assert.match(r.body.targets[0].resourceUrl, /^https:\/\/shopify-staged-uploads\.storage\.googleapis\.com\//);
  assert.deepEqual(r.body.targets[0].parameters, [{ name: "key", value: "tmp/1/Glow-Serum-1.jpg" }]);
  const stage = store.sent.find((c) => c.name === "Stage");
  assert.deepEqual(stage.variables.input[0], { filename: "Glow-Serum-1.jpg", mimeType: "image/jpeg", fileSize: "123456", resource: "IMAGE", httpMethod: "POST" });
  assert.ok(store.sent.every((c) => ["Stage"].includes(c.name)));  // nothing else is sent
  assert.equal(r.body.userErrors, "");
  // only pictures, of a sane size, at most 50 a call
  assert.equal((await send(e, signed({ op: "uploads", shop: SHOP, files: [{ filename: "x.pdf", mimeType: "application/pdf", fileSize: 10 }] }))).status, 400);
  assert.equal((await send(e, signed({ op: "uploads", shop: SHOP, files: [{ filename: "x.jpg", mimeType: "image/jpeg", fileSize: 21 * 1024 * 1024 }] }))).status, 400);
  assert.equal((await send(e, signed({ op: "uploads", shop: SHOP, files: [] }))).status, 400);
  const many = Array.from({ length: 51 }, (_, i) => ({ filename: `${i}.jpg`, mimeType: "image/jpeg", fileSize: 10 }));
  assert.equal((await send(e, signed({ op: "uploads", shop: SHOP, files: many }))).status, 400);
  assert.equal(cleanUpload({ filename: "a.jpg", mimeType: "image/jpeg", fileSize: 0 }), null);
  assert.equal((await send(e, fromBot({ op: "uploads", shop: SHOP, files: [{ filename: "a.jpg", mimeType: "image/jpeg", fileSize: 5 }] }, "short"))).status, 401);
});

test("activate: a DRAFT product goes ACTIVE and onto the Online Store, the status is the only field sent", async () => {
  store = fakeStore({ products: ["senso-a", "senso-b", "live-one", "archived-one", "broken"], statuses: { "live-one": "ACTIVE", "archived-one": "ARCHIVED" },
    failHandles: ["broken"] });
  globalThis.fetch = store.fetch;
  const e = env();
  assert.equal((await send(e, signed({ op: "activate", shop: SHOP, handles: ["senso-a"] }))).status, 400);  // no approver, no write
  assert.equal((await send(e, signed({ op: "activate", shop: SHOP, handles: ["bad handle!"], approved_by: "Harsh" }))).status, 400);
  const r = await send(e, signed({ op: "activate", shop: SHOP, approved_by: "Harsh (chat, 22 Oct 2026)",
    handles: ["senso-a", "senso-b", "live-one", "archived-one", "missing", "broken"] }));
  assert.equal(r.status, 200);
  assert.deepEqual(r.body.activated, ["senso-a", "senso-b"]);
  assert.deepEqual(r.body.already_active, ["live-one", "archived-one"]);  // an archived product is a person's choice: left alone
  assert.deepEqual(r.body.not_found, ["missing"]);
  assert.deepEqual(r.body.failed.map((f) => f.handle), ["broken"]);
  assert.deepEqual(r.body.left, []);
  const sent = store.sent.filter((c) => c.name === "Activate").map((c) => c.variables.product);
  assert.ok(sent.every((p) => Object.keys(p).sort().join() === "id,status" && p.status === "ACTIVE"));
  assert.deepEqual(store.published, [store.products.get("senso-a"), store.products.get("senso-b")]);
  assert.ok(store.sent.every((c) => !["CopyProduct", "CopyCollection", "SetPolicy"].includes(c.name)));
  const audit = [...e.VAULT.data.keys()].filter((k) => k.startsWith("audit:")).map((k) => JSON.parse(e.VAULT.data.get(k)));
  assert.equal(audit.length, 1);
  assert.equal(audit[0].approved_by, "Harsh (chat, 22 Oct 2026)");
});

test("activate: at most 12 a call, the rest come back in left", async () => {
  const handles = Array.from({ length: 30 }, (_, i) => `p${i}`);
  store = fakeStore({ products: handles });
  globalThis.fetch = store.fetch;
  const e = env();
  const first = (await send(e, fromBot({ op: "activate", shop: SHOP, handles, approved_by: "Riya (Telegram Approve)" }))).body;
  assert.equal(first.activated.length, 12);
  assert.deepEqual(first.left, handles.slice(12));
  const second = (await send(e, fromBot({ op: "activate", shop: SHOP, handles: first.left, approved_by: "Riya (Telegram Approve)" }))).body;
  assert.equal(second.activated.length, 12);
  assert.equal(second.left.length, 6);
  assert.equal((await send(e, signed({ op: "activate", shop: SHOP, handles: Array.from({ length: 251 }, (_, i) => `x${i}`), approved_by: "H" }))).status, 400);
});
