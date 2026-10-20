/* DTJ Product List script: gallery arrows, swatch pick / hover (picture, price, % OFF, stock, cart variant), add to cart in place (tells the theme through Shopify's standard
   cart event), the first swatch row, the carousel arrows. Talks to the store only when Add to cart is pressed. The original's page-cleaning script is left out (Harsh, 20 Oct 2026). */
(() => {
  if (window.__dtjProductList) return;
  window.__dtjProductList = true;
  let uid = 0;

  const slideFor = (card, mediaId) => (mediaId ? card.querySelector('.pl-slide[data-media-id="' + mediaId + '"]') : null);

  const showMedia = (card, mediaId) => {
    const slides = card.querySelector('[data-pl-slides]');
    const slide = slideFor(card, mediaId);
    if (!slides || !slide) return;
    slides.scrollTo({ left: slide.offsetLeft, behavior: 'smooth' });
  };

  const arrows = (card) => {
    const slides = card.querySelector('[data-pl-slides]');
    if (!slides) return;
    const prev = card.querySelector('.pl-arrow--prev');
    const next = card.querySelector('.pl-arrow--next');
    if (!prev || !next) return;
    const sync = () => {
      prev.disabled = slides.scrollLeft < 2;
      next.disabled = slides.scrollLeft + slides.clientWidth >= slides.scrollWidth - 2;
    };
    [prev, next].forEach((button) => button.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      slides.scrollBy({ left: Number(button.dataset.dir) * slides.clientWidth, behavior: 'smooth' });
    }));
    slides.addEventListener('scroll', () => requestAnimationFrame(sync), { passive: true });
    sync();
  };

  const offText = (card, cents, compare) => {
    const price = card.querySelector('[data-pl-price]');
    if (!price) return;
    const was = price.querySelector('.pl-price__was');
    const off = price.querySelector('.pl-price__off');
    const sale = compare > cents;
    if (was) {
      was.hidden = !sale;
      if (sale) was.textContent = was.dataset.text || was.textContent;
    }
    const section = card.closest('.pl');
    const pct = sale ? Math.round(((compare - cents) / compare) * 100) : 0;
    if (off) off.hidden = !sale;
    if (sale && !off) {
      const span = document.createElement('span');
      span.className = 'pl-price__off';
      price.appendChild(span);
    }
    const target = price.querySelector('.pl-price__off');
    if (target && sale) target.textContent = (section && section.dataset.offer === 'false' ? 'SAVE ' + pct + '%' : pct + '% OFF');
  };

  const swatches = (card) => {
    const form = card.querySelector('[data-pl-form]');
    const button = card.querySelector('[data-pl-add]');
    const inputs = card.querySelectorAll('[data-pl-swatches] input[type="radio"]');
    if (!inputs.length) return;
    const unique = 'pl-sw-' + (++uid);
    inputs.forEach((input) => { input.name = unique; });
    const selectedMedia = () => { const on = card.querySelector('[data-pl-swatches] input:checked'); return on ? on.dataset.mediaId : ''; };
    inputs.forEach((input) => {
      const label = input.closest('label');
      input.addEventListener('change', () => {
        const idInput = form && form.querySelector('input[name="id"]');
        if (idInput && input.dataset.variantId) idInput.value = input.dataset.variantId;
        const available = input.dataset.available !== 'false';
        if (button) {
          if (available) button.removeAttribute('disabled'); else button.setAttribute('disabled', 'true');
          const text = button.querySelector('.pl-add__text');
          if (text) text.textContent = available ? text.dataset.add : text.dataset.sold;
        }
        const now = card.querySelector('.pl-price__now');
        if (now && input.dataset.price) now.textContent = input.dataset.price;
        const was = card.querySelector('.pl-price__was');
        if (was && input.dataset.compare) was.textContent = input.dataset.compare;
        offText(card, Number(input.dataset.priceCents || 0), Number(input.dataset.compareCents || 0));
        showMedia(card, input.dataset.mediaId);
      });
      if (label) {
        label.addEventListener('pointerenter', () => showMedia(card, input.dataset.mediaId));
        label.addEventListener('pointerleave', () => showMedia(card, selectedMedia()));
      }
    });
  };

  // first swatch row: what fits beside the original's hidden "+N" slot; the rest wraps below
  const swatchRows = (card) => {
    const list = card.querySelector('.pl-swatches__list');
    const more = card.querySelector('.pl-swatches__more');
    const fieldset = card.querySelector('.pl-swatches');
    if (!list || !more || !fieldset) return;
    const lay = () => {
      while (more.firstChild) list.appendChild(more.firstChild);
      more.hidden = true;
      const items = Array.from(list.querySelectorAll('.pl-swatch-item'));
      if (items.length < 2) return;
      const gap = parseFloat(getComputedStyle(fieldset).columnGap) || 8;
      const size = items[0].getBoundingClientRect().width || 22;
      const room = list.getBoundingClientRect().width - 26 - gap;
      const fit = Math.max(1, Math.floor((room + gap) / (size + gap)));
      if (fit < items.length) {
        items.slice(fit).forEach((item) => more.appendChild(item));
        more.hidden = false;
      }
    };
    lay();
    if (window.ResizeObserver) new ResizeObserver(() => lay()).observe(fieldset);
  };

  // Shopify's standard events: current Horizon themes map '@shopify/events' to this module; their cart icon, drawer and cart items listen for the event.
  let eventsModule;
  const standardEvents = () => {
    if (!eventsModule) {
      eventsModule = import('@shopify/events').catch(() => import('https://cdn.shopify.com/storefront/standard-events.js')).catch(() => null);
    }
    return eventsModule;
  };

  const cart = (card) => {
    const form = card.querySelector('[data-pl-form]');
    const button = card.querySelector('[data-pl-add]');
    if (!form || !button) return;
    form.addEventListener('submit', (event) => {
      if (!window.fetch || button.disabled) return;
      event.preventDefault();
      const text = button.querySelector('.pl-add__text');
      button.classList.add('is-busy');
      const variantId = form.querySelector('input[name="id"]').value;
      const body = { id: Number(variantId), quantity: 1 };
      // tell the theme first (its drawer can open at once), settle with the real cart when the add is done
      const announced = standardEvents().then((mod) => {
        const Event = mod && mod.CartLinesUpdateEvent;
        if (!Event || !Event.createPromise) return null;
        const deferred = Event.createPromise();
        card.dispatchEvent(new Event({ action: 'add', context: 'product', lines: [{ merchandiseId: String(variantId), quantity: 1 }], promise: deferred.promise }));
        return { Event, deferred };
      }).catch(() => null);
      const settle = (didError) => announced.then((info) => {
        if (!info) return;
        return fetch('/cart.js', { headers: { Accept: 'application/json' }, credentials: 'same-origin' })
          .then((response) => response.json())
          .then((ajaxCart) => info.deferred.resolve({
            cart: info.Event.createCartFromAjaxResponse(ajaxCart),
            detail: { items: ajaxCart.items, source: 'dtj-product-list', sourceId: card.id || 'dtj-product-list', itemCount: 1, productId: card.dataset.productId, didError },
          }))
          .catch((error) => info.deferred.reject(error));
      });
      fetch(form.action + '.js', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(body) })
        .then((response) => {
          if (!response.ok) throw new Error('cart');
          return response.json();
        })
        .then(() => {
          button.classList.remove('is-busy');
          if (text) {
            text.textContent = text.dataset.added;
            window.setTimeout(() => { text.textContent = text.dataset.add; }, 1800);
          }
          return settle(false);
        })
        .catch(() => {
          settle(true);
          form.submit();
        });
    });
  };

  const go = (card) => {
    card.addEventListener('click', (event) => {
      if (event.target.closest('a, button, label, input, form, fieldset')) return;
      if (card.dataset.url) window.location.assign(card.dataset.url);
    });
  };

  const carousel = (root) => {
    const track = root.querySelector('[data-pl-track]');
    const prev = root.querySelector('.pl-nav--prev');
    const next = root.querySelector('.pl-nav--next');
    if (!track || !prev || !next) return;
    const sync = () => {
      prev.disabled = track.scrollLeft < 2;
      next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
    };
    [prev, next].forEach((button) => button.addEventListener('click', () => {
      const slide = track.querySelector('.pl-carousel__slide');
      const step = slide ? slide.getBoundingClientRect().width : track.clientWidth;
      track.scrollBy({ left: Number(button.dataset.nav) * step, behavior: 'smooth' });
    }));
    track.addEventListener('scroll', () => requestAnimationFrame(sync), { passive: true });
    sync();
  };

  const start = (scope) => {
    scope.querySelectorAll('[data-pl-card]').forEach((card) => {
      if (card.dataset.plReady) return;
      card.dataset.plReady = '1';
      arrows(card);
      swatches(card);
      swatchRows(card);
      cart(card);
      go(card);
    });
    scope.querySelectorAll('[data-pl-carousel]').forEach((root) => {
      if (root.dataset.plReady) return;
      root.dataset.plReady = '1';
      carousel(root);
    });
  };

  const boot = () => start(document);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
  document.addEventListener('shopify:section:load', (event) => start(event.target || document));
})();
