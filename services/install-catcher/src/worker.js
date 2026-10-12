// DTJ install catcher (Cloudflare Worker). Design: docs/install-catcher-design.md (approved by Harsh, 9 Oct 2026).
//
// A client store installs its own copies of our three apps (custom distribution). Shopify opens /start/<app>; we run the
// authorization code grant, keep the store key (an expiring offline token pair) encrypted, and switch the licence metafield
// dtj.licence on. Later Harsh's kill switch (n8n) asks /licence to switch it off or on. A store key never leaves this Worker.
//
// Configuration (wrangler.toml / Cloudflare dashboard):
//   vars.APPS           JSON {"<app key>": {"client_id": "...", "shop": "<store>.myshopify.com", "label": "DTJ Blocks - X"}}   (not secret)
//   secret SECRET_<APP KEY IN CAPITALS>   each app copy's client secret (app key: letters, digits, dashes -> underscores)
//   secret VAULT_KEY    32 random bytes, base64: encrypts the stored tokens (AES-GCM) and signs the OAuth state
//   secret CONTROL_KEY  shared key that signs /licence requests (HMAC-SHA256, hex): tools/licence_call.py
//   secret BOT_KEY      optional, 32+ characters: the Telegram bot in n8n sends it as X-DTJ-Bot-Key (see licenceCaller)
//   secret ALERT_URL    optional: where to POST a short alert when the scheduled refresh fails (no secrets in it)
//   kv     VAULT        token records, used-state marks, audit rows
// Facts (shopify.dev, 9 Oct 2026): hmac = HMAC-SHA256 hex of the sorted query without hmac, keyed with the client secret; the token
// request is form-encoded with expiring=1; a refresh (grant_type=refresh_token) returns a NEW access token AND a NEW refresh token.

export const API_VERSION = "2026-07";
const SHOP_RE = /^[a-z0-9][a-z0-9-]*\.myshopify\.com$/;
const APP_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const FRESH_SECONDS = 300;
const STATE_SECONDS = 600;
const READ = 'query { currentAppInstallation { id app { handle } licence: metafield(namespace: "dtj", key: "licence") { value } } }';
const WRITE = `mutation SetLicence($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) { metafields { id key value } userErrors { field message code } }
}`;
const STATES = new Set(["active", "inactive"]);

class Refuse extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

// ------------------------------------------------------------------------------------------------ small helpers
const enc = new TextEncoder();
const b64 = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes)));
const unb64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const b64url = (bytes) => b64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const unb64url = (s) => unb64(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
const hex = (bytes) => [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
const now = () => Math.floor(Date.now() / 1000);

export function sameText(a, b) {  // constant-time comparison of two strings
  a = String(a ?? ""); b = String(b ?? "");
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  return diff === 0;
}

async function hmacKey(secret) {
  const raw = typeof secret === "string" ? enc.encode(secret) : secret;
  return crypto.subtle.importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
}
export async function hmacHex(secret, message) {
  return hex(await crypto.subtle.sign("HMAC", await hmacKey(secret), enc.encode(message)));
}
async function hmacB64(secret, bytes) {
  return b64(await crypto.subtle.sign("HMAC", await hmacKey(secret), bytes));
}

export function appKeyEnv(app) { return "SECRET_" + app.toUpperCase().replace(/[^A-Z0-9]/g, "_"); }

function apps(env) {
  try { return JSON.parse(env.APPS || "{}"); } catch { throw new Refuse(500, "APPS is not valid JSON"); }
}
function appConfig(env, app) {
  if (!APP_RE.test(app || "")) throw new Refuse(404, "unknown app");
  const cfg = apps(env)[app];
  if (!cfg) throw new Refuse(404, "unknown app");
  if (!SHOP_RE.test(cfg.shop || "") || !cfg.client_id) throw new Refuse(500, `app ${app} is misconfigured`);
  const secret = env[appKeyEnv(app)];
  if (!secret) throw new Refuse(500, `the secret for ${app} is not set`);
  return { ...cfg, app, secret };
}

// Shopify's query hmac: drop hmac (and the legacy signature), sort the rest by name, join name=value with &, HMAC-SHA256 hex.
export async function shopifyQueryHmacOk(searchParams, secret) {
  const given = searchParams.get("hmac");
  if (!given) return false;
  const pairs = [...searchParams.entries()].filter(([k]) => k !== "hmac" && k !== "signature").sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  const message = pairs.map(([k, v]) => `${k}=${v}`).join("&");
  return sameText(await hmacHex(secret, message), given);
}

function checkShopRequest(url, cfg) {
  const shop = url.searchParams.get("shop");
  if (!SHOP_RE.test(shop || "")) throw new Refuse(400, "bad shop");
  if (shop !== cfg.shop) throw new Refuse(403, "this app copy belongs to another store");
  const ts = Number(url.searchParams.get("timestamp"));
  if (!Number.isFinite(ts) || Math.abs(now() - ts) > FRESH_SECONDS) throw new Refuse(400, "the request is too old");
  return shop;
}

// ------------------------------------------------------------------------------------------------ the vault (AES-GCM)
async function vaultKey(env) {
  const raw = unb64(env.VAULT_KEY || "");
  if (raw.length !== 32) throw new Refuse(500, "VAULT_KEY must be 32 bytes, base64");
  return raw;
}
async function aesKey(env) {
  return crypto.subtle.importKey("raw", await vaultKey(env), "AES-GCM", false, ["encrypt", "decrypt"]);
}
export async function seal(env, plaintext, aad) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv, additionalData: enc.encode(aad) }, await aesKey(env), enc.encode(plaintext));
  return { iv: b64(iv), ct: b64(ct) };
}
export async function open(env, box, aad) {
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64(box.iv), additionalData: enc.encode(aad) }, await aesKey(env), unb64(box.ct));
  return new TextDecoder().decode(pt);
}

