# 傾斜驅動的富士山照片瀏覽器 — 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `poc/index.html` 升級成 `app/` 下的單頁體驗，支援手機按住紅圈傾斜切換照片、桌機用滑鼠位置模擬，polaroid 有 damped 3D 傾斜與光影。

**Architecture:** 純前端靜態站。ES modules 拆成 loader / gyro / pointer / mapping / polaroid / debug，由 main.js 串接。Repo root 加 `package.json` 提供 vitest + jsdom 給單元測試使用，但 production code 不依賴 Node。

**Tech Stack:** Vanilla JS（ES modules）、CSS、Python 3（資料前處理腳本）、vitest + jsdom（單元測試）。

**Spec：** [docs/superpowers/specs/2026-05-06-tilt-driven-fuji-viewer-design.md](../specs/2026-05-06-tilt-driven-fuji-viewer-design.md)

---

## Task 1：建立 app/ 骨架與測試基礎建設

**Files:**
- Create: `package.json`
- Create: `vitest.config.js`
- Create: `app/index.html`（空骨架）
- Create: `app/styles.css`（空檔）
- Create: `app/main.js`（空檔）
- Create: `app/src/loader.js`、`app/src/gyro.js`、`app/src/pointer.js`、`app/src/mapping.js`、`app/src/polaroid.js`、`app/src/debug.js`（全部空檔）
- Create: `app/tests/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1：建立 `package.json`**

```json
{
  "name": "fujisan-app",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "dev": "python -m http.server 8765"
  },
  "devDependencies": {
    "vitest": "^2.1.0",
    "jsdom": "^25.0.0"
  }
}
```

- [ ] **Step 2：建立 `vitest.config.js`**

```js
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['app/tests/**/*.test.js'],
  },
});
```

- [ ] **Step 3：安裝相依套件**

執行：`npm install`
預期：成功安裝、產生 `node_modules/` 與 `package-lock.json`。

- [ ] **Step 4：更新 `.gitignore`**

在檔案末端追加：

```
# Node
node_modules/

# App images (copied locally, served from disk)
app/images/
```

- [ ] **Step 5：建立 `app/index.html` 空骨架**

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
<script type="module" src="main.js"></script>
</body>
</html>
```

- [ ] **Step 6：建立其他空檔**

每個 `.js` 檔案內容只放：

```js
// placeholder — implementation in later tasks
```

`app/styles.css`：留空。

`app/tests/.gitkeep`：留空。

- [ ] **Step 7：執行 vitest 確認基礎建設可運作**

執行：`npm test`
預期：`No test files found`（exit 0 或可接受的「沒有測試」訊息）。

- [ ] **Step 8：Commit**

```bash
git add package.json package-lock.json vitest.config.js app/ .gitignore
git commit -m "Bootstrap app/ skeleton with vitest + jsdom"
```

---

## Task 2：產生 photos.json、複製對齊資料與照片

**Files:**
- Create: `app/data/photos.json`（從 `poc/data.json` 攤平產生）
- Create: `app/data/alignments.json`（從 `alignment/aligned-all/alignments-normalized.json` 複製）
- Create: `scripts/build_app_data.py`（產生 photos.json 用）
- Create: `app/images/`（複製 `alignment/images-resized/` 的全部 125 張）

- [ ] **Step 1：建立 `scripts/build_app_data.py`**

