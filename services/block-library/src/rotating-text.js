/**
 * <dtj-rotating-text>
 * Typewriter effect that cycles through the phrases in data-phrases (JSON array).
 * Speeds (ms) come from data-type-speed, data-delete-speed and data-pause.
 * Leaves the first phrase static when the shopper prefers reduced motion.
 */
class DtjRotatingText extends HTMLElement {
  connectedCallback() {
    this.target = this.querySelector('[data-typed]');
    let phrases = [];
    try {
      phrases = JSON.parse(this.dataset.phrases || '[]');
    } catch (error) {
      phrases = [];
    }
    if (!this.target || phrases.length < 2) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    this.phrases = phrases;
    this.typeSpeed = Number(this.dataset.typeSpeed) || 60;
    this.deleteSpeed = Number(this.dataset.deleteSpeed) || 30;
    this.pause = Number(this.dataset.pause) || 1800;
    this.index = 0;
    this.length = 0;
    this.deleting = false;
    this.target.textContent = '';
    this.timer = setTimeout(() => this.tick(), this.typeSpeed);
  }

  disconnectedCallback() {
    clearTimeout(this.timer);
  }

  tick() {
    const phrase = this.phrases[this.index];
    this.length += this.deleting ? -1 : 1;
    this.target.textContent = phrase.substring(0, this.length);

    let delay = this.deleting ? this.deleteSpeed : this.typeSpeed;
    if (!this.deleting && this.length === phrase.length) {
      this.deleting = true;
      delay = this.pause;
    } else if (this.deleting && this.length === 0) {
      this.deleting = false;
      this.index = (this.index + 1) % this.phrases.length;
    }
    this.timer = setTimeout(() => this.tick(), delay);
  }
}

if (!customElements.get('dtj-rotating-text')) {
  customElements.define('dtj-rotating-text', DtjRotatingText);
}