// signed, short-lived OAuth state: payload.signature (the signature uses a key derived from VAULT_KEY, never the raw key)
async function stateKey(env) {
  return crypto.subtle.sign("HMAC", await hmacKey(await vaultKey(env)), enc.encode("dtj-oauth-state"));
}
export async function makeState(env, app, shop) {
  const payload = b64url(enc.encode(JSON.stringify({ app, shop, exp: now() + STATE_SECONDS, n: b64url(crypto.getRandomValues(new Uint8Array(16))) })));
  return `${payload}.${await hmacHex(await stateKey(env), payload)}`;
}
export async function readState(env, state, app, shop) {
  const [payload, sig] = String(state || "").split(".");
  if (!payload || !sig || !sameText(await hmacHex(await stateKey(env), payload), sig)) throw new Refuse(403, "bad state");
  const data = JSON.parse(new TextDecoder().decode(unb64url(payload)));
  if (data.app !== app || data.shop !== shop) throw new Refuse(403, "state is for another app or store");
  if (data.exp < now()) throw new Refuse(403, "state expired: start the install again");
  if (await env.VAULT.get(`used:${data.n}`)) throw new Refuse(403, "state already used");
  await env.VAULT.put(`used:${data.n}`, "1", { expirationTtl: STATE_SECONDS * 2 });
  return data;
}

// ------------------------------------------------------------------------------------------------ Shopify calls
export async function call(url, init, tries = 3) {  // retries 429/5xx with backoff (max 3); 4xx is final
  for (let attempt = 1; ; attempt++) {
    let res;
    try {
      res = await fetch(url, init);
    } catch (err) {
      if (attempt >= tries) throw new Refuse(502, "Shopify did not answer");
      await new Promise((r) => setTimeout(r, 300 * 2 ** attempt));
      continue;
    }
    if ((res.status === 429 || res.status >= 500) && attempt < tries) {
      const wait = Number(res.headers.get("Retry-After")) * 1000 || 300 * 2 ** attempt;
      await new Promise((r) => setTimeout(r, Math.min(wait, 5000)));
      continue;
    }
    return res;
  }
}

async function tokenRequest(shop, fields) {
  const res = await call(`https://${shop}/admin/oauth/access_token`, {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
    body: new URLSearchParams(fields).toString(),
  });
  const body = await res.json().catch(() => ({}));
  if (res.status !== 200 || !body.access_token || !body.refresh_token) {
    throw new Refuse(502, `Shopify refused the token request (HTTP ${res.status}${body.error ? ": " + body.error : ""})`);
  }
  return body;
}

async function graphql(shop, accessToken, query, variables) {
  if (/^\s*mutation/.test(query) && !/^\s*mutation SetLicence\b/.test(query)) throw new Refuse(500, "only the licence mutation may be sent");
  const res = await call(`https://${shop}/admin/api/${API_VERSION}/graphql.json`, {
    method: "POST", headers: { "Content-Type": "application/json", "X-Shopify-Access-Token": accessToken },
    body: JSON.stringify({ query, variables: variables || {} }),
  });
  const body = await res.json().catch(() => ({}));
  if (res.status !== 200 || body.errors) throw new Refuse(502, `Shopify GraphQL failed (HTTP ${res.status})`);
  return body.data;
}

export async function readLicence(shop, accessToken) {
  const inst = (await graphql(shop, accessToken, READ)).currentAppInstallation;
  return { install_id: inst.id, app_handle: inst.app?.handle, licence: inst.licence?.value ?? null };
}

