// Builds the Hopenskin website brief deck. Add new slides to the SLIDES list at the bottom.
const pptxgen = require("pptxgenjs");
const path = require("path");
const NAVY = "0B1B3F", GOLD = "D4B84A", INK = "1A1F2E", MUTED = "5B6478", SOFT = "F3F5FA", WHITE = "FFFFFF";
const IMG = (f) => path.join(__dirname, "images", f);

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "Hopenskin website brief";

function title(s, t, kicker) {
  s.background = { color: WHITE };
  s.addText(kicker, { x: 0.5, y: 0.22, w: 9, h: 0.25, fontFace: "Calibri", fontSize: 12, bold: true, color: GOLD, margin: 0, isTextBox: true });
  s.addText(t, { x: 0.5, y: 0.47, w: 9, h: 0.55, fontFace: "Cambria", fontSize: 28, bold: true, color: NAVY, margin: 0, isTextBox: true });
}

function cover() {
  const s = pres.addSlide(); s.background = { color: NAVY };
  s.addText("WEBSITE BRIEF", { x: 0.7, y: 1.5, w: 8.6, h: 0.4, fontFace: "Calibri", fontSize: 14, bold: true, color: GOLD, charSpacing: 4, margin: 0, isTextBox: true });
  s.addText("Hopenskin.com", { x: 0.7, y: 1.95, w: 8.6, h: 1, fontFace: "Cambria", fontSize: 48, bold: true, color: WHITE, margin: 0, isTextBox: true });
  s.addText("The kind of Shopify store we want built: homepage and product page", { x: 0.7, y: 3.0, w: 8.6, h: 0.6, fontFace: "Calibri", fontSize: 20, color: "CADCFC", margin: 0, isTextBox: true });
  s.addText("Prepared by Digital Tushar Joshi", { x: 0.7, y: 4.8, w: 8.6, h: 0.3, fontFace: "Calibri", fontSize: 12, color: "8FA3CC", margin: 0, isTextBox: true });
}

function intro() {
  const s = pres.addSlide(); title(s, "What we need from you", "THE BRIEF");
  const items = [
    ["1", "A Shopify store", "Built on Shopify, so we can manage products, offers and content ourselves."],
    ["2", "Premium and trust-led", "A dark, polished look where the product, the people and the proof are clear at a glance."],
    ["3", "Built around the reference pages", "The next slides show the style we want, page by page. We are sharing the idea, not asking for a copy."],
  ];
  items.forEach((it, i) => {
    const y = 1.6 + i * 1.2;
    s.addShape(pres.shapes.OVAL, { x: 0.5, y, w: 0.7, h: 0.7, fill: { color: NAVY }, line: { color: NAVY }, objectName: "num" + it[0] });
    s.addText(it[0], { x: 0.5, y, w: 0.7, h: 0.7, align: "center", valign: "middle", fontFace: "Cambria", fontSize: 22, bold: true, color: GOLD, margin: 0, isTextBox: true });
    s.addText(it[1], { x: 1.5, y: y - 0.05, w: 8, h: 0.4, fontFace: "Calibri", fontSize: 20, bold: true, color: INK, margin: 0, isTextBox: true });
    s.addText(it[2], { x: 1.5, y: y + 0.35, w: 8, h: 0.5, fontFace: "Calibri", fontSize: 14, color: MUTED, margin: 0, isTextBox: true });
  });
}

// Height a callout needs: title line + wrapped description lines (generous: 13 characters per inch at 11pt).
function noteHeight(n, bw) { return (1 + Math.ceil(n[1].length / (bw * 13))) * 0.19 + 0.04; }

