/**
 * <dtj-best-sellers>
 * Best Sellers. Markup contract: .dtj-bs__tab buttons (role=tab, aria-controls = a .dtj-bs__panel id), panels with a .dtj-bs__track scroll row,
 * .dtj-bs__arrow buttons (data-dir -1 / 1), .dtj-bs__form forms holding a variant id, .dtj-bs__sw variant swatches (data-id, data-price, data-compare,
 * data-available, optional data-img / data-srcset), .dtj-bs__heart buttons (data-handle) and .dtj-bs__gallery rows with .dtj-bs__dot dots.
 * data-after ("stay" or "cart"), data-added and data-sold (words) come from the settings. Without this script the first tab shows, every swatch is
 * a plain button and every cart button is a normal form post. It reads sizes only when an arrow is pressed or a row scrolls (once per frame) and talks
 * to the store only when a visitor presses the cart button. Favourites live in the visitor's own browser (localStorage), nowhere else.
 */
class DtjBestSellers extends HTMLElement {
  connectedCallback() {
    this.tabs = Array.from(this.querySelectorAll('.dtj-bs__tab'));
    this.panels = Array.from(this.querySelectorAll('.dtj-bs__panel'));
    this.prev = this.querySelector('.dtj-bs__prev');
    this.next = this.querySelector('.dtj-bs__next');
    this.status = this.querySelector('.dtj-bs__status');
    this.calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.queued = false;
    this.active = 0;
    this.addEventListener('click', (event) => {
      const tab = event.target.closest('.dtj-bs__tab');
      if (tab) { this.show(this.tabs.indexOf(tab)); return; }
      const arrow = event.target.closest('.dtj-bs__arrow');
      if (arrow) { this.move(Number(arrow.dataset.dir)); return; }
      const swatch = event.target.closest('.dtj-bs__sw');
      if (swatch) { this.pick(swatch); return; }
      const heart = event.target.closest('.dtj-bs__heart');
      if (heart) this.love(heart);
    });
    this.addEventListener('submit', (event) => {
      const form = event.target.closest('.dtj-bs__form');
      if (form) { event.preventDefault(); this.add(form); }
    });
    this.addEventListener('keydown', (event) => {
      const tab = event.target.closest('.dtj-bs__tab');
      if (!tab) return;
      const last = this.tabs.length - 1;
      const from = this.tabs.indexOf(tab);
      const to = { ArrowRight: from === last ? 0 : from + 1, ArrowLeft: from === 0 ? last : from - 1, Home: 0, End: last }[event.key];
      if (to !== undefined) { event.preventDefault(); this.show(to, true); }
    });
    this.querySelectorAll('.dtj-bs__track').forEach((track) => track.addEventListener('scroll', () => this.queue(), { passive: true }));
    this.querySelectorAll('.dtj-bs__gallery').forEach((row) => row.addEventListener('scroll', () => this.dots(row), { passive: true }));
    window.addEventListener('resize', () => this.queue(), { passive: true });
    this.restore();
    this.queue();
  }

  track() {
    return this.panels[this.active].querySelector('.dtj-bs__track');
  }

  show(index, focus) {
    if (index < 0 || index >= this.panels.length) return;
    this.active = index;
    this.tabs.forEach((tab, i) => {
      tab.setAttribute('aria-selected', String(i === index));
      tab.tabIndex = i === index ? 0 : -1;
    });
    this.panels.forEach((panel, i) => { panel.hidden = i !== index; });
    if (focus) this.tabs[index].focus();
    this.queue();
  }

  move(dir) {
    const track = this.track();
    const card = track.querySelector('.dtj-bs__card');
    if (!card) return;
    const step = card.getBoundingClientRect().width + parseFloat(getComputedStyle(track).columnGap || 0);
    track.scrollBy({ left: dir * step, behavior: this.calm ? 'auto' : 'smooth' });
  }

  queue() {
    if (this.queued) return;
    this.queued = true;
    requestAnimationFrame(() => {
      this.queued = false;
      if (!this.prev || !this.next) return;
      const t = this.track();
      this.prev.disabled = t.scrollLeft < 2;
      this.next.disabled = t.scrollLeft + t.clientWidth >= t.scrollWidth - 2;
    });
  }

