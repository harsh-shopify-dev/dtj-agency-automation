"""Headless Edge/Chrome for the review loop: measures a rendered page at a given width and takes a full-page screenshot.

A phone is simulated with an iframe of the true width (headless Edge will not make a window narrower than about 500 px, but media queries
inside an iframe follow the iframe's own width). The probe script runs INSIDE the page and only collects raw facts (colours, sizes,
positions); every judgement is made in Python (review.py), where it is tested.
"""
from __future__ import annotations

import html as htmllib
import json
import re
import subprocess
from pathlib import Path

CANDIDATES = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe", "/usr/bin/chromium", "/usr/bin/google-chrome")
MAX_HEIGHT = 16000  # px: taller pages are cut in the screenshot (the measurements still cover the whole page)

PROBE = r"""<script>(function(){
function alpha(c){c=c||'';if(/^transparent$/.test(c))return 0;var m=/rgba?\(([^)]+)\)/.exec(c);
  if(m){var p=m[1].replace('/',',').split(/[\s,]+/).filter(Boolean);return p.length>3?parseFloat(p[3]):1;}
  var s=/\/\s*([\d.]+%?)\s*\)\s*$/.exec(c);if(s)return s[1].slice(-1)==='%'?parseFloat(s[1])/100:parseFloat(s[1]);return 1;}
function bg(el){var layers=[];for(var e=el;e;e=e.parentElement){var cs=getComputedStyle(e);
  if(cs.backgroundImage&&cs.backgroundImage!=='none')return {image:true,layers:layers};
  var c=cs.backgroundColor;var a=alpha(c);if(a>0){layers.push(c);if(a>=0.999)return {image:false,layers:layers};}}
  layers.push('rgb(255, 255, 255)');return {image:false,layers:layers};}
function visible(el){var r=el.getBoundingClientRect();if(r.width<1||r.height<1)return false;var op=1;
  for(var e=el;e;e=e.parentElement){var cs=getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden')return false;op*=parseFloat(cs.opacity||'1');}
  return op>0.1;}
function owned(el){var b=el.closest('[data-pb-block]');if(!b||el.closest('[data-pb-theme]'))return null;
  var s=el.closest('[data-pb-section]');return {block:b.getAttribute('data-pb-block'),dtj:b.getAttribute('data-pb-dtj'),section:s?s.getAttribute('data-pb-section'):null};}
function clipAncestor(el){for(var e=el.parentElement;e&&e!==document.body;e=e.parentElement){var o=getComputedStyle(e).overflowX;if(o!=='visible')return true;}return false;}
function ownText(el){var t='';for(var i=0;i<el.childNodes.length;i++){var n=el.childNodes[i];if(n.nodeType===3)t+=n.nodeValue;}return t.replace(/\s+/g,' ').trim();}
function run(){var W=window.innerWidth,out={width:W,page_width:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth),
  page_height:Math.ceil(document.documentElement.scrollHeight),texts:[],offenders:[],clipped:[],taps:[],broken_images:[],blocks:[],sections:[]};
  var all=document.querySelectorAll('[data-pb-block] *');
  for(var i=0;i<all.length;i++){var el=all[i];var tag=el.tagName.toLowerCase();if(tag==='script'||tag==='style'||tag==='svg'||el.closest('svg'))continue;
    var own=owned(el);if(!own||!visible(el))continue;var r=el.getBoundingClientRect();var cs=getComputedStyle(el);
    var txt=ownText(el);
    if(txt){var b=bg(el);out.texts.push({section:own.section,block:own.block,dtj:own.dtj,tag:tag,text:txt.slice(0,60),color:cs.color,
      image:b.image,layers:b.layers,size:parseFloat(cs.fontSize),weight:parseInt(cs.fontWeight,10)||400});
      var clampN=cs.webkitLineClamp&&cs.webkitLineClamp!=='none';
      if((cs.overflowX!=='visible'&&el.scrollWidth>el.clientWidth+1)||(clampN&&el.scrollHeight>el.clientHeight+1))
        out.clipped.push({section:own.section,block:own.block,tag:tag,text:txt.slice(0,60)});}
    if((r.right>W+1||r.left<-1)&&!clipAncestor(el)&&out.offenders.length<20)
      out.offenders.push({section:own.section,block:own.block,dtj:own.dtj,tag:tag,cls:(el.className&&el.className.baseVal===undefined?el.className:'').slice(0,60),left:Math.round(r.left),right:Math.round(r.right)});
    if(/^(a|button|summary|select|input)$/.test(tag)||el.getAttribute('role')==='button')
      out.taps.push({section:own.section,block:own.block,tag:tag,w:Math.round(r.width),h:Math.round(r.height),label:(txt||el.getAttribute('aria-label')||'').slice(0,40)});
    if(tag==='img'&&el.complete&&el.naturalWidth===0)out.broken_images.push({section:own.section,block:own.block,src:(el.getAttribute('src')||'').slice(0,80)});}
  var bl=document.querySelectorAll('[data-pb-block]');for(var j=0;j<bl.length;j++){var x=bl[j];var rr=x.getBoundingClientRect();var s=x.closest('[data-pb-section]');
    out.blocks.push({block:x.getAttribute('data-pb-block'),dtj:x.getAttribute('data-pb-dtj'),section:s?s.getAttribute('data-pb-section'):null,
      height:Math.round(rr.height),text_len:(x.innerText||'').trim().length,images:x.querySelectorAll('img,video,picture').length});}
  var se=document.querySelectorAll('[data-pb-section]');for(var k=0;k<se.length;k++){var y=se[k];var r3=y.getBoundingClientRect();
    out.sections.push({section:y.getAttribute('data-pb-section'),top:Math.round(r3.top+window.scrollY),height:Math.round(r3.height)});}
  var sink=parent&&parent.document&&parent.document.getElementById('pbm');var json='PBRESULT'+JSON.stringify(out)+'PBEND';
  if(sink&&parent!==window)sink.textContent=json;else{var p=document.createElement('pre');p.id='pbm';p.textContent=json;document.body.appendChild(p);}}
window.addEventListener('load',function(){setTimeout(run,800);});})();</script>"""