```python
"""Build app/data/photos.json from poc/data.json by flattening into 6 rows."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
src = json.loads((REPO / "poc" / "data.json").read_text(encoding="utf-8"))

rows = [
    {"id": "top-rest", "label": "早上的散張", "photos": src["topRest"]},
]
for i, seq in enumerate(src["sequences"], start=1):
    rows.append({
        "id": f"seq-{i}",
        "label": seq["date"],
        "photos": seq["photos"],
    })
rows.append({
    "id": "bottom-rest",
    "label": "其他散張",
    "photos": src["bottomRest"],
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

- [ ] **Step 3：複製 alignments.json**

執行：`cp alignment/aligned-all/alignments-normalized.json app/data/alignments.json`
預期：檔案大小約 68K。

- [ ] **Step 4：複製 125 張照片到 `app/images/`**

執行：

```bash
mkdir -p app/images
cp alignment/images-resized/*.jpg app/images/
```

預期：`app/images/` 含 125 個 `.jpg` 檔（與 `alignment/images-resized/` 一致）。

- [ ] **Step 5：驗證每張被引用的照片都存在**

執行：

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

預期：`Total: 125, Missing: 0`。

- [ ] **Step 6：Commit**

```bash
git add app/data/ scripts/build_app_data.py
git commit -m "Add app data: flattened photos.json + alignments.json"
```

注意：`app/images/` 已被 gitignore，不會 commit 進去。

---

## Task 3：實作 `mapping.js`（純函式、TDD）

**Files:**
- Create: `app/tests/mapping.test.js`
- Modify: `app/src/mapping.js`

- [ ] **Step 1：寫測試**

`app/tests/mapping.test.js`：

```js
import { describe, it, expect } from 'vitest';
import { tiltToIndex } from '../src/mapping.js';

const rows = [
  { photos: new Array(29).fill('') },
  { photos: new Array(7).fill('') },
  { photos: new Array(10).fill('') },
  { photos: new Array(30).fill('') },
  { photos: new Array(20).fill('') },
  { photos: new Array(29).fill('') },
];

describe('tiltToIndex', () => {
  it('returns base position when delta is zero', () => {
    const r = tiltToIndex({ db: 0, dg: 0 }, 0.4, 0.5, 20, rows);
    expect(r.row).toBe(2);   // round(0.4 * 5) = 2
    expect(r.col).toBe(Math.floor(0.5 * rows[2].photos.length));
  });

  it('moves down a row at +4° beta with sensitivity 20', () => {
    const r = tiltToIndex({ db: 4, dg: 0 }, 0.5, 0.0, 20, rows);
    expect(r.row).toBe(4); // baseRow01=0.5, +4/20=0.2 -> 0.7 -> round(3.5)=4
  });

  it('clamps row at top', () => {
    const r = tiltToIndex({ db: -1000, dg: 0 }, 0.5, 0.5, 20, rows);
    expect(r.row).toBe(0);
  });

  it('clamps row at bottom', () => {
    const r = tiltToIndex({ db: 1000, dg: 0 }, 0.5, 0.5, 20, rows);
    expect(r.row).toBe(5);
  });

  it('clamps col at left', () => {
    const r = tiltToIndex({ db: 0, dg: -1000 }, 0.5, 0.5, 20, rows);
    expect(r.col).toBe(0);
  });

  it('clamps col at right of the resolved row', () => {
    const r = tiltToIndex({ db: 0, dg: 1000 }, 0.5, 0.5, 20, rows);
    const len = rows[Math.round(0.5 * 5)].photos.length;
    expect(r.col).toBe(len - 1);
  });

  it('respects sensitivity — same delta moves less when sensitivity is larger', () => {
    const small = tiltToIndex({ db: 4, dg: 0 }, 0.5, 0, 20, rows);
    const large = tiltToIndex({ db: 4, dg: 0 }, 0.5, 0, 40, rows);
    expect(large.row).toBeLessThanOrEqual(small.row);
  });
});
```

- [ ] **Step 2：執行測試確認失敗**

執行：`npm test -- mapping`
預期：FAIL，訊息類似 `tiltToIndex is not a function` 或 import 失敗。

- [ ] **Step 3：實作 `mapping.js`**

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

- [ ] **Step 4：執行測試確認通過**

執行：`npm test -- mapping`
預期：所有 7 個測試通過。

- [ ] **Step 5：Commit**

```bash
git add app/src/mapping.js app/tests/mapping.test.js
git commit -m "Add mapping.js: tilt delta to (row, col) with clamping"
```

---

## Task 4：實作 `gyro.js`（裝置方向 + EMA filter + 權限偵測）

**Files:**
- Create: `app/tests/gyro.test.js`
- Modify: `app/src/gyro.js`

- [ ] **Step 1：寫測試**

`app/tests/gyro.test.js`：

```js
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { probePermission, ensurePermission, createGyroSource } from '../src/gyro.js';

describe('probePermission', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('resolves "granted" when an event with non-null beta arrives', async () => {
    const promise = probePermission(500);
    queueMicrotask(() => {
      window.dispatchEvent(new Event('deviceorientation'));
      // jsdom's Event doesn't carry beta/gamma; simulate via custom dispatch
      const e = new Event('deviceorientation');
      Object.assign(e, { beta: 12, gamma: 5 });
      window.dispatchEvent(e);
    });
    await vi.advanceTimersByTimeAsync(500);
    expect(await promise).toBe('granted');
  });

  it('resolves "unknown" when no event arrives', async () => {
    const promise = probePermission(200);
    await vi.advanceTimersByTimeAsync(200);
    expect(await promise).toBe('unknown');
  });
});

describe('ensurePermission', () => {
  afterEach(() => {
    delete window.DeviceOrientationEvent.requestPermission;
  });

  it('returns "granted" when requestPermission is undefined (Android-style)', async () => {
    if (!window.DeviceOrientationEvent) window.DeviceOrientationEvent = function () {};
    expect(await ensurePermission()).toBe('granted');
  });

  it('forwards the result of requestPermission when defined (iOS-style)', async () => {
    if (!window.DeviceOrientationEvent) window.DeviceOrientationEvent = function () {};
    window.DeviceOrientationEvent.requestPermission = vi.fn().mockResolvedValue('denied');
    expect(await ensurePermission()).toBe('denied');
  });
});

describe('createGyroSource', () => {
  it('emits {db, dg} relative to neutral set by startCalibrated', () => {
    const source = createGyroSource({ alpha: 1.0 }); // alpha=1 disables EMA smoothing
    const events = [];
    source.onTilt(e => events.push(e));

    // First event sets stream "current" but no neutral yet
    const e1 = new Event('deviceorientation');
    Object.assign(e1, { beta: 30, gamma: 10 });
    window.dispatchEvent(e1);

    source.startCalibrated();

    const e2 = new Event('deviceorientation');
    Object.assign(e2, { beta: 35, gamma: 8 });
    window.dispatchEvent(e2);

    expect(events.length).toBeGreaterThan(0);
    const last = events[events.length - 1];
    expect(last.db).toBeCloseTo(5, 5);
    expect(last.dg).toBeCloseTo(-2, 5);

    source.stop();
  });

  it('applies EMA smoothing when alpha < 1', () => {
    const source = createGyroSource({ alpha: 0.5 });
    const events = [];
    source.onTilt(e => events.push(e));
    source.startCalibrated();

    const e1 = new Event('deviceorientation');
    Object.assign(e1, { beta: 0, gamma: 0 });
    window.dispatchEvent(e1);

    const e2 = new Event('deviceorientation');
    Object.assign(e2, { beta: 10, gamma: 0 });
    window.dispatchEvent(e2);

    // EMA: smoothed = 0.5 * 10 + 0.5 * 0 = 5
    const last = events[events.length - 1];
    expect(last.db).toBeCloseTo(5, 5);

    source.stop();
  });
});
```

- [ ] **Step 2：執行測試確認失敗**

執行：`npm test -- gyro`
預期：FAIL — 模組沒實作。

- [ ] **Step 3：實作 `gyro.js`**

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

- [ ] **Step 4：執行測試確認通過**

執行：`npm test -- gyro`
預期：所有測試通過。

- [ ] **Step 5：Commit**

```bash
git add app/src/gyro.js app/tests/gyro.test.js
git commit -m "Add gyro.js: permission probe, request, calibrated tilt stream"
```

---

## Task 5：實作 `pointer.js`（桌機 / fallback 用）

**Files:**
- Create: `app/tests/pointer.test.js`
- Modify: `app/src/pointer.js`

- [ ] **Step 1：寫測試**

`app/tests/pointer.test.js`：

```js
import { describe, it, expect } from 'vitest';
import { createPointerSource } from '../src/pointer.js';

function dispatchMouse(type, x, y) {
  const e = new MouseEvent(type, { clientX: x, clientY: y, bubbles: true, button: 0 });
  window.dispatchEvent(e);
}

describe('createPointerSource', () => {
  it('emits dg/db relative to the mousedown anchor, scaled by maxDeg', () => {
    Object.defineProperty(window, 'innerWidth', { value: 1000, configurable: true });
    Object.defineProperty(window, 'innerHeight', { value: 800, configurable: true });

    const source = createPointerSource({ maxDeg: 20 });
    const events = [];
    source.onTilt(e => events.push(e));

    let pressEvents = 0;
    source.onPressStart(() => pressEvents++);

    dispatchMouse('mousedown', 500, 400);
    source.startCalibrated();
    dispatchMouse('mousemove', 600, 400);

    expect(pressEvents).toBe(1);
    const last = events[events.length - 1];
    // dx = 100/1000 = 0.1 → 0.1 * 20 = 2
    expect(last.dg).toBeCloseTo(2, 5);
    expect(last.db).toBeCloseTo(0, 5);

    dispatchMouse('mouseup', 600, 400);
    source.stop();
  });

  it('stops emitting after mouseup', () => {
    Object.defineProperty(window, 'innerWidth', { value: 1000, configurable: true });
    Object.defineProperty(window, 'innerHeight', { value: 800, configurable: true });

    const source = createPointerSource({ maxDeg: 20 });
    const events = [];
    source.onTilt(e => events.push(e));

    dispatchMouse('mousedown', 500, 400);
    source.startCalibrated();
    dispatchMouse('mouseup', 500, 400);
    const before = events.length;
    dispatchMouse('mousemove', 600, 400);
    expect(events.length).toBe(before);

    source.stop();
  });
});
```

- [ ] **Step 2：執行測試確認失敗**

執行：`npm test -- pointer`
預期：FAIL。

- [ ] **Step 3：實作 `pointer.js`**

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

- [ ] **Step 4：執行測試確認通過**

執行：`npm test -- pointer`
預期：所有測試通過。

- [ ] **Step 5：Commit**

```bash
git add app/src/pointer.js app/tests/pointer.test.js
git commit -m "Add pointer.js: mouse-position tilt simulation with press lifecycle"
```

---

## Task 6：實作 `loader.js`（資料 + 對齊 + 預載）

**Files:**
- Create: `app/tests/loader.test.js`
- Modify: `app/src/loader.js`

- [ ] **Step 1：寫測試**

`app/tests/loader.test.js`：

```js
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { loadAll } from '../src/loader.js';

const photosFixture = {
  rows: [
    { id: 'a', label: 'A', photos: ['x.jpg', 'y.jpg'] },
    { id: 'b', label: 'B', photos: ['z.jpg'] },
  ],
};

const alignmentsFixture = {
  calibration_unit_px: 1568,
  items: {
    'x.jpg': { matrix: [[1, 0, 0.1], [0, 1, 0.2]] },
    'y.jpg': { matrix: [[1, 0, 0.0], [0, 1, 0.0]] },
    'z.jpg': { matrix: [[0.5, 0, 0.3], [0, 0.5, 0.4]] },
  },
};

beforeEach(() => {
  global.fetch = vi.fn((url) => {
    if (url.endsWith('photos.json')) return Promise.resolve({ json: () => Promise.resolve(photosFixture) });
    if (url.endsWith('alignments.json')) return Promise.resolve({ json: () => Promise.resolve(alignmentsFixture) });
    return Promise.reject(new Error('unexpected url ' + url));
  });
});

describe('loadAll', () => {
  it('returns rows, alignment, and an img per referenced file', async () => {
    const stage = document.createElement('div');
    const result = await loadAll({ stage, photosUrl: 'data/photos.json', alignmentsUrl: 'data/alignments.json' });
    expect(result.rows).toEqual(photosFixture.rows);
    expect(result.alignment.calibration_unit_px).toBe(1568);
    expect(Object.keys(result.imgByFile).sort()).toEqual(['x.jpg', 'y.jpg', 'z.jpg']);
    expect(stage.querySelectorAll('img').length).toBe(3);
  });

  it('denormalizes the matrix tx/ty by calibration_unit_px', async () => {
    const stage = document.createElement('div');
    const result = await loadAll({ stage, photosUrl: 'data/photos.json', alignmentsUrl: 'data/alignments.json' });
    const m = result.alignment.items['x.jpg'].matrix;
    // Normalized tx 0.1 * 1568 = 156.8
    expect(m[0][2]).toBeCloseTo(156.8, 5);
    expect(m[1][2]).toBeCloseTo(0.2 * 1568, 5);
  });
});
```

- [ ] **Step 2：執行測試確認失敗**

執行：`npm test -- loader`
預期：FAIL。

- [ ] **Step 3：實作 `loader.js`**

```js
// Fetches photos.json + alignments.json, denormalizes alignment matrices,
// preloads every referenced image into hidden <img> elements attached to
// the stage. Returns { rows, alignment, imgByFile } for the rest of the app.

export async function loadAll({ stage, photosUrl = 'data/photos.json', alignmentsUrl = 'data/alignments.json' } = {}) {
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

  const referenced = new Set();
  for (const row of photos.rows) for (const f of row.photos) referenced.add(f);

  const imgByFile = {};
  for (const file of referenced) {
    const img = document.createElement('img');
    img.src = `images/${file}`;
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

  return { rows: photos.rows, alignment, imgByFile };
}

export function showPhoto(imgByFile, currentFile, nextFile) {
  if (currentFile && imgByFile[currentFile]) imgByFile[currentFile].style.display = 'none';
  if (imgByFile[nextFile]) imgByFile[nextFile].style.display = '';
  return nextFile;
}
```

- [ ] **Step 4：執行測試確認通過**

執行：`npm test -- loader`
預期：兩個測試通過。

- [ ] **Step 5：Commit**

```bash
git add app/src/loader.js app/tests/loader.test.js
git commit -m "Add loader.js: fetch + denormalize + preload images"
```

---

## Task 7：實作 `polaroid.js`（3D transform + 光影）

**Files:**
- Create: `app/tests/polaroid.test.js`
- Modify: `app/src/polaroid.js`

- [ ] **Step 1：寫測試**

`app/tests/polaroid.test.js`：

```js
import { describe, it, expect, beforeEach } from 'vitest';
import { applyTiltVisual } from '../src/polaroid.js';

let el;
beforeEach(() => {
  el = document.createElement('div');
});

describe('applyTiltVisual', () => {
  it('writes rotateX/Y proportional to tilt × damping', () => {
    applyTiltVisual(el, { db: 20, dg: 10 }, { tiltDamping: 0.4, highlightIntensity: 0.5 });
    expect(el.style.transform).toContain('rotateX(-8deg)');  // -20 * 0.4
    expect(el.style.transform).toContain('rotateY(4deg)');   //  10 * 0.4
  });

  it('writes shine CSS variables that move opposite the tilt direction', () => {
    applyTiltVisual(el, { db: 0, dg: 10 }, { tiltDamping: 0.4, highlightIntensity: 0.5 });
    // shineX = 50 - 10*1.5 = 35
    expect(el.style.getPropertyValue('--shine-x')).toBe('35%');
  });

  it('zero tilt yields neutral transform and centered shine', () => {
    applyTiltVisual(el, { db: 0, dg: 0 }, { tiltDamping: 0.4, highlightIntensity: 0.5 });
    expect(el.style.transform).toContain('rotateX(0deg)');
    expect(el.style.transform).toContain('rotateY(0deg)');
    expect(el.style.getPropertyValue('--shine-x')).toBe('50%');
    expect(el.style.getPropertyValue('--shine-y')).toBe('30%');
  });

  it('shadow offset reverses sign of dg', () => {
    applyTiltVisual(el, { db: 0, dg: 10 }, { tiltDamping: 0.4, highlightIntensity: 0.5 });
    // shadowOffsetX = -10 * 0.6 = -6 px
    expect(el.style.boxShadow).toContain('-6px');
  });
});
```

- [ ] **Step 2：執行測試確認失敗**

執行：`npm test -- polaroid`
預期：FAIL。

- [ ] **Step 3：實作 `polaroid.js`**

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

- [ ] **Step 4：執行測試確認通過**

執行：`npm test -- polaroid`
預期：所有測試通過。

- [ ] **Step 5：Commit**

```bash
git add app/src/polaroid.js app/tests/polaroid.test.js
git commit -m "Add polaroid.js: 3D transform + shifting highlight + shadow"
```

---

## Task 8：實作 `debug.js`（slider + URL hash）

**Files:**
- Create: `app/tests/debug.test.js`
- Modify: `app/src/debug.js`

- [ ] **Step 1：寫測試**

`app/tests/debug.test.js`：

```js
import { describe, it, expect, beforeEach } from 'vitest';
import { parseHash, formatHash, createTuning } from '../src/debug.js';

describe('parseHash / formatHash', () => {
  it('parses sensitivity, damping, highlight from hash', () => {
    expect(parseHash('#s=25&d=0.6&h=0.8')).toEqual({ s: 25, d: 0.6, h: 0.8 });
  });

  it('returns empty object for empty hash', () => {
    expect(parseHash('')).toEqual({});
  });

  it('formats numeric tuning back to a hash string', () => {
    expect(formatHash({ s: 25, d: 0.6, h: 0.8 })).toBe('#s=25&d=0.6&h=0.8');
  });
});

describe('createTuning', () => {
  beforeEach(() => {
    history.replaceState(null, '', location.pathname);
  });

  it('uses defaults when hash is empty', () => {
    const t = createTuning({ defaults: { s: 20, d: 0.4, h: 0.5 } });
    expect(t.values.s).toBe(20);
    expect(t.values.d).toBe(0.4);
    expect(t.values.h).toBe(0.5);
  });

  it('reads initial values from location.hash', () => {
    history.replaceState(null, '', location.pathname + '#s=30&d=0.2&h=0.9');
    const t = createTuning({ defaults: { s: 20, d: 0.4, h: 0.5 } });
    expect(t.values.s).toBe(30);
    expect(t.values.d).toBe(0.2);
    expect(t.values.h).toBe(0.9);
  });

  it('persists set() updates to location.hash', () => {
    const t = createTuning({ defaults: { s: 20, d: 0.4, h: 0.5 } });
    t.set('s', 28);
    expect(location.hash).toContain('s=28');
  });
});
```

- [ ] **Step 2：執行測試確認失敗**

執行：`npm test -- debug`
預期：FAIL。

- [ ] **Step 3：實作 `debug.js`**

```js
// URL-hash backed live-tunable parameters: sensitivity (s), tilt damping
// (d), highlight intensity (h). Renders three vertical sliders on the
// left edge during tuning, removed once values are settled.

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
  // ranges: { s: [10, 40], d: [0, 1], h: [0, 1] }
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

- [ ] **Step 4：執行測試確認通過**

執行：`npm test -- debug`
預期：所有測試通過。

- [ ] **Step 5：Commit**

```bash
git add app/src/debug.js app/tests/debug.test.js
git commit -m "Add debug.js: URL-hash-backed sensitivity/damping/highlight tuning"
```

---

## Task 9：串接 `main.js`、`index.html`、`styles.css`

這個 task 沒有單元測試 — 用瀏覽器手動驗證（透過 Claude Preview MCP）。

**Files:**
- Modify: `app/index.html`
- Modify: `app/styles.css`
- Modify: `app/main.js`
- Modify: `.claude/launch.json`

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
  background:
    radial-gradient(circle, currentColor 1.5px, transparent 2px) 0 0/6px 6px;
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

async function init() {
  const data = await loadAll({ stage });
  rows = data.rows;
  imgByFile = data.imgByFile;
  CANVAS = data.alignment.calibration_unit_px;
  fitStage();
  setPhoto(0, 0);

  const initialPermission = await probePermission(500);
  const useGyro = isCoarsePointer();
  let source;

  if (useGyro) {
    source = createGyroSource({ alpha: 0.18 });
    wireMobile(source, initialPermission);
  } else {
    source = createPointerSource({ maxDeg: tuning.values.s });
    wireDesktop(source);
  }
}

function startPress(source) {
  baseRow01 = currentRow / (rows.length - 1);
  const len = rows[currentRow].photos.length;
  baseCol01 = len > 1 ? currentCol / (len - 1) : 0;
  source.startCalibrated();
  tiltBtn?.classList.add('active');
}

function endPress(source) {
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
        // TODO Task 10/11: hook touch-drag fallback. For now press is no-op.
        return;
      }
    }
    startPress(source);
  };
  const handlerUp = () => endPress(source);
  tiltBtn.addEventListener('touchstart', handlerDown, { passive: false });
  tiltBtn.addEventListener('touchend', handlerUp);
  tiltBtn.addEventListener('touchcancel', handlerUp);
  source.onTilt(onTiltUpdate);
}

function wireDesktop(source) {
  source.onPressStart(() => startPress(source));
  source.onPressEnd(() => endPress(source));
  source.onTilt(onTiltUpdate);
}

init().catch(err => { caption.textContent = 'load error: ' + err.message; });
```

- [ ] **Step 4：更新 `.claude/launch.json` 加入 app 預覽 entry**

修改檔案內容為：

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "fujisan",
      "runtimeExecutable": "python",
      "runtimeArgs": ["-m", "http.server", "8765"],
      "port": 8765
    }
  ]
}
```

（保持原樣即可 — 同一個 server 服務 repo 全部，導向 `/app/index.html` 即可。）

- [ ] **Step 5：執行所有單元測試確保沒有 regression**

執行：`npm test`
預期：所有測試通過。

- [ ] **Step 6：在瀏覽器手動驗證**

啟動 preview server（透過 `mcp__Claude_Preview__preview_start` 用 `fujisan`），導向 `/app/index.html`。

驗證項目：
1. 畫面中央顯示一張 polaroid，照片是 row 0 col 0（top-rest 第一張）。
2. 桌機按住滑鼠拖曳畫面，polaroid 微微傾斜、光影移動、照片切換。
3. 放開滑鼠：polaroid 平滑回到 neutral，照片停在當下這張。
4. 左上 debug panel 顯示三條 slider，拖動 slider 立刻有反應、URL hash 同步更新。
5. Console 沒有錯誤。

- [ ] **Step 7：Commit**

```bash
git add app/index.html app/styles.css app/main.js
git commit -m "Wire app: index.html + styles + main.js bootstrap with desktop pointer input"
```

---

## Task 10：行動裝置觸控驗證 + 觸控拖曳 fallback

**Files:**
- Modify: `app/main.js`

- [ ] **Step 1：在桌機用 mobile viewport 模擬驗證**

啟動 preview，使用 `mcp__Claude_Preview__preview_resize`：

```
preset: 'mobile'   // 375 × 812
```

預期觀察：紅色虛線圓圈出現在右下角（80×80），桌機滑鼠 input 仍可作用（因為 jsdom 沒辦法真的關掉 hover；瀏覽器 emulation 會切換 pointer media query — 若紅圈沒出現，請手動在 devtools 切到 mobile emulation）。截圖記下狀態。

- [ ] **Step 2：擴充 `wireMobile` 加入觸控拖曳 fallback**

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
  const handlerUp = () => endPress(source);
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
  // PointerSource listens on window mousemove; we patch it by also
  // dispatching synthetic mousedown/move/up from touch events.
  let active = false;
  const fakeMouse = (type, t) =>
    window.dispatchEvent(new MouseEvent(type, { clientX: t.clientX, clientY: t.clientY, button: 0 }));
  document.addEventListener('touchstart', (e) => {
    if (e.target === tiltBtn || tiltBtn.contains(e.target)) return;
    active = true;
    const t = e.touches[0];
    fakeMouse('mousedown', t);
  });
  document.addEventListener('touchmove', (e) => {
    if (!active) return;
    const t = e.touches[0];
    fakeMouse('mousemove', t);
  });
  document.addEventListener('touchend', () => {
    if (!active) return;
    active = false;
    fakeMouse('mouseup', { clientX: 0, clientY: 0 });
  });
  fb.onPressStart(() => startPress(fb));
  fb.onPressEnd(() => endPress(fb));
  fb.onTilt(onTiltUpdate);
}
```

注意：這段重用了 `pointer.js`，把 touch 事件 forward 成 mouse 事件再餵給同一個 source，避免重複實作 calibration / press lifecycle。

- [ ] **Step 3：在 mobile preset 下手動驗證觸控拖曳**

執行 `mcp__Claude_Preview__preview_resize` 切到 `mobile`，到瀏覽器 devtools 開「Sensors → Orientation」設定 device orientation 為 unset/blank，模擬 iOS 拒絕授權。

預期：拒絕後紅圈變灰色（denied），全螢幕拖曳會切換照片。

- [ ] **Step 4：執行全部單元測試**

執行：`npm test`
預期：全部通過。

- [ ] **Step 5：Commit**

```bash
git add app/main.js
git commit -m "Add touch-drag fallback when device orientation permission is denied"
```

---

## Task 11：最終整合驗證

這個 task 是 end-to-end smoke test。沒有 commit（除非有 fix）。

- [ ] **Step 1：桌機驗證**

`mcp__Claude_Preview__preview_resize` width=1400 height=900。
逐項勾：

- [ ] 進入 `/app/index.html` 後 5 秒內看到 polaroid 與照片
- [ ] 按住滑鼠拖曳 → polaroid 傾斜、照片變化
- [ ] 放開滑鼠 → polaroid 回 neutral，照片不變
- [ ] 再次按下滑鼠 → 從當下照片繼續，polaroid 立刻回應 delta（不會有跳一下的瞬間）
- [ ] 拖到極右 → 照片停在當前 row 最後一張，polaroid 仍繼續傾斜
- [ ] 拖到極上 → 照片停在 row 0，polaroid 仍繼續傾斜
- [ ] 拖到極下 → 照片停在 row 5
- [ ] Caption 正確顯示日期時間（YYYY/MM/DD HH:MM 格式）

- [ ] **Step 2：行動裝置 emulation 驗證**

`mcp__Claude_Preview__preview_resize` preset='mobile'。

- [ ] 紅色虛線圓圈出現在右下，呼吸效果正常
- [ ] 在 devtools 設定一個合理的 orientation，按住紅圈會切到 active 狀態（實線、停止呼吸）
- [ ] 改變 device orientation 時照片切換
- [ ] 放開 → 回 idle 呼吸

- [ ] **Step 3：Console / Network 檢查**

`mcp__Claude_Preview__preview_console_logs` 確認沒有錯誤。
`mcp__Claude_Preview__preview_network` 確認 photos.json / alignments.json / 125 張圖都載入成功（200）。

- [ ] **Step 4：截圖留證**

`mcp__Claude_Preview__preview_screenshot` 桌機 + mobile 各一張，附在 PR 描述。

- [ ] **Step 5：若有 fix 才 commit；無則結束**

```bash
# only if fixes were made
git add app/
git commit -m "Tweak: <describe fix>"
```

---

## 結尾備註

完成 11 個 task 之後：
- `poc/` 不動，作為歷史參考。
- `app/` 已可獨立用 `python -m http.server` 提供服務。
- Debug slider 還在畫面上 — 等使用者手機實測決定 sensitivity / damping / highlight 的最終值之後，把那些常數寫死在 `mapping.js` / `polaroid.js`（spec §「可調整常數總表」），並從 `index.html` / `main.js` / `debug.js` 移除 slider 相關程式（後續工作，不在本 plan 範圍）。
