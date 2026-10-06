/**
 * <dtj-ts>
 * Arrows and dots for the testimonials slider. The cards are a native scroll-snap row (swipe works with no script);
 * this adds the buttons and the dots, one dot per "page" (a screenful of cards). Markup contract: [data-track] is the
 * scrolling row, [data-nav] the (initially hidden) controls, [data-prev] / [data-next] the arrows, [data-dots] the dot holder.
 */
class DtjTs extends HTMLElement {
  connectedCallback() {
    this.track = this.querySelector('[data-track]');
    this.nav = this.querySelector('[data-nav]');
    if (!this.track || !this.nav) return;
    this.prev = this.querySelector('[data-prev]');
    this.next = this.querySelector('[data-next]');
    this.dots = this.querySelector('[data-dots]');

    this.prev?.addEventListener('click', () => this.page(-1));
    this.next?.addEventListener('click', () => this.page(1));
    this.track.addEventListener('scroll', () => this.update(), { passive: true });
    this.resizer = new ResizeObserver(() => this.rebuild());
    this.resizer.observe(this.track);
    this.rebuild();
  }

  disconnectedCallback() {
    this.resizer?.disconnect();
  }

  pages() {
    // a partly filled last page still counts (4 cards, 3 in view = 2 pages); the small allowance ignores rounding noise
    return Math.max(1, Math.ceil(this.track.scrollWidth / this.track.clientWidth - 0.05));
  }

  page(step) {
    const width = this.track.clientWidth;
    this.track.scrollTo({ left: this.track.scrollLeft + step * width, behavior: 'smooth' });
  }

  rebuild() {
    const count = this.pages();
    this.nav.hidden = count < 2; // everything already fits: no controls
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
    const current = atEnd ? this.pages() - 1 : Math.round(this.track.scrollLeft / width); // the last page cannot scroll a full width, so it is "at the end"
    this.dots?.querySelectorAll('.dtj-ts__dot').forEach((dot, index) => dot.setAttribute('aria-current', String(index === current)));
    this.prev?.setAttribute('aria-disabled', String(this.track.scrollLeft <= 2));
    this.next?.setAttribute('aria-disabled', String(atEnd));
  }
}

if (!customElements.get('dtj-ts')) customElements.define('dtj-ts', DtjTs);