// Reference-image slide with two automatic layouts; picks whichever gives the bigger picture.
//  below: picture across the slide, callouts in columns underneath.  side: picture left, callouts right.
function refSlide({ kicker, heading, img, ratio = 536 / 800, notes, footnote, start = 0 }) {
  const TOP = 1.15, BOTTOM = 5.2, MAXW = 9.0;
  let best = null;
  for (let cols = 1; cols <= Math.min(4, notes.length); cols++) {
    const gap = 0.25, bw = (MAXW - (cols - 1) * gap) / cols - 0.4;
    const rows = []; notes.forEach((n, i) => { const r = Math.floor(i / cols); rows[r] = Math.max(rows[r] || 0, noteHeight(n, bw)); });
    const total = rows.reduce((a, b) => a + b + 0.08, 0);
    const imgH = Math.min(MAXW * ratio, BOTTOM - TOP - total - 0.25);
    if (imgH > 0.4 && (!best || imgH * 1 > best.w * ratio + 1e-9)) best = { mode: "below", cols, bw, rows, total, w: imgH / ratio };
  }
  const sw = Math.min(5.0, 3.9 / ratio), sbw = 9.5 - (0.5 + sw + 0.2 + 0.35 + 0.38);
  let sy = TOP; notes.forEach((n) => { sy += noteHeight(n, sbw) + 0.07; });
  const sideOk = sy <= BOTTOM + 0.05 && sbw > 2.2;
  if (sideOk && (!best || sw > best.w * 1.15)) best = { mode: "side", w: sw, bw: sbw };

  const s = pres.addSlide(); title(s, heading, kicker);
  const dot = (i, x, y) => {
    s.addShape(pres.shapes.OVAL, { x, y: y + 0.01, w: 0.28, h: 0.28, fill: { color: GOLD }, line: { color: GOLD }, objectName: "dot" + i });
    s.addText(String(start + i + 1), { x, y: y + 0.01, w: 0.28, h: 0.28, align: "center", valign: "middle", fontFace: "Calibri", fontSize: 11, bold: true, color: NAVY, margin: 0, isTextBox: true });
  };
  const body = (n, x, y, w, h) => s.addText([{ text: n[0], options: { bold: true, color: INK, breakLine: true } }, { text: n[1], options: { color: MUTED } }],
    { x, y, w, h, fontFace: "Calibri", fontSize: 11, margin: 0, valign: "top", isTextBox: true });
  let endY;
  if (best.mode === "below") {
    const w = best.w, h = w * ratio, x = 0.5 + (MAXW - w) / 2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.08, y: TOP - 0.08, w: w + 0.16, h: h + 0.16, rectRadius: 0.08, fill: { color: SOFT }, line: { color: SOFT }, objectName: "frame" });
    s.addImage({ path: IMG(img), x, y: TOP, w, h, altText: "Reference image: " + heading });
    const gap = 0.25, top = TOP + h + 0.25;
    notes.forEach((n, i) => {
      const c = i % best.cols, r = Math.floor(i / best.cols);
      const y = top + best.rows.slice(0, r).reduce((a, b) => a + b + 0.08, 0), nx = 0.5 + c * (best.bw + 0.4 + gap);
      dot(i, nx, y); body(n, nx + 0.38, y, best.bw, best.rows[r]);
    });
    endY = top + best.total;
  } else {
    const w = best.w, h = w * ratio;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.42, y: TOP - 0.08, w: w + 0.16, h: h + 0.16, rectRadius: 0.08, fill: { color: SOFT }, line: { color: SOFT }, objectName: "frame" });
    s.addImage({ path: IMG(img), x: 0.5, y: TOP, w, h, altText: "Reference image: " + heading });
    const x0 = 0.5 + w + 0.2 + 0.35; let y = TOP;
    notes.forEach((n, i) => { const bh = noteHeight(n, best.bw); dot(i, x0, y); body(n, x0 + 0.38, y, best.bw, bh); y += bh + 0.07; });
    endY = y;
  }
  console.log(heading + ": " + best.mode + ", picture " + best.w.toFixed(1) + "in wide, notes end " + endY.toFixed(2));
  if (endY > 5.25) console.warn("OVERFLOW on slide '" + heading + "'");
  if (footnote) s.addText(footnote, { x: 0.5, y: 5.25, w: 9, h: 0.3, fontFace: "Calibri", fontSize: 10, italic: true, color: MUTED, margin: 0, isTextBox: true });
}

// A reference image with many callouts is split over two slides, same picture, numbering continues.
function splitSlide(o) {
  const half = Math.ceil(o.notes.length / 2);
  refSlide({ ...o, heading: o.heading + " (1 of 2)", notes: o.notes.slice(0, half) });
  refSlide({ ...o, heading: o.heading + " (2 of 2)", notes: o.notes.slice(half), start: half });
}


