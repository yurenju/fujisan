# 傾斜驅動的富士山照片瀏覽器 — 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `poc/index.html` 升級成 `app/` 下的單頁體驗，支援手機按住紅圈傾斜切換照片、桌機用滑鼠位置模擬，polaroid 有 damped 3D 傾斜與光影。

**Architecture:** 純前端靜態站，純 ES modules，無建置流程。Repo 完全不引入 Node tooling — 用既有的 `python -m http.server` 開發。模組拆成 loader / gyro / pointer / mapping / polaroid / debug，由 main.js 串接。每個 task 結尾用瀏覽器（透過 Claude Preview MCP）做行為驗收。

**Tech Stack:** Vanilla JS (ES modules)、CSS、Python 3 + Pillow（資料 / 圖片前處理腳本）。

**驗收方式（取代 TDD）：** 每個 task 結束前在瀏覽器執行具體的行為檢查（按下、傾斜到某個方向、觀察 caption 數字變化等），用 `mcp__Claude_Preview__preview_*` 工具確認 console 沒錯誤、DOM/畫面符合預期。

**Spec：** [docs/superpowers/specs/2026-05-06-tilt-driven-fuji-viewer-design.md](../specs/2026-05-06-tilt-driven-fuji-viewer-design.md)

---

## Task 1：建立 `app/` 骨架

**Files:**
- Create: `app/index.html`、`app/styles.css`、`app/main.js`
- Create: `app/src/loader.js`、`app/src/gyro.js`、`app/src/pointer.js`、`app/src/mapping.js`、`app/src/polaroid.js`、`app/src/debug.js`（全部 placeholder）
- Modify: `.gitignore`

- [ ] **Step 1：建立 `app/index.html` 空骨架**

```html
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<title>Fujisan</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<script type="module" src="main.js"></script>
</body>
</html>
```

- [ ] **Step 2：建立各模組 placeholder**

`app/main.js`、`app/styles.css`、`app/src/*.js` 內容都只放：

```js
// placeholder — implementation in later tasks
```

（CSS 檔案保持空白即可，無需註解。）

- [ ] **Step 3：`.gitignore` 不需要為 app/ 增加任何規則**

WebP 後的 `app/images/` 約 10 MB，可以直接 commit 進 git，使部署只需要單一 git pull 就能拿到全部資產。

- [ ] **Step 4：在瀏覽器確認骨架可載入**

啟動 preview server (`mcp__Claude_Preview__preview_start` 'fujisan')，導向 `/app/index.html`。
預期：看到空白頁面、`mcp__Claude_Preview__preview_console_logs` 沒有錯誤。

- [ ] **Step 5：Commit**

```bash
git add app/
git commit -m "Bootstrap app/ skeleton with empty modules"
```

---

## Task 2：產生 `photos.json`、轉碼 WebP、複製對齊資料

**Files:**
- Create: `scripts/build_app_data.py`
- Create: `scripts/build_app_images.py`
- Create: `app/data/photos.json`、`app/data/alignments.json`
- Create: `app/images/`（125 張 WebP）

- [ ] **Step 1：建立 `scripts/build_app_data.py`**

```python
"""Build app/data/photos.json from poc/data.json by flattening into 6 rows.

Filenames in the output are switched from .jpg to .webp so the app loads
the transcoded assets.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
src = json.loads((REPO / "poc" / "data.json").read_text(encoding="utf-8"))

def to_webp(name: str) -> str:
    return name.rsplit(".", 1)[0] + ".webp"

rows = [
    {"id": "top-rest", "label": "早上的散張",
     "photos": [to_webp(p) for p in src["topRest"]]},
]
for i, seq in enumerate(src["sequences"], start=1):
    rows.append({
        "id": f"seq-{i}",
        "label": seq["date"],
        "photos": [to_webp(p) for p in seq["photos"]],
    })
rows.append({
    "id": "bottom-rest",
    "label": "其他散張",
    "photos": [to_webp(p) for p in src["bottomRest"]],
})

out_path = REPO / "app" / "data" / "photos.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

total = sum(len(r["photos"]) for r in rows)
print(f"Wrote {out_path} with {len(rows)} rows, {total} photos")
```

- [ ] **Step 2：執行腳本產生 photos.json**

執行：`python scripts/build_app_data.py`
預期輸出：`Wrote .../app/data/photos.json with 6 rows, 125 photos`

- [ ] **Step 3：建立 `scripts/build_app_images.py`**

