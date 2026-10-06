/**
 * <dtj-shade-picker>
 * A row of links to sibling products. Sold-out options cannot be followed, and the
 * name beside the label ([data-selected]) follows the option the shopper hovers or focuses,
 * going back to the current one afterwards.
 */
class DtjShadePicker extends HTMLElement {
  connectedCallback() {
    const selected = this.querySelector('[data-selected]');
    const fallback = selected ? selected.textContent : '';

    this.querySelectorAll('[data-item]').forEach((item) => {
      if (item.dataset.unavailable === 'true') {
        item.addEventListener('click', (event) => event.preventDefault());
      }
      if (!selected || !item.dataset.label) return;
      const show = () => {
        selected.textContent = item.dataset.label;
      };
      const reset = () => {
        selected.textContent = fallback;
      };
      item.addEventListener('mouseenter', show);
      item.addEventListener('focus', show);
      item.addEventListener('mouseleave', reset);
      item.addEventListener('blur', reset);
    });
  }
}

if (!customElements.get('dtj-shade-picker')) {
  customElements.define('dtj-shade-picker', DtjShadePicker);
}
