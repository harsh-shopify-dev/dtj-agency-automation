// n8n Code node "Claude Code Reply: Reel" in "Reel Factory: New Reel" (mode: Run Once for All Items).
// Reads what Claude Code posted to the Wait node (a timeout resumes with no body) and keeps only well-formed values: the same rules as
// n8n/store-factory/reply.py (stage "reel"), which refuses a malformed answer before sending it.
const posted = $input.first().json.body;
const b = posted && typeof posted === 'object' && !Array.isArray(posted) ? posted : {};
const allowed = ['reel ready', 'needs a look', 'could not make'];
let status = allowed.includes(b.reel_status) ? b.reel_status : (Object.keys(b).length ? 'reply not understood' : 'timed out (no reply in 3 days)');
const path = String(b.final_path || '');
const pathOk = /\.mp4$/i.test(path) && !/[\r\n]/.test(path);
if (status === 'reel ready' && !pathOk) status = 'reply not understood (no final file)';
const num = (v, lo, hi) => (typeof v === 'number' && isFinite(v) && v >= lo && v <= hi ? v : null);
return [{ json: {
  row_id: $('Request for Claude Code: Reel').first().json.request.job_id,
  reel_status: status,
  final_path: pathOk ? path.slice(0, 400) : '',
  job_folder: String(b.job_folder || '').slice(0, 400),
  duration_s: num(b.duration_s, 0, 180),
  lufs: num(b.lufs, -60, 0),
  generations: Number.isInteger(b.generations) && b.generations >= 0 ? b.generations : null,
  credits_used: num(b.credits_used, 0, 100000),
  reel_note: String(b.note || '').slice(0, 1000),
} }];
