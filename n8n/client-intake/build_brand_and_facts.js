// n8n Code node "Build Brand and Facts" (mode: Run Once for Each Item).
// Turns one client intake form answer into the page builder's two inputs:
//   brand  -> services/store-builder/page_builder/schemas/brand-profile.schema.json
//   facts  -> services/store-builder/page_builder/schemas/product-facts.schema.json
// Rules: nothing is invented. An empty answer leaves the section out. A line that
// does not fit the format is reported in `problems`, never silently dropped or cut.
// `demo` is never set, so client pages can never use placeholders.
// Source of truth for the node's code: keep this file and the n8n node identical
// (n8n/client-intake/test_build_brand_and_facts.py checks the export).

const LABELS = {
  store_domain: 'Shopify store address',
  theme_id: 'Draft theme ID',
  brand_name: 'Brand name',
  category: 'Category',
  price_tier: 'Price level',
  voice: 'Brand voice',
  shape_language: 'Shape style',
  color_primary: 'Main brand colour',
  color_accent: 'Accent colour',
  color_background: 'Page background colour',
  color_text: 'Text colour',
  heading_style: 'Heading font style',
  logo_link: 'Logo link',
  product_title: 'Product name',
  product_link: 'Product page link',
  picture_links: 'Picture links',
  default_source: 'Where do these facts come from?',
  buybox_tagline: 'Short tagline next to the price',
  trust_points: 'Trust points',
  benefits: 'Benefits',
  story_heading: 'Story heading',
  story_body: 'Story text',
  steps: 'How to use (steps)',
  key_facts: 'Key facts',
  pack_contents: 'What is in the pack',
  free_from: 'Free from',
  faqs: 'Questions and answers',
  reviews: 'Real customer reviews',
  rating: 'Average star rating',
  guarantees: 'Guarantees and policies',
  comparison_other_label: 'Comparison: who are you compared with?',
  comparison_rows: 'Comparison rows',
  comparison_approved: 'Comparison approval',
  facts_confirmed: 'Confirmation',
  notes: 'Anything else for the DTJ team',
};

const CATEGORIES = ['beauty', 'supplements', 'home-care', 'food', 'apparel', 'other'];
const PRICE_TIERS = ['value', 'mid', 'premium'];
const VOICES = ['plain', 'warm', 'clinical', 'playful', 'luxe'];
const SHAPES = ['sharp', 'soft', 'round'];
const HEADING_CLASSES = ['theme', 'sans', 'serif'];