// Product-page slide: picture top-left, first 4 callouts beside it, the rest in a 3-column grid below.
function prodSlide({ kicker, heading, img, ratio, notes, footnote }) {
  const s = pres.addSlide(); title(s, heading, kicker);
  const w = 4.0, h = w * ratio;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 1.35, w: w + 0.2, h: h + 0.2, rectRadius: 0.1, fill: { color: SOFT }, line: { color: SOFT }, objectName: "frame" });
  s.addImage({ path: IMG(img), x: 0.6, y: 1.45, w, h, altText: "Reference image: " + heading });
  const badge = (i, x, y) => {
    s.addShape(pres.shapes.OVAL, { x, y: y + 0.02, w: 0.3, h: 0.3, fill: { color: GOLD }, line: { color: GOLD }, objectName: "dot" + i });
    s.addText(String(i + 1), { x, y: y + 0.02, w: 0.3, h: 0.3, align: "center", valign: "middle", fontFace: "Calibri", fontSize: 11, bold: true, color: NAVY, margin: 0, isTextBox: true });
  };
  const body = (n, x, y, bw, bh) => s.addText([{ text: n[0], options: { bold: true, color: INK, breakLine: true } }, { text: n[1], options: { color: MUTED } }],
    { x, y, w: bw, h: bh, fontFace: "Calibri", fontSize: 11, margin: 0, valign: "top", isTextBox: true });
  let y = 1.35; const rbw = 4.0;
  notes.slice(0, 4).forEach((n, i) => { const bh = noteHeight(n, rbw); badge(i, 5.0, y); body(n, 5.4, y, rbw, bh); y += bh + 0.06; });
  const gridTop = Math.max(y, 1.35 + h + 0.2 + 0.2), gbw = 2.55;
  let gy = gridTop; const rows = [];
  notes.slice(4).forEach((n, j) => { const r = Math.floor(j / 3); rows[r] = Math.max(rows[r] || 0, noteHeight(n, gbw)); });
  notes.slice(4).forEach((n, j) => {
    const i = j + 4, col = j % 3, r = Math.floor(j / 3);
    const yy = gridTop + rows.slice(0, r).reduce((a, b) => a + b + 0.08, 0), x = 0.5 + col * 3.05;
    badge(i, x, yy); body(n, x + 0.4, yy, gbw, rows[r]); gy = yy + rows[r];
  });
  if (gy > 5.1) console.warn("OVERFLOW on slide '" + heading + "': notes end at " + gy.toFixed(2));
  if (footnote) s.addText(footnote, { x: 0.5, y: 5.15, w: 9, h: 0.4, fontFace: "Calibri", fontSize: 10, italic: true, color: MUTED, margin: 0, isTextBox: true });
}

// Tall-picture slide: picture on the left (fixed height), callouts in a wide column on the right.
function tallSlide({ kicker, heading, img, ratio, notes, footnote }) {
  const s = pres.addSlide(); title(s, heading, kicker);
  const h = 3.4, w = h / ratio;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 1.35, w: w + 0.2, h: h + 0.2, rectRadius: 0.1, fill: { color: SOFT }, line: { color: SOFT }, objectName: "frame" });
  s.addImage({ path: IMG(img), x: 0.6, y: 1.45, w, h, altText: "Reference image: " + heading });
  const x0 = 0.5 + w + 0.2 + 0.35, bw = 9.5 - x0 - 0.42 - 0.0;
  let y = 1.35;
  notes.forEach((n, i) => {
    const bh = noteHeight(n, bw);
    s.addShape(pres.shapes.OVAL, { x: x0, y: y + 0.02, w: 0.3, h: 0.3, fill: { color: GOLD }, line: { color: GOLD }, objectName: "dot" + i });
    s.addText(String(i + 1), { x: x0, y: y + 0.02, w: 0.3, h: 0.3, align: "center", valign: "middle", fontFace: "Calibri", fontSize: 11, bold: true, color: NAVY, margin: 0, isTextBox: true });
    s.addText([{ text: n[0], options: { bold: true, color: INK, breakLine: true } }, { text: n[1], options: { color: MUTED } }],
      { x: x0 + 0.4, y, w: bw, h: bh, fontFace: "Calibri", fontSize: 11, margin: 0, valign: "top", isTextBox: true });
    y += bh + 0.07;
  });
  if (y > 5.1) console.warn("OVERFLOW on slide '" + heading + "': notes end at " + y.toFixed(2));
  if (footnote) s.addText(footnote, { x: 0.5, y: 5.15, w: 9, h: 0.4, fontFace: "Calibri", fontSize: 10, italic: true, color: MUTED, margin: 0, isTextBox: true });
}