class BrowserError(RuntimeError):
    pass


def find_browser() -> Path | None:
    return next((Path(p) for p in CANDIDATES if Path(p).is_file()), None)


class EdgeBrowser:
    """The real browser. Anything with the same two methods (measure, screenshot) can replace it in tests."""

    def __init__(self, exe: Path | None = None, work: Path | None = None, timeout: int = 120):
        self.exe = exe or find_browser()
        if not self.exe:
            raise BrowserError("no Edge or Chrome found: install one, or run the page builder with --no-browser")
        self.work = work
        self.timeout = timeout

    def _frame(self, doc: str, width: int, height: int, name: str) -> Path:
        self.work.mkdir(parents=True, exist_ok=True)
        frame = self.work / name
        frame.write_text(f'<!doctype html><html><body style="margin:0;background:#fff"><pre id="pbm" style="display:none"></pre>'
                         f'<iframe srcdoc="{htmllib.escape(doc, quote=True)}" style="width:{width}px;height:{height}px;border:0;display:block"></iframe>'
                         f'</body></html>', encoding="utf-8")
        return frame

    def measure(self, doc: str, width: int) -> dict:
        probe_doc = doc.replace("</body>", PROBE + "</body>", 1)
        frame = self._frame(probe_doc, width, 2000, f"measure-{width}.html")
        r = subprocess.run([str(self.exe), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={max(width, 500) + 20},2000",
                            "--virtual-time-budget=6000", "--dump-dom", frame.resolve().as_uri()],
                           capture_output=True, text=True, timeout=self.timeout, encoding="utf-8", errors="replace")
        m = re.search(r"PBRESULT(.*?)PBEND", htmllib.unescape(r.stdout), re.S)
        if not m:
            raise BrowserError(f"the probe did not report at width {width} (exit {r.returncode}): {r.stderr[-300:]}")
        return json.loads(m.group(1))

    def screenshot(self, doc: str, width: int, height: int, out_png: Path, scale: int = 1) -> Path:
        height = min(max(height, 400), MAX_HEIGHT)
        frame = self._frame(doc, width, height, f"shot-{width}.html")
        out_png.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([str(self.exe), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                            f"--window-size={max(width, 500)},{height}", "--virtual-time-budget=6000", f"--screenshot={out_png.resolve()}",
                            frame.resolve().as_uri()], capture_output=True, text=True, timeout=self.timeout)
        if not out_png.is_file():
            raise BrowserError(f"no screenshot at width {width} (exit {r.returncode}): {r.stderr[-300:]}")
        return out_png
