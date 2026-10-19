// n8n Code node "Check the Report" in "SEO Engine: Weekly Report" (mode: Run Once for All Items).
// The Monday report from GitHub (.github/workflows/seo-weekly.yml, step "Send the report to the bot", n8n/seo-engine/notify_n8n.py).
// CLAUDE.md rule 8: signature first, then the JSON Schema; anything else goes to the dead-letter queue and nothing else runs.
//  1. The signature: the webhook node already refused any request without a valid JWT signed with the n8n credential
//     "DTJ SEO Report Key" (HS256, the same secret as GitHub's N8N_SEO_REPORT_KEY). Here: its claims (issuer, audience, 15 minutes at
//     most) and the SHA-256 of the body's "content" text, which the signature covers, so not one character can change on the way.
//  2. The schema: schemas/seo-weekly-report.schema.json, written out below (n8n's Code step has no schema library); the tests run
//     the same samples through both and expect the same verdict.
// Output: one item, { ok: true, report } or { ok: false, reason, raw } ("Plan the Report" sends the second to the dead-letter table).
const item = $input.first().json || {};
const body = item.body && typeof item.body === 'object' ? item.body : {};
const rawText = (() => { try { return JSON.stringify(item.body === undefined ? null : item.body); } catch (e) { return String(item.body); } })();
const bad = (reason) => [{ json: { ok: false, reason, raw: String(rawText).slice(0, 20000) } }];
const REPO = 'harsh-shopify-dev/dtj-agency-automation';

