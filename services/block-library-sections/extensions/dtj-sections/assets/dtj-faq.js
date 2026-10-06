/**
 * <dtj-faq>
 * Category pills for the FAQ. Markup contract: .dtj-faq__pill buttons carry data-cat ("all" or 1-4),
 * .dtj-faq__item <details> elements carry data-cat (0 = no category, shown only under "all").
 */
class DtjFaq extends HTMLElement {
  connectedCallback() {
    this.pills = Array.from(this.querySelectorAll('.dtj-faq__pill'));
    this.items = Array.from(this.querySelectorAll('.dtj-faq__item'));
    this.pills.forEach((pill) => pill.addEventListener('click', () => this.filter(pill)));
  }

  filter(active) {
    const cat = active.dataset.cat;
    this.pills.forEach((pill) => pill.setAttribute('aria-pressed', String(pill === active)));
    this.items.forEach((item) => {
      const show = cat === 'all' || item.dataset.cat === cat;
      item.hidden = !show;
      if (!show) item.removeAttribute('open');
    });
  }
}

if (!customElements.get('dtj-faq')) customElements.define('dtj-faq', DtjFaq);
