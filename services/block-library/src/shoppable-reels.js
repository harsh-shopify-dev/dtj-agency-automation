/**
 * <dtj-reels>
 * Plays each reel video muted while at least 60% of it is on screen, pauses it
 * when it leaves, and lets the shopper tap to play with sound or pause.
 * A reel the shopper paused by hand is never resumed automatically.
 * Button labels come from data-play-label / data-pause-label (translatable in the block settings).
 */
class DtjReels extends HTMLElement {
  connectedCallback() {
    this.videos = Array.from(this.querySelectorAll('video'));
    this.manuallyPaused = new WeakSet();
    this.reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    this.addEventListener('click', (event) => {
      const button = event.target.closest('[data-toggle]');
      const video = button
        ? document.getElementById(button.dataset.target)
        : event.target.closest('video');
      if (video) this.toggle(video);
    });

    if (this.videos.length === 0) return;
    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const video = entry.target;
          if (entry.isIntersecting && !this.manuallyPaused.has(video) && !this.reduceMotion) {
            video.muted = true;
            video.play().catch(() => {});
          } else if (!entry.isIntersecting) {
            video.pause();
          }
          this.sync(video);
        });
      },
      { root: this, threshold: 0.6 }
    );
    this.videos.forEach((video) => this.observer.observe(video));
  }

  disconnectedCallback() {
    this.observer?.disconnect();
  }

  button(video) {
    return this.querySelector(`[data-target="${video.id}"]`);
  }

  sync(video) {
    const button = this.button(video);
    if (!button) return;
    const playing = !video.paused;
    button.classList.toggle('is-playing', playing);
    button.setAttribute('aria-label', playing ? this.dataset.pauseLabel || 'Pause video' : this.dataset.playLabel || 'Play video');
  }

  toggle(video) {
    if (video.paused) {
      this.manuallyPaused.delete(video);
      video.muted = false;
      video.play().catch(() => {});
    } else {
      this.manuallyPaused.add(video);
      video.pause();
    }
    this.sync(video);
  }
}

if (!customElements.get('dtj-reels')) {
  customElements.define('dtj-reels', DtjReels);
}
