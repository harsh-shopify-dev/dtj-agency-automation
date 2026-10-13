/**
 * <dtj-video-reviews>
 * Video Reviews. Markup contract: .dtj-vr__card children of .dtj-vr__stage, each with data-d = its distance from the centre card
 * (0, -2..2, or "x" for hidden); .dtj-vr__arrow buttons carry data-dir (-1 / 1); .dtj-vr__play carries data-src (the video file).
 * The script only moves data-d between the cards (the CSS does the rest). A video file is requested ONLY when a visitor presses play:
 * nothing but the pictures loads with the page. Autoplay of the carousel (data-auto) runs only while it is on screen, never while a
 * video plays or the pointer is over it, and never for visitors who ask their device for less motion.
 */
class DtjVideoReviews extends HTMLElement {
  connectedCallback() {
    this.cards = Array.from(this.querySelectorAll('.dtj-vr__card'));
    this.n = this.cards.length;
    this.a = 0;
    this.addEventListener('click', (event) => {
      const arrow = event.target.closest('.dtj-vr__arrow');
      if (arrow) { this.go(this.a + Number(arrow.dataset.dir)); return; }
      const card = event.target.closest('.dtj-vr__card');
      if (!card) return;
      const close = event.target.closest('.dtj-vr__close');
      if (close) { this.stop(); return; }
      if (card !== this.cards[this.a]) { event.preventDefault(); this.go(this.cards.indexOf(card)); return; }
      const play = event.target.closest('.dtj-vr__play');
      if (play) this.play(card, play);
    });
    if (this.n < 2) return;
    this.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') this.go(this.a - 1);
      if (event.key === 'ArrowRight') this.go(this.a + 1);
    });
    let startX = null;
    const stage = this.querySelector('.dtj-vr__stage');
    stage.addEventListener('pointerdown', (event) => { startX = event.clientX; }, { passive: true });
    stage.addEventListener('pointerup', (event) => {
      if (startX !== null && Math.abs(event.clientX - startX) > 40) this.go(this.a + (event.clientX < startX ? 1 : -1));
      startX = null;
    }, { passive: true });
    stage.addEventListener('pointercancel', () => { startX = null; }, { passive: true });
    this.addEventListener('pointerenter', (event) => { if (event.pointerType === 'mouse') this.hover = true; });
    this.addEventListener('pointerleave', () => { this.hover = false; });
    this.addEventListener('focusin', () => { this.hover = true; });
    this.addEventListener('focusout', () => { this.hover = false; });
    this.watch();
  }

  disconnectedCallback() {
    clearInterval(this.timer);
    if (this.io) this.io.disconnect();
  }

  watch() {
    this.io = new IntersectionObserver((entries) => {
      this.visible = entries[entries.length - 1].isIntersecting;
      if (!this.visible) this.stop();
    });
    this.io.observe(this);
    const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (this.dataset.auto === 'true' && !calm) {
      this.timer = setInterval(() => {
        if (this.visible && !this.hover && !this.playing) this.go(this.a + 1);
      }, Number(this.dataset.seconds || 5) * 1000);
    }
  }

  go(next) {
    this.stop();
    const n = this.n;
    const h = n >> 1;
    this.a = ((next % n) + n) % n;
    this.cards.forEach((card, k) => {
      const d = ((k - this.a + n + h) % n) - h;
      card.dataset.d = Math.abs(d) <= 2 ? String(d) : 'x';
      if (d !== 0) card.setAttribute('aria-hidden', 'true'); else card.removeAttribute('aria-hidden');
      card.querySelectorAll('a, button.dtj-vr__play').forEach((el) => el.setAttribute('tabindex', d === 0 ? '0' : '-1'));
    });
  }

  play(card, button) {
    const src = button.dataset.src;
    if (!src) return;
    this.stop();
    const video = document.createElement('video');
    video.className = 'dtj-vr__video';
    video.src = src;
    video.controls = true;
    video.autoplay = true;
    video.playsInline = true;
    video.setAttribute('controlslist', 'nodownload');
    video.addEventListener('ended', () => this.stop());
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'dtj-vr__close';
    close.setAttribute('aria-label', 'Close video');
    close.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    card.querySelector('.dtj-vr__media').append(video);
    card.append(close);
    card.classList.add('is-playing');
    this.playing = card;
    const started = video.play();
    if (started && started.catch) started.catch(() => {});
  }

  stop() {
    const card = this.playing;
    if (!card) return;
    this.playing = null;
    card.classList.remove('is-playing');
    const video = card.querySelector('.dtj-vr__video');
    if (video) { video.pause(); video.removeAttribute('src'); video.load(); video.remove(); }
    const close = card.querySelector('.dtj-vr__close');
    if (close) close.remove();
  }
}

if (!customElements.get('dtj-video-reviews')) customElements.define('dtj-video-reviews', DtjVideoReviews);
