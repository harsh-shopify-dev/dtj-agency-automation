// n8n Code node "Request for Claude Code: Reel" in "Reel Factory: New Reel" (mode: Run Once for All Items).
// The run pauses at the Wait node after this one. On DTJ's VPS, n8n/store-factory/worker.py finds it, asks in the reel bot
// "tap Start if you are watching" and then runs Claude Code with `instructions` (Harsh, 25 Oct 2026: "create the full n8n ai
// workflow and use claude on VPS"). A person watches and approves in Telegram (plan, pictures, final reel); the reel watcher
// (skill dtj-reel-watcher, tools/vps/watcher.sh) judges every step before the person is asked. No API (rule 9: attended).
const row = $input.first().json;
if (!row || !row.id) throw new Error('No reel job row (dtj_reel_jobs id) reached this step');
const resumeUrl = $execution.resumeUrl;
const slug = String(row.product_name || 'reel').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'reel';
const folder = 'n8n-' + row.id + '-' + slug;
const ROOT = '/home/ai/dtj-agency-automation';
const J = ROOT + '/.work/reels/' + folder;
const RJ = 'python n8n/reel-factory/reel_job.py';
const JOB = 'r' + row.id;
const list = (s) => String(s || '').split('\n').filter(Boolean);
const type = row.reel_type === 'remake' ? 'remake' : 'ugc';
const request = {
  job_id: row.id, reel_type: type, product_name: row.product_name, brand_name: row.brand_name || '', audience: row.audience || '',
  product_images: list(row.product_images), reference_reels: list(row.reference_reels), language: row.language, music: row.music || '',
  facts: row.facts || '', notes: row.notes || '', requested_by: row.requested_by || '', telegram_chat_id: row.telegram_chat_id || '',
};
const langName = { en: 'English', hi: 'Hindi', hinglish: 'Hinglish', gu: 'Gujarati', none: 'none (music only)' }[row.language] || row.language;
const chat = row.telegram_chat_id || '';
const gate = (g, n) => [
  `   WATCHER: bash tools/vps/watcher.sh ${g} ${J} <round>   (fresh Claude + Codex judges; writes ${J}/watch/${g}.verdict.json).`,
  `   verdict "block" = fix every blocking issue yourself and run the watcher again (round +1), at most 2 extra rounds; then ask:`,
  `   ${RJ} ${n} --job ${JOB} --watch ${J}/watch/${g}.verdict.json --round <round> ...   (exit 3 = waiting: end your turn with`,
  `   DTJ_WAIT: <that exact command>). {"ok": true} = go on; {"ok": false, "note"} = make those changes, then the watcher and this ask again (round +1).`,
];

const common = [
  'DTJ REEL FACTORY - ' + (type === 'remake'
    ? 'REMAKE ONE REFERENCE EDIT shot for shot for this product (music only, no voiceover).'
    : 'make one finished 9:16 UGC script reel for this product, copying the winning reference reel(s) closely.'),
  'You are the AI step on DTJ\'s VPS (worker.py started you; a person watches in the reel bot). Everything you need is below and in the repo.',
  '',
  'JOB',
  '- Row ' + row.id + ' in dtj_reel_jobs | type: ' + type + ' | asked by: ' + (row.requested_by || '?') + ' | Telegram chat: ' + (chat || 'none (admin chat)'),
  '- Product: ' + row.product_name + (row.brand_name ? ' (' + row.brand_name + ')' : '') + ' | audience: ' + (row.audience || 'not given: ask in plan text'),
  '- Language: ' + langName + ' | reference reels: ' + list(row.reference_reels).join(' ') + ' | product pictures: ' + list(row.product_images).length,
  '- Music: ' + (row.music || (type === 'remake' ? 'the reference reel\'s own soundtrack (extract it), unless a person says otherwise' : 'none given: no music bed')),
  '- Approved facts (the ONLY claims): ' + (String(row.facts || '').replace(/\s+/g, ' ').slice(0, 1500) || '(none: no claims at all)'),
  '- Notes: ' + (row.notes || '(none)'),
  '- Job folder: ' + J + '   (use full paths; reel code ONLY through bash tools/vps/reel.sh; pictures through bash tools/vps/codex_image.sh;',
  '  Google Flow in the reel Chrome through the Playwright MCP tools (mcp__playwright__*); downloads through bash tools/vps/reel.sh remake fetch|reference)',
  '',
  'START',
  '0. Read CLAUDE.md. Load the skills dtj-ugc-reel and dtj-reel-watcher. Save `request` from this node as ' + J + '/request.in.json.',
  `   ${RJ} start --job ${JOB} --chat "${chat}" --title "Reel: ${String(row.product_name).replace(/"/g, '')} (${type})"`,
  `   Move the bar at every step: ${RJ} step --job ${JOB} --stage <refs|plan|pictures|clips|edit|final> --done <n> --total <m>`,
  `   Product pictures: https links -> bash tools/vps/reel.sh remake fetch <link> ${J}/inputs/pack<N>.png (a product PAGE: read it with WebFetch, take its main pack image link);`,
  `   tg:<id> -> ${RJ} photos --job ${JOB} --ids <id,...> --out ${J}/inputs`,
  '   If Flow shows a sign-in or a human check: ' + RJ + ' person --job ' + JOB + ' --what "sign in to Google Flow in the VPS remote view (ssh -L 6080:localhost:6080 ...)"; never type a password.',
];

