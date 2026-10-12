// DTJ Call To Action: "scroll" buttons bring the shopper to the product's own add to cart button (one listener for every CTA on the page).
(function () {
  if (window.__dtjCta) return;
  window.__dtjCta = true;
  document.addEventListener('click', function (event) {
    var link = event.target && event.target.closest ? event.target.closest('[data-dtj-cta-scroll]') : null;
    if (!link) return;
    var form = document.querySelector('form[action*="/cart/add"]:not(.dtj-cta__form)');
    var target = form || document.querySelector('[id$="__main"]') || document.querySelector('main');
    if (!target) return;
    event.preventDefault();
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var top = target.getBoundingClientRect().top + window.pageYOffset - 80;
    window.scrollTo({ top: Math.max(0, top), behavior: reduce ? 'auto' : 'smooth' });
    var button = form && form.querySelector('button[type="submit"], [name="add"]');
    if (button) {
      setTimeout(function () {
        try { button.focus({ preventScroll: true }); } catch (e) { /* older browsers */ }
      }, reduce ? 0 : 600);
    }
  });
})();