// Wide-strip slide: a thin picture across the slide, callouts in 3 columns below.
function stripSlide({ kicker, heading, img, ratio, notes, footnote }) {
  const s = pres.addSlide(); title(s, heading, kicker);
  const w = 9, h = w * ratio;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 1.45, w: w, h: h + 0.2, rectRadius: 0.1, fill: { color: SOFT }, line: { color: SOFT }, objectName: "frame" });
  s.addImage({ path: IMG(img), x: 0.6, y: 1.55, w: w - 0.2, h: (w - 0.2) * ratio, altText: "Reference image: " + heading });
  notes.forEach((n, i) => {
    const col = i % 3, row = Math.floor(i / 3), x = 0.5 + col * 3.05, y = 2.85 + row * 1.0;
    s.addShape(pres.shapes.OVAL, { x, y: y + 0.02, w: 0.3, h: 0.3, fill: { color: GOLD }, line: { color: GOLD }, objectName: "dot" + i });
    s.addText(String(i + 1), { x, y: y + 0.02, w: 0.3, h: 0.3, align: "center", valign: "middle", fontFace: "Calibri", fontSize: 11, bold: true, color: NAVY, margin: 0, isTextBox: true });
    s.addText([{ text: n[0], options: { bold: true, color: INK, breakLine: true } }, { text: n[1], options: { color: MUTED } }],
      { x: x + 0.4, y, w: 2.55, h: 0.95, fontFace: "Calibri", fontSize: 11, margin: 0, valign: "top", isTextBox: true });
  });
  if (footnote) s.addText(footnote, { x: 0.5, y: 5.2, w: 9, h: 0.3, fontFace: "Calibri", fontSize: 10, italic: true, color: MUTED, margin: 0, isTextBox: true });
}

function nextSteps() {
  const s = pres.addSlide(); s.background = { color: NAVY };
  s.addText("Next steps", { x: 0.5, y: 0.5, w: 9, h: 0.7, fontFace: "Cambria", fontSize: 36, bold: true, color: WHITE, margin: 0, isTextBox: true });
  const cols = [
    ["Please send us", ["A quote and a timeline for the homepage and product page", "How you would build each section: theme, custom sections, and which apps (for example Judge.me for reviews)", "A mobile-first mockup of both pages for us to approve before the build starts", "Two or three Shopify stores you have built, as examples"]],
    ["We will provide", ["Hopenskin logo, colours and fonts", "Product details, photos and videos", "Offers and claims that the brand has confirmed", "One point of contact for feedback and approvals"]],
  ];
  cols.forEach((c, i) => {
    const x = 0.5 + i * 4.6;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.5, w: 4.4, h: 3.6, rectRadius: 0.12, fill: { color: "15295A" }, line: { color: "15295A" }, objectName: "col" + i });
    s.addText(c[0], { x: x + 0.3, y: 1.7, w: 3.8, h: 0.5, fontFace: "Calibri", fontSize: 20, bold: true, color: GOLD, margin: 0, isTextBox: true });
    s.addText(c[1].map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < c[1].length - 1 } })),
      { x: x + 0.3, y: 2.3, w: 3.8, h: 2.7, fontFace: "Calibri", fontSize: 14, color: WHITE, paraSpaceAfter: 8, margin: 0, valign: "top", isTextBox: true });
  });
}

