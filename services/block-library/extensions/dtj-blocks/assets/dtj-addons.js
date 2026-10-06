/* <dtj-addons>: add-on cards under the product form. Ticked add-ons go into the cart with the product in ONE
   /cart/add.js call (real prices only). Nothing ticked = the theme's own flow. Drawer opening is best effort. */
const DTJ_ADDONS_NO_FORM = 'cart-drawer, cart-drawer-component, [is="cart-drawer"], .cart-drawer, #cart-drawer';

class DtjAddons extends HTMLElement {
  connectedCallback() {
    this.cards = Array.from(this.querySelectorAll('[data-card]'));
    if (!this.cards.length) return;

    this.afterAdd = this.dataset.afterAdd || 'cart';
    this.moneyFormat = this.dataset.moneyFormat || '{{amount}}';
    this.selectLabel = this.dataset.selectLabel || '';
    this.selectedLabel = this.dataset.selectedLabel || '';
    this.totalValue = this.querySelector('[data-total-value]');
    this.prices = {};
    (this.dataset.mainPrices || '').split(',').forEach((pair) => {
      const [id, cents] = pair.split(':');
      if (id && !Number.isNaN(parseInt(cents, 10))) this.prices[id] = parseInt(cents, 10);
    });
    this.processing = false;

    this.cards.forEach((card) => this.bindCard(card));
    this.updateTotal();

    this.onVariantChange = () => this.updateTotal();
    document.addEventListener('variant:change', this.onVariantChange);
    document.addEventListener('cart:refresh', this.onVariantChange);
    this.variantInput = document.querySelector('form[action*="/cart/add"] [name="id"]');
    if (this.variantInput) {
      this.lastVariant = this.variantInput.value;
      this.poll = setInterval(() => {
        if (this.variantInput.value !== this.lastVariant) {
          this.lastVariant = this.variantInput.value;
          this.updateTotal();
        }
      }, 400);
    }

    this.onClick = (event) => this.handleClick(event);
    document.addEventListener('click', this.onClick, true);
  }

  disconnectedCallback() {
    document.removeEventListener('variant:change', this.onVariantChange);
    document.removeEventListener('cart:refresh', this.onVariantChange);
    document.removeEventListener('click', this.onClick, true);
    clearInterval(this.poll);
  }

  // ----- money -----
  formatMoney(cents) {
    const value = cents / 100;
    const placeholder = this.moneyFormat.match(/\{\{\s*(\w+)\s*\}\}/);
    const kind = placeholder ? placeholder[1] : 'amount';
    let formatted = kind.indexOf('no_decimals') > -1 ? Math.round(value).toString() : value.toFixed(2);
    if (kind.indexOf('comma_separator') > -1) {
      formatted = formatted.replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    } else {
      formatted = formatted.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }
    return this.moneyFormat.replace(/\{\{\s*\w+\s*\}\}/, formatted);
  }

  mainPrice() {
    const id = this.variantInput ? this.variantInput.value : this.dataset.mainVariant;
    return this.prices[id] != null ? this.prices[id] : this.prices[this.dataset.mainVariant] || 0;
  }

  // ----- selection -----
  selectedCards() {
    return this.cards.filter((card) => card.getAttribute('data-selected') === 'true');
  }

  activeVariant(card) {
    return card.getAttribute(card.getAttribute('data-active-variant') === 'alt' ? 'data-variant-alt' : 'data-variant-main');
  }

  activePrice(card) {
    return parseInt(card.getAttribute(card.getAttribute('data-active-variant') === 'alt' ? 'data-price-alt' : 'data-price-main'), 10);
  }

  updateTotal() {
    if (!this.totalValue) return;
    let total = this.mainPrice();
    this.selectedCards().forEach((card) => {
      const cents = this.activePrice(card);
      if (!Number.isNaN(cents)) total += cents;
    });
    this.totalValue.textContent = this.formatMoney(total);
  }

  setSelected(card, on) {
    card.setAttribute('data-selected', on ? 'true' : 'false');
    card.setAttribute('aria-pressed', on ? 'true' : 'false');
    const label = card.querySelector('[data-cta-label]');
    if (label && !card.matches('[data-sold-out="true"]')) label.textContent = on ? this.selectedLabel : this.selectLabel;
  }

  toggle(card) {
    if (card.getAttribute('data-sold-out') === 'true') return;
    this.setSelected(card, card.getAttribute('data-selected') !== 'true');
    this.changed();
  }

  changed() {
    this.updateTotal();
    const ids = this.selectedCards().map((card) => this.activeVariant(card)).filter(Boolean);
    this.setAttribute('data-selected-ids', ids.join(','));
    document.dispatchEvent(new CustomEvent('dtj:addons:change', { detail: { ids } }));
  }