function buildIntake(answers) {
  const problems = [];
  const problem = (msg) => problems.push(msg);

  const raw = (key) => {
    let v = answers[key];
    if (v === undefined) v = answers[LABELS[key]];
    if (v === undefined || v === null) return '';
    if (Array.isArray(v)) return v.map((x) => String(x).trim()).filter(Boolean).join('\n');
    return String(v).trim();
  };
  const lines = (key) => raw(key).split(/\r?\n/).map((l) => l.trim()).filter(Boolean);

  // "text [source]" -> { body: "text", source: "source" }; source falls back to the default.
  const defaultSource = raw('default_source');
  const sourceOk = (s) => s.length >= 2 && s.length <= 120;
  const splitSource = (line, field) => {
    const m = line.match(/^(.*?)\s*\[([^\[\]]+)\]\s*$/);
    const body = (m ? m[1] : line).trim();
    const source = (m ? m[2] : defaultSource).trim();
    if (!sourceOk(source)) {
      problem(`${LABELS[field]}: "${line}" has no usable source. Add it in [brackets] or fill in "${LABELS.default_source}".`);
      return null;
    }
    return { body, source };
  };
  const textOk = (t, field, line, max = 400) => {
    if (!t) { problem(`${LABELS[field]}: "${line}" is missing text.`); return false; }
    if (t.length > max) { problem(`${LABELS[field]}: "${t.slice(0, 40)}..." is longer than ${max} characters. Please shorten it.`); return false; }
    return true;
  };
  const cap = (list, max, field) => {
    if (list.length > max) {
      problem(`${LABELS[field]}: only ${max} are allowed, so the first ${max} were kept. Please choose your best ${max}.`);
      return list.slice(0, max);
    }
    return list;
  };
  const parts = (body) => body.split('|').map((p) => p.trim());
  const chosen = (key, allowed) => {
    const v = raw(key).toLowerCase();
    if (!v || v.startsWith('not sure')) return undefined;
    const hit = allowed.find((a) => v === a || v.startsWith(a + ' '));
    if (!hit) problem(`${LABELS[key]}: "${raw(key)}" is not one of the choices.`);
    return hit;
  };
  const colour = (key) => {
    let v = raw(key);
    if (!v) return undefined;
    if (!v.startsWith('#')) v = '#' + v;
    if (/^#[0-9A-Fa-f]{3}$/.test(v)) v = '#' + v.slice(1).split('').map((c) => c + c).join('');
    if (!/^#[0-9A-Fa-f]{6}$/.test(v)) {
      problem(`${LABELS[key]}: "${raw(key)}" is not a colour code like #0B4A6F.`);
      return undefined;
    }
    return v.toUpperCase();
  };

  // ---- who and where
  let storeDomain = raw('store_domain').toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '');
  if (!/^[a-z0-9][a-z0-9-]*\.myshopify\.com$/.test(storeDomain)) {
    problem(`${LABELS.store_domain}: "${raw('store_domain')}" must be the store's .myshopify.com address (Shopify admin > Settings > Domains).`);
  }

  // The draft theme the page builder writes into: the number, or a theme editor link containing /themes/<number>.
  // Optional here (DTJ can add it later); the page builder refuses to write without it and checks it is not the live theme.
  const themeAnswer = raw('theme_id');
  const themeId = (themeAnswer.match(/\/themes\/(\d+)/) || [])[1] || (/^\d+$/.test(themeAnswer) ? themeAnswer : '');
  if (themeAnswer && !themeId) problem(`${LABELS.theme_id}: "${themeAnswer}" should be the theme's number (Online Store > Themes > ... > Edit code: the number in the address).`);

  const brand = {};
  const brandName = raw('brand_name');
  if (!brandName) problem(`${LABELS.brand_name} is missing.`);
  else if (brandName.length > 60) problem(`${LABELS.brand_name} is longer than 60 characters.`);
  else brand.brand_name = brandName;

  const category = chosen('category', CATEGORIES);
  if (category) brand.category = category;
  else if (!raw('category')) problem(`${LABELS.category} is missing.`);

  const tier = chosen('price_tier', PRICE_TIERS);
  if (tier) brand.price_tier = tier;
  const voice = chosen('voice', VOICES);
  if (voice) brand.voice = voice;
  const shape = chosen('shape_language', SHAPES);
  if (shape) brand.shape_language = shape;

  const colors = {};
  for (const [field, key] of [['color_primary', 'primary'], ['color_accent', 'accent'], ['color_background', 'background'], ['color_text', 'text']]) {
    const c = colour(field);
    if (c) colors[key] = c;
  }
  if (Object.keys(colors).length) brand.colors = colors;
  const headingClass = chosen('heading_style', HEADING_CLASSES);
  if (headingClass) brand.fonts = { heading_class: headingClass };

  const logoLink = raw('logo_link');
  if (logoLink && !/^https?:\/\/\S+$/.test(logoLink)) problem(`${LABELS.logo_link}: "${logoLink}" is not a web link.`);

  // ---- product
  const facts = {};
  const title = raw('product_title');
  if (!title) problem(`${LABELS.product_title} is missing.`);
  else if (title.length > 80) problem(`${LABELS.product_title} is longer than 80 characters.`);
  const product = { title };
  const productLink = raw('product_link');
  const handle = (productLink.match(/\/products\/([a-z0-9][a-z0-9-]*)/i) || [])[1];
  if (handle) product.handle = handle.toLowerCase();
  else if (productLink) problem(`${LABELS.product_link}: "${productLink}" is not a product page link (it should contain /products/...).`);
  facts.product = product;

  const pictures = [];
  lines('picture_links').forEach((line, i) => {
    const p = parts(line);
    const url = p.length > 1 ? p[1] : p[0];
    const role = (p.length > 1 ? p[0] : `photo_${i + 1}`).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    if (!/^https?:\/\/\S+$/.test(url)) { problem(`${LABELS.picture_links}: "${line}" is not a web link.`); return; }
    if (!/^[a-z0-9_]{2,30}$/.test(role)) { problem(`${LABELS.picture_links}: the label in "${line}" should be 2 to 30 letters or numbers.`); return; }
    pictures.push({ role, url });
  });

  // ---- facts the page may say
  const simpleList = (field, max, make) => {
    const out = [];
    for (const line of lines(field)) {
      const s = splitSource(line, field);
      if (!s) continue;
      const item = make(s, line);
      if (item) out.push(item);
    }
    return cap(out, max, field);
  };

  const trust = simpleList('trust_points', 6, (s, line) => textOk(s.body, 'trust_points', line) && { text: s.body, source: s.source });
  if (trust.length) facts.trust_points = trust;

  const benefits = simpleList('benefits', 6, (s, line) => {
    const [t, ...rest] = parts(s.body);
    const more = rest.join(' | ');
    if (!textOk(t, 'benefits', line) || !(!more || textOk(more, 'benefits', line))) return null;
    return more ? { title: t, text: more, source: s.source } : { title: t, source: s.source };
  });
  if (benefits.length) facts.benefits = benefits;

  const storyHeading = raw('story_heading');
  const storyBody = raw('story_body');
  if (storyHeading) {
    const s = splitSource(storyHeading, 'story_heading');
    if (s && textOk(s.body, 'story_heading', storyHeading) && (!storyBody || textOk(storyBody, 'story_body', storyBody))) {
      facts.story = storyBody ? { heading: s.body, body: storyBody, source: s.source } : { heading: s.body, source: s.source };
    }
  } else if (storyBody) {
    problem(`${LABELS.story_body} was given without a ${LABELS.story_heading}, so the story was left out.`);
  }

  const stepLines = lines('steps');
  if (stepLines.length) {
    const items = [];
    let stepSource = null;
    for (const line of stepLines) {
      const s = splitSource(line, 'steps');
      if (!s || !textOk(s.body, 'steps', line)) continue;
      items.push(s.body);
      stepSource = stepSource || s.source;
    }
    if (items.length < 2) problem(`${LABELS.steps}: at least 2 steps are needed, so the steps were left out.`);
    else facts.steps = { items: cap(items, 5, 'steps'), source: stepSource };
  }

  const keyFacts = simpleList('key_facts', 6, (s, line) => {
    const [value, label, note] = parts(s.body);
    if (!value || !label) { problem(`${LABELS.key_facts}: "${line}" should look like "400 g | Net weight".`); return null; }
    if (value.length > 40) { problem(`${LABELS.key_facts}: the value "${value}" is longer than 40 characters.`); return null; }
    if (!textOk(label, 'key_facts', line)) return null;
    if (note && note.length > 200) { problem(`${LABELS.key_facts}: the note "${note.slice(0, 40)}..." is longer than 200 characters.`); return null; }
    const item = { value, label, source: s.source };
    if (note) item.note = note;
    return item;
  });
  if (keyFacts.length) facts.key_facts = keyFacts;

  const pack = simpleList('pack_contents', 6, (s, line) => {
    const [name, detail] = parts(s.body);
    if (!textOk(name, 'pack_contents', line)) return null;
    return detail ? { name, detail, source: s.source } : { name, source: s.source };
  });
  if (pack.length) facts.pack_contents = pack;

  const freeFrom = simpleList('free_from', 12, (s, line) => textOk(s.body, 'free_from', line) && { name: s.body, source: s.source });
  if (freeFrom.length) facts.free_from = freeFrom;

  const faqs = simpleList('faqs', 12, (s, line) => {
    const [q, ...rest] = parts(s.body);
    const a = rest.join(' | ');
    if (!q || !a) { problem(`${LABELS.faqs}: "${line}" should look like "Question? | Answer".`); return null; }
    if (!textOk(q, 'faqs', line) || !textOk(a, 'faqs', line)) return null;
    return { q, a, source: s.source };
  });
  if (faqs.length) facts.faqs = faqs;

  const reviews = simpleList('reviews', 8, (s, line) => {
    const [stars, who, ...rest] = parts(s.body);
    const quote = rest.join(' | ');
    const rating = Number(stars);
    if (!Number.isInteger(rating) || rating < 1 || rating > 5 || !who || !quote) {
      problem(`${LABELS.reviews}: "${line}" should look like "5 | Name, City | What they wrote [where it was posted]".`);
      return null;
    }
    if (!textOk(quote, 'reviews', line)) return null;
    const [name, ...place] = who.split(',').map((x) => x.trim());
    const item = { quote, name, rating, source: s.source };
    if (place.length && place.join(', ')) item.location = place.join(', ');
    return item;
  });
  if (reviews.length) facts.reviews = reviews;

  const ratingLine = raw('rating');
  if (ratingLine) {
    const s = splitSource(ratingLine, 'rating');
    if (s) {
      if (/^[0-5](\.[0-9])?$/.test(s.body) && Number(s.body) <= 5) facts.rating = { value: s.body, source: s.source };
      else problem(`${LABELS.rating}: "${ratingLine}" should be a number from 0 to 5 with at most one decimal, like 4.6.`);
    }
  }

  const guarantees = simpleList('guarantees', 4, (s, line) => textOk(s.body, 'guarantees', line) && { text: s.body, source: s.source });
  if (guarantees.length) facts.guarantees = guarantees;

  const compLines = lines('comparison_rows');
  if (compLines.length) {
    const rows = [];
    let compSource = null;
    for (const line of compLines) {
      const s = splitSource(line, 'comparison_rows');
      if (!s) continue;
      const [ours, other] = parts(s.body);
      if (!ours || !other) { problem(`${LABELS.comparison_rows}: "${line}" should look like "Us | Them".`); continue; }
      if (!textOk(ours, 'comparison_rows', line) || !textOk(other, 'comparison_rows', line)) continue;
      rows.push({ ours, other });
      compSource = compSource || s.source;
    }
    if (rows.length < 3) problem(`${LABELS.comparison_rows}: at least 3 rows are needed, so the comparison was left out.`);
    else {
      const comparison = { rows: cap(rows, 10, 'comparison_rows'), claims_approved: raw('comparison_approved') !== '', source: compSource };
      if (brand.brand_name) comparison.ours_label = brand.brand_name;
      const otherLabel = raw('comparison_other_label');
      if (otherLabel) comparison.other_label = otherLabel;
      facts.comparison = comparison;
    }
  }

  const tagline = raw('buybox_tagline');
  if (tagline) {
    const s = splitSource(tagline, 'buybox_tagline');
    if (s && s.body.length > 40) problem(`${LABELS.buybox_tagline}: "${s.body}" is longer than 40 characters.`);
    else if (s && s.body) facts.buybox = { tagline: s.body, source: s.source };
  }

  if (!raw('facts_confirmed')) problem(`${LABELS.facts_confirmed}: the facts were not confirmed as true.`);

  return {
    submitted_at: String(answers.submittedAt || ''),
    status: problems.length ? 'needs-fixes' : 'new',
    store_domain: storeDomain,
    theme_id: themeId,
    brand_name: brandName,
    product_title: title,
    problems: problems.join('\n'),
    problem_count: problems.length,
    brand_json: JSON.stringify(brand),
    facts_json: JSON.stringify(facts),
    picture_links_json: JSON.stringify(pictures),
    logo_link: logoLink,
    notes: raw('notes'),
    raw_json: JSON.stringify(answers),
  };
}

return { json: buildIntake($json) };