// Sticky-bar slide: a simple "screen" drawn natively, with only the real bar as a picture at its bottom.
function stickySlide({ kicker, heading, img, ratio, notes, footnote }) {
  const s = pres.addSlide(); title(s, heading, kicker);
  const x = 0.5, y = 1.3, W = 9, H = 2.4, bh = W * ratio;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: W, h: H, rectRadius: 0.1, fill: { color: SOFT }, line: { color: "D5DAE8", width: 1 }, objectName: "screen" });
  s.addText("The page keeps scrolling here: details, reviews, FAQ", { x, y: y + 0.45, w: W, h: 0.6, align: "center", fontFace: "Calibri", fontSize: 16, color: MUTED, margin: 0, isTextBox: true });
  s.addText("The bar stays fixed at the bottom of the screen", { x, y: y + 1.05, w: W, h: 0.4, align: "center", fontFace: "Calibri", fontSize: 12, italic: true, color: MUTED, margin: 0, isTextBox: true });
  s.addImage({ path: IMG(img), x, y: y + H - bh - 0.04, w: W, h: bh, altText: "Reference image: sticky Add to Cart bar" });
  notes.forEach((n, i) => {
    const nx = 0.5 + i * 3.05, ny = 4.0;
    s.addShape(pres.shapes.OVAL, { x: nx, y: ny + 0.01, w: 0.28, h: 0.28, fill: { color: GOLD }, line: { color: GOLD }, objectName: "dot" + i });
    s.addText(String(i + 1), { x: nx, y: ny + 0.01, w: 0.28, h: 0.28, align: "center", valign: "middle", fontFace: "Calibri", fontSize: 11, bold: true, color: NAVY, margin: 0, isTextBox: true });
    s.addText([{ text: n[0], options: { bold: true, color: INK, breakLine: true } }, { text: n[1], options: { color: MUTED } }],
      { x: nx + 0.38, y: ny, w: 2.55, h: 1.1, fontFace: "Calibri", fontSize: 11, margin: 0, valign: "top", isTextBox: true });
  });
  if (footnote) s.addText(footnote, { x: 0.5, y: 5.25, w: 9, h: 0.3, fontFace: "Calibri", fontSize: 10, italic: true, color: MUTED, margin: 0, isTextBox: true });
}