export async function writeLicence(shop, accessToken, value) {
  if (!STATES.has(value)) throw new Refuse(400, "state must be active or inactive");
  const before = await readLicence(shop, accessToken);
  const data = await graphql(shop, accessToken, WRITE, { metafields: [{ ownerId: before.install_id, namespace: "dtj", key: "licence", type: "single_line_text_field", value }] });
  if (data.metafieldsSet.userErrors?.length) throw new Refuse(502, `Shopify refused the licence change: ${data.metafieldsSet.userErrors[0].message}`);
  const after = await readLicence(shop, accessToken);  // read back: never report a change that did not land
  return { before: before.licence, after: after.licence, verified: after.licence === value };
}

// ------------------------------------------------------------------------------------------------ token records
async function saveTokens(env, cfg, tokens) {
  const aad = `${cfg.app}|${cfg.shop}`;
  const record = {
    shop: cfg.shop, box: await seal(env, tokens.refresh_token, aad), scope: tokens.scope ?? "",
    refresh_expires_at: now() + Number(tokens.refresh_token_expires_in || 0), updated_at: new Date().toISOString(),
  };
  await env.VAULT.put(`token:${cfg.app}`, JSON.stringify(record));
}

// a fresh access token: refresh with the stored refresh token and store the NEW pair before using it (Shopify rotates both)
export async function freshAccess(env, cfg) {
  const raw = await env.VAULT.get(`token:${cfg.app}`);
  if (!raw) throw new Refuse(404, `no store key for ${cfg.app}: the store has not installed it (or uninstalled it)`);
  const record = JSON.parse(raw);
  if (record.shop !== cfg.shop) throw new Refuse(500, "stored key belongs to another store");
  const refresh = await open(env, record.box, `${cfg.app}|${cfg.shop}`);
  const tokens = await tokenRequest(cfg.shop, { client_id: cfg.client_id, client_secret: cfg.secret, grant_type: "refresh_token", refresh_token: refresh });
  await saveTokens(env, cfg, tokens);
  return tokens.access_token;
}

export async function audit(env, row) {
  const ts = new Date().toISOString();
  const clean = Object.fromEntries(Object.entries(row).filter(([k]) => !/token|secret|code|hmac|signature/i.test(k)));
  await env.VAULT.put(`audit:${ts}:${row.app || "-"}:${b64url(crypto.getRandomValues(new Uint8Array(4)))}`, JSON.stringify({ ts, ...clean }));
}

// ------------------------------------------------------------------------------------------------ routes
async function start(url, env, app) {
  const cfg = appConfig(env, app);
  if (!(await shopifyQueryHmacOk(url.searchParams, cfg.secret))) throw new Refuse(403, "bad hmac");
  const shop = checkShopRequest(url, cfg);
  const auth = new URL(`https://${shop}/admin/oauth/authorize`);
  auth.searchParams.set("client_id", cfg.client_id);
  auth.searchParams.set("redirect_uri", `${url.origin}/callback/${app}`);
  auth.searchParams.set("state", await makeState(env, app, shop));
  return Response.redirect(auth.toString(), 302);
}

async function callback(url, env, app) {
  const cfg = appConfig(env, app);
  if (!(await shopifyQueryHmacOk(url.searchParams, cfg.secret))) throw new Refuse(403, "bad hmac");
  const shop = checkShopRequest(url, cfg);
  await readState(env, url.searchParams.get("state"), app, shop);
  const code = url.searchParams.get("code");
  if (!code) throw new Refuse(400, "no code");
  const tokens = await tokenRequest(shop, { client_id: cfg.client_id, client_secret: cfg.secret, code, expiring: "1" });
  await saveTokens(env, cfg, tokens);
  const change = await writeLicence(shop, tokens.access_token, "active");
  await audit(env, { app, shop, action: "install: store key saved, licence on", result: change.verified ? "success" : "failed", ...change, scope: tokens.scope ?? "" });
  if (!change.verified) throw new Refuse(502, "the licence did not switch on; DTJ has been told");
  return html(200, `${cfg.label || "DTJ"} is connected`, "DTJ blocks are now switched on for this store. You can close this tab.");
}

async function webhook(request, env, app) {
  const cfg = appConfig(env, app);
  const raw = new Uint8Array(await request.arrayBuffer());
  if (!sameText(await hmacB64(cfg.secret, raw), request.headers.get("X-Shopify-Hmac-Sha256"))) throw new Refuse(401, "bad webhook hmac");
  const shop = request.headers.get("X-Shopify-Shop-Domain");
  if (shop !== cfg.shop) throw new Refuse(403, "webhook from another store");
  const topic = request.headers.get("X-Shopify-Topic");
  if (topic === "app/uninstalled") {
    await env.VAULT.delete(`token:${app}`);
    await audit(env, { app, shop, action: "uninstalled: store key deleted", result: "success" });
  }
  return new Response("ok");
}

