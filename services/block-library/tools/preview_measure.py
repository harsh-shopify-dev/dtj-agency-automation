"""DEV TOOL: measures, in a real browser, how far the Add-ons tick is from the centre of its circle (should be 0px).
usage (from services/block-library): python tools/preview_addons.py OUT/addons.png tick=1,2 ; python tools/preview_measure.py OUT/addons.html"""
import subprocess, sys, re, json
from pathlib import Path
html = Path(sys.argv[1]).read_text(encoding="utf-8")
probe = """<pre id="m"></pre><script>window.addEventListener('load',()=>setTimeout(()=>{
const out=[];document.querySelectorAll('[data-card]').forEach((c,i)=>{const b=c.querySelector('.dtj-addons__cta').getBoundingClientRect();
const p=c.querySelector('.dtj-addons__cta svg polyline').getBoundingClientRect();
out.push({card:i+1,sel:c.dataset.selected,circle:[+(b.left+b.width/2).toFixed(2),+(b.top+b.height/2).toFixed(2),+b.width.toFixed(1)],tick:[+(p.left+p.width/2).toFixed(2),+(p.top+p.height/2).toFixed(2)]});});
document.getElementById('m').textContent='RESULT'+JSON.stringify(out)+'END';},300));</script>"""
doc = html.replace("</body>", probe + "</body>")
tmp = Path(sys.argv[1]).with_name("measure.html"); tmp.write_text(doc, encoding="utf-8")
edge = next(p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe") if Path(p).is_file())
r = subprocess.run([edge, "--headless=new", "--disable-gpu", "--window-size=390,640", "--virtual-time-budget=2000", "--dump-dom", tmp.resolve().as_uri()], capture_output=True, text=True, timeout=90)
m = re.search(r"RESULT(.*?)END", r.stdout, re.S)
for row in json.loads(m.group(1)):
    dx = round(row["tick"][0]-row["circle"][0], 2); dy = round(row["tick"][1]-row["circle"][1], 2)
    print(f"card {row['card']} selected={row['sel']}: circle centre {row['circle'][:2]} (w {row['circle'][2]}), tick centre {row['tick']}  -> off by x={dx}px y={dy}px")
