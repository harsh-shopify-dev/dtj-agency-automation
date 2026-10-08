/**
 * <dtj-ts>
 * Testimonials slider extras. The cards are a native scroll-snap row (swipe works with no script); this adds the arrows, the dots
 * and the "view more" links. Markup contract: [data-track] is the scrolling row, [data-prev] / [data-next] the arrows, [data-dots]
 * the dot holder (all start hidden and are shown only when there is more than one page), [data-more-toggle] a button inside a card
 * whose text has a [data-short] and a [data-full] part. Link labels come from this element's data-more / data-less attributes.
 */
class DtjTs extends HTMLElement {
  connectedCallback() {
    this.track = this.querySelector('[data-track]');
    if (!this.track) return;
    this.prev = this.querySelector('[data-prev]');
    this.next = this.querySelector('[data-next]');
    this.dots = this.querySelector('[data-dots]');
    this.controls = [this.prev, this.next, this.dots].filter(Boolean);

    this.prev?.addEventListener('click', () => this.page(-1));
    this.next?.addEventListener('click', () => this.page(1));
    this.track.addEventListener('scroll', () => this.update(), { passive: true });
    this.querySelectorAll('[data-more-toggle]').forEach((button) => button.addEventListener('click', () => this.toggle(button)));

    if (this.controls.length) {
      this.resizer = new ResizeObserver(() => this.rebuild());
      this.resizer.observe(this.track);
      this.rebuild();
    }
  }

  disconnectedCallback() {
    this.resizer?.disconnect();
  }

  toggle(button) {
    const card = button.closest('[data-slide]');
    const short = card.querySelector('[data-short]');
    const full = card.querySelector('[data-full]');
    const open = full.hidden; // currently showing the short text: open the full one
    full.hidden = !open;
    short.hidden = open;
    button.setAttribute('aria-expanded', String(open));
    button.textContent = open ? this.dataset.less : this.dataset.more;
  }

  pages() {
    // a partly filled last page still counts (4 cards, 3 in view = 2 pages); the small allowance ignores rounding noise
    return Math.max(1, Math.ceil(this.track.scrollWidth / this.track.clientWidth - 0.05));
  }

  page(step) {
    this.track.scrollTo({ left: this.track.scrollLeft + step * this.track.clientWidth, behavior: 'smooth' });
  }

  rebuild() {
    const count = this.pages();
    this.controls.forEach((control) => {
      control.hidden = count < 2; // everything already fits: no controls
    });
    if (this.dots) {
      this.dots.replaceChildren(
        ...Array.from({ length: count }, (_, index) => {
          const dot = document.createElement('button');
          dot.type = 'button';
          dot.className = 'dtj-ts__dot';
          dot.setAttribute('aria-label', `Go to page ${index + 1}`);
          dot.addEventListener('click', () => this.track.scrollTo({ left: index * this.track.clientWidth, behavior: 'smooth' }));
          return dot;
        })
      );
    }
    this.update();
  }

  update() {
    const width = this.track.clientWidth || 1;
    const atEnd = this.track.scrollLeft + width >= this.track.scrollWidth - 2;
    const current = atEnd ? this.pages() - 1 : Math.round(this.track.scrollLeft / width); // the last page cannot scroll a full width
    this.dots?.querySelectorAll('.dtj-ts__dot').forEach((dot, index) => dot.setAttribute('aria-current', String(index === current)));
    this.prev?.setAttribute('aria-disabled', String(this.track.scrollLeft <= 2));
    this.next?.setAttribute('aria-disabled', String(atEnd));
  }
}

if (!customElements.get('dtj-ts')) customElements.define('dtj-ts', DtjTs);
