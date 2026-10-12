// Runs the REAL src/shoppable-reels.js in Node with small stand-ins for the browser, and checks the tap and sound logic.
// Run: node tests/reels_logic.js   (the Python test suite runs it and fails if it throws)
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'shoppable-reels.js'), 'utf8');

function fakeVideo(id) {
  return {
    id, paused: true, muted: true,
    play() { this.paused = false; return Promise.resolve(); },
    pause() { this.paused = true; }
  };
}

function fakeButton(kind, id) {
  const classes = new Set();
  const attrs = {};
  return {
    kind, dataset: { target: id }, attrs,
    classList: { toggle: (name, on) => (on ? classes.add(name) : classes.delete(name)), contains: (name) => classes.has(name) },
    setAttribute: (name, value) => { attrs[name] = value; }
  };
}

// A page with `count` reels. Each reel has a video, a play/pause button and a sound button.
function setup({ count = 2, reduceMotion = false } = {}) {
  let Ctor;
  let observerCallback;
  const videos = [];
  const toggles = {};
  const sounds = {};
  for (let i = 1; i <= count; i += 1) {
    const id = `reel-${i}`;
    videos.push(fakeVideo(id));
    toggles[id] = fakeButton('toggle', id);
    sounds[id] = fakeButton('sound', id);
  }
  const sandbox = {
    HTMLElement: class {},
    customElements: { get: () => undefined, define: (name, ctor) => { Ctor = ctor; } },
    IntersectionObserver: class { constructor(callback) { observerCallback = callback; } observe() {} disconnect() {} },
    window: { matchMedia: () => ({ matches: reduceMotion }) },
    document: { getElementById: (id) => videos.find((video) => video.id === id) || null }
  };
  vm.runInNewContext(source + '\n;this.__ctor = DtjReels;', sandbox);
  const element = new sandbox.__ctor();
  let clickHandler;
  element.dataset = {};
  element.addEventListener = (type, handler) => { if (type === 'click') clickHandler = handler; };
  element.querySelectorAll = (selector) => (selector === 'video' ? videos : []);
  element.querySelector = (selector) => {
    const match = selector.match(/^\[data-(toggle|sound)\]\[data-target="(.+)"\]$/);
    if (!match) return null;
    return (match[1] === 'toggle' ? toggles : sounds)[match[2]] || null;
  };
  element.connectedCallback();

  const reel = (n) => videos[n - 1];
  const scrollIntoView = (n) => observerCallback([{ target: reel(n), isIntersecting: true }]);
  const scrollOut = (n) => observerCallback([{ target: reel(n), isIntersecting: false }]);
  // A tap on the video picture itself.
  const tapVideo = (n) => clickHandler({ target: { closest: (selector) => (selector === 'video' ? reel(n) : null) } });
  // A tap on the play/pause button or on the sound button of reel n.
  const tapButton = (kind, n) => {
    const button = (kind === 'sound' ? sounds : toggles)[`reel-${n}`];
    clickHandler({ target: { closest: (selector) => (selector === `[data-${kind}]` ? button : null) } });
  };
  return { reel, toggles, sounds, scrollIntoView, scrollOut, tapVideo, tapButton };
}

let passed = 0;
function test(name, fn) {
  try { fn(); passed += 1; } catch (error) { console.error(`FAIL: ${name}`); throw error; }
}

test('a reel scrolled into view plays silently by itself', () => {
  const page = setup();
  page.scrollIntoView(1);
  assert.equal(page.reel(1).paused, false);
  assert.equal(page.reel(1).muted, true);
  assert.equal(page.sounds['reel-1'].classList.contains('is-on'), false);
  assert.equal(page.sounds['reel-1'].attrs['aria-label'], 'Turn sound on');
});

test('FIRST TAP on a silent reel turns the sound on and keeps it playing (the reported bug)', () => {
  const page = setup();
  page.scrollIntoView(1);
  page.tapVideo(1);
  assert.equal(page.reel(1).paused, false, 'must keep playing, not pause');
  assert.equal(page.reel(1).muted, false, 'sound must be on');
  assert.equal(page.sounds['reel-1'].classList.contains('is-on'), true);
  assert.equal(page.sounds['reel-1'].attrs['aria-label'], 'Turn sound off');
  assert.equal(page.sounds['reel-1'].attrs['aria-pressed'], 'true');
});