```python
"""Build app/images/*.webp from the originals at alignment/images/*.jpg.

Mirrors alignment/resize.py's geometry (exif_transpose + LANCZOS
thumbnail to 1568x1568) so alignments.json's matrices remain valid,
but encodes WebP q80 directly from the original to avoid the extra
JPG round-trip that alignment/images-resized/ has gone through.

Also rewrites alignments.json's keys from .jpg to .webp.
"""
import json
from pathlib import Path
from PIL import Image, ImageOps

REPO = Path(__file__).resolve().parents[1]
SRC_DIR = REPO / "alignment" / "images"
OUT_DIR = REPO / "app" / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_SIDE = 1568
QUALITY = 80
total_bytes = 0
count = 0

for src in sorted(SRC_DIR.glob("*.jpg")):
    out = OUT_DIR / (src.stem + ".webp")
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        im.save(out, format="WEBP", quality=QUALITY, method=6)
    total_bytes += out.stat().st_size
    count += 1

print(f"Wrote {count} WebPs, total {total_bytes/1024/1024:.1f} MB, "
      f"avg {total_bytes/count/1024:.1f} KB")

# Rewrite alignments.json keys from .jpg to .webp.
src_align = json.loads((REPO / "alignment" / "aligned-all"
                        / "alignments-normalized.json").read_text(encoding="utf-8"))
new_items = {}
for k, v in src_align.get("items", {}).items():
    new_key = k.rsplit(".", 1)[0] + ".webp" if k.lower().endswith(".jpg") else k
    new_items[new_key] = v
src_align["items"] = new_items

out_align = REPO / "app" / "data" / "alignments.json"
out_align.parent.mkdir(parents=True, exist_ok=True)
out_align.write_text(json.dumps(src_align, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {out_align}")
```

- [ ] **Step 4：執行轉碼腳本**

執行：`python scripts/build_app_images.py`
預期輸出：類似 `Wrote 125 WebPs, total 10.4 MB, avg 85.2 KB`

- [ ] **Step 5：驗證每張被引用的照片都存在**

```bash
python -c "
import json, os
data = json.load(open('app/data/photos.json', encoding='utf-8'))
files = []
for row in data['rows']:
    files.extend(row['photos'])
missing = [f for f in files if not os.path.exists(f'app/images/{f}')]
print(f'Total: {len(files)}, Missing: {len(missing)}')
if missing: print('First missing:', missing[:3])
"
```

預期：`Total: 125, Missing: 0`

- [ ] **Step 6：Commit**

```bash
git add app/data/ app/images/ scripts/build_app_data.py scripts/build_app_images.py
git commit -m "Add app data: photos.json + alignments.json + 125 WebP images + transcoding scripts"
```

注意：`app/images/` 含 125 個 WebP 共 ~10 MB，全部一起 commit。

---

## Task 3：實作 `mapping.js`（純函式）

**Files:**
- Modify: `app/src/mapping.js`

- [ ] **Step 1：實作**

```js
// Pure mapping from tilt delta to (row, col) index. No DOM, no events.
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

export function tiltToIndex({ db, dg }, baseRow01, baseCol01, sensitivityDeg, rows) {
  const rowCount = rows.length;
  const rowIndex01 = clamp(baseRow01 + db / sensitivityDeg, 0, 1);
  const colIndex01 = clamp(baseCol01 + dg / sensitivityDeg, 0, 1);

  const row = Math.round(rowIndex01 * (rowCount - 1));
  const len = rows[row].photos.length;
  const col = clamp(Math.floor(colIndex01 * len), 0, len - 1);

  return { row, col };
}
```

- [ ] **Step 2：在瀏覽器 console 快速 sanity check**

啟動 preview，在 `/app/index.html` 的 console 用 `mcp__Claude_Preview__preview_eval` 載入並執行：

```js
(async () => {
  const m = await import('./src/mapping.js');
  const rows = [{photos:Array(29)}, {photos:Array(7)}, {photos:Array(10)}, {photos:Array(30)}, {photos:Array(20)}, {photos:Array(29)}];
  return {
    zero: m.tiltToIndex({db:0,dg:0}, 0.5, 0.5, 20, rows),
    clampTop: m.tiltToIndex({db:-1000,dg:0}, 0.5, 0.5, 20, rows),
    clampBottom: m.tiltToIndex({db:1000,dg:0}, 0.5, 0.5, 20, rows),
    rightEdge: m.tiltToIndex({db:0,dg:1000}, 0.5, 0.5, 20, rows),
  };
})()
```

預期：
- `zero.row === 3`（round(0.5*5) = 3，配合 ceil 邏輯可能 2 或 3 — 兩者皆可接受）
- `clampTop.row === 0`
- `clampBottom.row === 5`
- `rightEdge.col === rows[clampedRow].photos.length - 1`

- [ ] **Step 3：Commit**

```bash
git add app/src/mapping.js
git commit -m "Add mapping.js: tilt delta to (row, col) with clamping"
```

---

## Task 4：實作 `gyro.js`（DeviceOrientation + 權限偵測 + EMA filter）

**Files:**
- Modify: `app/src/gyro.js`

- [ ] **Step 1：實作**

