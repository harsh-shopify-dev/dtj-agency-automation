/**
 * <dtj-category-slider>
 * Category Slider. Markup contract: .dtj-cr__track is a native scroll-snap row of .dtj-cr__tile items; .dtj-cr__arrow buttons carry data-dir (-1 / 1).
 * Touch, trackpad and keyboard scrolling are the browser's own. This script only moves the row by one tile when an arrow is pressed and switches an arrow
 * off at the end of the row. It reads sizes only when an arrow is pressed or the row scrolls (once per frame), never while the page loads.
 */
class DtjCategorySlider extends HTMLElement {
  connectedCallback() {
    this.track = this.querySelector('.dtj-cr__track');
    this.prev = this.querySelector('.dtj-cr__prev');
    this.next = this.querySelector('.dtj-cr__next');
    if (!this.track || !this.prev || !this.next) return;
    this.calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.queued = false;
    this.addEventListener('click', (event) => {
      const arrow = event.target.closest('.dtj-cr__arrow');
      if (arrow) this.move(Number(arrow.dataset.dir));
    });
    this.track.addEventListener('scroll', () => this.queue(), { passive: true });
    window.addEventListener('resize', () => this.queue(), { passive: true });
    this.queue();
  }

  move(dir) {
    const tile = this.track.querySelector('.dtj-cr__tile');
    if (!tile) return;
    const step = tile.getBoundingClientRect().width + parseFloat(getComputedStyle(this.track).columnGap || 0);
    this.track.scrollBy({ left: dir * step, behavior: this.calm ? 'auto' : 'smooth' });
  }

  queue() {
    if (this.queued) return;
    this.queued = true;
    requestAnimationFrame(() => {
      this.queued = false;
      const t = this.track;
      this.prev.disabled = t.scrollLeft < 2;
      this.next.disabled = t.scrollLeft + t.clientWidth >= t.scrollWidth - 2;
    });
  }
}

if (!customElements.get('dtj-category-slider')) customElements.define('dtj-category-slider', DtjCategorySlider);
