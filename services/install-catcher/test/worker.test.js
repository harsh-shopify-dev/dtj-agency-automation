// Tests for the DTJ install catcher. A stand-in Shopify answers every call, so nothing reaches a store or Cloudflare.
// Run: node --test test/*.test.js(Node 22: fetch, Request, Response and Web Crypto are built in, as in a Worker)
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import worker, { appKeyEnv, refreshAll, sameText, seal, open, call } from "../src/worker.js";

const SHOP = "client-store.myshopify.com";
const APP = "client-store-blocks";
const SECRET = "shpss_test_client_secret_blocks";
const ORIGIN = "https://dtj-install-catcher.example.workers.dev";

class FakeKV {
  constructor() { this.data = new Map(); }
  async get(k) { return this.data.has(k) ? this.data.get(k) : null; }
  async put(k, v) { this.data.set(k, v); }
  async delete(k) { this.data.delete(k); }
  keys(prefix) { return [...this.data.keys()].filter((k) => k.startsWith(prefix)); }
}

function makeEnv(extra = {}) {
  return {
    APPS: JSON.stringify({ [APP]: { client_id: "client-id-blocks", shop: SHOP, label: "DTJ Blocks - Client" } }),
    [appKeyEnv(APP)]: SECRET,
    VAULT_KEY: Buffer.alloc(32, 7).toString("base64"),
    CONTROL_KEY: "control-key-for-n8n",
    VAULT: new FakeKV(),
    ...extra,
  };
}

// a stand-in Shopify: token endpoint (code and refresh grants, rotating pairs) and the GraphQL licence read/write
function fakeShopify() {
  const s = { access: null, refresh: null, licence: null, n: 0, calls: [], failNext: [] };
  s.fetch = async (url, init = {}) => {
    const u = new URL(url);
    s.calls.push({ url: u.toString(), body: init.body });
    if (s.failNext.length) return new Response("busy", { status: s.failNext.shift() });
    if (u.host !== SHOP) return new Response("wrong host", { status: 404 });
    if (u.pathname === "/admin/oauth/access_token") {
      const f = new URLSearchParams(init.body);
      if (f.get("client_secret") !== SECRET) return Response.json({ error: "invalid_client" }, { status: 401 });
      if (f.get("grant_type") === "refresh_token" && f.get("refresh_token") !== s.refresh) return Response.json({ error: "invalid_grant" }, { status: 400 });
      if (!f.get("grant_type") && (f.get("code") !== "the-code" || f.get("expiring") !== "1")) return Response.json({ error: "invalid_request" }, { status: 400 });
      s.n += 1;
      s.access = `shpat_access_${s.n}`;
      s.refresh = `shprt_refresh_${s.n}`;
      return Response.json({ access_token: s.access, expires_in: 3600, refresh_token: s.refresh, refresh_token_expires_in: 7776000, scope: "" });
    }
    if (u.pathname.endsWith("/graphql.json")) {
      if (init.headers["X-Shopify-Access-Token"] !== s.access) return new Response("unauthorized", { status: 401 });
      const { query, variables } = JSON.parse(init.body);
      if (query.includes("metafieldsSet")) {
        s.licence = variables.metafields[0].value;
        return Response.json({ data: { metafieldsSet: { metafields: [{ id: "gid://shopify/Metafield/1", key: "licence", value: s.licence }], userErrors: [] } } });
      }
      return Response.json({ data: { currentAppInstallation: { id: "gid://shopify/AppInstallation/9", app: { handle: "dtj-blocks-client" }, licence: s.licence ? { value: s.licence } : null } } });
    }
    return new Response("not found", { status: 404 });
  };
  return s;
}

let shopify;
beforeEach(() => {
  shopify = fakeShopify();
  globalThis.fetch = shopify.fetch;
});

const signQuery = (params, secret = SECRET) => {
  const msg = Object.keys(params).sort().map((k) => `${k}=${params[k]}`).join("&");
  return new URLSearchParams({ ...params, hmac: createHmac("sha256", secret).update(msg).digest("hex") }).toString();
};
const ts = () => String(Math.floor(Date.now() / 1000));
const get = (env, path) => worker.fetch(new Request(`${ORIGIN}${path}`), env);
const signed = (body, key = "control-key-for-n8n") => {
  const raw = JSON.stringify(body);
  return new Request(`${ORIGIN}/licence`, { method: "POST", body: raw, headers: { "X-DTJ-Signature": createHmac("sha256", key).update(raw).digest("hex") } });
};

