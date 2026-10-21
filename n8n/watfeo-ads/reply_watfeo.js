// n8n Code node "Claude Code Reply: WATFEO Ad" in "WATFEO Ads: New Ad" (mode: Run Once for All Items).
// Reads what Claude Code posted to the Wait node (a timeout resumes with no body) and keeps only well-formed values: the same
// rules as n8n/store-factory/reply.py (stage "reel" with "kind"), which refuses a malformed answer before sending it.
const posted = $input.first().json.body;
const b = posted && typeof posted === 'object' && !Array.isArray(posted) ? posted : {};
const allowed = ['reel ready', 'needs a look', 'could not make'];
let status = allowed.includes(b.reel_status) ? b.reel_status : (Object.keys(b).length ? 'reply not understood' : 'timed out (no reply in 3 days)');
const kind = ['reel', 'scripts', 'prompts'].includes(b.kind) ? b.kind : 'reel';
const path = String(b.final_path || '');
const pathOk = (kind === 'reel' ? /\.mp4$/i : /\.(md|json|txt)$/i).test(path) && !/[\r\n]/.test(path);
if (status === 'reel ready' && !pathOk) status = 'reply not understood (no final file)';
const angle = Number.isInteger(b.angle) && b.angle >= 1 && b.angle <= 58 ? b.angle : null;
return [{ json: {
  row_id: $('Request for Claude Code: WATFEO Ad').first().json.request.job_id,
  ad_status: status,
  final_path: pathOk ? path.slice(0, 400) : '',
  angle_used: status === 'reel ready' ? angle : null,
  ad_note: String(b.note || '').slice(0, 1000),
} }];