  dots(row) {
    if (row.dotsQueued) return;
    row.dotsQueued = true;
    requestAnimationFrame(() => {
      row.dotsQueued = false;
      const at = Math.round(row.scrollLeft / Math.max(row.clientWidth, 1));
      row.parentElement.querySelectorAll('.dtj-bs__dot').forEach((dot, i) => dot.classList.toggle('is-on', i === at));
    });
  }

  // a swatch changes the picture (a short fade), the price, the cart variant and whether the product can be added
  pick(swatch) {
    const card = swatch.closest('.dtj-bs__card');
    card.querySelectorAll('.dtj-bs__sw').forEach((sw) => {
      sw.classList.toggle('is-on', sw === swatch);
      sw.setAttribute('aria-checked', String(sw === swatch));
    });
    const data = swatch.dataset;
    const img = card.querySelector('.dtj-bs__img--main');
    if (img && data.img && img.getAttribute('src') !== data.img) {
      const fresh = new Image();
      img.classList.add('is-fading');
      fresh.onload = fresh.onerror = () => {
        img.src = data.img;
        if (data.srcset) img.srcset = data.srcset;
        img.classList.remove('is-fading');
      };
      fresh.src = data.img;
    }
    card.querySelectorAll('.dtj-bs__now').forEach((el) => { el.textContent = data.price; });
    card.querySelectorAll('.dtj-bs__old').forEach((el) => { el.textContent = data.compare; el.hidden = !data.compare; });
    const form = card.querySelector('.dtj-bs__form');
    const button = card.querySelector('.dtj-bs__add');
    if (form) form.elements.id.value = data.id;
    if (button && button.tagName === 'BUTTON') {
      const sold = data.available !== 'true';
      button.disabled = sold;
      const label = button.querySelector('.dtj-bs__add-label');
      if (label) {
        if (sold) { button.dataset.was = label.textContent; label.textContent = this.dataset.sold || label.textContent; }
        else if (button.dataset.was) { label.textContent = button.dataset.was; delete button.dataset.was; }
      }
    }
  }

  love(heart) {
    const on = heart.getAttribute('aria-pressed') !== 'true';
    heart.setAttribute('aria-pressed', String(on));
    try {
      const saved = new Set(JSON.parse(localStorage.getItem('dtj-bs-fav') || '[]'));
      if (on) saved.add(heart.dataset.handle); else saved.delete(heart.dataset.handle);
      localStorage.setItem('dtj-bs-fav', JSON.stringify(Array.from(saved)));
    } catch (error) { /* private mode: the heart still toggles for this visit */ }
  }

  restore() {
    let saved = [];
    try { saved = JSON.parse(localStorage.getItem('dtj-bs-fav') || '[]'); } catch (error) { return; }
    this.querySelectorAll('.dtj-bs__heart').forEach((heart) => heart.setAttribute('aria-pressed', String(saved.includes(heart.dataset.handle))));
  }

  add(form) {
    const button = form.querySelector('.dtj-bs__add');
    if (!button || button.disabled || button.classList.contains('is-busy')) return;
    const label = button.querySelector('.dtj-bs__add-label');
    const before = label ? label.textContent : '';
    button.classList.add('is-busy');
    fetch((this.dataset.cartAdd || '/cart/add') + '.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ id: Number(form.elements.id.value), quantity: 1 }),
    })
      .then((response) => {
        if (!response.ok) throw new Error('cart');
        if (this.dataset.after === 'cart') { window.location.assign(this.dataset.cart || '/cart'); return; }
        if (label) label.textContent = this.dataset.added || before;
        if (this.status) this.status.textContent = this.dataset.added || '';
        setTimeout(() => { if (label) label.textContent = before; if (this.status) this.status.textContent = ''; }, 2200);
      })
      .catch(() => form.submit())
      .finally(() => button.classList.remove('is-busy'));
  }
}

if (!customElements.get('dtj-best-sellers')) customElements.define('dtj-best-sellers', DtjBestSellers);