async function install(env) {
  const start = await get(env, `/start/${APP}?${signQuery({ shop: SHOP, timestamp: ts(), host: "abc" })}`);
  assert.equal(start.status, 302);
  const auth = new URL(start.headers.get("Location"));
  const state = auth.searchParams.get("state");
  const cb = await get(env, `/callback/${APP}?${signQuery({ code: "the-code", shop: SHOP, state, timestamp: ts() })}`);
  return { start, auth, state, cb };
}

test("hmac follows Shopify's rule (sorted query without hmac, HMAC-SHA256 hex) and compares in constant time", async () => {
  const { start } = await install(makeEnv());
  assert.equal(start.status, 302);
  assert.ok(sameText("abc", "abc") && !sameText("abc", "abd") && !sameText("abc", "abcd"));
});

test("start sends the merchant to Shopify's authorize page with this app, our callback and a signed state", async () => {
  const { auth } = await install(makeEnv());
  assert.equal(auth.origin + auth.pathname, `https://${SHOP}/admin/oauth/authorize`);
  assert.equal(auth.searchParams.get("client_id"), "client-id-blocks");
  assert.equal(auth.searchParams.get("redirect_uri"), `${ORIGIN}/callback/${APP}`);
  assert.match(auth.searchParams.get("state"), /^[A-Za-z0-9_-]+\.[0-9a-f]{64}$/);
  assert.equal(auth.searchParams.get("scope"), null);  // our copies ask for no store data
});

test("start refuses a bad hmac, another store, an old request and an unknown app", async () => {
  const env = makeEnv();
  assert.equal((await get(env, `/start/${APP}?${signQuery({ shop: SHOP, timestamp: ts() }, "wrong-secret")}`)).status, 403);
  assert.equal((await get(env, `/start/${APP}?${signQuery({ shop: "other-store.myshopify.com", timestamp: ts() })}`)).status, 403);
  assert.equal((await get(env, `/start/${APP}?${signQuery({ shop: SHOP, timestamp: "1000" })}`)).status, 400);
  assert.equal((await get(env, `/start/nope?${signQuery({ shop: SHOP, timestamp: ts() })}`)).status, 404);
  assert.equal((await get(env, `/start/${APP}?${signQuery({ shop: "evil.myshopify.com.attacker.io", timestamp: ts() })}`)).status, 400);
  assert.equal(shopify.calls.length, 0);  // nothing was sent to Shopify
});

test("callback exchanges the code (expiring=1), keeps the store key encrypted and switches the licence on", async () => {
  const env = makeEnv();
  const { cb } = await install(env);
  assert.equal(cb.status, 200);
  assert.match(await cb.text(), /is connected/);
  assert.equal(shopify.licence, "active");
  const tokenCall = shopify.calls.find((c) => c.url.endsWith("/admin/oauth/access_token"));
  assert.equal(new URLSearchParams(tokenCall.body).get("expiring"), "1");
  const stored = await env.VAULT.get(`token:${APP}`);
  assert.ok(stored && !stored.includes("shprt_") && !stored.includes("shpat_"));  // ciphertext only
  const record = JSON.parse(stored);
  assert.equal(await open(env, record.box, `${APP}|${SHOP}`), "shprt_refresh_1");
  const rows = env.VAULT.keys("audit:").map((k) => env.VAULT.data.get(k));
  assert.equal(rows.length, 1);
  assert.ok(!rows[0].includes("shprt_") && !rows[0].includes("shpat_") && !rows[0].includes(SECRET));
  assert.equal(JSON.parse(rows[0]).after, "active");
});

test("a stored key cannot be opened for another app or store (the ciphertext is bound to both)", async () => {
  const env = makeEnv();
  const box = await seal(env, "secret-refresh", `${APP}|${SHOP}`);
  await assert.rejects(open(env, box, `${APP}|other-store.myshopify.com`));
});

test("the state is single-use, signed and bound to the app and store", async () => {
  const env = makeEnv();
  const { state } = await install(env);
  const again = await get(env, `/callback/${APP}?${signQuery({ code: "the-code", shop: SHOP, state, timestamp: ts() })}`);
  assert.equal(again.status, 403);
  const tampered = state.slice(0, -1) + (state.endsWith("0") ? "1" : "0");
  assert.equal((await get(env, `/callback/${APP}?${signQuery({ code: "the-code", shop: SHOP, state: tampered, timestamp: ts() })}`)).status, 403);
});

