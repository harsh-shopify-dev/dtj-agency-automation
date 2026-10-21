// n8n Code node "Request for Claude Code: WATFEO Ad" in "WATFEO Ads: New Ad" (mode: Run Once for All Items).
// Inputs: this job (from "Save WATFEO Ad") and every earlier job (from "Load Earlier Ads"), so the request carries the angles the
// whole team has already used. The run pauses at the Wait node after this one; a Claude Code session with the skill
// watfeo-ugc-ads does the task and answers resume_url. CLAUDE.md rule 9: a subscription session is the AI step only while a
// person is on duty.
const job = $('Save WATFEO Ad').first().json;
if (!job || !job.id) throw new Error('No job row (dtj_watfeo_ads id) reached this step');
const resumeUrl = $execution.resumeUrl;
const earlier = $input.all().map((i) => i.json).filter((r) => r && r.id && r.id !== job.id);
const used = [...new Set(earlier.map((r) => Number(r.angle_used)).filter((n) => Number.isInteger(n) && n > 0))].sort((a, b) => a - b);
const folder = 'watfeo-' + job.id;
const langName = { en: 'English', hi: 'Hindi (casual, spoken)', hinglish: 'Hinglish (casual, spoken)' }[job.language] || job.language;
const what = { reel: 'finished reel(s)', scripts: 'script(s) only, in chat and saved', prompts: 'script(s) + every generation prompt, in chat and saved' }[job.kind];

const lines = [
  'WATFEO AD FACTORY - make ' + job.count + ' ' + what + ' for the book "We Are There For Each Other" by Sagar Chudesara.',
  'You are the AI step: a Claude Code session on a DTJ laptop. Nobody has briefed you; the skill has everything.',
  '',
  'JOB',
  '- Job row: id ' + job.id + ' in the n8n data table dtj_watfeo_ads | Asked by: ' + (job.requested_by || '?'),
  '- Language: ' + langName + ' | Count: ' + job.count,
  '- Angle: ' + (job.angle_asked ? '#' + job.angle_asked + ' (asked for; if it is already used, say so and pick the closest fresh one)' : 'your choice: a fresh one'),
  '- Angles the team already used (count them as used): ' + (used.length ? used.join(', ') : 'none recorded in n8n yet'),
  '- Reference reel: ' + (job.reference || 'none: use the skill\'s ad shapes'),
  '- Notes: ' + (job.notes || '(none)'),
  '',
  'DO THIS, IN ORDER',
  '1. In the dtj-agency-automation repo, read CLAUDE.md, then load the skill watfeo-ugc-ads and follow its steps 1-8. Stay on the current branch; do not commit.',
  '2. Work in .work/watfeo/' + folder + '/ (one sub-folder per ad: script.json, prompts.md, and for reels the clips and finals).',
  '3. Every script must pass: python .claude/skills/watfeo-ugc-ads/scripts/lint_script.py <script.json>',
  job.kind === 'reel'
    ? '4. Produce each reel as the skill says (Flow in the signed-in browser, takes checked at 4 fps, sparkle removed, phone look, captions, -14 LUFS, score 80+).'
    : '4. Give the ' + (job.kind === 'scripts' ? 'scripts' : 'scripts and prompts') + ' in chat as the skill says, and save them in the folder.',
  '5. Write .work/watfeo/' + folder + '/result.json: {"reel_status": "reel ready" | "needs a look" | "could not make", "kind": "' + job.kind + '", "final_path": "<' + (job.kind === 'reel' ? 'the final .mp4' : 'the saved .md file') + '>", "angle": <angle number of the first ad>, "note": "<plain words: what was made, the score, what to look at>"}',
  '6. Answer this n8n run, from the repo root, also when nothing could be made:',
  '   python n8n/store-factory/reply.py --resume-url "' + resumeUrl + '" --body .work/watfeo/' + folder + '/result.json',
  '7. Record the angle(s) in the skill (scripts/angles.py use N --ad ' + folder + '), add a dated line to docs/HANDOFF.md, and tell the person on duty in plain words.',
  '',
  'RULES',
  '- Only what the book says (search it with the skill\'s book_search.py). No invented names, numbers, reviews or personal stories.',
  '- The terrace rescue scene is reserved. One setup per ad. The last clip says Read Now / Shop Now / Abhi padhe.',
  '- A new, real-looking creator every time (the skill\'s creators.md); never the generic AI face.',
  '- No password or token in any file or chat. A sign-in or human check = stop and answer "could not make" with "needs a person: <what>".',
  '- Nothing is posted and no ad is started: a person decides.',
];

return [{ json: { claude_code_stage: 'watfeo_ad', resume_url: resumeUrl, instructions: lines.join('\n'),
  request: { job_id: job.id, kind: job.kind, language: job.language, count: job.count, angle_asked: job.angle_asked || null,
             angles_used: used, reference: job.reference || '', notes: job.notes || '', requested_by: job.requested_by || '' },
  job_folder: '.work/watfeo/' + folder } }];
