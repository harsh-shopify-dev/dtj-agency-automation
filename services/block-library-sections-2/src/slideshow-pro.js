/**
 * <dtj-slideshow>
 * Slideshow Pro. Markup contract: .dtj-sl__track holds .dtj-sl__slide children (the first has .is-active), .dtj-sl__arrow buttons carry
 * data-dir (-1 / 1), each slide has a .dtj-sl__fill timer element. data-auto="true" turns the timer on: when the active slide's fill animation
 * ends the next slide shows. Hovering with a mouse, or focus inside, pauses the timer; a sideways swipe or the arrow keys change the slide.
 * Visitors who ask their device for less motion get no automatic change.
 */
class DtjSlideshow extends HTMLElement {
  connectedCallback() {
    this.slides = Array.from(this.querySelectorAll('.dtj-sl__slide'));
    this.track = this.querySelector('.dtj-sl__track');
    this.index = 0;
    if (this.slides.length < 2) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      this.classList.remove('dtj-sl--auto');
    }
    this.querySelectorAll('.dtj-sl__arrow').forEach((button) => {
      button.addEventListener('click', () => this.go(this.index + Number(button.dataset.dir)));
    });
    this.querySelectorAll('.dtj-sl__fill').forEach((fill) => {
      fill.addEventListener('animationend', () => this.go(this.index + 1));
    });
    this.addEventListener('pointerenter', (event) => { if (event.pointerType === 'mouse') this.classList.add('is-paused'); });
    this.addEventListener('pointerleave', () => this.classList.remove('is-paused'));
    this.addEventListener('focusin', () => this.classList.add('is-paused'));
    this.addEventListener('focusout', () => this.classList.remove('is-paused'));
    this.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') this.go(this.index - 1);
      if (event.key === 'ArrowRight') this.go(this.index + 1);
    });
    let startX = null;
    this.track.addEventListener('pointerdown', (event) => { startX = event.clientX; });
    this.track.addEventListener('pointerup', (event) => {
      if (startX !== null && Math.abs(event.clientX - startX) > 40) this.go(this.index + (event.clientX < startX ? 1 : -1));
      startX = null;
    });
    this.track.addEventListener('pointercancel', () => { startX = null; });
  }

  go(next) {
    const count = this.slides.length;
    this.index = (next + count) % count;
    this.style.setProperty('--sl-i', this.index);
    this.slides.forEach((slide, i) => {
      const active = i === this.index;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', String(!active));
      if (active) slide.removeAttribute('inert'); else slide.setAttribute('inert', '');
      if (active) { // restart the timer line of the slide that just came in
        const fill = slide.querySelector('.dtj-sl__fill');
        if (fill) { fill.style.animation = 'none'; void fill.offsetWidth; fill.style.animation = ''; }
      }
    });
  }
}

if (!customElements.get('dtj-slideshow')) customElements.define('dtj-slideshow', DtjSlideshow);