// Who may call /licence: a request signed with CONTROL_KEY (licence_call.py, HMAC of the exact body), or the Telegram bot in n8n,
// which cannot sign (n8n Code steps have no crypto) and sends BOT_KEY in a header from an encrypted n8n credential instead. BOT_KEY
// is a separate secret so it can be revoked alone (Harsh, 12 Oct 2026); unset or short, the bot path is off.
export async function licenceCaller(request, env, raw) {
  const sig = request.headers.get("X-DTJ-Signature");
  if (sig && env.CONTROL_KEY && sameText(await hmacHex(env.CONTROL_KEY, raw), sig)) return "signed request";
  const botKey = request.headers.get("X-DTJ-Bot-Key");
  if (botKey && String(env.BOT_KEY || "").length >= 32 && sameText(botKey, env.BOT_KEY)) return "telegram bot";
  throw new Refuse(401, "bad signature");
}

async function licence(request, env) {
  const raw = await request.text();
  const via = await licenceCaller(request, env, raw);
  let body;
  try { body = JSON.parse(raw); } catch { throw new Refuse(400, "body is not JSON"); }
  if (!Number.isFinite(body.ts) || Math.abs(now() - body.ts) > FRESH_SECONDS) throw new Refuse(400, "the request is too old");
  const cfg = appConfig(env, body.app);
  if (body.state === "status") {
    const access = await freshAccess(env, cfg);
    const cur = await readLicence(cfg.shop, access);
    return json(200, { app: cfg.app, shop: cfg.shop, licence: cur.licence, app_handle: cur.app_handle });  // the handle names this copy's blocks in a theme
  }
  if (!STATES.has(body.state)) throw new Refuse(400, "state must be active, inactive or status");
  if (!String(body.approved_by || "").trim()) throw new Refuse(400, "approved_by is required for a licence change");
  try {
    const access = await freshAccess(env, cfg);
    const change = await writeLicence(cfg.shop, access, body.state);
    await audit(env, { app: cfg.app, shop: cfg.shop, action: `licence ${body.state}`, result: change.verified ? "success" : "failed", approved_by: body.approved_by, reason: body.reason || "", via, ...change });
    return json(change.verified ? 200 : 502, { app: cfg.app, shop: cfg.shop, ...change });
  } catch (err) {
    await audit(env, { app: cfg.app, shop: cfg.shop, action: `licence ${body.state}`, result: "failed", approved_by: body.approved_by, via, error: String(err.message || err) });
    throw err;
  }
}

export async function refreshAll(env) {
  const out = [];
  for (const [app] of Object.entries(apps(env))) {
    try {
      const cfg = appConfig(env, app);
      if (!(await env.VAULT.get(`token:${app}`))) { out.push({ app, result: "no key yet" }); continue; }
      await freshAccess(env, cfg);
      out.push({ app, result: "refreshed" });
    } catch (err) {
      out.push({ app, result: "failed", error: String(err.message || err) });
    }
  }
  await audit(env, { action: "scheduled refresh", result: out.some((r) => r.result === "failed") ? "failed" : "success", apps: out });
  const failed = out.filter((r) => r.result === "failed");
  if (failed.length && env.ALERT_URL) {
    await fetch(env.ALERT_URL, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: "dtj-install-catcher", problem: "store key refresh failed", apps: failed }) }).catch(() => {});
  }
  return out;
}

const json = (status, data) => new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const html = (status, title, text) => new Response(
  `<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title>` +
  `<body style="font:16px/1.5 system-ui,sans-serif;max-width:560px;margin:15vh auto;padding:0 20px"><h1 style="font-size:22px">${esc(title)}</h1><p>${esc(text)}</p></body>`,
  { status, headers: { "Content-Type": "text/html; charset=utf-8" } });

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const [, route, app] = url.pathname.split("/");
    try {
      if (request.method === "GET" && route === "start") return await start(url, env, app);
      if (request.method === "GET" && route === "callback") return await callback(url, env, app);
      if (request.method === "POST" && route === "webhooks") return await webhook(request, env, app);
      if (request.method === "POST" && route === "licence") return await licence(request, env);
      if (request.method === "GET" && route === "health") return json(200, { ok: true, apps: Object.keys(apps(env)).length });
      return json(404, { error: "not found" });
    } catch (err) {
      const status = err instanceof Refuse ? err.status : 500;
      const message = err instanceof Refuse ? err.message : "unexpected error";
      if (route === "start" || route === "callback") return html(status, "DTJ could not connect", `${message}. Please contact DTJ.`);
      return json(status, { error: message });
    }
  },
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(refreshAll(env));
  },
};
