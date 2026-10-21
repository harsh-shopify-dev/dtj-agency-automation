// n8n Code node "Take the WATFEO Ad Request" in "WATFEO Ads: New Ad" (mode: Run Once for All Items).
// Input: the form ("New WATFEO ad") or another workflow (later: the Telegram bot). Output: { ok, problems, row } for dtj_watfeo_ads.
// The product is fixed (the book "We Are There For Each Other"), so a person only chooses the language, how many ads, and,
// if they want, the angle number from the skill's angle bank (1-58). Everything else comes from the skill watfeo-ugc-ads.
const j = $input.first().json || {};
const pick = (...keys) => { for (const k of keys) { if (j[k] != null && String(j[k]).trim()) return String(j[k]).trim(); } return ''; };
const langs = { english: 'en', en: 'en', hindi: 'hi', hi: 'hi', hinglish: 'hinglish' };
const kinds = { 'full reel': 'reel', reel: 'reel', 'scripts only': 'scripts', scripts: 'scripts', 'prompts only': 'prompts', prompts: 'prompts' };

const language = langs[pick('language', 'Language').toLowerCase()] || '';
const kind = kinds[pick('kind', 'What do you need?').toLowerCase()] || '';
const angleText = pick('angle', 'Angle number (optional, 1-58)');
const angle = angleText ? Number(angleText) : 0;
const count = Number(pick('count', 'How many ads') || '1');
const problems = [];
if (!language) problems.push('language must be English, Hindi or Hinglish');
if (!kind) problems.push('choose: full reel, scripts only or prompts only');
if (angleText && !(Number.isInteger(angle) && angle >= 1 && angle <= 58)) problems.push('the angle must be a number from 1 to 58');
if (!(Number.isInteger(count) && count >= 1 && count <= (kind === 'reel' ? 2 : 5))) {
  problems.push(kind === 'reel' ? 'at most 2 full reels per request' : 'between 1 and 5 per request');
}
const reference = pick('reference', 'Reference reel to copy (optional link)');
if (reference && !/^https:\/\/\S+$/.test(reference) && !/^([A-Za-z]:[\\/]|\/)\S/.test(reference)) problems.push('the reference must be a https link or a path on the laptop');

return [{ json: {
  ok: problems.length === 0,
  problems: problems.join('; '),
  row: {
    submitted_at: new Date().toISOString(),
    status: problems.length ? 'refused' : 'new',
    kind,
    language,
    angle_asked: angle || null,
    count,
    reference,
    notes: pick('notes', 'Notes').slice(0, 2000),
    requested_by: pick('requested_by', 'Your name') || 'form',
    telegram_chat_id: pick('chat_id'),
    raw_json: JSON.stringify(j).slice(0, 8000),
    ad_status: problems.length ? 'refused: ' + problems.join('; ') : 'waiting for Claude Code',
  },
} }];
