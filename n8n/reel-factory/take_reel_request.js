// n8n Code node "Take the Reel Request" in "Reel Factory: New Reel" (mode: Run Once for All Items).
// Input: the form ("New UGC Reel") or another workflow (the reel bot's /remake and /reel, 25 Oct 2026). Output: { ok, problems, row }
// for dtj_reel_jobs. Links only (one per line): pictures and reels must be reachable by the reel worker on the VPS (Drive "anyone
// with the link", the store's CDN or product page, a path on the VPS, or tg:<file_id> = a photo sent to the reel bot, which
// reel_job.py photos downloads on the VPS). Nothing is invented here: facts are the client's own words, kept as typed.
// Two kinds (Harsh, 25 Oct 2026): "remake" copies ONE reference edit shot for shot (music only: no language, no facts needed);
// "ugc" is a script reel spoken in a language, saying only the approved facts.
const j = $input.first().json || {};
const pick = (...keys) => { for (const k of keys) { if (j[k] != null && String(j[k]).trim()) return String(j[k]).trim(); } return ''; };
const lines = (s) => String(s || '').split(/[\r\n]+/).map((x) => x.trim()).filter(Boolean);
const okLink = (s) => /^https:\/\/\S+$/.test(s) || /^([A-Za-z]:[\\/]|\/)\S/.test(s) || /^tg:[\w-]{10,200}$/.test(s);
const langs = { english: 'en', en: 'en', hindi: 'hi', hi: 'hi', hinglish: 'hinglish', gujarati: 'gu', gu: 'gu' };
const types = { remake: 'remake', 'remake a reference edit': 'remake', ugc: 'ugc', 'ugc script reel': 'ugc' };

const reelType = types[pick('reel_type', 'Reel type').toLowerCase()] || (pick('reel_type', 'Reel type') ? '' : 'ugc');
const product = pick('product_name', 'Product name');
const audience = pick('audience', 'Audience (who it is for)');
const images = lines(pick('product_images', 'Product pictures (links, one per line)'));
const refs = lines(pick('reference_reels', 'Winning reference reels (links, one per line)'));
const language = langs[pick('language', 'Language').toLowerCase()] || (reelType === 'remake' ? 'none' : '');
const music = pick('music', 'Background music (licensed; link)');
const facts = pick('facts', 'Approved facts (only these may be said)');
const problems = [];
if (!reelType) problems.push('reel type must be remake or ugc');
if (!product) problems.push('no product name');
if (!images.length) problems.push('no product picture (a link, a product page or a photo sent to the bot)');
if (!refs.length) problems.push('no reference reel link');
if (reelType === 'remake' && refs.length > 1) problems.push('a remake copies exactly one reference reel');
if (!language) problems.push('language must be English, Hindi, Hinglish or Gujarati');
if (!facts && reelType === 'ugc') problems.push('no approved facts (the reel may only say what is in them)');
const bad = [...images, ...refs, ...(music ? [music] : [])].filter((x) => !okLink(x));
if (bad.length) problems.push('not a https link, a VPS path or a bot photo: ' + bad.slice(0, 3).join(', '));
if (images.length > 8) problems.push('at most 8 product pictures');
if (refs.length > 5) problems.push('at most 5 reference reels');

return [{ json: {
  ok: problems.length === 0,
  problems: problems.join('; '),
  row: {
    submitted_at: new Date().toISOString(),
    status: problems.length ? 'refused' : 'new',
    reel_type: reelType,
    product_name: product.slice(0, 200),
    audience: audience.slice(0, 300),
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