const SLIDES = [
  cover, intro,
  () => refSlide({
    kicker: "HOMEPAGE", heading: "Hero section", img: "home-hero-2.png", ratio: 842 / 1627,
    notes: [
      ["Full-width lifestyle photo", "A real person using the product. Text sits on the plain left side."],
      ["Tag, headline and one italic word", "Small “Now on sale” tag, then a big, short headline."],
      ["Rating and benefit ticks", "Star rating with the real review count, then three one-line benefits."],
      ["Two buttons and a guarantee", "Bright Shop Now, quieter Learn More, small guarantee line below."],
    ],
    footnote: "Reference only. Wording, ratings and guarantee must be Hopenskin's own and confirmed. Do not copy the health claims shown (stress, pain relief).",
  }),
 () => refSlide({
    kicker: "HOMEPAGE", heading: "Shop by concern", img: "home-shop-by-concern.png", ratio: 832 / 1792,
    notes: [
      ["Heading and concern dropdown", "Visitor picks a need and the products change."],
      ["Product cards in a row", "Photo, rating, name, price and discount. Scrolls sideways."],
      ["Variant picker and Add to Cart", "Choose the pack on the card and buy from it."],
      ["View Collection button", "Leads to the full collection page."],
    ],
    footnote: "Reference only. Concerns, products, prices and ratings must come from Hopenskin's own store data.",
  }),
  () => refSlide({
    kicker: "HOMEPAGE", heading: "Trust section", img: "home-trust.png", ratio: 733 / 1708,
    notes: [
      ["Expert photo with badge", "A real team member in a lab, with a “verified” badge."],
      ["Headline with accent words", "A strong promise, e.g. “proven” and “trusted”."],
      ["Short expert quote", "One or two lines, with name and qualification."],
      ["Four proof numbers", "Big figures with small labels, e.g. years and customers."],
    ],
    footnote: "Reference only. Use Hopenskin's own experts, quotes and numbers. Only verified claims go on the page.",
  }),
  () => refSlide({
    kicker: "HOMEPAGE", heading: "Product showcase with tabs", img: "home-essentials.png", ratio: 842 / 1436,
    notes: [
      ["Section title", "A simple heading, e.g. “Essentials”."],
      ["Tabs to switch the list", "Bestsellers, Value Pack, Newly Launched and similar."],
      ["Four product cards in a row", "Large photo, rating, name, short details, price and discount."],
      ["Pack or colour picker on the card", "Visitor chooses the option without opening the product."],
      ["Add to Cart on every card", "One clear button on each card."],
      ["Show More button", "Loads more products below."],
    ],
    footnote: "Reference only. Tabs, products, prices and ratings must come from Hopenskin's own store data. The category section follows below this.",
  }),
  () => refSlide({
    kicker: "HOMEPAGE", heading: "Video reviews", img: "home-video-reviews.png", ratio: 572 / 1815,
    notes: [
      ["Small section label", "A quiet heading such as “Real people, real results”."],
      ["Row of tall video cards", "Short customer videos in a sideways scroll."],
      ["Price under the video", "Tapping goes to that product."],
      ["Stars and “Verified review”", "A badge on every card to show it is real."],
    ],
    footnote: "Reference only. Use Hopenskin's own customer videos, with the customer's permission.",
  }),
  () => refSlide({
    kicker: "HOMEPAGE", heading: "Written reviews", img: "home-text-reviews.png", ratio: 420 / 1323,
    notes: [
      ["Heading with accent words", "Short title and a one-line promise under it."],
      ["Overall rating box", "Star rating and total review count, using the real figures."],
      ["Review cards in a row", "Name, city, “Verified” tag, stars and a short review."],
      ["Product tag and date", "Shows which product was reviewed and when."],
      ["Arrows and progress bar", "Visitor can move through the reviews."],
    ],
    footnote: "Reference only. Show real, verified Hopenskin reviews only. Ratings and counts must come from the review app.",
  }),
  () => refSlide({
    kicker: "HOMEPAGE", heading: "Brand belief banner", img: "home-brand-belief.png", ratio: 512 / 1851,
    notes: [
      ["Big belief statement", "One bold line about what the brand stands for, with the key phrase underlined."],
      ["Four short proof phrases", "Written as quick lines under the statement."],
      ["Creative, memorable image", "A playful picture on the right that people remember."],
      ["Soft background with small sparkles", "A calm colour block that breaks up the page."],
    ],
    footnote: "Reference only. Write Hopenskin's own belief line and image. Do not reuse the reference wording.",
  }),
  () => refSlide({
    kicker: "HOMEPAGE", heading: "Blogs section", img: "home-blogs.png", ratio: 582 / 1477,
    notes: [
      ["Title and View All link", "Title on the left, link to all articles on the right."],
      ["Three article cards", "A branded cover image on top of each card."],
      ["Titles, teaser and date", "Question-style titles, a two-line teaser, date and arrow."],
      ["Arrows and progress bar", "Move through more articles."],
    ],
    footnote: "Optional. Useful for search traffic and trust. Needs Hopenskin's own articles; we will confirm topics and who writes them.",
  }),
  () => refSlide({
    kicker: "HOMEPAGE", heading: "Footer", img: "home-footer.png", ratio: 477 / 1887,
    notes: [
      ["Logo, tagline and social icons", "Brand on the left, with links to its social pages."],
      ["Newsletter sign-up", "Email box and a Subscribe button at the top of the footer."],
      ["Link columns", "About, useful links (policies, shipping, contact) and where to buy."],
      ["Customer help and bulk orders", "Support email, phone and working hours in one place."],
      ["Bottom bar", "Copyright and the payment icons."],
      ["Back-to-top button", "Round button at the corner."],
    ],
    footnote: "Style reference with a request: make ours cleaner and easier to scan. Keep it to the links Hopenskin needs. Any offer in the newsletter text must be confirmed first.",
  }),
  () => splitSlide({
    kicker: "PRODUCT PAGE", heading: "Top of the product page", img: "pdp-top.png", ratio: 770 / 1772,
    notes: [
      ["Breadcrumb trail", "Home > Products > product name."],
      ["Thumbnail strip", "Tap a small picture to change the main image."],
      ["Large main image", "Big picture, with dots to move through the gallery."],
      ["Product name and share icon", "Large name with a share button at the right."],
      ["Rating chip", "Stars and number of ratings. Tap to jump to reviews."],
      ["Price row", "Big price, old price struck through, green discount tag."],
      ["Benefit chips", "3–4 short benefits with icons. Scrolls sideways on mobile."],
      ["Quantity and Add to Cart", "Round quantity box and one wide, bold button."],
      ["Trust strip", "Fast delivery, secure payment and COD, easy support."],
      ["Delivery check", "Pincode box with a Check button for the delivery date."],
    ],
    footnote: "Reference only. Name, price, discount, rating and benefits must come from Hopenskin's own product data. Delivery promises must be confirmed first.",
  }),
  () => refSlide({
    kicker: "PRODUCT PAGE", heading: "Offers, details and add-ons", img: "pdp-offers-details.png", ratio: 718 / 767,
    notes: [
      ["Delivery date line", "Shows the delivery date right after the pincode check."],
      ["“Available offers” box", "One rounded box with all current offers, just under the buy button."],
      ["Offer coupon cards", "Ticket-style cards: title, short line, code with Copy Code button or “Auto applied”. Scrolls sideways."],
      ["Fold-out sections", "Descriptions, Benefits, Manufacturing Details, Shipping & Return. Each opens with a plus sign."],
      ["“Frequently bought together” box", "Suggests add-on products below the details."],
      ["Add-on product cards", "Photo, name, teaser, price, discount tag and own Add to Cart. Scrolls sideways."],
    ],
    footnote: "Reference only. Offers, codes and shipping text must be Hopenskin's own, confirmed by the brand. Do not copy the reference offers.",
  }),
  () => refSlide({
    kicker: "PRODUCT PAGE", heading: "Video reviews on the product page", img: "home-video-reviews.png", ratio: 572 / 1815,
    notes: [
      ["Same video review row as the homepage", "Placed below the offers and details on the product page."],
      ["Only videos for this product", "Each product page shows the videos made for that product."],
      ["Tall video cards", "Short customer videos in a sideways scroll. Tap to play."],
      ["Stars and “Verified review”", "A badge on every card to show it is real."],
    ],
    footnote: "Same style as the homepage slide. Use Hopenskin's own customer videos, with the customer's permission.",
  }),
  () => refSlide({
    kicker: "PRODUCT PAGE", heading: "Written reviews on the product page", img: "home-text-reviews.png", ratio: 420 / 1323,
    notes: [
      ["Same review block as the homepage", "Placed after the video reviews."],
      ["Overall rating box", "Star rating and total number of reviews for this product."],
      ["Review cards in a row", "Name, city, “Verified” tag, stars and a short review."],
      ["Photo reviews and filters", "Nice to have: customer photos, and filters by star rating."],
      ["Arrows and progress bar", "Visitor can move through the reviews."],
    ],
    footnote: "Show real, verified Hopenskin reviews only. Ratings and counts must come from the review app.",
  }),
  () => refSlide({
    kicker: "PRODUCT PAGE", heading: "Ingredients", img: "pdp-ingredients.png", ratio: 395 / 1207,
    notes: [
      ["Centered section title", "Simple heading on a soft, plain background."],
      ["Round ingredient pictures", "One round picture for each key ingredient."],
      ["Ingredient name", "Short name in capitals under the picture."],
      ["One-line benefit", "What the ingredient does, in plain words. Scrolls sideways if there are many."],
      ["Learn More link", "Opens the full ingredient details."],
    ],
    footnote: "Reference only. Ingredients and benefit lines must match Hopenskin's real product label and approved claims.",
  }),
  () => refSlide({
    kicker: "PRODUCT PAGE", heading: "Claims and before/after", img: "pdp-before-after.png", ratio: 697 / 1558,
    notes: [
      ["Title and short intro", "A plain heading and two to four lines on what it does."],
      ["Key claims as short lines", "Ingredient or feature plus what it does."],
      ["Before and after slider", "One face split in the middle. Drag the handle to compare."],
      ["Labels and thumbnails", "“Before” and “After” tags, plus a strip to switch sets."],
    ],
    footnote: "Reference only. Use only real, unedited customer or clinical photos, with consent, and only claims Hopenskin can prove. Do not use AI-made or retouched faces.",
  }),
  () => refSlide({
    kicker: "PRODUCT PAGE", heading: "FAQ", img: "pdp-faq.png", ratio: 417 / 1252,
    notes: [
      ["Title and friendly one-liner", "Centered heading with a short, soft line under it."],
      ["Question rows", "One question per row, separated by thin lines. Only the product's own questions."],
      ["Plus / minus button", "Tap to open or close an answer. Only one open at a time keeps it tidy."],
      ["Short answer", "One or two plain lines under the question when it is open."],
    ],
    footnote: "Reference only. Questions and answers (usage, skin type, safety) must be written with Hopenskin and match the real product.",
  }),
  () => stickySlide({
    kicker: "PRODUCT PAGE", heading: "Sticky Add to Cart bar", img: "pdp-sticky-cart.png", ratio: 65 / 1250,
    notes: [
      ["Appears when the buy button scrolls away", "A bar fixed to the bottom of the screen. It stays visible while the visitor reads reviews and details."],
      ["Product mini-card", "Small product picture, name, price, old price and discount tag, so the visitor always knows what they are buying."],
      ["Quantity and Add to Cart", "The same quantity box and bold button as the top of the page. Must work on mobile too, full width."],
    ],
    footnote: "Reference only. Product name, price and discount must update live with the chosen variant on Hopenskin's store.",
  }),
  () => {
    const s = pres.addSlide(); title(s, "More inspiration", "REFERENCE WEBSITES");
    s.addText("Please browse these two live stores for more ideas on layout, sections and feel. Use them as a guide, not as something to copy.", { x: 0.5, y: 1.5, w: 9, h: 0.7, fontFace: "Calibri", fontSize: 16, color: MUTED, margin: 0, isTextBox: true });
    [["Earth Rhythm", "https://earthrhythm.com/", "Product page, offers, ingredients, how to use, FAQ, sticky Add to Cart"],
     ["Perfora", "https://perforacare.com/", "Homepage hero, categories, product showcase, trust section, reviews"]].forEach((r, i) => {
      const x = 0.5 + i * 4.6, y = 2.5;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 4.4, h: 2.2, rectRadius: 0.12, fill: { color: SOFT }, line: { color: SOFT }, objectName: "card" + i });
      s.addText(r[0], { x: x + 0.3, y: y + 0.25, w: 3.8, h: 0.5, fontFace: "Cambria", fontSize: 24, bold: true, color: NAVY, margin: 0, isTextBox: true });
      s.addText(r[1].replace("https://", ""), { x: x + 0.3, y: y + 0.85, w: 3.8, h: 0.4, fontFace: "Calibri", fontSize: 16, bold: true, color: "2B59C3", margin: 0, isTextBox: true, hyperlink: { url: r[1] } });
      s.addText("Good for: " + r[2], { x: x + 0.3, y: y + 1.3, w: 3.8, h: 0.7, fontFace: "Calibri", fontSize: 13, color: MUTED, margin: 0, valign: "top", isTextBox: true });
    });
    s.addText("Most reference screenshots in this deck come from these two sites. Hopenskin's own products, claims, offers and photos must replace theirs.", { x: 0.5, y: 5.0, w: 9, h: 0.4, fontFace: "Calibri", fontSize: 10, italic: true, color: MUTED, margin: 0, isTextBox: true });
  },
  () => refSlide({
    kicker: "HOMEPAGE", heading: "Category section", img: "home-categories.png", ratio: 502 / 1816,
    notes: [
      ["Centered title with accent words", "Category name in the brand accent colour."],
      ["Row of round-framed pictures", "One clean product photo for each category, on a soft tinted shape."],
      ["Short label under each picture", "Two lines at most, in the same font as the headings."],
      ["Optional offer tile", "A bundle or “build your own box” tile in the same row."],
      ["Sideways scroll", "The last tile is cut off so people know to swipe."],
      ["Every tile is a link", "Tapping goes straight to that collection page."],
    ],
    footnote: "Placed below the hero by default (it could also sit at the top). Reference only: Hopenskin's own categories, photos and offers must be used.",
  }),
  () => refSlide({
    kicker: "PRODUCT PAGE", heading: "Judge.me review block", img: "pdp-judgeme-reviews.png", ratio: 747 / 1131,
    notes: [
      ["Built with the Judge.me app", "Install Judge.me on Shopify and use its review widget. Do not hand-build or type in reviews."],
      ["AI summary box on top", "A short summary of what customers say, topic tags and a “View customer reviews” button."],
      ["Score and star bars", "Overall score, review count, and a bar for each of 5 to 1 stars. Write a review button at the right."],
      ["Sort menu and review cards", "“Most recent” sort, then cards with stars, name, Verified tag, date and text."],
      ["Load More button", "Shows more reviews below without leaving the page."],
    ],
    footnote: "Reference only. All scores, counts and reviews come from Hopenskin's own Judge.me account. Keep the page's colours consistent with the brand.",
  }),
];
// final order (indices follow the order the slides were added above)
const ORDER = [0, 1, 19, 2, 20, 5, 3, 8, 4, 6, 7, 9, 10, 11, 12, 13, 14, 21, 15, 16, 17, 18];
ORDER.forEach((i) => SLIDES[i]());
// nextSteps(); (removed from the deck on request)
pres.writeFile({ fileName: path.join(__dirname, "Hopenskin-website-brief.pptx") }).then(() => console.log("ok"));
