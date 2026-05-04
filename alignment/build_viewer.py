"""Generate viewer.html from alignments-normalized.json.

The normalized file is the canonical source of truth: tx and ty are stored
as fractions of the calibration canvas edge, so the same data drives any
target resolution. The viewer denormalizes to the calibration canvas size
internally for editing, and re-normalizes when you download — overwrite
alignments-normalized.json on disk to commit further manual fixes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
NORMALIZED = ROOT / "aligned-all" / "alignments-normalized.json"
FINAL = ROOT / "aligned-all" / "alignments-final.json"

# Read the normalized file so we exercise the resolution-independent format,
# then denormalize to the calibration canvas size (square) for the viewer's
# pixel-coordinate runtime. Falls back to the final file if normalized is absent.
if NORMALIZED.exists():
    norm = json.load(open(NORMALIZED))
    K = norm["calibration_unit_px"]
    final_data = json.load(open(FINAL))  # for canvas/reference/stats metadata
    items_dict = {}
    for name, r in norm["items"].items():
        if r.get("matrix") is None:
            items_dict[name] = {
                "matrix": None,
                "source": r.get("source", "unaligned"),
                "reason": r.get("reason"),
                "src_w": final_data["items"][name].get("src_w"),
                "src_h": final_data["items"][name].get("src_h"),
            }
            continue
        a, b, tx_n = r["matrix"][0]
        c, d, ty_n = r["matrix"][1]
        items_dict[name] = {
            "matrix": [[a, b, tx_n * K], [c, d, ty_n * K]],
            "scale": r.get("scale"),
            "rotation_deg": r.get("rotation_deg"),
            "src_w": final_data["items"][name].get("src_w"),
            "src_h": final_data["items"][name].get("src_h"),
            "source": r.get("source"),
        }
    data = {
        "reference": final_data["reference"],
        "canvas": final_data["canvas"],
        "stats": final_data.get("stats", {}),
        "items": items_dict,
    }
elif FINAL.exists():
    data = json.load(open(FINAL))
else:
    raise SystemExit(
        f"Missing {NORMALIZED} and {FINAL}. Run align_all.py + merge_alignments.py first."
    )

ordered = sorted(data["items"].items())  # filenames are timestamps


def orientation(r):
    if r.get("src_w") and r.get("src_h"):
        return "landscape" if r["src_w"] >= r["src_h"] else "portrait"
    return None


def find_neighbor_seed(idx):
    target_o = orientation(ordered[idx][1])
    for offset in range(1, len(ordered)):
        for j in (idx - offset, idx + offset):
            if 0 <= j < len(ordered):
                nm, nr = ordered[j]
                if nr.get("matrix") and orientation(nr) == target_o:
                    return {"matrix": nr["matrix"], "from": nm}
    return None


items = []
for i, (name, r) in enumerate(ordered):
    item = {
        "name": name,
        "matrix": r.get("matrix"),
        "source": r.get("source", "unaligned"),
        "src_w": r.get("src_w"),
        "src_h": r.get("src_h"),
        "scale": r.get("scale"),
        "rot": r.get("rotation_deg"),
        "reason": r.get("reason"),
    }
    if item["matrix"] is None:
        seed = find_neighbor_seed(i)
        if seed:
            item["seed"] = seed
    items.append(item)

ref_name = data["reference"]
canvas = data["canvas"]
stats = data["stats"]

HTML = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>Fujisan alignment viewer</title>
<style>
  html, body { margin: 0; padding: 0; background: #111; color: #ddd; font: 14px/1.4 system-ui, sans-serif; height: 100%; overflow: hidden; }
  #stage { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; }
  #frame {
    position: relative;
    width: __W__px; height: __H__px;
    background: #000; overflow: hidden;
    transform-origin: center center;
    box-shadow: 0 0 0 1px #333;
  }
  #frame img {
    position: absolute; left: 0; top: 0;
    transform-origin: 0 0;
    user-select: none; pointer-events: none;
    will-change: transform;
  }
  .panel {
    position: fixed;
    background: rgba(0,0,0,0.6); padding: 10px 14px; border-radius: 6px;
    font-size: 12px; backdrop-filter: blur(4px);
  }
  #hud { left: 10px; top: 10px; max-width: 480px; }
  #hud b { color: #fff; }
  #controls { right: 10px; top: 10px; }
  #controls label { display: block; margin: 4px 0; cursor: pointer; }
  #help { left: 10px; bottom: 10px; font-size: 11px; color: #aaa; }
  #editPanel { right: 10px; bottom: 10px; font-family: monospace; }
  #editPanel.active { background: rgba(150, 60, 0, 0.7); }
  .badge { display: inline-block; padding: 1px 6px; border-radius: 3px; font-weight: bold; margin-right: 6px; }
  .auto { background: #2a6; color: #fff; }
  .manual { background: #38a; color: #fff; }
  .edited { background: #60c; color: #fff; }
  .seed { background: #c70; color: #fff; }
  .fail { background: #c33; color: #fff; }
  kbd {
    background: #333; border: 1px solid #555; border-radius: 3px;
    padding: 1px 5px; font-size: 11px; color: #ddd;
  }
</style>
</head>
<body>
<div id="stage"><div id="frame"></div></div>

<div id="hud" class="panel">
  <div><span id="badge" class="badge"></span><b id="counter"></b></div>
  <div id="filename" style="font-family: monospace; font-size: 11px; color: #aaa; margin-top: 4px;"></div>
  <div id="meta" style="margin-top: 4px;"></div>
</div>

<div id="controls" class="panel">
  <label><input type="checkbox" id="aligned" checked> 套用對齊</label>
  <label><input type="checkbox" id="overlay"> 半透明疊參考圖</label>
  <label><input type="checkbox" id="onlyAligned"> 只看已對齊</label>
  <label><input type="checkbox" id="onlyUnaligned"> 只看未對齊</label>
</div>

<div id="editPanel" class="panel">
  <div id="editStatus">Tweak: <kbd>T</kbd> 進入修正</div>
  <div id="editValues" style="margin-top: 4px; display: none;"></div>
</div>

<div id="help" class="panel">
  <div><b>檢視</b>: <kbd>←</kbd><kbd>→</kbd> 切換 <kbd>A</kbd> 對齊 <kbd>O</kbd> 疊圖 <kbd>F</kbd> 已對齊 <kbd>G</kbd> 未對齊</div>
  <div style="margin-top: 4px;"><b>修正</b>: <kbd>T</kbd> 進入/退出 &nbsp; <kbd>D</kbd> 下載完整 alignments-normalized.json &nbsp; <kbd>C</kbd> 清除本地編輯</div>
  <div style="margin-top: 2px; color: #888;">修正模式中：<kbd>↑↓←→</kbd> 移動 (Shift = ×10) <kbd>Z</kbd><kbd>X</kbd> 旋轉 <kbd>-</kbd><kbd>=</kbd> 縮放 <kbd>R</kbd> 重置</div>
</div>

<script>
const ITEMS = __ITEMS__;
const REF_NAME = __REF__;
const CANVAS = __CANVAS__;
const META = __META__;  // {reference, canvas, stats, calibration_unit_px}
const K = META.calibration_unit_px;  // canvas edge in calibration pixels
const STORAGE_KEY = 'fujisan_local_edits_v1';

const frame = document.getElementById('frame');
const badge = document.getElementById('badge');
const counter = document.getElementById('counter');
const filename = document.getElementById('filename');
const meta = document.getElementById('meta');
const cbAligned = document.getElementById('aligned');
const cbOverlay = document.getElementById('overlay');
const cbOnlyAligned = document.getElementById('onlyAligned');
const cbOnlyUnaligned = document.getElementById('onlyUnaligned');
const editPanel = document.getElementById('editPanel');
const editStatus = document.getElementById('editStatus');
const editValues = document.getElementById('editValues');

let idx = 0;
let editMode = false;
let editParams = null;

function loadLocal() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
  catch (e) { return {}; }
}
function saveLocal(obj) { localStorage.setItem(STORAGE_KEY, JSON.stringify(obj)); }
let localEdits = loadLocal();

function paramsToMatrix(p) {
  const r = p.rot * Math.PI / 180;
  const a = p.scale * Math.cos(r);
  const b = p.scale * Math.sin(r);
  const c = -p.scale * Math.sin(r);
  const d = p.scale * Math.cos(r);
  return [[a, b, p.tx], [c, d, p.ty]];
}

function matrixToParams(M) {
  const [[a, b, tx], [c, d, ty]] = M;
  const scale = Math.sqrt(a * a + b * b);
  const rot = Math.atan2(b, a) * 180 / Math.PI;
  return { scale, rot, tx, ty };
}

// What matrix do we render right now?
function effectiveMatrix(it) {
  if (localEdits[it.name]) return paramsToMatrix(localEdits[it.name]);
  if (it.matrix) return it.matrix;
  if (it.seed) return it.seed.matrix;
  return null;
}

function effectiveStatus(it) {
  if (localEdits[it.name]) return 'edited';
  if (it.source === 'manual') return 'manual';
  if (it.source === 'auto') return 'auto';
  if (it.seed) return 'seed';
  return 'fail';
}

function visibleItems() {
  if (cbOnlyAligned.checked) return ITEMS.filter(it => {
    const s = effectiveStatus(it);
    return s !== 'fail' && s !== 'seed';
  });
  if (cbOnlyUnaligned.checked) return ITEMS.filter(it => {
    const s = effectiveStatus(it);
    return s === 'fail' || s === 'seed';
  });
  return ITEMS;
}

function fitFrame() {
  const pad = 80;
  const sx = (window.innerWidth - pad) / CANVAS.w;
  const sy = (window.innerHeight - pad) / CANVAS.h;
  const s = Math.min(sx, sy, 1);
  frame.style.transform = `scale(${s})`;
}
window.addEventListener('resize', fitFrame);

function render() {
  const list = visibleItems();
  if (list.length === 0) {
    frame.innerHTML = '';
    counter.textContent = '0 / 0';
    filename.textContent = '(empty)';
    return;
  }
  if (idx >= list.length) idx = list.length - 1;
  if (idx < 0) idx = 0;
  const it = list[idx];

  frame.innerHTML = '';

  if (cbOverlay.checked || editMode) {
    const r = document.createElement('img');
    r.src = 'images-resized/' + REF_NAME;
    r.style.opacity = '0.5';
    frame.appendChild(r);
  }

  const img = document.createElement('img');
  img.src = 'images-resized/' + it.name;
  let M;
  if (editMode && editParams) {
    M = paramsToMatrix(editParams);
  } else if (cbAligned.checked) {
    M = effectiveMatrix(it);
  }
  if (M) {
    const [[a, b, tx], [c, d, ty]] = M;
    img.style.transform = `matrix(${a}, ${c}, ${b}, ${d}, ${tx}, ${ty})`;
  } else {
    const offX = (CANVAS.w - (it.src_w || CANVAS.w)) / 2;
    const offY = (CANVAS.h - (it.src_h || CANVAS.h)) / 2;
    img.style.transform = `translate(${offX}px, ${offY}px)`;
  }
  if (cbOverlay.checked || editMode) img.style.opacity = '0.55';
  frame.appendChild(img);

  const st = effectiveStatus(it);
  const labels = { auto: 'AUTO', manual: 'MANUAL', edited: 'EDITED', seed: 'SEED', fail: 'FAIL' };
  badge.className = 'badge ' + st;
  badge.textContent = labels[st];
  counter.textContent = `${idx + 1} / ${list.length}`;
  filename.textContent = it.name;
  if (editMode && editParams) {
    meta.textContent = `[edit] scale=${editParams.scale.toFixed(3)}  rot=${editParams.rot.toFixed(2)}°  t=(${editParams.tx.toFixed(0)}, ${editParams.ty.toFixed(0)})`;
  } else if (st === 'edited') {
    const p = localEdits[it.name];
    meta.textContent = `local edit: scale=${p.scale.toFixed(3)}  rot=${p.rot.toFixed(2)}°  t=(${p.tx.toFixed(0)}, ${p.ty.toFixed(0)})`;
  } else if (it.matrix) {
    meta.textContent = `${it.source}: scale=${it.scale.toFixed(3)}  rot=${it.rot.toFixed(2)}°`;
  } else if (it.seed) {
    meta.textContent = `seed from: ${it.seed.from}`;
  } else {
    meta.textContent = `unaligned (${it.reason || 'no data'})`;
  }

  if (editMode) {
    editPanel.classList.add('active');
    editStatus.innerHTML = '<b>修正模式</b> &nbsp; <kbd>T</kbd>/<kbd>Esc</kbd> 退出';
    editValues.style.display = 'block';
    if (editParams) {
      editValues.innerHTML =
        `tx=${editParams.tx.toFixed(1)}  ty=${editParams.ty.toFixed(1)}<br>` +
        `scale=${editParams.scale.toFixed(4)}  rot=${editParams.rot.toFixed(3)}°`;
    }
  } else {
    editPanel.classList.remove('active');
    editStatus.innerHTML = 'Tweak: <kbd>T</kbd> 進入修正';
    editValues.style.display = 'none';
  }
}

function enterEditMode() {
  const list = visibleItems();
  if (!list.length) return;
  const it = list[idx];
  const M = effectiveMatrix(it);
  editParams = M ? matrixToParams(M) : { scale: 1.0, rot: 0, tx: 0, ty: 0 };
  editMode = true;
  render();
}

function exitEditMode() {
  if (editParams) {
    const list = visibleItems();
    const it = list[idx];
    localEdits[it.name] = { ...editParams };
    saveLocal(localEdits);
  }
  editMode = false;
  editParams = null;
  render();
}

function nudge(dx, dy, dscale, drot) {
  if (!editMode || !editParams) return;
  if (dx) editParams.tx += dx;
  if (dy) editParams.ty += dy;
  if (dscale) editParams.scale *= dscale;
  if (drot) editParams.rot += drot;
  const list = visibleItems();
  const it = list[idx];
  localEdits[it.name] = { ...editParams };
  saveLocal(localEdits);
  render();
}

function resetCurrent() {
  const list = visibleItems();
  const it = list[idx];
  delete localEdits[it.name];
  saveLocal(localEdits);
  if (editMode) {
    const M = effectiveMatrix(it);
    editParams = M ? matrixToParams(M) : { scale: 1, rot: 0, tx: 0, ty: 0 };
  }
  render();
}

function clearLocalEdits() {
  if (Object.keys(localEdits).length === 0) return;
  if (!confirm(`清除全部 ${Object.keys(localEdits).length} 筆本地編輯？`)) return;
  localEdits = {};
  saveLocal(localEdits);
  if (editMode) exitEditMode();
  render();
}

// Build full alignments-normalized.json with local edits applied. Pixel
// translations get divided by K to match the on-disk normalized format.
function buildNormalizedSnapshot() {
  const out = {
    reference: META.reference,
    calibration_unit_px: K,
    coordinate_system: META.coordinate_system,
    items: {},
  };
  let nManual = 0, nAuto = 0, nUnaligned = 0;
  for (const it of ITEMS) {
    let M, src, scale, rot;
    if (localEdits[it.name]) {
      const p = localEdits[it.name];
      M = paramsToMatrix(p);
      scale = p.scale; rot = p.rot; src = 'manual';
    } else if (it.matrix) {
      M = it.matrix;
      scale = it.scale; rot = it.rot; src = it.source;
    } else {
      out.items[it.name] = {
        matrix: null,
        source: 'unaligned',
        reason: it.reason,
      };
      nUnaligned++;
      continue;
    }
    const [[a, b, tx], [c, d, ty]] = M;
    out.items[it.name] = {
      matrix: [[a, b, tx / K], [c, d, ty / K]],
      scale: scale,
      rotation_deg: rot,
      tx: tx / K,
      ty: ty / K,
      src_aspect: (it.src_w && it.src_h) ? it.src_w / it.src_h : null,
      source: src,
    };
    if (src === 'manual') nManual++; else nAuto++;
  }
  out.stats = { total: ITEMS.length, manual: nManual, auto: nAuto, unaligned: nUnaligned };
  return out;
}

function downloadNormalized() {
  const snap = buildNormalizedSnapshot();
  const blob = new Blob([JSON.stringify(snap, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'alignments-normalized.json';
  a.click();
  URL.revokeObjectURL(a.href);
}

document.addEventListener('keydown', e => {
  if (editMode) {
    const big = e.shiftKey;
    if (e.key === 'ArrowLeft')  { nudge(big ? -10 : -1, 0, null, null); e.preventDefault(); return; }
    if (e.key === 'ArrowRight') { nudge(big ?  10 :  1, 0, null, null); e.preventDefault(); return; }
    if (e.key === 'ArrowUp')    { nudge(0, big ? -10 : -1, null, null); e.preventDefault(); return; }
    if (e.key === 'ArrowDown')  { nudge(0, big ?  10 :  1, null, null); e.preventDefault(); return; }
    if (e.key === 'z' || e.key === 'Z') { nudge(null, null, null, big ? -1 : -0.1); return; }
    if (e.key === 'x' || e.key === 'X') { nudge(null, null, null, big ?  1 :  0.1); return; }
    if (e.key === '-' || e.key === '_') { nudge(null, null, big ? 0.95 : 0.99, null); return; }
    if (e.key === '=' || e.key === '+') { nudge(null, null, big ? 1.05 : 1.01, null); return; }
    if (e.key === 'r' || e.key === 'R') { resetCurrent(); return; }
    if (e.key === 'd' || e.key === 'D') { downloadNormalized(); return; }
    if (e.key === 't' || e.key === 'T' || e.key === 'Escape') { exitEditMode(); return; }
    return;
  }
  if (e.key === 'ArrowRight' || e.key === ' ') { idx++; render(); e.preventDefault(); }
  else if (e.key === 'ArrowLeft') { idx--; render(); e.preventDefault(); }
  else if (e.key === 'a' || e.key === 'A') { cbAligned.checked = !cbAligned.checked; render(); }
  else if (e.key === 'o' || e.key === 'O') { cbOverlay.checked = !cbOverlay.checked; render(); }
  else if (e.key === 'f' || e.key === 'F') { cbOnlyAligned.checked = !cbOnlyAligned.checked; if (cbOnlyAligned.checked) cbOnlyUnaligned.checked = false; idx = 0; render(); }
  else if (e.key === 'g' || e.key === 'G') { cbOnlyUnaligned.checked = !cbOnlyUnaligned.checked; if (cbOnlyUnaligned.checked) cbOnlyAligned.checked = false; idx = 0; render(); }
  else if (e.key === 't' || e.key === 'T') { enterEditMode(); }
  else if (e.key === 'd' || e.key === 'D') { downloadNormalized(); }
  else if (e.key === 'c' || e.key === 'C') { clearLocalEdits(); }
});

[cbAligned, cbOverlay].forEach(cb => cb.addEventListener('change', render));
cbOnlyAligned.addEventListener('change', () => { if (cbOnlyAligned.checked) cbOnlyUnaligned.checked = false; idx = 0; render(); });
cbOnlyUnaligned.addEventListener('change', () => { if (cbOnlyUnaligned.checked) cbOnlyAligned.checked = false; idx = 0; render(); });

fitFrame();
render();
</script>
</body>
</html>
"""

html = (HTML
        .replace("__W__", str(canvas["w"]))
        .replace("__H__", str(canvas["h"]))
        .replace("__ITEMS__", json.dumps(items))
        .replace("__REF__", json.dumps(ref_name))
        .replace("__CANVAS__", json.dumps(canvas))
        .replace("__META__", json.dumps({
            "reference": ref_name,
            "canvas": canvas,
            "stats": stats,
            "calibration_unit_px": canvas["w"],
            "coordinate_system": (
                "Square canvas, normalized to unit length 1.0. "
                "tx and ty are fractions of the canvas edge."
            ),
        })))

(ROOT / "viewer.html").write_text(html, encoding="utf-8")

n_seeded = sum(1 for it in items if it.get("seed"))
src_label = "alignments-normalized.json" if NORMALIZED.exists() else "alignments-final.json"
print(f"Wrote viewer.html from {src_label}")
print(f"  total: {stats['total']}  manual: {stats['manual']}  auto: {stats['auto']}  unaligned: {stats['unaligned']}")
print(f"  unaligned with neighbor seed: {n_seeded}")
print(f"Open: http://localhost:8765/alignment/viewer.html")