  bindCard(card) {
    card.addEventListener('click', (event) => {
      if (event.target.closest('[data-swap]')) return;
      this.toggle(card);
    });
    card.addEventListener('keydown', (event) => {
      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault();
        this.toggle(card);
      }
    });
    const swaps = card.querySelectorAll('[data-swap]');
    swaps.forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        swaps.forEach((other) => other.setAttribute('aria-pressed', 'false'));
        button.setAttribute('aria-pressed', 'true');
        const which = button.getAttribute('data-swap');
        card.setAttribute('data-active-variant', which);
        const image = card.querySelector('[data-thumb] img');
        const newImage = button.getAttribute('data-image');
        if (image && newImage) {
          image.removeAttribute('srcset');
          image.removeAttribute('sizes');
          image.setAttribute('src', newImage);
        }
        const headline = card.querySelector('[data-headline]');
        if (headline) headline.textContent = button.getAttribute('data-title');
        const price = parseInt(card.getAttribute(which === 'alt' ? 'data-price-alt' : 'data-price-main'), 10);
        const compare = parseInt(card.getAttribute(which === 'alt' ? 'data-compare-alt' : 'data-compare-main'), 10);
        const priceElement = card.querySelector('[data-price]');
        const compareElement = card.querySelector('[data-compare]');
        if (priceElement && !Number.isNaN(price)) priceElement.textContent = this.formatMoney(price);
        if (compareElement) {
          const show = card.getAttribute('data-show-compare') === 'true' && !Number.isNaN(compare) && compare > price;
          compareElement.hidden = !show;
          if (show) compareElement.textContent = this.formatMoney(compare);
        }
        this.changed();
      });
    });
  }

  // ----- cart -----
  items() {
    return this.selectedCards()
      .map((card) => ({ id: parseInt(this.activeVariant(card), 10), quantity: 1 }))
      .filter((item) => !Number.isNaN(item.id) && item.id > 0);
  }

  productForm() {
    const forms = Array.from(document.querySelectorAll('form[action*="/cart/add"]'));
    return forms.find((form) => !form.closest(DTJ_ADDONS_NO_FORM)) || forms[0];
  }

  post(items) {
    return fetch('/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ items })
    }).then((response) => response.json().then((data) => {
      if (!response.ok) throw data;
      return data;
    }));
  }

  handleClick(event) {
    if (this.processing) return;
    const addons = this.items();
    if (!addons.length) return; // nothing ticked: the theme's own flow runs

    const buyNow = event.target.closest('.accelerated-checkout-block button, .accelerated-checkout-block .button, .shopify-payment-button__button');
    const addButton = buyNow ? null : event.target.closest('add-to-cart-button, button.add-to-cart-button, button[name="add"], [type="submit"]');
    const form = buyNow ? this.productForm() : addButton && addButton.closest('form[action*="/cart/add"]');
    if (!form || form.closest(DTJ_ADDONS_NO_FORM)) return;

    const idInput = form.querySelector('[name="id"], [ref="variantId"]');
    if (!idInput || !idInput.value) return;
    const quantityInput = form.querySelector('[name="quantity"]');
    const quantity = quantityInput ? Math.max(1, parseInt(quantityInput.value, 10) || 1) : 1;

    event.preventDefault();
    event.stopImmediatePropagation();
    this.processing = true;
    if (addButton) addButton.setAttribute('disabled', 'disabled');
    const items = [{ id: parseInt(idInput.value, 10), quantity }].concat(addons);

    this.post(items)
      .then(() => {
        if (buyNow || this.afterAdd === 'checkout') {
          window.location.href = '/checkout';
          return;
        }
        ['cart:refresh', 'cart:updated', 'cart-update'].forEach((name) => document.dispatchEvent(new CustomEvent(name, { bubbles: true })));
        if (this.afterAdd === 'drawer') this.openDrawer();
        else window.location.href = '/cart';
      })
      .catch((error) => {
        if (window.console) console.warn('[dtj-addons] add failed, falling back to the theme flow', error);
        if (buyNow) {
          window.location.href = '/checkout';
          return;
        }
        try { form.submit(); } catch (submitError) { /* nothing more to try */ }
      })
      .finally(() => {
        if (addButton) addButton.removeAttribute('disabled');
        this.processing = false;
      });
  }

  openDrawer() {
    const drawer = document.querySelector('cart-drawer, [is="cart-drawer"], .cart-drawer, #cart-drawer, cart-drawer-component');
    if (drawer) {
      for (const method of ['showDialog', 'show', 'open']) {
        if (typeof drawer[method] === 'function') {
          drawer[method]();
          return;
        }
      }
      drawer.setAttribute('open', '');
    }
    document.dispatchEvent(new CustomEvent('cart:open'));
    document.dispatchEvent(new CustomEvent('cart:refresh'));
  }
}

if (!customElements.get('dtj-addons')) {
  customElements.define('dtj-addons', DtjAddons);
}