```js
// Wrap DeviceOrientation events: permission probing, request, and a
// calibrated tilt stream emitting {db, dg} (delta beta/gamma) relative
// to the orientation captured at the most recent startCalibrated().

export function probePermission(timeoutMs = 500) {
  return new Promise(resolve => {
    let received = false;
    const onEvent = (e) => {
      if (e.beta != null || e.gamma != null) received = true;
    };
    window.addEventListener('deviceorientation', onEvent);
    setTimeout(() => {
      window.removeEventListener('deviceorientation', onEvent);
      resolve(received ? 'granted' : 'unknown');
    }, timeoutMs);
  });
}

export async function ensurePermission() {
  const D = window.DeviceOrientationEvent;
  if (D && typeof D.requestPermission === 'function') {
    return D.requestPermission();
  }
  return 'granted';
}

export function createGyroSource({ alpha = 0.18 } = {}) {
  const listeners = [];
  let smoothedBeta = 0;
  let smoothedGamma = 0;
  let initialized = false;
  let neutralBeta = 0;
  let neutralGamma = 0;
  let calibrated = false;

  const handler = (e) => {
    const b = e.beta ?? 0;
    const g = e.gamma ?? 0;
    if (!initialized) {
      smoothedBeta = b;
      smoothedGamma = g;
      initialized = true;
    } else {
      smoothedBeta = alpha * b + (1 - alpha) * smoothedBeta;
      smoothedGamma = alpha * g + (1 - alpha) * smoothedGamma;
    }
    if (calibrated) {
      const ev = {
        db: smoothedBeta - neutralBeta,
        dg: smoothedGamma - neutralGamma,
      };
      listeners.forEach(fn => fn(ev));
    }
  };

  window.addEventListener('deviceorientation', handler);

  return {
    onTilt(fn) { listeners.push(fn); },
    startCalibrated() {
      neutralBeta = smoothedBeta;
      neutralGamma = smoothedGamma;
      calibrated = true;
    },
    stop() {
      calibrated = false;
      window.removeEventListener('deviceorientation', handler);
      listeners.length = 0;
    },
  };
}
```

- [ ] **Step 2：Commit**

```bash
git add app/src/gyro.js
git commit -m "Add gyro.js: permission probe, request, calibrated tilt stream with EMA filter"
```

（這個模組在 Task 9 main.js 串好之後才會在瀏覽器跑得到，所以這邊不單獨驗收。）

---

## Task 5：實作 `pointer.js`（桌機 / fallback）

**Files:**
- Modify: `app/src/pointer.js`

- [ ] **Step 1：實作**

```js
// Mouse-position simulation of the gyro tilt stream. Same shape as gyro:
// onTilt({db, dg}), startCalibrated(), stop(). Also exposes onPressStart /
// onPressEnd so main.js can drive the same press-to-recalibrate flow.

export function createPointerSource({ maxDeg = 20 } = {}) {
  const tiltListeners = [];
  const pressStartListeners = [];
  const pressEndListeners = [];

  let pressed = false;
  let neutralX = 0;
  let neutralY = 0;
  let lastX = 0;
  let lastY = 0;
  let calibrated = false;

  const onMouseDown = (e) => {
    pressed = true;
    lastX = e.clientX;
    lastY = e.clientY;
    pressStartListeners.forEach(fn => fn());
  };

  const onMouseMove = (e) => {
    if (!pressed) return;
    lastX = e.clientX;
    lastY = e.clientY;
    if (!calibrated) return;
    const dg = ((lastX - neutralX) / window.innerWidth)  * maxDeg;
    const db = ((lastY - neutralY) / window.innerHeight) * maxDeg;
    tiltListeners.forEach(fn => fn({ db, dg }));
  };

  const onMouseUp = () => {
    if (!pressed) return;
    pressed = false;
    calibrated = false;
    pressEndListeners.forEach(fn => fn());
  };

  window.addEventListener('mousedown', onMouseDown);
  window.addEventListener('mousemove', onMouseMove);
  window.addEventListener('mouseup', onMouseUp);

  return {
    onTilt(fn) { tiltListeners.push(fn); },
    onPressStart(fn) { pressStartListeners.push(fn); },
    onPressEnd(fn) { pressEndListeners.push(fn); },
    startCalibrated() {
      neutralX = lastX;
      neutralY = lastY;
      calibrated = true;
    },
    stop() {
      window.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      tiltListeners.length = 0;
      pressStartListeners.length = 0;
      pressEndListeners.length = 0;
    },
  };
}
```

- [ ] **Step 2：Commit**

```bash
git add app/src/pointer.js
git commit -m "Add pointer.js: mouse-position tilt simulation with press lifecycle"
```

---

## Task 6：實作 `loader.js`（含優先載入 + 進度回呼）

**Files:**
- Modify: `app/src/loader.js`

