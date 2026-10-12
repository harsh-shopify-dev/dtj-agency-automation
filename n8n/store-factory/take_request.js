// n8n Code node "Take the Request" in "Store Factory: New Page" (mode: Run Once for All Items).
// One shape for every way in: "What to Design (edit me)" (by hand) or another workflow (the Telegram bot) calling this one with
// { product_link, note, requested_by, chat_id }.
const r = $input.first().json || {};
return [{ json: {
  product_link: String(r.product_link || '').trim(),
  note: String(r.note || '').trim().slice(0, 1500),
  requested_by: String(r.requested_by || 'unknown').trim().slice(0, 120),
  chat_id: String(r.chat_id || '').trim(),
} }];
