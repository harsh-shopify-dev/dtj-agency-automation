// Paste into the Google Flow tab (browser pane, javascript_tool). Flow's file picker cannot open in the pane, so pictures are
// fetched from a public URL (DTJ's n8n media folder through images.weserv.nl for CORS) and handed to Flow's hidden file input.
// Usage:
//   await window.__load(['p04.png','p10.png'])   // fetch pictures from MEDIA into memory
//   then REAL-click Start (the frame slot) -> "Upload media"   // the hook fills the input; tiles appear named mx_<file>
//   then REAL-click the option for the picture in the picker; check: __startIs('mx_p04.png') === true
//   type the motion prompt, REAL-click "Start generation"
//   finished clip: REAL-click its tile, then  [...document.querySelectorAll('video')].map(v=>v.currentSrc).filter(Boolean)[0]
//   and curl that signed URL into <job>/clips/; navigate back.
// JS .click() on Flow tiles or the Start slot does NOT work (opens a detail view or nothing): use real clicks for those.
window.MEDIA = window.MEDIA || 'n8n.srv2048145.hstgr.cloud/media/reel-inputs/<job-token>/';   // set per job
window.__files = [];
window.__fill = (inp) => {
  if (!window.__files.length) return false;
  const dt = new DataTransfer(); window.__files.forEach(f => dt.items.add(f));
  inp.files = dt.files; inp.dispatchEvent(new Event('change', { bubbles: true }));
  window.__filled = (window.__filled || 0) + 1; window.__files = []; return true;
};
if (!window.__hooked) {
  const oc = HTMLInputElement.prototype.click;
  HTMLInputElement.prototype.click = function () { if (this.type === 'file' && window.__files.length) { window.__fill(this); return; } return oc.call(this); };
  const sp = HTMLInputElement.prototype.showPicker;
  HTMLInputElement.prototype.showPicker = function () { if (this.type === 'file' && window.__files.length) { window.__fill(this); return; } return sp.call(this); };
  document.addEventListener('click', e => { const t = e.target; if (t instanceof HTMLInputElement && t.type === 'file' && window.__files.length) { e.preventDefault(); window.__fill(t); } }, true);
  window.__hooked = true;
}
window.__load = async (names, prefix = 'mx_') => {
  window.__files = [];
  for (const n of names) {
    const r = await fetch('https://images.weserv.nl/?url=' + encodeURIComponent(window.MEDIA + n));
    const b = await r.blob(); window.__files.push(new File([b], prefix + n, { type: b.type || 'image/png' }));
  }
  return window.__files.map(f => f.name + ' ' + f.size);
};
// which picture sits in the Start slot (compares Flow's image ids)
window.__tileId = (name) => {
  for (const im of document.querySelectorAll('img[alt^="Tile displaying"]')) {
    let n = im;
    for (let k = 0; k < 8 && n; k++) {
      n = n.parentElement;
      const b = n && [...n.querySelectorAll('button[type=button]')].find(x => x.innerText.includes(name));
      if (b) { if (n.querySelectorAll('img[alt^="Tile displaying"]').length === 1) return (im.src.match(/image\/([\w-]+)/) || [])[1]; break; }
    }
  }
  return null;
};
window.__startIs = (name) => {
  const chip = document.querySelector('button[aria-label="Image ingredient"] img');
  return !!chip && (chip.src.match(/image\/([\w-]+)/) || [])[1] === window.__tileId(name);
};