- [ ] **Step 1：實作**

```js
// Fetches photos.json + alignments.json, denormalizes alignment matrices,
// creates a hidden <img> per referenced file with its alignment transform.
// The first photo is fetched synchronously so the UI has something to show
// before returning; the rest are loaded by N parallel background workers
// and emit onProgress(loaded, total) per completion.

const CONCURRENCY = 6;

export async function loadAll({
  stage,
  photosUrl = 'data/photos.json',
  alignmentsUrl = 'data/alignments.json',
  onProgress,
} = {}) {
  const [photos, alignmentsRaw] = await Promise.all([
    fetch(photosUrl).then(r => r.json()),
    fetch(alignmentsUrl).then(r => r.json()),
  ]);

  const K = alignmentsRaw.calibration_unit_px || 1568;
  const items = {};
  for (const [name, r] of Object.entries(alignmentsRaw.items || {})) {
    if (!r.matrix) continue;
    const [a, b, txN] = r.matrix[0];
    const [c, d, tyN] = r.matrix[1];
    items[name] = { matrix: [[a, b, txN * K], [c, d, tyN * K]] };
  }
  const alignment = { calibration_unit_px: K, items };

  const ordered = [];
  for (const row of photos.rows) for (const f of row.photos) ordered.push(f);

  const imgByFile = {};
  for (const file of ordered) {
    const img = document.createElement('img');
    img.style.display = 'none';
    img.style.position = 'absolute';
    img.style.top = '0';
    img.style.left = '0';
    img.style.transformOrigin = '0 0';
    img.style.willChange = 'transform';
    const item = items[file];
    if (item) {
      const [[a, b, tx], [c, d, ty]] = item.matrix;
      img.style.transform = `matrix(${a}, ${c}, ${b}, ${d}, ${tx}, ${ty})`;
    }
    stage.appendChild(img);
    imgByFile[file] = img;
  }

  // Synchronously load the first photo so the caller can show it immediately.
  let loaded = 0;
  const total = ordered.length;
  await assignSrc(imgByFile[ordered[0]], `images/${ordered[0]}`);
  loaded++;
  onProgress?.(loaded, total);

  // Background workers fetch the rest in row-major order.
  const queue = ordered.slice(1);
  const startWorker = async () => {
    while (queue.length) {
      const file = queue.shift();
      if (!file) return;
      try { await assignSrc(imgByFile[file], `images/${file}`); }
      catch { /* swallow — img.onerror still resolves */ }
      loaded++;
      onProgress?.(loaded, total);
    }
  };
  // Fire and forget; do not block loadAll's caller.
  Promise.all(Array.from({ length: CONCURRENCY }, startWorker));

  return { rows: photos.rows, alignment, imgByFile };
}

function assignSrc(img, url) {
  return new Promise((resolve) => {
    img.onload = () => resolve();
    img.onerror = () => resolve();
    img.src = url;
  });
}

export function showPhoto(imgByFile, currentFile, nextFile) {
  if (currentFile && imgByFile[currentFile]) imgByFile[currentFile].style.display = 'none';
  if (imgByFile[nextFile]) imgByFile[nextFile].style.display = '';
  return nextFile;
}
```

- [ ] **Step 2：Commit**

```bash
git add app/src/loader.js
git commit -m "Add loader.js: prioritized first-photo load + parallel background preload + progress callback"
```

---

## Task 7：實作 `polaroid.js`

**Files:**
- Modify: `app/src/polaroid.js`

- [ ] **Step 1：實作**

```js
// Apply the polaroid's per-frame visual transform: 3D rotation, specular
// highlight position, and shadow offset. Pure DOM mutation — no event
// subscription, no calibration logic.

export function applyTiltVisual(el, { db, dg }, { tiltDamping = 0.4, highlightIntensity = 0.5 } = {}) {
  const rx = (-db * tiltDamping).toFixed(3);
  const ry = ( dg * tiltDamping).toFixed(3);
  el.style.transform = `rotateX(${rx}deg) rotateY(${ry}deg)`;

  const shineX = 50 - dg * 1.5;
  const shineY = 30 - db * 1.5;
  const intensityScale = highlightIntensity / 0.5;
  const shineOpacity = 0.35 + Math.min(0.4, (Math.abs(db) + Math.abs(dg)) * 0.015) * intensityScale;
  el.style.setProperty('--shine-x', `${shineX}%`);
  el.style.setProperty('--shine-y', `${shineY}%`);
  el.style.setProperty('--shine-opacity', shineOpacity.toFixed(3));

  const sx = -dg * 0.6;
  const sy = 12 + db * 0.4;
  el.style.boxShadow =
    `${sx}px ${sy}px 40px rgba(0,0,0,0.55), ${sx/3}px ${sy/4}px 6px rgba(0,0,0,0.4)`;
}
```

- [ ] **Step 2：Commit**

