// DTJ page audit: paste the whole file into the built-in browser's javascript tool on a LIVE product page (phone preset first,
// then desktop). Returns one JSON object of measured facts for the CRO rubric. Read-only: it changes nothing on the page.
(() => {
  const vw = document.documentElement.clientWidth, vh = window.innerHeight;
  const visible = (e) => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && Number(s.opacity) > 0.05; };
  const top = (e) => e.getBoundingClientRect().top + window.scrollY;
  const text = (e) => (e.innerText || e.textContent || '').replace(/\s+/g, ' ').trim();
  const norm = (t) => t.toLowerCase().replace(/[^a-z0-9ऀ-ॿ ]+/g, ' ').replace(/\s+/g, ' ').trim();

  // 1. first screen (what a shopper sees before scrolling)
  const inFirst = (e) => visible(e) && e.getBoundingClientRect().top < vh && e.getBoundingClientRect().bottom > 0;
  const all = [...document.querySelectorAll('body *')];
  const buttons = [...document.querySelectorAll('button, a, input[type=submit]')].filter(visible);
  const buyRe = /(add to cart|buy now|buy it now|sold out|get (my|your)|shop now|order now)/i;
  const buy = buttons.filter((b) => buyRe.test(text(b) || b.value || ''));
  const priceEls = all.filter((e) => e.children.length === 0 && /(₹|rs\.?|inr)\s?\d/i.test(text(e)));
  const h1 = [...document.querySelectorAll('h1')].filter(visible).map(text);
  const mainBuy = buy.find((b) => /(add to cart|buy|sold out)/i.test(text(b) || b.value || ''));
  const visibleFraction = (e) => { if (!e) return 0; const r = e.getBoundingClientRect(); const seen = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0)); return r.height ? Math.round(100 * seen / r.height) / 100 : 0; };
  const firstScreen = {
    h1, price_visible: priceEls.some(inFirst), buy_button_visible: buy.some(inFirst), buy_button_visible_fraction: visibleFraction(mainBuy),
    rating_visible: all.some((e) => inFirst(e) && /★|rated\s+\d|\d\.\d\s*(\/|out of)\s*5|reviews?\b/i.test(e.children.length ? '' : text(e))),
  };

  // 2. buttons that ask for the sale
  const ctas = buy.map((b) => ({ label: text(b) || b.value, y: Math.round(top(b)) })).filter((c) => c.label);
  const ys = ctas.map((c) => c.y).sort((a, b) => a - b);
  // Horizon can scroll an inner wrapper: take the tallest of the document, the body and the lowest visible element
  const pageH = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight,
    ...[...document.querySelectorAll('[id^="shopify-section-"]')].map((e) => Math.round(e.getBoundingClientRect().bottom + window.scrollY)));
  let maxGap = ys.length ? Math.max(ys[0], pageH - ys[ys.length - 1]) : pageH;
  for (let i = 1; i < ys.length; i++) maxGap = Math.max(maxGap, ys[i] - ys[i - 1]);

  // 3. repetition: sentences and pictures used more than once
  // a marquee repeats its own items to loop (the copy is aria-hidden): that is not repetition
  const blocks = all.filter((e) => visible(e) && !e.closest('[aria-hidden="true"]') && /^(P|H1|H2|H3|H4|LI|SPAN|DIV|BLOCKQUOTE|SUMMARY|DT|DD)$/.test(e.tagName)
    && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 0));
  const counts = {};
  for (const e of blocks) for (const s of text(e).split(/(?<=[.!?])\s+/)) { const k = norm(s); if (k.length >= 18) counts[k] = (counts[k] || 0) + 1; }
  const repeatedText = Object.entries(counts).filter(([, n]) => n > 1).sort((a, b) => b[1] - a[1]).slice(0, 25).map(([t, n]) => ({ text: t, times: n }));
  const imgCounts = {};
  for (const i of document.querySelectorAll('img')) { if (!visible(i)) continue; const k = (i.currentSrc || i.src || '').split('?')[0].replace(/_\d+x\d*(?=\.)/, ''); if (k) imgCounts[k] = (imgCounts[k] || 0) + 1; }
  const repeatedImages = Object.entries(imgCounts).filter(([, n]) => n > 2).map(([src, n]) => ({ src: src.split('/').pop(), times: n }));

  // 4. legibility and touch
  const tinyText = blocks.filter((e) => parseFloat(getComputedStyle(e).fontSize) < 12 && text(e).length > 3).length;
  const smallTargets = buttons.filter((b) => { const r = b.getBoundingClientRect(); return (r.width < 40 || r.height < 40) && !b.closest('p, li'); })
    .slice(0, 30).map((b) => (text(b) || b.getAttribute('aria-label') || b.tagName).slice(0, 40));
  const noAlt = [...document.querySelectorAll('img')].filter((i) => visible(i) && !i.hasAttribute('alt')).length;

  // 5. layout
  const overflowing = document.documentElement.scrollWidth > vw + 1;
  const sections = [...document.querySelectorAll('[id^="shopify-section-"]')].filter(visible).map((s) => s.id.replace('shopify-section-', ''));
  const headings = [...document.querySelectorAll('h1, h2, h3')].filter(visible).map((h) => `${h.tagName}: ${text(h).slice(0, 80)}`);
  const moving = document.getAnimations ? document.getAnimations().filter((a) => a.playState === 'running' && a.effect && a.effect.target && inFirst(a.effect.target)).length : null;

  // pictures (for palette_report.py --mask) and fonts actually used
  const images = [...document.querySelectorAll('img, video')].filter((i) => visible(i) && i.getBoundingClientRect().width > 60)
    .map((i) => { const r = i.getBoundingClientRect(); return { x: Math.round(r.left), y: Math.round(r.top + window.scrollY), w: Math.round(r.width), h: Math.round(r.height) }; });
  const fontOf = (e) => e ? getComputedStyle(e).fontFamily.split(',')[0].replace(/["']/g, '').trim() : null;
  const fonts = { h1: fontOf(document.querySelector('h1')), h2: fontOf([...document.querySelectorAll('h2')].find(visible)), body: fontOf(document.querySelector('p') || document.body) };

  return {
    url: location.href, viewport: [vw, vh], page_width: vw, page_height: pageH, overflowing_sideways: overflowing, fonts, images,
    sold_out: buy.some((b) => /sold out/i.test(text(b))),
    first_screen: firstScreen,
    ctas: { count: ctas.length, labels: [...new Set(ctas.map((c) => c.label.toLowerCase()))], longest_gap_px: Math.round(maxGap), list: ctas.slice(0, 30) },
    repetition: { sentences: repeatedText, images_used_3plus: repeatedImages },
    legibility: { text_under_12px: tinyText, small_tap_targets: smallTargets, images_without_alt: noAlt },
    structure: { sections, headings, animations_running_in_first_screen: moving },
  };
})()
