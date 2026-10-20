/**
 * <dtj-concern-slider>
 * Shop by Concern. Markup contract: a .dtj-cs__concern select (option index = panel index), .dtj-cs__panel panels each holding a .dtj-cs__track scroll
 * row of .dtj-cs__card cards, .dtj-cs__arrow buttons (data-dir -1 / 1), an optional .dtj-cs__count and .dtj-cs__thumb, and .dtj-cs__form forms whose
 * select.dtj-cs__var (name="id") lists variants with data-price, data-compare, data-off, data-available and optional data-img / data-srcset.
 * data-after ("stay" or "cart"), data-added and data-sold (words) come from the settings. Without this script the first concern shows and every cart
 * button is a normal form post of the chosen variant. It reads sizes only when a row scrolls or is resized (once per frame) and talks to the store
 * only when a visitor presses the cart button.
 */
class DtjConcernSlider extends HTMLElement {
  connectedCallback() {
    this.select = this.querySelector('.dtj-cs__concern');
    this.panels = Array.from(this.querySelectorAll('.dtj-cs__panel'));
    this.status = this.querySelector('.dtj-cs__status');
    this.calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.queued = false;
    this.active = 0;
    if (this.select) this.select.addEventListener('change', () => this.show(Number(this.select.value)));
    this.addEventListener('click', (event) => {
      const arrow = event.target.closest('.dtj-cs__arrow');
      if (arrow) this.move(Number(arrow.dataset.dir));
    });
    this.addEventListener('change', (event) => {
      if (event.target.classList.contains('dtj-cs__var')) this.pick(event.target);
    });
    this.addEventListener('submit', (event) => {
      const form = event.target.closest('.dtj-cs__form');
      if (form) { event.preventDefault(); this.add(form); }
    });
    this.querySelectorAll('.dtj-cs__track').forEach((track) => track.addEventListener('scroll', () => this.queue(), { passive: true }));
    window.addEventListener('resize', () => this.queue(), { passive: true });
    this.queue();
  }

  track() {
    return this.panels[this.active].querySelector('.dtj-cs__track');
  }

  show(index) {
    if (index < 0 || index >= this.panels.length) return;
    this.active = index;
    this.panels.forEach((panel, i) => { panel.hidden = i !== index; });
    this.track().scrollLeft = 0;
    this.queue();
  }

  move(dir) {
    const track = this.track();
    const card = track.querySelector('.dtj-cs__card');
    if (!card) return;
    const step = card.getBoundingClientRect().width + parseFloat(getComputedStyle(track).columnGap || 0);
    track.scrollBy({ left: dir * step, behavior: this.calm ? 'auto' : 'smooth' });
  }

  // the arrows, the faded edge, the counter and the progress line all follow the row's scroll position
  queue() {
    if (this.queued) return;
    this.queued = true;
    requestAnimationFrame(() => {
      this.queued = false;
      const panel = this.panels[this.active];
      const t = this.track();
      const max = Math.max(t.scrollWidth, 1);
      const atEnd = t.scrollLeft + t.clientWidth >= t.scrollWidth - 2;
      panel.querySelectorAll('.dtj-cs__arrow').forEach((arrow) => {
        arrow.disabled = arrow.dataset.dir === '-1' ? t.scrollLeft < 2 : atEnd;
      });
      panel.querySelector('.dtj-cs__viewport').classList.toggle('is-end', atEnd);
      const thumb = panel.querySelector('.dtj-cs__thumb');
      if (thumb) {
        thumb.style.setProperty('--cs-tw', Math.min(100, (t.clientWidth / max) * 100) + '%');
        thumb.style.setProperty('--cs-x', (t.scrollLeft / max) * 100 + '%');
      }
      const count = panel.querySelector('.dtj-cs__count');
      const card = t.querySelector('.dtj-cs__card');
      if (count && card) {
        const total = Number(panel.dataset.total) || t.children.length;
        const step = card.getBoundingClientRect().width + parseFloat(getComputedStyle(t).columnGap || 0);
        const at = Math.min(total, Math.round(t.scrollLeft / Math.max(step, 1)) + 1);
        count.textContent = String(at).padStart(2, '0') + ' / ' + String(total).padStart(2, '0');
      }
    });
  }

  // the option dropdown changes the picture (a short fade), the price, the percent-off pill and whether the product can be added
  pick(select) {
    const card = select.closest('.dtj-cs__card');
    const data = select.selectedOptions[0].dataset;
    const img = card.querySelector('.dtj-cs__img');
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
    card.querySelectorAll('.dtj-cs__now').forEach((el) => { el.textContent = data.price; });
    card.querySelectorAll('.dtj-cs__old').forEach((el) => { el.textContent = data.compare; el.hidden = !data.compare; });
    card.querySelectorAll('.dtj-cs__off').forEach((el) => { el.textContent = data.off; el.hidden = !data.off; });
    const button = card.querySelector('.dtj-cs__add');
    const label = button.querySelector('.dtj-cs__add-label');
    const sold = data.available !== 'true';
    button.disabled = sold;
    if (sold) { button.dataset.was = button.dataset.was || label.textContent; label.textContent = this.dataset.sold || label.textContent; }
    else if (button.dataset.was) { label.textContent = button.dataset.was; delete button.dataset.was; }
  }

  add(form) {
    const button = form.querySelector('.dtj-cs__add');
    if (!button || button.disabled || button.classList.contains('is-busy')) return;
    const label = button.querySelector('.dtj-cs__add-label');
    const before = label.textContent;
    button.classList.add('is-busy');
    fetch((this.dataset.cartAdd || '/cart/add') + '.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ id: Number(form.elements.id.value), quantity: 1 }),
    })
      .then((response) => {
        if (!response.ok) throw new Error('cart');
        if (this.dataset.after === 'cart') { window.location.assign(this.dataset.cart || '/cart'); return; }
        label.textContent = this.dataset.added || before;
        if (this.status) this.status.textContent = this.dataset.added || '';
        setTimeout(() => { label.textContent = before; if (this.status) this.status.textContent = ''; }, 2200);
      })
      .catch(() => form.submit())
      .finally(() => button.classList.remove('is-busy'));
  }
}

if (!customElements.get('dtj-concern-slider')) customElements.define('dtj-concern-slider', DtjConcernSlider);
