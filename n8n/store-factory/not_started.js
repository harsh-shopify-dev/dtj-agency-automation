// n8n Code node "Not Started" in "Store Factory: New Page" (mode: Run Once for All Items): the plain reason, nothing was saved.
const m = $input.first().json || {};
return [{ json: { ok: false, row_id: null, message: String(m.message || 'Something was missing. Ask Harsh.') } }];
