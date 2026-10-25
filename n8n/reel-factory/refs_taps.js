// n8n Code node "Match the Taps" in "Reel Factory: Find References" (mode: Run Once for All Items).
// The Keep / Skip buttons under each reference carry "a:ref-<library row id>:keep:<0 Keep | 1 Skip>"; the Telegram bot's
// "Save the Answer" writes every tap into dtj_bot_answers (job ref-<id>, key keep, choice, by, at). Here: the last tap per reference
// from the last two days (older taps were recorded by earlier runs) -> one item per reference for "Record the Choice".
const WINDOW_MS = 2 * 24 * 3600 * 1000;
const since = new Date(Date.now() - WINDOW_MS).toISOString().slice(0, 19);
const last = {};
for (const it of $input.all()) {
  const r = it.json || {};
  const m = String(r.job || '').match(/^ref-(\d{1,12})$/);
  if (!m || String(r.key || '') !== 'keep') continue;
  const at = String(r.at || '').slice(0, 19);
  if (!at || at < since) continue;
  const choice = String(r.choice || '');
  const label = String(r.value || '').trim().toLowerCase();
  const keep = choice === '0' || (choice === '' && label === 'keep') ? 'yes' : choice === '1' || (choice === '' && label === 'skip') ? 'no' : '';
  if (!keep) continue;
  const prev = last[m[1]];
  if (prev && (prev.at > at || (prev.at === at && prev.id > Number(r.id || 0)))) continue;
  last[m[1]] = { at, id: Number(r.id || 0), keep, by: String(r.by || '').trim() || 'someone on the DTJ bot' };
}
return Object.keys(last).map((id) => ({ json: { row_id: Number(id), keep: last[id].keep, kept_by: last[id].by, kept_at: last[id].at + 'Z' } }));
