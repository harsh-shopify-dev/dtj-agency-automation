// n8n Code node "What to Design (edit me)" in "Store Factory: New Page" (mode: Run Once for All Items).
// 1. Open the product on the shop's own website and copy the address from the top of the browser.
// 2. Paste it between the two ` marks on the product_link line below. Add a note between the ` marks on the note line if you like.
// 3. Press "Execute workflow". Nothing else needs filling in: the shop's details come from the stores table (dtj_stores).
const product_link = ``; // e.g. https://test-store-harsh-dtj.myshopify.com/products/pore-clarifying-serum-2-salicylic-acid-30ml
const note = ``;         // optional, plain words (apostrophes are fine): what to lead with, the real rating and its source, a look you like

return [{ json: { product_link, note, requested_by: 'n8n (run by hand)', chat_id: '' } }];