```bash
git add app/src/polaroid.js
git commit -m "Add polaroid.js: 3D transform + shifting highlight + shadow"
```

---

## Task 8：實作 `debug.js`（slider + URL hash）

**Files:**
- Modify: `app/src/debug.js`

- [ ] **Step 1：實作**

```js
// URL-hash backed live-tunable parameters: sensitivity (s), tilt damping
// (d), highlight intensity (h). Renders three sliders that other modules
// read via the returned tuning object.

export function parseHash(hash) {
  if (!hash || hash === '#') return {};
  const out = {};
  const body = hash.startsWith('#') ? hash.slice(1) : hash;
  for (const part of body.split('&')) {
    const [k, v] = part.split('=');
    if (!k) continue;
    const num = Number(v);
    if (!Number.isNaN(num)) out[k] = num;
  }
  return out;
}

export function formatHash(values) {
  return '#' + Object.entries(values).map(([k, v]) => `${k}=${v}`).join('&');
}

export function createTuning({ defaults }) {
  const fromHash = parseHash(location.hash);
  const values = { ...defaults, ...fromHash };

  function set(key, value) {
    values[key] = value;
    history.replaceState(null, '', location.pathname + location.search + formatHash(values));
  }

  return { values, set };
}

export function mountSliders(container, tuning, ranges) {
  const wrap = document.createElement('div');
  wrap.className = 'debug-sliders';
  wrap.innerHTML = `
    <label>sensitivity <span data-out="s">${tuning.values.s}</span>°</label>
    <input type="range" min="${ranges.s[0]}" max="${ranges.s[1]}" step="0.5" value="${tuning.values.s}" data-key="s">
    <label>tilt damping <span data-out="d">${tuning.values.d}</span></label>
    <input type="range" min="${ranges.d[0]}" max="${ranges.d[1]}" step="0.05" value="${tuning.values.d}" data-key="d">
    <label>highlight <span data-out="h">${tuning.values.h}</span></label>
    <input type="range" min="${ranges.h[0]}" max="${ranges.h[1]}" step="0.05" value="${tuning.values.h}" data-key="h">
  `;
  container.appendChild(wrap);
  wrap.addEventListener('input', (e) => {
    const key = e.target.dataset.key;
    if (!key) return;
    const v = Number(e.target.value);
    tuning.set(key, v);
    const out = wrap.querySelector(`[data-out="${key}"]`);
    if (out) out.textContent = v;
  });
  return wrap;
}
```

- [ ] **Step 2：Commit**

```bash
git add app/src/debug.js
git commit -m "Add debug.js: URL-hash-backed sensitivity/damping/highlight tuning"
```

---

## Task 9：串接 `main.js`、`index.html`、`styles.css` + 桌機驗收

**Files:**
- Modify: `app/index.html`、`app/styles.css`、`app/main.js`

- [ ] **Step 1：擴充 `app/index.html`**

```html
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Fujisan</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="scene">
    <div id="polaroid">
      <div id="photo-frame">
        <div id="stage-clip"><div id="stage"></div></div>
      </div>
      <div id="caption"></div>
    </div>
  </div>
  <div id="progress" aria-hidden="true"></div>
  <button id="tilt-button" type="button" aria-label="按住傾斜">
    <span class="dot-grid"></span>
    <span class="label">按住傾斜</span>
  </button>
  <div id="debug-panel"></div>
  <script type="module" src="main.js"></script>
</body>
</html>
```

- [ ] **Step 2：撰寫 `app/styles.css`**