const remake = [
  '',
  'REMAKE (follow .claude/skills/dtj-ugc-reel/references/remake-a-reference-edit.md step by step; it wins over this summary)',
  `1. bash tools/vps/reel.sh remake reference <the reference link> ${J}/inputs/reference.mp4   (Instagram = Apify, capped). No music given:`,
  `   ffmpeg -y -v error -i ${J}/inputs/reference.mp4 -vn -c:a libmp3lame -q:a 2 ${J}/music/reference.mp3`,
  `2. Cut list: ffmpeg scene detection (select='gt(scene,0.12)'), plan.md + cut.json; anchors; bash tools/vps/reel.sh remake measure_motion ${J}/inputs/reference.mp4 ${J}/cut.json <anchors> ${J}/refs/ref_motion.json`,
  `3. One frame per shot; LOOK for another brand's marks; bash tools/vps/reel.sh remake clean_brand ${J}/refs/clean <frames> --box ...; marks templates:`,
  `   bash tools/vps/reel.sh watch marks --job ${J} --from <a raw frame> --box ...`,
  '4. Audience: if the request names one, check .claude/skills/dtj-reel-watcher/audiences/<slug>.md is 14 days old or newer (else say so in the plan).',
  '5. G1 PLAN: write ' + J + '/plan.md (one line per reference shot: time, what, our picture, still or Flow clip, effect) and cut.json.',
  ...gate('g1', 'plan --file ' + J + '/plan.md'),
  '6. Pictures: per shot, Codex with the cleaned frame + the pack: bash tools/vps/codex_image.sh --prompt-file <txt> --out ' + J + '/images/pNN.png --ref <clean frame> --ref <pack>',
  '   (the runbook\'s exact prompt; never a written description). Garbled small packs: bash tools/vps/reel.sh remake fixpack ...',
  ...gate('g2', 'pictures --dir ' + J + '/images'),
  '7. Flow clips (Frames, 9:16, 6 s, x1) ONLY for shots that really move; Playwright MCP: upload with browser_file_upload, prompt, generate, read the',
  '   clip\'s signed video URL on its page, bash tools/vps/reel.sh remake fetch <url> ' + J + '/clips/raw/pNN.mp4; bash tools/vps/reel.sh sparkle <raw> ' + J + '/clips/pNN.mp4',
  '   WATCHER: bash tools/vps/watcher.sh g3 ' + J + ' <round>; a clip it blocks is made again (at most 3 rounds per shot, then a still with edit motion).',
  `8. Edit: cut.json every shot "move": "ref", label "" (no burned-in AI line); bash tools/vps/reel.sh remake recut ${J}/cut.json`,
  ...gate('g4', 'final --file <the final mp4>'),
];

const ugc = [
  '',
  'UGC (follow .claude/skills/dtj-ugc-reel/SKILL.md and references/script-playbook.md)',
  `1. bash tools/vps/reel.sh job new --job ${J} --request ${J}/request.in.json ; bash tools/vps/reel.sh job refs --job ${J} ; LOOK at every sheet.`,
  `2. G1 SCRIPT: write ${J}/script.json; bash tools/vps/reel.sh job lint --job ${J} (exit 0) ; bash tools/vps/reel.sh slop ${J}/script.json`,
  '   Write a plain summary of the script (lines per shot) to ' + J + '/plan.md for the person.',
  ...gate('g1', 'plan --file ' + J + '/plan.md'),
  `3. Pictures (character, hero, start pictures) with Codex (bash tools/vps/codex_image.sh ...) or bash tools/vps/reel.sh job character|images --job ${J} --cdp http://127.0.0.1:9222`,
  ...gate('g2', 'pictures --dir ' + J + '/images'),
  `4. bash tools/vps/reel.sh job clips --job ${J} --cdp http://127.0.0.1:9222 (or Flow by hand in the Playwright MCP); WATCHER g3 per round.`,
  `5. bash tools/vps/reel.sh job edit --job ${J}`,
  ...gate('g4', 'final --file ' + J + '/final/reel_final.mp4'),
];

const end = [
  '',
  'FINISH',
  `9. Write ${J}/result.json: {"reel_status": "reel ready" | "needs a look" | "could not make", "final_path", "job_folder", "duration_s", "lufs",`,
  '   "generations", "credits_used", "note"} ("reel ready" only after the person\'s final Approve). Answer n8n from ' + ROOT + ':',
  '   python n8n/store-factory/reply.py --resume-url "' + resumeUrl + '" --body ' + J + '/result.json',
  `   ${RJ} finish --job ${JOB} --ok --note "<one line>"   (or --stopped)`,
  `10. WATCHER G5 (process): bash tools/vps/watcher.sh g5 ${J} 1 ; send its card: ${RJ} tell --job ${JOB} --text "<the card>".`,
  '    New lessons go to ' + ROOT + '/.work/handoff/<date>-run-<n8n run>.md (the laptop merges them into the runbook\'s lessons log).',
  '',
  'RULES',
  '- Never invent a number, review, result, price, year or claim: only the approved facts. No other brand\'s name or mark anywhere.',
  '- No password, token or key in any file or chat. Nothing is posted anywhere and no ad is started (Tier 2: a person decides).',
  '- Flow credits: only after the pictures Approve; at most 3 rounds per shot.',
];

const lines = [...common, ...(type === 'remake' ? remake : ugc), ...end];
return [{ json: { claude_code_stage: 'reel', resume_url: resumeUrl, instructions: lines.join('\n'), request, job_folder: J } }];
