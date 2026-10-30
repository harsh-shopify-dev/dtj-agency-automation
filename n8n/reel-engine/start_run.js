// n8n Code node "Start run" in "Reel Engine" (mode: Run Once for All Items).
// Takes what "Reel: <Brand>" passed (brand, style, request, language, chat, watcher, requested_by), refuses a run nobody
// watches (CLAUDE.md rule 9), and gives the run its id: r<yyyymmdd-hhmm>-<4 letters> (Asia/Kolkata), one folder on the engine host.
const i = $input.first().json || {};
const clean = (v) => String(v == null ? '' : v).trim();
const brand = clean(i.brand).toLowerCase();
if (!/^[a-z0-9][a-z0-9_-]{0,62}$/.test(brand)) throw new Error('No brand (or not a slug like "branda"): start the reel from "Reel: <Brand>"');
const watcher = clean(i.watcher);
if (!watcher) throw new Error('No watcher: a person must be watching this reel run (who asked in Telegram, or who clicked Run)');
const request = clean(i.request);
if (!request) throw new Error('No request: say what the reel is about (e.g. "Diwali reel, the family shares the pack")');
const style = clean(i.style).toLowerCase() || 'ugc';
const now = new Date(Date.now() + 330 * 60000).toISOString(); // IST
const stamp = now.slice(0, 10).replace(/-/g, '') + '-' + now.slice(11, 16).replace(':', '');
const tail = Math.random().toString(36).slice(2, 6);
return [{ json: { brand, style, request, watcher, run: `r${stamp}-${tail}`, language: clean(i.language) || 'en',
  chat: clean(i.chat), requested_by: clean(i.requested_by) || watcher } }];