```css
:root {
  --bg: #111;
  --fg: #eee;
  --paper: #f5f1e8;
  --inner: #e8e1d0;
  --accent-red: #d34d4d;
  --transition: 300ms ease-out;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  height: 100%;
  background: var(--bg);
  color: var(--fg);
  font-family: -apple-system, "Helvetica Neue", sans-serif;
  overflow: hidden;
}
#scene {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1200px;
}
#polaroid {
  position: relative;
  background: var(--paper);
  padding: 22px 22px 80px 22px;
  border-radius: 2px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.55), 0 2px 6px rgba(0,0,0,0.4);
  transform-style: preserve-3d;
  transition: transform var(--transition), box-shadow var(--transition);
  max-width: calc(100vh - 32px);
  max-height: calc(100vh - 32px);
}
#polaroid::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(
    circle at var(--shine-x, 50%) var(--shine-y, 30%),
    rgba(255,255,255,0.55) 0%,
    rgba(255,255,255,0.18) 18%,
    rgba(255,255,255,0) 45%);
  mix-blend-mode: screen;
  opacity: var(--shine-opacity, 0.35);
  transition: opacity var(--transition);
}
#photo-frame {
  width: min(80vh, calc(100vw - 64px));
  height: min(80vh, calc(100vw - 64px));
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--inner);
  overflow: hidden;
  position: relative;
}
#stage-clip {
  position: relative;
  overflow: hidden;
  background: var(--inner);
}
#stage {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
  background: var(--inner);
}
#caption {
  margin-top: 18px;
  font-family: "Permanent Marker", "Marker Felt", "Bradley Hand", cursive;
  color: #2a2a2a;
  font-size: 18px;
  text-align: center;
  align-self: stretch;
  min-height: 22px;
}

/* Preload progress indicator — fades out when complete */
#progress {
  position: fixed;
  right: 24px;
  top: 24px;
  font-family: "SF Mono", Consolas, monospace;
  font-size: 11px;
  color: #888;
  letter-spacing: 0.05em;
  opacity: 1;
  transition: opacity 600ms ease;
  z-index: 35;
}
#progress.done {
  opacity: 0;
  pointer-events: none;
}

/* Tilt button — hidden on desktop, shown on coarse pointer (mobile) */
#tilt-button {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 2px dashed var(--accent-red);
  background: rgba(211, 77, 77, 0.08);
  color: var(--accent-red);
  font: inherit;
  font-size: 11px;
  display: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  -webkit-touch-callout: none;
  user-select: none;
  animation: breathe 2s ease-in-out infinite;
  cursor: pointer;
  z-index: 30;
}
#tilt-button.active {
  border-style: solid;
  background: rgba(211, 77, 77, 0.18);
  box-shadow: 0 0 18px rgba(211, 77, 77, 0.5);
  animation: none;
}
#tilt-button.denied {
  border-color: #888;
  color: #888;
  background: rgba(136,136,136,0.08);
}
#tilt-button .dot-grid {
  width: 16px;
  height: 16px;
  background: radial-gradient(circle, currentColor 1.5px, transparent 2px) 0 0/6px 6px;
}
@keyframes breathe {
  0%, 100% { opacity: 0.7; }
  50%      { opacity: 1.0; }
}
@media (hover: none) and (pointer: coarse) {
  #tilt-button { display: flex; }
}

/* Debug sliders */
#debug-panel { position: fixed; left: 12px; top: 12px; z-index: 40; }
.debug-sliders {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  border-radius: 6px;
  font-size: 11px;
  color: #ccc;
  width: 180px;
}
.debug-sliders input[type="range"] { width: 100%; }
```

- [ ] **Step 3：撰寫 `app/main.js`**

```js
import { loadAll, showPhoto } from './src/loader.js';
import { probePermission, ensurePermission, createGyroSource } from './src/gyro.js';
import { createPointerSource } from './src/pointer.js';
import { tiltToIndex } from './src/mapping.js';
import { applyTiltVisual } from './src/polaroid.js';
import { createTuning, mountSliders } from './src/debug.js';

const polaroid = document.getElementById('polaroid');
const photoFrame = document.getElementById('photo-frame');
const stage = document.getElementById('stage');
const stageClip = document.getElementById('stage-clip');
const caption = document.getElementById('caption');
const tiltBtn = document.getElementById('tilt-button');
const debugPanel = document.getElementById('debug-panel');
const progress = document.getElementById('progress');

const tuning = createTuning({ defaults: { s: 20, d: 0.4, h: 0.5 } });
mountSliders(debugPanel, tuning, { s: [10, 40], d: [0, 1], h: [0, 1] });

let CANVAS = 1568;
let rows = [];
let imgByFile = {};
let currentFile = null;
let currentRow = 0;
let currentCol = 0;
let baseRow01 = 0;
let baseCol01 = 0;

function fitStage() {
  const w = photoFrame.clientWidth;
  const h = photoFrame.clientHeight;
  const s = Math.min(w / CANVAS, h / CANVAS);
  stageClip.style.width = (CANVAS * s) + 'px';
  stageClip.style.height = (CANVAS * s) + 'px';
  stage.style.width = CANVAS + 'px';
  stage.style.height = CANVAS + 'px';
  stage.style.transform = `scale(${s})`;
}
window.addEventListener('resize', fitStage);

function setPhoto(rowIdx, colIdx) {
  currentRow = rowIdx;
  currentCol = colIdx;
  const file = rows[rowIdx].photos[colIdx];
  if (file !== currentFile) {
    currentFile = showPhoto(imgByFile, currentFile, file);
    const m = file.match(/PXL_(\d{8})_(\d{6})/);
    if (m) {
      const [, d, t] = m;
      caption.textContent = `${d.slice(0,4)}/${d.slice(4,6)}/${d.slice(6,8)}  ${t.slice(0,2)}:${t.slice(2,4)}`;
    } else {
      caption.textContent = file;
    }
  }
}

function isCoarsePointer() {
  return matchMedia('(hover: none) and (pointer: coarse)').matches;
}

function startPress(source) {
  baseRow01 = currentRow / (rows.length - 1);
  const len = rows[currentRow].photos.length;
  baseCol01 = len > 1 ? currentCol / (len - 1) : 0;
  source.startCalibrated();
  tiltBtn?.classList.add('active');
}

function endPress() {
  applyTiltVisual(polaroid, { db: 0, dg: 0 }, { tiltDamping: tuning.values.d, highlightIntensity: tuning.values.h });
  tiltBtn?.classList.remove('active');
}

function onTiltUpdate(ev) {
  applyTiltVisual(polaroid, ev, { tiltDamping: tuning.values.d, highlightIntensity: tuning.values.h });
  const { row, col } = tiltToIndex(ev, baseRow01, baseCol01, tuning.values.s, rows);
  if (row !== currentRow || col !== currentCol) setPhoto(row, col);
}

function wireMobile(source, initialPermission) {
  let permission = initialPermission;
  const handlerDown = async (e) => {
    e.preventDefault();
    if (permission !== 'granted') {
      permission = await ensurePermission();
      if (permission !== 'granted') {
        tiltBtn.classList.add('denied');
        return; // Task 10 will install touch-drag fallback here
      }
    }
    startPress(source);
  };
  const handlerUp = () => endPress();
  tiltBtn.addEventListener('touchstart', handlerDown, { passive: false });
  tiltBtn.addEventListener('touchend', handlerUp);
  tiltBtn.addEventListener('touchcancel', handlerUp);
  source.onTilt(onTiltUpdate);
}

function wireDesktop(source) {
  source.onPressStart(() => startPress(source));
  source.onPressEnd(() => endPress());
  source.onTilt(onTiltUpdate);
}

function onLoadProgress(loaded, total) {
  progress.textContent = `${loaded} / ${total}`;
  if (loaded === total) progress.classList.add('done');
}

async function init() {
  const data = await loadAll({ stage, onProgress: onLoadProgress });
  rows = data.rows;
  imgByFile = data.imgByFile;
  CANVAS = data.alignment.calibration_unit_px;
  fitStage();
  setPhoto(0, 0);

  const initialPermission = await probePermission(500);
  if (isCoarsePointer()) {
    wireMobile(createGyroSource({ alpha: 0.18 }), initialPermission);
  } else {
    wireDesktop(createPointerSource({ maxDeg: tuning.values.s }));
  }
}

init().catch(err => { caption.textContent = 'load error: ' + err.message; });
```

