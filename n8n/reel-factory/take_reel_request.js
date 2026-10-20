// n8n Code node "Take the Reel Request" in "Reel Factory: New Reel" (mode: Run Once for All Items).
// Input: the form ("New UGC Reel") or another workflow (later: the Telegram bot's /reel). Output: { ok, problems, row } for dtj_reel_jobs.
// Links only (one per line): pictures and reels must be reachable by the reel worker on the VPS (Drive "anyone with the link",
// the store's CDN, or a path on the VPS). Nothing is invented here: facts are the client's own words, kept as typed.
const j = $input.first().json || {};
const pick = (...keys) => { for (const k of keys) { if (j[k] != null && String(j[k]).trim()) return String(j[k]).trim(); } return ''; };
const lines = (s) => String(s || '').split(/[\r\n]+/).map((x) => x.trim()).filter(Boolean);
const okLink = (s) => /^https:\/\/\S+$/.test(s) || /^([A-Za-z]:[\\/]|\/)\S/.test(s);
const langs = { english: 'en', en: 'en', hindi: 'hi', hi: 'hi', hinglish: 'hinglish' };

const product = pick('product_name', 'Product name');
const images = lines(pick('product_images', 'Product pictures (links, one per line)'));
const refs = lines(pick('reference_reels', 'Winning reference reels (links, one per line)'));
const language = langs[pick('language', 'Language').toLowerCase()] || '';
const music = pick('music', 'Background music (licensed; link)');
const facts = pick('facts', 'Approved facts (only these may be said)');
const problems = [];
if (!product) problems.push('no product name');
if (!images.length) problems.push('no product picture link');
if (!refs.length) problems.push('no reference reel link');
if (!language) problems.push('language must be English, Hindi or Hinglish');
if (!facts) problems.push('no approved facts (the reel may only say what is in them)');
const bad = [...images, ...refs, ...(music ? [music] : [])].filter((x) => !okLink(x));
if (bad.length) problems.push('not a https link or a VPS path: ' + bad.slice(0, 3).join(', '));
if (images.length > 5) problems.push('at most 5 product pictures');
if (refs.length > 5) problems.push('at most 5 reference reels');

return [{ json: {
  ok: problems.length === 0,
  problems: problems.join('; '),
  row: {
    submitted_at: new Date().toISOString(),
    status: problems.length ? 'refused' : 'new',
    product_name: product.slice(0, 200),
    brand_name: pick('brand_name', 'Brand name').slice(0, 200),
    product_images: images.join('\n'),
    reference_reels: refs.join('\n'),
    language,
    music,
    facts: facts.slice(0, 4000),
    notes: pick('notes', 'Notes for the reel').slice(0, 2000),
    requested_by: pick('requested_by', 'Your name') || 'form',
    telegram_chat_id: pick('chat_id'),
    raw_json: JSON.stringify(j).slice(0, 8000),
    reel_status: problems.length ? 'refused: ' + problems.join('; ') : 'waiting for Claude Code',
  },
} }];
