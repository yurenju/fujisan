"""Generate a single-file viewer.html from alignments.json. Open directly in browser."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
data = json.load(open(ROOT / "aligned-all" / "alignments.json"))

# Strip down to what the viewer needs
items = []
for name, r in data["items"].items():
    items.append({
        "name": name,
        "status": r["status"],
        "reason": r.get("reason"),
        "matrix": r.get("matrix"),  # may be None for failures
        "src_w": r.get("src_w"),
        "src_h": r.get("src_h"),
        "scale": r.get("scale"),
        "rot": r.get("rotation_deg"),
        "inliers": r.get("inliers"),
    })

ref_name = data["reference"]
canvas = data["canvas"]
stats = data["stats"]

html = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>Fujisan alignment viewer</title>
<style>
  html, body {{ margin: 0; padding: 0; background: #111; color: #ddd; font: 14px/1.4 system-ui, sans-serif; height: 100%; overflow: hidden; }}
  #stage {{
    position: fixed; inset: 0;
    display: flex; align-items: center; justify-content: center;
  }}
  #frame {{
    position: relative;
    width: {canvas['w']}px; height: {canvas['h']}px;
    background: #000;
    overflow: hidden;
    transform-origin: center center;
    box-shadow: 0 0 0 1px #333;
  }}
  #frame img {{
    position: absolute;
    left: 0; top: 0;
    transform-origin: 0 0;
    user-select: none;
    pointer-events: none;
    will-change: transform;
  }}
  #hud {{
    position: fixed; left: 10px; top: 10px;
    background: rgba(0,0,0,0.6); padding: 10px 14px; border-radius: 6px;
    font-size: 12px; max-width: 480px;
    backdrop-filter: blur(4px);
  }}
  #hud b {{ color: #fff; }}
  .badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-weight: bold; margin-right: 6px; }}
  .ok {{ background: #2a6; color: #fff; }}
  .fail {{ background: #c33; color: #fff; }}
  #controls {{
    position: fixed; right: 10px; top: 10px;
    background: rgba(0,0,0,0.6); padding: 10px 14px; border-radius: 6px;
    font-size: 12px;
  }}
  #controls label {{ display: block; margin: 4px 0; cursor: pointer; }}
  #help {{
    position: fixed; left: 10px; bottom: 10px;
    background: rgba(0,0,0,0.6); padding: 8px 12px; border-radius: 6px;
    font-size: 11px; color: #aaa;
  }}
  kbd {{
    background: #333; border: 1px solid #555; border-radius: 3px;
    padding: 1px 5px; font-size: 11px; color: #ddd;
  }}
</style>
</head>
<body>
<div id="stage"><div id="frame"></div></div>

<div id="hud">
  <div><span id="badge" class="badge"></span><b id="counter"></b></div>
  <div id="filename" style="font-family: monospace; font-size: 11px; color: #aaa; margin-top: 4px;"></div>
  <div id="meta" style="margin-top: 4px;"></div>
</div>

<div id="controls">
  <label><input type="checkbox" id="aligned" checked> 套用對齊</label>
  <label><input type="checkbox" id="overlay"> 半透明疊在參考圖上</label>
  <label><input type="checkbox" id="onlyOk"> 只看成功的</label>
</div>

<div id="help">
  <kbd>←</kbd> <kbd>→</kbd> 切換 &nbsp;
  <kbd>A</kbd> 對齊 &nbsp;
  <kbd>O</kbd> 疊圖 &nbsp;
  <kbd>F</kbd> 只看成功
</div>

<script>
const ITEMS = {json.dumps(items)};
const REF_NAME = {json.dumps(ref_name)};
const CANVAS = {json.dumps(canvas)};

const frame = document.getElementById('frame');
const badge = document.getElementById('badge');
const counter = document.getElementById('counter');
const filename = document.getElementById('filename');
const meta = document.getElementById('meta');

const cbAligned = document.getElementById('aligned');
const cbOverlay = document.getElementById('overlay');
const cbOnlyOk = document.getElementById('onlyOk');

let idx = 0;
let refImg = null;

function visibleItems() {{
  return cbOnlyOk.checked ? ITEMS.filter(it => it.status === 'ok') : ITEMS;
}}

function ensureRef() {{
  if (refImg) return refImg;
  refImg = document.createElement('img');
  refImg.src = 'images-resized/' + REF_NAME;
  refImg.style.opacity = '0.5';
  refImg.style.zIndex = '0';
  return refImg;
}}

function fitFrame() {{
  // Scale the fixed-size frame to fit the viewport
  const pad = 80;
  const sx = (window.innerWidth - pad) / CANVAS.w;
  const sy = (window.innerHeight - pad) / CANVAS.h;
  const s = Math.min(sx, sy, 1);
  frame.style.transform = `scale(${{s}})`;
}}
window.addEventListener('resize', fitFrame);

function render() {{
  const list = visibleItems();
  if (list.length === 0) return;
  if (idx >= list.length) idx = list.length - 1;
  if (idx < 0) idx = 0;
  const it = list[idx];

  frame.innerHTML = '';
  if (cbOverlay.checked) {{
    // Re-create ref each time, simpler
    const r = document.createElement('img');
    r.src = 'images-resized/' + REF_NAME;
    r.style.opacity = '0.5';
    frame.appendChild(r);
  }}

  const img = document.createElement('img');
  img.src = 'images-resized/' + it.name;
  if (cbAligned.checked && it.matrix) {{
    const [[a,b,tx],[c,d,ty]] = it.matrix;
    // CSS matrix(a, b, c, d, tx, ty) maps (x,y) → (a*x + c*y + tx, b*x + d*y + ty)
    // Our matrix maps (x,y) → (a*x + b*y + tx, c*x + d*y + ty)
    img.style.transform = `matrix(${{a}}, ${{c}}, ${{b}}, ${{d}}, ${{tx}}, ${{ty}})`;
  }} else {{
    // Center the unaligned image in the frame
    const offX = (CANVAS.w - it.src_w) / 2;
    const offY = (CANVAS.h - it.src_h) / 2;
    img.style.transform = `translate(${{offX}}px, ${{offY}}px)`;
  }}
  if (cbOverlay.checked) img.style.opacity = '0.5';
  frame.appendChild(img);

  badge.className = 'badge ' + it.status;
  badge.textContent = it.status === 'ok' ? 'OK' : 'FAIL';
  counter.textContent = `${{idx + 1}} / ${{list.length}}`;
  filename.textContent = it.name;
  if (it.status === 'ok') {{
    meta.textContent = `scale=${{it.scale.toFixed(3)}}  rot=${{it.rot.toFixed(2)}}°  inliers=${{it.inliers}}`;
  }} else {{
    meta.textContent = `reason: ${{it.reason}}` + (it.scale ? `  scale=${{it.scale.toFixed(3)}}  rot=${{it.rot.toFixed(2)}}°` : '');
  }}
}}

document.addEventListener('keydown', e => {{
  if (e.key === 'ArrowRight' || e.key === ' ') {{ idx++; render(); e.preventDefault(); }}
  else if (e.key === 'ArrowLeft') {{ idx--; render(); e.preventDefault(); }}
  else if (e.key === 'a' || e.key === 'A') {{ cbAligned.checked = !cbAligned.checked; render(); }}
  else if (e.key === 'o' || e.key === 'O') {{ cbOverlay.checked = !cbOverlay.checked; render(); }}
  else if (e.key === 'f' || e.key === 'F') {{ cbOnlyOk.checked = !cbOnlyOk.checked; idx = 0; render(); }}
}});
[cbAligned, cbOverlay, cbOnlyOk].forEach(cb => cb.addEventListener('change', () => {{
  if (cb === cbOnlyOk) idx = 0;
  render();
}}));

fitFrame();
render();
</script>
</body>
</html>
"""

(ROOT / "viewer.html").write_text(html, encoding="utf-8")
print(f"Wrote viewer.html — {stats['ok']} OK / {stats['total']} total")
print(f"Open: file:///{ROOT.as_posix()}/viewer.html")
