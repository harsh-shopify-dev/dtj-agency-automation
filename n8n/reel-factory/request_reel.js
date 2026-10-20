// n8n Code node "Request for Claude Code: Reel" in "Reel Factory: New Reel" (mode: Run Once for All Items).
// The run pauses at the Wait node after this one. A Claude Code session on the reel VPS (logged in to Claude, ChatGPT and Google
// Flow in the reel Chrome) finds this waiting run, reads `instructions` and does everything in it, then answers resume_url.
// Harsh's decision (20 Oct 2026): no API; Claude and ChatGPT run on the VPS, Flow is driven in that browser.
// CLAUDE.md rule 9: a subscription Claude Code session is the AI step only while a person is on duty ("listen" mode).
const row = $input.first().json;
if (!row || !row.id) throw new Error('No reel job row (dtj_reel_jobs id) reached this step');
const resumeUrl = $execution.resumeUrl;
const slug = String(row.product_name || 'reel').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'reel';
const folder = 'n8n-' + row.id + '-' + slug;
const J = '../../.work/reels/' + folder;
const list = (s) => String(s || '').split('\n').filter(Boolean);
const request = {
  job_id: row.id, product_name: row.product_name, brand_name: row.brand_name || '', product_images: list(row.product_images),
  reference_reels: list(row.reference_reels), language: row.language, music: row.music || '', facts: row.facts || '',
  notes: row.notes || '', requested_by: row.requested_by || '',
};
const langName = { en: 'English', hi: 'Hindi', hinglish: 'Hinglish' }[row.language] || row.language;

const lines = [
  'DTJ REEL FACTORY - make one finished 9:16 UGC ad reel for this product, copying the winning reference reel(s) closely.',
  'You are the AI step: a Claude Code session on DTJ\'s reel VPS. Nobody has briefed you; everything you need is below and in the repo.',
  '',
  'JOB',
  '- Job row: id ' + row.id + ' in the n8n data table dtj_reel_jobs | Asked by: ' + (row.requested_by || '?'),
  '- Product: ' + row.product_name + (row.brand_name ? ' (' + row.brand_name + ')' : ''),
  '- Language: ' + langName + ' | Reference reels: ' + list(row.reference_reels).length + ' | Product pictures: ' + list(row.product_images).length,
  '- Music: ' + (row.music ? row.music + ' (must be licensed for paid ads; if unsure, say so in the note)' : 'none given: no music bed'),
  '- Approved facts (the ONLY claims the reel may make): ' + String(row.facts || '').replace(/\s+/g, ' ').slice(0, 1500),
  '- Notes: ' + (row.notes || '(none)'),
  '',
  'DO THIS, IN ORDER (every reel_factory command from services/reel-factory, with the reel Python)',
  '1. Work in the repo (dtj-agency-automation). Read CLAUDE.md. Load the skill dtj-ugc-reel (the runbook) and follow it. Stay on the current git branch; do not commit.',
  '2. Save `request` from this node as ' + J + '/request.in.json, then:',
  '   python -m reel_factory.job new --job ' + J + ' --request ' + J + '/request.in.json',
  '   python -m reel_factory.job refs --job ' + J,
  '   Watch every reference: look at refs/<n>/hook.jpg and every sheet_*.jpg, read breakdown.json (words, cuts, pace).',
  '3. Write ' + J + '/script.json as the skill says (character, shots with exact lines, image and video prompts; product shots say how the product stays). Then:',
  '   python -m reel_factory.job lint --job ' + J + '   (exit 0 needed; it also prints the Flow credits for one round)',
  '4. python -m reel_factory.job character --job ' + J + '   (ChatGPT, fresh chats). LOOK at images/character.png and images/hero.png: a real-person look, no AI-slop set, the exact product readable.',
  '5. python -m reel_factory.job images --job ' + J + '   LOOK at checks/images_sheet.jpg and pick one start picture per shot: python -m reel_factory.job pick --job ' + J + ' --shot s1 --image <file>',
  '6. python -m reel_factory.job clips --job ' + J + '   (2 takes per shot, sparkle removed with LaMa, checked). LOOK at every picked take\'s 4 fps sheet: a drop, float, smear, extra hand or a wrong product = reject; fix that shot\'s video_prompt and run clips --shots <id> again (at most 2 extra rounds per shot).',
  '7. python -m reel_factory.job edit --job ' + J + '   then WATCH final/reel_final.mp4 (a 4 fps sheet) and read the words: captions at the bottom mark, nothing on a face, the product name right.',
  '8. python -m reel_factory.job result --job ' + J + '   and answer this n8n run with it (also when the reel could not be made), from the repo root:',
  '   python n8n/store-factory/reply.py --resume-url "' + resumeUrl + '" --body .work/reels/' + folder + '/result.json',
  '9. Add a dated entry to docs/HANDOFF.md (what was made, where the file is, what needs a look). Tell the person on duty in plain words.',
  '',
  'RULES',
  '- Never invent a number, review, result or claim: only the approved facts above. lint refuses numbers that are not in them.',
  '- The character is made from a written description in a FRESH ChatGPT chat, never from the reference creator\'s face.',
  '- No password, token or key in any file or chat. If Google or ChatGPT asks for a sign-in or a human check, stop and answer n8n with reel_status "could not make" and the note "needs a person: <what>".',
  '- Do not post the reel anywhere and do not start an ad: the reel goes to a person, who decides (Tier 2).',
  '- Flow credits: stop after 3 rounds on one shot and answer "needs a look" with what went wrong.',
];

return [{ json: { claude_code_stage: 'reel', resume_url: resumeUrl, instructions: lines.join('\n'), request, job_folder: '.work/reels/' + folder } }];