- [ ] **Step 4：桌機行為驗收**

啟動 preview，導向 `/app/index.html`，用 `mcp__Claude_Preview__preview_resize` width=1400 height=900。

逐項檢查（每一項都用 Claude Preview 工具確認）：

- [ ] `preview_screenshot`：看到 polaroid 中央、顯示 row 0 col 0 的照片、caption 顯示日期時間。
- [ ] `preview_console_logs`：沒有錯誤訊息。
- [ ] `preview_eval` 模擬按下並向右拖曳：

```js
(() => {
  const fire = (type, x, y) => window.dispatchEvent(new MouseEvent(type, {clientX:x, clientY:y, button:0}));
  fire('mousedown', 700, 400);
  fire('mousemove', 1100, 400);
  return { caption: document.getElementById('caption').textContent, transform: getComputedStyle(document.getElementById('polaroid')).transform };
})()
```

預期：caption 已換成另一張照片的日期；`transform` matrix 不再是 identity（polaroid 真的有旋轉）。

- [ ] 接著放開：

```js
window.dispatchEvent(new MouseEvent('mouseup', {clientX:1100, clientY:400, button:0}));
```

`preview_screenshot` 確認 polaroid 平滑回到正中央（但 caption 不變）。

- [ ] **Step 5：Commit**

```bash
git add app/index.html app/styles.css app/main.js
git commit -m "Wire main.js + styles + index: desktop pointer input working end-to-end"
```

---

## Task 10：行動裝置 + 觸控拖曳 fallback

**Files:**
- Modify: `app/main.js`

- [ ] **Step 1：在桌機用 mobile preset 驗證紅圈出現**

`mcp__Claude_Preview__preview_resize` preset='mobile'。
`mcp__Claude_Preview__preview_screenshot`：

預期：右下角看到紅色虛線圓圈（80×80），呼吸動畫進行中。

如果紅圈沒出現，原因通常是 Chrome devtools emulation 沒切到 mobile pointer media。在 emulation 開「Force CSS media: pointer:coarse」即可。

- [ ] **Step 2：擴充 main.js 加入觸控拖曳 fallback**

`app/main.js` 中 `wireMobile` 改為：