test("the kill switch needs a signature, a fresh timestamp and an approver; it refreshes, rotates and reads back", async () => {
  const env = makeEnv();
  await install(env);
  const body = { app: APP, state: "inactive", approved_by: "Harsh", reason: "unpaid invoice", ts: Math.floor(Date.now() / 1000) };
  assert.equal((await worker.fetch(signed(body, "wrong-key"), env)).status, 401);
  assert.equal((await worker.fetch(signed({ ...body, ts: 1000 }), env)).status, 400);
  assert.equal((await worker.fetch(signed({ ...body, approved_by: " " }), env)).status, 400);
  const res = await worker.fetch(signed(body), env);
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { app: APP, shop: SHOP, before: "active", after: "inactive", verified: true });
  assert.equal(shopify.licence, "inactive");
  const record = JSON.parse(await env.VAULT.get(`token:${APP}`));
  assert.equal(await open(env, record.box, `${APP}|${SHOP}`), "shprt_refresh_2");  // the NEW refresh token is kept
  const status = await worker.fetch(signed({ app: APP, state: "status", ts: Math.floor(Date.now() / 1000) }), env);
  assert.deepEqual(await status.json(), { app: APP, shop: SHOP, licence: "inactive", app_handle: "dtj-blocks-client" });
  const rows = env.VAULT.keys("audit:").map((k) => JSON.parse(env.VAULT.data.get(k)));
  assert.ok(rows.some((r) => r.approved_by === "Harsh" && r.after === "inactive" && r.reason === "unpaid invoice"));
});

test("uninstall deletes the store key only for a genuine webhook from that store", async () => {
  const env = makeEnv();
  await install(env);
  const raw = JSON.stringify({ id: 1 });
  const sig = createHmac("sha256", SECRET).update(raw).digest("base64");
  const hook = (h, shop = SHOP) => new Request(`${ORIGIN}/webhooks/${APP}`, { method: "POST", body: raw,
    headers: { "X-Shopify-Hmac-Sha256": h, "X-Shopify-Topic": "app/uninstalled", "X-Shopify-Shop-Domain": shop } });
  assert.equal((await worker.fetch(hook("bad"), env)).status, 401);
  assert.equal((await worker.fetch(hook(sig, "other-store.myshopify.com"), env)).status, 403);
  assert.ok(await env.VAULT.get(`token:${APP}`));
  assert.equal((await worker.fetch(hook(sig), env)).status, 200);
  assert.equal(await env.VAULT.get(`token:${APP}`), null);
});

test("the scheduled refresh keeps keys alive and alerts without secrets when one fails", async () => {
  const alerts = [];
  const env = makeEnv({ ALERT_URL: "https://n8n.example/webhook/alert" });
  await install(env);
  assert.deepEqual((await refreshAll(env)).map((r) => r.result), ["refreshed"]);
  shopify.refresh = "a-token-shopify-no-longer-knows";  // simulate a broken key
  const base = shopify.fetch;
  globalThis.fetch = async (url, init) => (String(url).startsWith("https://n8n.example") ? (alerts.push(init.body), new Response("ok")) : base(url, init));
  assert.deepEqual((await refreshAll(env)).map((r) => r.result), ["failed"]);
  assert.equal(alerts.length, 1);
  assert.ok(!alerts[0].includes(SECRET) && !alerts[0].includes("shprt_"));
});

test("Shopify calls retry 429 and 5xx (max 3) but not 4xx", async () => {
  shopify.failNext = [503, 429];
  const res = await call(`https://${SHOP}/admin/api/x/graphql.json`, { method: "POST", headers: { "X-Shopify-Access-Token": "x" }, body: "{}" });
  assert.equal(res.status, 401);  // reached the stand-in after two retries (it then refuses the fake token)
  shopify.failNext = [503, 503, 503];
  assert.equal((await call(`https://${SHOP}/x`, {})).status, 503);  // gives up after 3 tries
  shopify.failNext = [400];
  assert.equal((await call(`https://${SHOP}/x`, {})).status, 400);
  assert.equal(shopify.calls.length, 7);  // 3 (two retries, then an answer) + 3 (gives up) + 1 (a 400 is final)
});

test("errors never echo a secret, and unknown routes are 404", async () => {
  const env = makeEnv();
  const res = await get(env, `/start/${APP}?${signQuery({ shop: SHOP, timestamp: ts() }, "wrong")}`);
  const text = await res.text();
  assert.ok(!text.includes(SECRET) && !text.includes(env.VAULT_KEY));
  assert.equal((await get(env, "/anything")).status, 404);
  assert.deepEqual(await (await get(env, "/health")).json(), { ok: true, apps: 1 });
});
