/**
 * <dtj-testimonials>
 * Auto-advancing review carousel (translateX track). Attributes:
 *   data-interval  seconds per review
 * Markup contract: [data-track] holds [data-slide] items, [data-next] is the
 * next button, [data-progress] is the optional progress bar.
 * Pauses on hover, focus and when scrolled off screen; swipe on touch screens.
 */
class DtjTestimonials extends HTMLElement {
  connectedCallback() {
    this.track = this.querySelector('[data-track]');
    this.slides = Array.from(this.querySelectorAll('[data-slide]'));
    this.nextButton = this.querySelector('[data-next]');
    this.progress = this.querySelector('[data-progress]');
    if (!this.track || this.slides.length < 2) return;

    this.current = 0;
    this.interval = (Number(this.dataset.interval) || 5) * 1000;
    this.visible = true;
    this.hovered = false;
    this.reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    this.nextButton?.addEventListener('click', () => this.goTo(this.current + 1));
    this.addEventListener('mouseenter', () => this.setPaused(true, 'hovered'));
    this.addEventListener('mouseleave', () => this.setPaused(false, 'hovered'));
    this.addEventListener('focusin', () => this.setPaused(true, 'focused'));
    this.addEventListener('focusout', () => this.setPaused(false, 'focused'));

    let startX = 0;
    this.track.addEventListener(
      'touchstart',
      (event) => {
        startX = event.touches[0].clientX;
      },
      { passive: true }
    );
    this.track.addEventListener(
      'touchend',
      (event) => {
        const diff = startX - event.changedTouches[0].clientX;
        if (Math.abs(diff) > 40) this.goTo(this.current + (diff > 0 ? 1 : -1));
      },
      { passive: true }
    );

    this.observer = new IntersectionObserver(([entry]) => {
      this.visible = entry.isIntersecting;
      this.schedule();
    });
    this.observer.observe(this);
    this.schedule();
  }

  disconnectedCallback() {
    clearTimeout(this.timer);
    this.observer?.disconnect();
  }

  setPaused(paused, reason) {
    this[reason] = paused;
    this.toggleAttribute('data-paused', Boolean(this.hovered || this.focused));
    this.schedule();
  }

  schedule() {
    clearTimeout(this.timer);
    if (this.reduceMotion || !this.visible || this.hovered || this.focused) return;
    this.timer = setTimeout(() => this.goTo(this.current + 1), this.interval);
  }

  goTo(index) {
    const total = this.slides.length;
    this.current = ((index % total) + total) % total;
    this.track.style.transform = `translateX(${this.current * (document.dir === 'rtl' || getComputedStyle(this).direction === 'rtl' ? 100 : -100)}%)`;
    this.slides.forEach((slide, position) => slide.setAttribute('aria-hidden', String(position !== this.current)));
    if (this.progress) {
      this.progress.style.animation = 'none';
      void this.progress.offsetWidth;
      this.progress.style.animation = '';
    }
    this.schedule();
  }
}

if (!customElements.get('dtj-testimonials')) {
  customElements.define('dtj-testimonials', DtjTestimonials);
}