test('second tap pauses it, and a paused reel is not resumed by scrolling back', () => {
  const page = setup();
  page.scrollIntoView(1);
  page.tapVideo(1);
  page.tapVideo(1);
  assert.equal(page.reel(1).paused, true);
  assert.equal(page.toggles['reel-1'].classList.contains('is-playing'), false);
  page.scrollOut(1);
  page.scrollIntoView(1);
  assert.equal(page.reel(1).paused, true, 'a hand-paused reel must stay paused');
});

test('tapping a paused reel plays it WITH sound', () => {
  const page = setup();
  page.scrollIntoView(1);
  page.tapVideo(1);
  page.tapVideo(1);
  page.tapVideo(1);
  assert.equal(page.reel(1).paused, false);
  assert.equal(page.reel(1).muted, false);
  assert.equal(page.toggles['reel-1'].classList.contains('is-playing'), true);
});

test('the sound button turns sound on and off without pausing', () => {
  const page = setup();
  page.scrollIntoView(1);
  page.tapButton('sound', 1);
  assert.equal(page.reel(1).muted, false);
  assert.equal(page.reel(1).paused, false);
  page.tapButton('sound', 1);
  assert.equal(page.reel(1).muted, true);
  assert.equal(page.reel(1).paused, false, 'sound off must not pause');
  assert.equal(page.sounds['reel-1'].attrs['aria-label'], 'Turn sound on');
});

test('the play/pause button pauses a silent playing reel and resumes it with sound', () => {
  const page = setup();
  page.scrollIntoView(1);
  page.tapButton('toggle', 1);
  assert.equal(page.reel(1).paused, true);
  page.tapButton('toggle', 1);
  assert.equal(page.reel(1).paused, false);
  assert.equal(page.reel(1).muted, false);
});

test('only one reel has sound: turning it on for reel 2 silences reel 1 but keeps it playing', () => {
  const page = setup();
  page.scrollIntoView(1);
  page.scrollIntoView(2);
  page.tapVideo(1);
  assert.equal(page.reel(1).muted, false);
  page.tapVideo(2);
  assert.equal(page.reel(2).muted, false);
  assert.equal(page.reel(1).muted, true, 'reel 1 must be silenced');
  assert.equal(page.reel(1).paused, false, 'reel 1 keeps playing');
  assert.equal(page.sounds['reel-1'].classList.contains('is-on'), false, 'reel 1 button must show sound off');
});

test('a reel that comes back into view always starts silent again', () => {
  const page = setup();
  page.scrollIntoView(1);
  page.tapVideo(1);
  page.scrollOut(1);
  assert.equal(page.reel(1).paused, true);
  page.scrollIntoView(1);
  assert.equal(page.reel(1).muted, true);
  assert.equal(page.reel(1).paused, false);
});

test('reduced motion: nothing autoplays, but a tap plays with sound', () => {
  const page = setup({ reduceMotion: true });
  page.scrollIntoView(1);
  assert.equal(page.reel(1).paused, true);
  page.tapVideo(1);
  assert.equal(page.reel(1).paused, false);
  assert.equal(page.reel(1).muted, false);
});

test('labels can be translated through the data attributes', () => {
  let Ctor;
  const page = setup();
  page.scrollIntoView(1);
  // setup() builds the element internally; rebuild one with translated labels
  const sandbox = { HTMLElement: class {}, customElements: { get: () => undefined, define: (n, c) => { Ctor = c; } },
    IntersectionObserver: class { observe() {} disconnect() {} }, window: { matchMedia: () => ({ matches: false }) }, document: { getElementById: () => null } };
  vm.runInNewContext(source + '\n;this.__ctor = DtjReels;', sandbox);
  const element = new sandbox.__ctor();
  const video = fakeVideo('x');
  const sound = fakeButton('sound', 'x');
  element.dataset = { soundOnLabel: 'Awaaz chalu', soundOffLabel: 'Awaaz band' };
  element.querySelector = (selector) => (selector.includes('data-sound') ? sound : null);
  element.sync(video);
  assert.equal(sound.attrs['aria-label'], 'Awaaz chalu');
  video.muted = false;
  element.sync(video);
  assert.equal(sound.attrs['aria-label'], 'Awaaz band');
});

console.log(`ALL OK (${passed} checks)`);
