/**
 * <dtj-reels>
 * Plays each reel video muted while at least 60% of it is on screen and pauses it
 * when it leaves. Tapping a reel plays it with sound: a silent reel gets its sound
 * turned on and keeps playing, a reel that already has sound is paused, a paused
 * reel plays with sound. The sound button turns sound on or off without pausing.
 * Only one reel has sound at a time. A reel the shopper paused by hand is never
 * resumed automatically.
 * Button labels come from data-play-label, data-pause-label, data-sound-on-label
 * and data-sound-off-label (translatable in the block settings).
 */
class DtjReels extends HTMLElement {
  connectedCallback() {
    this.videos = Array.from(this.querySelectorAll('video'));
    this.manuallyPaused = new WeakSet();
    this.reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    this.addEventListener('click', (event) => {
      const soundButton = event.target.closest('[data-sound]');
      if (soundButton) {
        const target = document.getElementById(soundButton.dataset.target);
        if (target) this.setSound(target, target.muted);
        return;
      }
      const button = event.target.closest('[data-toggle]');
      const video = button
        ? document.getElementById(button.dataset.target)
        : event.target.closest('video');
      if (!video) return;
      if (button) this.playPause(video);
      else this.tap(video);
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

  sync(video) {
    const toggle = this.querySelector(`[data-toggle][data-target="${video.id}"]`);
    if (toggle) {
      const playing = !video.paused;
      toggle.classList.toggle('is-playing', playing);
      toggle.setAttribute('aria-label', playing ? this.dataset.pauseLabel || 'Pause video' : this.dataset.playLabel || 'Play video');
    }
    const sound = this.querySelector(`[data-sound][data-target="${video.id}"]`);
    if (sound) {
      const on = !video.muted;
      sound.classList.toggle('is-on', on);
      sound.setAttribute('aria-pressed', String(on));
      sound.setAttribute('aria-label', on ? this.dataset.soundOffLabel || 'Turn sound off' : this.dataset.soundOnLabel || 'Turn sound on');
    }
  }

  play(video) {
    this.manuallyPaused.delete(video);
    this.setSound(video, true);
    video.play().catch(() => {});
    this.sync(video);
  }

  pause(video) {
    this.manuallyPaused.add(video);
    video.pause();
    this.sync(video);
  }

  playPause(video) {
    if (video.paused) this.play(video);
    else this.pause(video);
  }

  tap(video) {
    if (video.paused) this.play(video);
    else if (video.muted) this.setSound(video, true);
    else this.pause(video);
  }

  setSound(video, on) {
    if (on) {
      this.videos.forEach((other) => {
        if (other !== video && !other.muted) {
          other.muted = true;
          this.sync(other);
        }
      });
    }
    video.muted = !on;
    this.sync(video);
  }
}

if (!customElements.get('dtj-reels')) {
  customElements.define('dtj-reels', DtjReels);
}