// ---- SHA-256 of a text's UTF-8 bytes (no crypto module in n8n's Code step) ----
function utf8(s) {
  const out = [];
  for (let i = 0; i < s.length; i++) {
    let c = s.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff && i + 1 < s.length) {
      const d = s.charCodeAt(i + 1);
      if (d >= 0xdc00 && d <= 0xdfff) { c = 0x10000 + ((c - 0xd800) << 10) + (d - 0xdc00); i++; }
    }
    if (c < 0x80) out.push(c);
    else if (c < 0x800) out.push(0xc0 | (c >> 6), 0x80 | (c & 63));
    else if (c < 0x10000) out.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
    else out.push(0xf0 | (c >> 18), 0x80 | ((c >> 12) & 63), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
  }
  return out;
}
function sha256hex(text) {
  const K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01,
    0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f,
    0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70,
    0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
  const H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];
  const bytes = utf8(text);
  const bitLen = bytes.length * 8;
  bytes.push(0x80);
  while (bytes.length % 64 !== 56) bytes.push(0);
  const hi = Math.floor(bitLen / 0x100000000), lo = bitLen >>> 0;
  bytes.push((hi >>> 24) & 255, (hi >>> 16) & 255, (hi >>> 8) & 255, hi & 255, (lo >>> 24) & 255, (lo >>> 16) & 255, (lo >>> 8) & 255, lo & 255);
  const W = new Array(64);
  const rotr = (x, n) => (x >>> n) | (x << (32 - n));
  for (let off = 0; off < bytes.length; off += 64) {
    for (let t = 0; t < 16; t++) {
      W[t] = ((bytes[off + 4 * t] << 24) | (bytes[off + 4 * t + 1] << 16) | (bytes[off + 4 * t + 2] << 8) | bytes[off + 4 * t + 3]) >>> 0;
    }
    for (let t = 16; t < 64; t++) {
      const s0 = rotr(W[t - 15], 7) ^ rotr(W[t - 15], 18) ^ (W[t - 15] >>> 3);
      const s1 = rotr(W[t - 2], 17) ^ rotr(W[t - 2], 19) ^ (W[t - 2] >>> 10);
      W[t] = (W[t - 16] + s0 + W[t - 7] + s1) >>> 0;
    }
    let [a, b, c, d, e, f, g, h] = H;
    for (let t = 0; t < 64; t++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const t1 = (h + S1 + ((e & f) ^ (~e & g)) + K[t] + W[t]) >>> 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const t2 = (S0 + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    H[0] = (H[0] + a) >>> 0; H[1] = (H[1] + b) >>> 0; H[2] = (H[2] + c) >>> 0; H[3] = (H[3] + d) >>> 0;
    H[4] = (H[4] + e) >>> 0; H[5] = (H[5] + f) >>> 0; H[6] = (H[6] + g) >>> 0; H[7] = (H[7] + h) >>> 0;
  }
  return H.map((x) => x.toString(16).padStart(8, '0')).join('');
}

// ---- the signature's claims: from the webhook node (jwtPayload), else read from the header it has already verified ----
function claimsFromHeader() {
  const auth = String((item.headers || {}).authorization || '');
  const m = auth.match(/^Bearer\s+[A-Za-z0-9_-]+\.([A-Za-z0-9_-]+)\.[A-Za-z0-9_-]+$/);
  if (!m) return null;
  try {
    const b64 = m[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(Buffer.from(b64, 'base64').toString('utf8'));
  } catch (e) { return null; }
}
const claims = (item.jwtPayload && typeof item.jwtPayload === 'object') ? item.jwtPayload : claimsFromHeader();
if (!claims) return bad('no signed claims: the request did not carry the JWT the webhook checks');
const now = Math.floor(Date.now() / 1000);
if (claims.iss !== 'dtj-seo-weekly' || claims.aud !== 'dtj-n8n') return bad('the signature was not made for this report (issuer or audience)');
if (typeof claims.exp !== 'number' || typeof claims.iat !== 'number') return bad('the signature has no time on it');
if (claims.exp < now) return bad('the signature has expired (older than its 15 minutes)');
if (claims.iat > now + 120 || claims.exp - claims.iat > 900) return bad('the signature\'s times are not valid');
if (typeof body.content !== 'string' || !body.content) return bad('the body has no "content" text');
if (body.content.length > 200000) return bad('the report is too large (more than 200,000 characters)');
if (Object.keys(body).some((k) => k !== 'content')) return bad('the body has fields other than "content"');
if (sha256hex(body.content) !== String(claims.sha256 || '').toLowerCase()) return bad('the content does not match its signature (SHA-256)');

let r;
try { r = JSON.parse(body.content); } catch (e) { return bad('the content is not valid JSON'); }

// ---- schemas/seo-weekly-report.schema.json ----
const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const isInt = (v) => Number.isInteger(v) && v >= 0;
const str = (v, max, re) => typeof v === 'string' && v.length <= max && (!re || re.test(v));
function only(o, allowed) { return Object.keys(o).every((k) => allowed.includes(k)); }
function check(r) {
  if (!isObj(r)) return 'the report is not an object';
  const top = ['schema', 'repo', 'run_id', 'run_url', 'ref', 'made_at', 'site', 'mode', 'scan', 'batch', 'report_md'];
  for (const k of top.filter((k) => k !== 'mode')) if (!(k in r)) return 'missing ' + k;
  if (!only(r, top)) return 'unknown field at the top: ' + Object.keys(r).filter((k) => !top.includes(k)).join(', ');
  if (r.schema !== 'dtj-seo-weekly/1') return 'schema is not dtj-seo-weekly/1';
  if (!str(r.repo, 200, /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/)) return 'repo is not owner/name';
  if (!str(r.run_id, 20, /^[0-9]{1,20}$/)) return 'run_id is not a run number';
  if (!str(r.run_url, 300, /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/actions\/runs\/[0-9]{1,20}$/)) return 'run_url is not a GitHub run link';
  if (!str(r.ref, 200) || !r.ref) return 'ref is empty';
  if (!str(r.made_at, 40, /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:.]+(Z|[+-][0-9]{2}:[0-9]{2})$/)) return 'made_at is not a date and time';
  if (!str(r.site, 200, /^https:\/\/[^\s]+$/)) return 'site is not an https address';
  if ('mode' in r && !['shadow', 'approve', 'auto'].includes(r.mode)) return 'mode is not shadow, approve or auto';
  const s = r.scan;
  if (!isObj(s)) return 'scan is not an object';
  for (const k of ['pages', 'high', 'medium', 'low', 'complete']) if (!(k in s)) return 'scan: missing ' + k;
  if (!only(s, ['pages', 'high', 'medium', 'low', 'complete', 'warning'])) return 'scan: unknown field';
  if (!['pages', 'high', 'medium', 'low'].every((k) => isInt(s[k]))) return 'scan: counts must be whole numbers';
  if (typeof s.complete !== 'boolean') return 'scan: complete must be true or false';
  if ('warning' in s && !str(s.warning, 2000)) return 'scan: warning too long';
  const b = r.batch;
  if (!isObj(b)) return 'batch is not an object';
  for (const k of ['id', 'counts', 'changes', 'manual', 'notes']) if (!(k in b)) return 'batch: missing ' + k;
  if (!only(b, ['id', 'counts', 'changes', 'manual', 'notes'])) return 'batch: unknown field';
  if (!str(b.id, 40, /^fix-[0-9]{4}-[0-9]{2}-[0-9]{2}$/)) return 'batch: id is not fix-YYYY-MM-DD';
  if (!isObj(b.counts) || !only(b.counts, ['auto', 'blocked', 'manual']) || !['auto', 'blocked', 'manual'].every((k) => isInt(b.counts[k]))) {
    return 'batch: counts must be auto, blocked and manual whole numbers';
  }
  if (!Array.isArray(b.changes) || b.changes.length > 200) return 'batch: changes must be a list of at most 200';
  for (const c of b.changes) {
    if (!isObj(c)) return 'batch: a change is not an object';
    for (const k of ['cid', 'kind', 'url', 'before', 'after', 'how']) if (!(k in c)) return 'batch: a change is missing ' + k;
    if (!only(c, ['cid', 'kind', 'url', 'before', 'after', 'how', 'why'])) return 'batch: a change has an unknown field';
    if (!str(c.cid, 6, /^c[0-9]{3,5}$/)) return 'batch: a change id is not c001 style';
    if (!str(c.kind, 40, /^[a-z_]{1,40}$/)) return 'batch: a change kind is not valid';
    if (!str(c.url, 500) || !c.url) return 'batch: a change has no page';
    if (!(c.before === null || str(c.before, 600))) return 'batch: a change\'s "before" is too long';
    if (!str(c.after, 600)) return 'batch: a change\'s "after" is too long';
    if (!['auto', 'blocked'].includes(c.how)) return 'batch: a change is neither auto nor blocked';
    if ('why' in c && !str(c.why, 600)) return 'batch: a change\'s "why" is too long';
  }
  if (b.changes.filter((c) => c.how === 'auto').length !== b.counts.auto) return 'batch: the auto count does not match the list';
  if (!Array.isArray(b.manual) || b.manual.length > 50 || !b.manual.every((x) => str(x, 600))) return 'batch: manual must be at most 50 short texts';
  if (!Array.isArray(b.notes) || b.notes.length > 50 || !b.notes.every((x) => str(x, 600))) return 'batch: notes must be at most 50 short texts';
  if (!str(r.report_md, 60000) || !r.report_md) return 'report_md is empty or longer than 60,000 characters';
  return '';
}
const problem = check(r);
if (problem) return bad('the report does not match its schema: ' + problem);
if (r.repo !== REPO) return bad('the report is from another repository: ' + r.repo);
if (String(claims.run_id) !== r.run_id || String(claims.batch_id) !== r.batch.id) return bad('the signed run or batch is not the one in the report');
return [{ json: { ok: true, report: r } }];
