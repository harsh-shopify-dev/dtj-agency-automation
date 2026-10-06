// Runs the REAL src/addons.js in Node with small stand-ins for the browser, and checks the cart logic.
// Run: node tests/addons_logic.js   (the Python test suite runs it and fails if it throws)
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'addons.js'), 'utf8');

function load(overrides = {}) {
  const calls = { fetch: [], events: [], hrefs: [] };
  let Ctor;
  const forms = overrides.forms || [];
  const sandbox = {
    HTMLElement: class {},
    customElements: { get: () => undefined, define: (name, ctor) => { Ctor = ctor; } },
    CustomEvent: class { constructor(name, init) { this.type = name; this.detail = init && init.detail; } },
    document: {
      dispatchEvent: (event) => calls.events.push(event.type),
      querySelectorAll: () => forms,
      querySelector: () => null,
      addEventListener() {},
      removeEventListener() {}
    },
    window: { location: { set href(value) { calls.hrefs.push(value); }, get href() { return ''; } }, console: { warn() {} } },
    console: { warn() {} },
    fetch: overrides.fetch || ((url, init) => { calls.fetch.push({ url, body: JSON.parse(init.body) }); return Promise.resolve({ ok: true, json: () => Promise.resolve({}) }); }),
    setInterval() {}, clearInterval() {}
  };
  vm.runInNewContext(source + '\n;this.__ctor = DtjAddons;', sandbox);
  const element = new sandbox.__ctor();
  element.dataset = { mainVariant: '10' };
  element.moneyFormat = 'Rs. {{amount}}';
  element.afterAdd = 'cart';
  element.prices = { 10: 100000, 20: 150000 };
  element.cards = [];
  element.processing = false;
  element.variantInput = { value: '10' };
  element.setAttribute = () => {};
  return { element, calls, sandbox };
}

function card({ selected = false, active = 'main', main = '111', alt = '222', priceMain = 30000, priceAlt = 40000 } = {}) {
  const attributes = {
    'data-selected': String(selected), 'data-active-variant': active, 'data-variant-main': main, 'data-variant-alt': alt,
    'data-price-main': String(priceMain), 'data-price-alt': String(priceAlt)
  };
  return { getAttribute: (name) => attributes[name], matches: () => false };
}

function clickOn({ form, button, buyNow = null }) {
  const calls = { prevented: 0, stopped: 0 };
  const target = {
    closest: (selector) => {
      if (selector.includes('accelerated-checkout')) return buyNow;
      if (selector.includes('add-to-cart-button')) return button;
      return null;
    }
  };
  return { event: { target, preventDefault: () => calls.prevented++, stopImmediatePropagation: () => calls.stopped++ }, calls };
}

function productForm({ id = '10', quantity = '1', inDrawer = false } = {}) {
  const inputs = { '[name="id"], [ref="variantId"]': { value: id }, '[name="quantity"]': { value: quantity } };
  let submitted = 0;
  const form = { querySelector: (selector) => inputs[selector] || null, closest: () => (inDrawer ? {} : null), submit: () => submitted++, get submitted() { return submitted; } };
  const button = { closest: () => form, setAttribute() {}, removeAttribute() {} };
  return { form, button };
}