```js
function wireMobile(source, initialPermission) {
  let permission = initialPermission;
  const handlerDown = async (e) => {
    e.preventDefault();
    if (permission !== 'granted') {
      permission = await ensurePermission();
      if (permission !== 'granted') {
        tiltBtn.classList.add('denied');
        wireTouchDragFallback();
        return;
      }
    }
    startPress(source);
  };
  const handlerUp = () => endPress();
  tiltBtn.addEventListener('touchstart', handlerDown, { passive: false });
  tiltBtn.addEventListener('touchend', handlerUp);
  tiltBtn.addEventListener('touchcancel', handlerUp);
  source.onTilt(onTiltUpdate);
}

let touchFallbackInstalled = false;
function wireTouchDragFallback() {
  if (touchFallbackInstalled) return;
  touchFallbackInstalled = true;
  const fb = createPointerSource({ maxDeg: tuning.values.s });
  let active = false;
  const fakeMouse = (type, t) =>
    window.dispatchEvent(new MouseEvent(type, { clientX: t.clientX, clientY: t.clientY, button: 0 }));
  document.addEventListener('touchstart', (e) => {
    if (e.target === tiltBtn || tiltBtn.contains(e.target)) return;
    active = true;
    fakeMouse('mousedown', e.touches[0]);
  });
  document.addEventListener('touchmove', (e) => {
    if (!active) return;
    fakeMouse('mousemove', e.touches[0]);
  });
  document.addEventListener('touchend', () => {
    if (!active) return;
    active = false;
    fakeMouse('mouseup', { clientX: 0, clientY: 0 });
  });
  fb.onPressStart(() => startPress(fb));
  fb.onPressEnd(() => endPress());
  fb.onTilt(onTiltUpdate);
}
```

註：這段重用了 `pointer.js`，把 touch 事件 forward 成 mouse 事件再餵給同一個 source，避免重複實作 calibration / press lifecycle。

- [ ] **Step 3：Commit**

```bash
git add app/main.js
git commit -m "Add touch-drag fallback when device orientation permission is denied"
```

---

## Task 11：最終整合驗收

End-to-end smoke test。沒有 fix 就不 commit。

- [ ] **Step 1：桌機 1400×900 驗收**

`preview_resize` width=1400 height=900。逐項用 `preview_eval` + `preview_screenshot` 確認：

- [ ] 進入頁面後 5 秒內看到 polaroid（`preview_snapshot` 找到 polaroid 元素 + 至少一張可見的 img）
- [ ] 右上角 `#progress` 出現 `1/125` 之類的數字，過幾秒後變成 `125/125` 然後淡出
- [ ] `preview_eval` 確認 progress 最終狀態：

```js
({ text: document.getElementById('progress').textContent, done: document.getElementById('progress').classList.contains('done') })
```

預期：text 是 `125 / 125`、done 是 true。

- [ ] 按住 + 向右拖：caption 變化、transform 非 identity
- [ ] 放開：transform 回到 identity（CSS transition 平滑）、caption 不變
- [ ] 再次按下並向同方向拖：caption 從當下繼續往同方向變化（不是跳回原始位置）
- [ ] 拖到極右：caption 停在某張、polaroid 仍會繼續向右轉
- [ ] 拖到極上 / 極下：caption 停在 row 0 / row 5
- [ ] Slider 拖動時 URL hash 更新

- [ ] **Step 2：行動裝置 emulation 驗收**

`preview_resize` preset='mobile'。

- [ ] 紅色虛線圓圈出現在右下，呼吸動畫運作
- [ ] 用 chrome devtools 的 Sensors 面板設定一個有效的 device orientation
- [ ] 在 preview 模擬 touchstart on tilt button：紅圈 class 變 `active`
- [ ] 改變 sensor 數值：caption 切換
- [ ] touchend：紅圈回 idle
- [ ] 把 sensor 設成 unset，重新整理：紅圈第一次按下時跳出權限請求；模擬 deny 之後紅圈變 `denied`，全螢幕觸控拖曳能切照片

- [ ] **Step 3：Network / Console 全綠**

- [ ] `preview_console_logs`：沒有錯誤
- [ ] `preview_network`：`photos.json`、`alignments.json`、125 張 `images/*.webp` 全部 200

- [ ] **Step 4：截圖留存**

`preview_screenshot` 桌機 + mobile 各一張，附在最終 commit message 或後續 PR description。

- [ ] **Step 5：若有 fix 才 commit**

```bash
# only if fixes were made
git add app/
git commit -m "Tweak: <describe fix>"
```

---

## 結尾備註

完成 11 個 task 之後：
- `poc/` 不動，作為歷史參考。
- `app/` 已可獨立用 `python -m http.server 8765` 提供服務。
- Debug slider 還在畫面上 — 等使用者手機實測決定 sensitivity / damping / highlight 的最終值之後，把那些常數寫死在 `mapping.js` / `polaroid.js`（spec §「可調整常數總表」），並從 `index.html` / `main.js` / `debug.js` 移除 slider 相關程式（後續工作，不在本 plan 範圍）。
