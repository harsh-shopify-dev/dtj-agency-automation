// n8n Code node "Intake Question" in "Store Factory: Telegram Bot" (mode: Run Once for All Items).
// After "Store Factory: New Page" started a page: ask the person who sent the link whether the designer should collect the brand's
// data first (19 Oct 2026, Harsh: "if i am starting the design of a product page or homepage it should ask me if it should run the
// scraper or not and using the data available it should start designing"). The tap is saved on the brief (column brand_intake) by
// "Note the Choice"; the designer's Claude Code reads it before designing (request_page_design.js, step 2).
// Output: one item for "Ask About Intake" (the question with a Yes and a No button), or nothing when no page was started.
const ask = $('Who Is It').first().json;
const res = $input.first().json || {};
if (!res.ok || !res.row_id) return [];
return [{ json: {
  chat_id: ask.chat_id,
  text: 'One question before the designer starts brief ' + res.row_id + ': collect the brand\'s data first? That reads its website '
    + '(product pictures and videos, logo, colours, fonts, policies; a few minutes) and the page is designed from it.',
  yes_data: 'brief:intake:' + res.row_id,
  no_data: 'brief:skip:' + res.row_id,
} }];