const tests = {
  'money: default, no decimals and comma formats'() {
    const { element } = load();
    assert.equal(element.formatMoney(69900), 'Rs. 699.00');
    assert.equal(element.formatMoney(199900), 'Rs. 1,999.00');
    element.moneyFormat = '{{amount_no_decimals}} INR';
    assert.equal(element.formatMoney(199900), '1,999 INR');
    element.moneyFormat = '{{amount_with_comma_separator}} EUR';
    assert.equal(element.formatMoney(199900), '1.999,00 EUR');
  },
  'main price follows the variant the shopper picked, with a safe fallback'() {
    const { element } = load();
    assert.equal(element.mainPrice(), 100000);
    element.variantInput.value = '20';
    assert.equal(element.mainPrice(), 150000);
    element.variantInput.value = '999';
    assert.equal(element.mainPrice(), 100000);
  },
  'items(): only ticked cards, the active variant, quantity 1, bad ids dropped'() {
    const { element } = load();
    element.cards = [card({ selected: true }), card({ selected: false, main: '333' }), card({ selected: true, active: 'alt', alt: '444' }), card({ selected: true, main: 'abc' })];
    // compared as JSON: objects made inside the vm sandbox have a different prototype than the ones in this file
    assert.equal(JSON.stringify(element.items()), JSON.stringify([{ id: 111, quantity: 1 }, { id: 444, quantity: 1 }]));
  },
  'total uses the active variant price of ticked add-ons'() {
    const { element } = load();
    element.totalValue = { textContent: '' };
    element.cards = [card({ selected: true, priceMain: 30000 }), card({ selected: true, active: 'alt', priceAlt: 40000 }), card({ selected: false, priceMain: 99999 })];
    element.updateTotal();
    assert.equal(element.totalValue.textContent, 'Rs. 1,700.00');
  },
  'nothing ticked: the theme flow is left alone'() {
    const { element, calls } = load();
    element.cards = [card({ selected: false })];
    const { form, button } = productForm();
    const { event, calls: c } = clickOn({ form, button });
    element.handleClick(event);
    assert.equal(c.prevented + c.stopped, 0);
    assert.equal(calls.fetch.length, 0);
  },
  async 'ticked: one request with the product (quantity) and the add-ons, then the cart page'() {
    const { element, calls } = load();
    element.cards = [card({ selected: true, main: '111' }), card({ selected: true, main: '222' })];
    const { form, button } = productForm({ id: '10', quantity: '3' });
    const { event, calls: c } = clickOn({ form, button });
    element.handleClick(event);
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(c.prevented, 1);
    assert.equal(c.stopped, 1);
    assert.equal(calls.fetch.length, 1);
    assert.equal(calls.fetch[0].url, '/cart/add.js');
    assert.deepEqual(calls.fetch[0].body.items, [{ id: 10, quantity: 3 }, { id: 111, quantity: 1 }, { id: 222, quantity: 1 }]);
    assert.deepEqual(calls.hrefs, ['/cart']);
    assert.ok(calls.events.includes('cart:refresh'));
    assert.equal(element.processing, false);
  },
  async 'after-add checkout and the buy-now button both go to checkout'() {
    for (const mode of ['checkout', 'cart']) {
      const { element, calls } = load({ forms: [] });
      element.afterAdd = mode;
      element.cards = [card({ selected: true })];
      const { form, button } = productForm();
      element.productForm = () => form;
      const buyNow = mode === 'cart' ? {} : null; // buy-now with the cart mode must still go to checkout
      const { event } = clickOn({ form, button, buyNow });
      element.handleClick(event);
      await new Promise((resolve) => setImmediate(resolve));
      assert.deepEqual(calls.hrefs, ['/checkout'], mode);
    }
  },
  'a form inside the cart drawer is never hijacked'() {
    const { element, calls } = load();
    element.cards = [card({ selected: true })];
    const { form, button } = productForm({ inDrawer: true });
    const { event, calls: c } = clickOn({ form, button });
    element.handleClick(event);
    assert.equal(c.prevented, 0);
    assert.equal(calls.fetch.length, 0);
  },
  async 'a failed request falls back to the theme form so the order is not lost'() {
    const { element, calls } = load({ fetch: () => Promise.resolve({ ok: false, json: () => Promise.resolve({ description: 'sold out' }) }) });
    element.cards = [card({ selected: true })];
    const { form, button } = productForm();
    const { event } = clickOn({ form, button });
    element.handleClick(event);
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(form.submitted, 1);
    assert.deepEqual(calls.hrefs, []);
    assert.equal(element.processing, false);
  },
  'a second click while a request is running is ignored'() {
    const { element, calls } = load();
    element.cards = [card({ selected: true })];
    element.processing = true;
    const { form, button } = productForm();
    const { event, calls: c } = clickOn({ form, button });
    element.handleClick(event);
    assert.equal(c.prevented, 0);
    assert.equal(calls.fetch.length, 0);
  }
};

(async () => {
  let failed = 0;
  for (const [name, run] of Object.entries(tests)) {
    try {
      await run();
      console.log('ok   ' + name);
    } catch (error) {
      failed++;
      console.log('FAIL ' + name + '\n     ' + String(error.message).split('\n').slice(0, 4).join('\n     '));
    }
  }
  if (failed) process.exit(1);
  console.log('ALL OK (' + Object.keys(tests).length + ' cart-logic checks)');
})();
