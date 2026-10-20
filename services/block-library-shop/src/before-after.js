/**
 * <dtj-before-after>
 * Before / After. Markup contract: a .dtj-ba__pic element holding an <input class="dtj-ba__range"> (0 to 100). The input's value is copied into the
 * picture's --ba-pos custom property, which the stylesheet uses to place the divider and clip the "after" picture. Without this script the picture
 * shows the starting position set in the markup. It reads nothing from the page and talks to nobody.
 */
class DtjBeforeAfter extends HTMLElement {
  connectedCallback() {
    const pic = this.querySelector('.dtj-ba__pic');
    const range = this.querySelector('.dtj-ba__range');
    if (!pic || !range) return;
    const set = () => pic.style.setProperty('--ba-pos', range.value + '%');
    range.addEventListener('input', set);
    set();
  }
}

if (!customElements.get('dtj-before-after')) customElements.define('dtj-before-after', DtjBeforeAfter);
