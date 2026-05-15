# 將傾斜映射改為速度模型 — 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目標:** 把現有的「角度 → 位置」映射改為「角度 → 速度」並在邊緣 wrap，上下切 row 時依比例重算 col。

**架構:** 在 `mapping.js` 新增兩支純函式 `tiltToVelocity` 與 `advance`；`gyro.js` / `pointer.js` 加 `latest()` pull 介面；`main.js` 啟動 RAF loop 在按壓期間持續積分位置。`applyTiltVisual` 仍由 push event 驅動，視覺與映射解耦。

**技術:** Vanilla JS、DeviceOrientation API、`requestAnimationFrame`。視覺驗證透過 Claude Preview 工具觀察瀏覽器行為。

**相關 spec:** [docs/superpowers/specs/2026-05-15-tilt-as-velocity-design.md](../specs/2026-05-15-tilt-as-velocity-design.md)

---

## 檔案結構

| 檔案 | 動作 | 職責 |
|---|---|---|
| [app/src/gyro.js](../../../app/src/gyro.js) | 修改 | 新增 `latest()` 拉取最新校準後 tilt |
| [app/src/pointer.js](../../../app/src/pointer.js) | 修改 | 新增 `latest()` 對齊介面（拉取虛擬 tilt） |
| [app/src/mapping.js](../../../app/src/mapping.js) | 改寫 | `tiltToVelocity` + `advance` 取代 `tiltToIndex` |
| [app/main.js](../../../app/main.js) | 修改 | RAF loop、`rowFloat`/`colFloat` state、移除 base01 |
| [app/src/debug.js](../../../app/src/debug.js) | 修改 | 新增 `deadzone` slider、更新 sv/sh 標籤與範圍 |

---

## 驗證準備

開始之前用 Claude Preview 工具開啟 dev server 以利後續每個 task 末段桌面驗證。

- [ ] **預備: 啟動 dev server**

使用 `mcp__Claude_Preview__preview_start`（如尚未啟動），確認可開啟 [app/index.html](../../../app/index.html) 並見到照片框。

---

## Task 0: 啟動行動裝置測試 tunnel（使用者執行）

iOS Safari 的 `DeviceOrientationEvent.requestPermission()` 需要 HTTPS。用 `cloudflared` 把 local server 暴露成 HTTPS URL 給手機連。

`cloudflared` 已安裝（version 2025.8.1 確認過）。

**檔案:** 可選新增 `scripts/dev-tunnel.bat` 或 `scripts/dev-tunnel.sh`

- [ ] **步驟 1: 啟動 local server**

terminal A，從專案根目錄：

```bash
python -m http.server 8765
```

- [ ] **步驟 2: 啟動 tunnel**

terminal B：

```bash
cloudflared tunnel --url http://localhost:8765
```

輸出中會看到一行像 `https://xxx-yyy-zzz.trycloudflare.com`，複製下來。

- [ ] **步驟 3: 手機開啟並確認**

手機瀏覽器導到 `<URL>/app/`，確認:
- 頁面載入完成、照片顯示
- 看得到 tilt 按鈕
- 點 tilt 按鈕應彈出 iOS DeviceOrientation 權限對話框（iOS 17+）；點允許後，再次按住應能切換照片

如果權限被拒，會 fall back 到觸控拖曳模式 — 拖曳螢幕也應能切換照片。

- [ ] **步驟 4: （可選）打包成一行**

新增 `scripts/dev-tunnel.bat` 或 `dev-tunnel.sh`，把兩個 process 同時啟動，方便之後重複使用。範例 `dev-tunnel.bat`：

```bat
@echo off
start cmd /k python -m http.server 8765
cloudflared tunnel --url http://localhost:8765
```

- [ ] **步驟 5: 在每個後續 Task 之後做行動裝置驗證**

之後 Task 1 / 2 / 3 結束時，除了 Claude Preview 桌面驗證，使用者也在手機上重新整理頁面實機驗證該 task 涵蓋的行為。**每次重啟 cloudflared URL 會變**，要重貼一次。

---

## Task 1: gyro / pointer 新增 `latest()` 拉取介面

**檔案:**
- 修改: [app/src/gyro.js](../../../app/src/gyro.js)
- 修改: [app/src/pointer.js](../../../app/src/pointer.js)

這是非破壞性新增：原本 push (`onTilt`) 介面保留；只多一個 pull (`latest()`)。Task 3 才會用到。

- [ ] **步驟 1: 修改 `app/src/gyro.js`，在回傳物件中新增 `latest()`**

把 `createGyroSource` 回傳物件改為：

```js
return {
  onTilt(fn) { listeners.push(fn); },
  latest() {
    if (!calibrated) return { db: 0, dg: 0 };
    return {
      db: smoothedBeta - neutralBeta,
      dg: smoothedGamma - neutralGamma,
    };
  },
  startCalibrated() {
    neutralBeta = smoothedBeta;
    neutralGamma = smoothedGamma;
    calibrated = true;
  },
  endCalibrated() {
    calibrated = false;
  },
  stop() {
    calibrated = false;
    window.removeEventListener('deviceorientation', handler);
    listeners.length = 0;
  },
};
```

- [ ] **步驟 2: 修改 `app/src/pointer.js`，在回傳物件中新增 `latest()`**

`createPointerSource` 內部已有 `lastX`/`lastY`/`neutralX`/`neutralY`/`calibrated` 變數。`latest()` 直接從這些算出：

```js
return {
  onTilt(fn) { tiltListeners.push(fn); },
  onPressStart(fn) { pressStartListeners.push(fn); },
  onPressEnd(fn) { pressEndListeners.push(fn); },
  latest() {
    if (!calibrated) return { db: 0, dg: 0 };
    const dg = ((lastX - neutralX) / window.innerWidth)  * maxH;
    const db = ((lastY - neutralY) / window.innerHeight) * maxV;
    return { db, dg };
  },
  startCalibrated() {
    neutralX = lastX;
    neutralY = lastY;
    calibrated = true;
  },
  endCalibrated() {
    calibrated = false;
  },
  stop() {
    window.removeEventListener('mousedown', onMouseDown);
    window.removeEventListener('mousemove', onMouseMove);
    window.removeEventListener('mouseup', onMouseUp);
    window.removeEventListener('blur', onMouseUp);
    tiltListeners.length = 0;
    pressStartListeners.length = 0;
    pressEndListeners.length = 0;
  },
};
```

注意:
- 額外加 `endCalibrated()` 方法（之前沒有），讓 gyro/pointer 兩者介面一致。
- `stop()` 內容保持原樣。

- [ ] **步驟 3: 瀏覽器驗證（行為不變）**

使用 `mcp__Claude_Preview__preview_eval` 重新載入頁面，並用 `mcp__Claude_Preview__preview_click` 模擬按下 tilt 按鈕後拖曳，確認原本的位置型切換照片行為仍正常（因為 main.js 尚未改）。
透過 `mcp__Claude_Preview__preview_console_logs` 確認無新錯誤。

- [ ] **步驟 4: Commit**

```bash
git add app/src/gyro.js app/src/pointer.js
git commit -m "Add latest() pull interface to gyro and pointer sources"
```

---

## Task 2: 改寫 `mapping.js` 為速度模型，並切換 `main.js`

這個 task 是核心變動：刪除 `tiltToIndex`、新增 `tiltToVelocity` + `advance`，同時改寫 `main.js` 採用 RAF loop。整包一起做，避免中間狀態壞掉。

**檔案:**
- 改寫: [app/src/mapping.js](../../../app/src/mapping.js)
- 修改: [app/main.js](../../../app/main.js)

- [ ] **步驟 1: 改寫 `app/src/mapping.js`**

全部覆寫為：

```js
// Velocity-based mapping. tiltToVelocity is pure: tilt → speed.
// advance is pure: (state, velocity, dt, rows) → next state with wrap and
// cross-row column rescaling.

const clamp = (v, min, max) => Math.min(max, Math.max(min, v));

// Floor-mod that handles negatives correctly.
function wrap(x, mod) {
  return ((x % mod) + mod) % mod;
}

// Linear with dead zone. Returns 0 inside the dead zone, otherwise
// (|tilt| - deadzone) / sensitivity with the original sign.
function speedFrom(tilt, sensitivity, deadzone) {
  const m = Math.abs(tilt);
  if (m <= deadzone) return 0;
  return Math.sign(tilt) * (m - deadzone) / sensitivity;
}

export function tiltToVelocity({ db, dg }, { sv, sh, deadzone }) {
  return {
    vRow: speedFrom(db, sv, deadzone),  // rows / sec
    vCol: speedFrom(dg, sh, deadzone),  // photos / sec
  };
}

// state: { rowFloat, colFloat }
// velocity: { vRow, vCol }
// dt: seconds since last tick
// rows: [{ photos: [...] }, ...]
// Returns: { rowFloat, colFloat, row, col }
export function advance(state, velocity, dt, rows) {
  const rowCount = rows.length;
  const prevRow = clamp(Math.floor(state.rowFloat), 0, rowCount - 1);

  // Integrate and wrap row.
  let rowFloat = wrap(state.rowFloat + velocity.vRow * dt, rowCount);
  const newRow = Math.floor(rowFloat) % rowCount;

  // Cross-row column rescale to preserve normalized horizontal position.
  let colFloat = state.colFloat;
  if (newRow !== prevRow) {
    const prevLen = rows[prevRow].photos.length;
    const newLen  = rows[newRow].photos.length;
    const ratio = prevLen > 0 ? colFloat / prevLen : 0;
    colFloat = ratio * newLen;
  }

  // Integrate and wrap column on the current row's length.
  const len = rows[newRow].photos.length;
  colFloat = wrap(colFloat + velocity.vCol * dt, len);

  return {
    rowFloat,
    colFloat,
    row: newRow,
    col: Math.floor(colFloat),
  };
}
```

- [ ] **步驟 2: 改寫 `app/main.js`**

主要變動：
- 移除 `baseRow01` / `baseCol01` / `tiltToIndex` import；改 import `tiltToVelocity` 與 `advance`
- 新增 `rowFloat` / `colFloat` / `rafHandle` / `lastTickMs` 模組級 state
- `currentRow` / `currentCol` 仍保留（給 `setPhoto` 比對「是否變化」用）
- `startPress` 改為啟動 RAF loop（不再凍結 base）
- `endPress` 改為停止 RAF loop
- `onTiltUpdate` 只剩視覺更新（`applyTiltVisual`），mapping 移到 RAF tick
- 從 `tuning.values` 讀取新欄位 `dz`（deadzone）

完整新版 `app/main.js`：

```js
import { loadAll, showPhoto } from './src/loader.js';
import { probePermission, ensurePermission, createGyroSource } from './src/gyro.js';
import { createPointerSource } from './src/pointer.js';
import { tiltToVelocity, advance } from './src/mapping.js';
import { applyTiltVisual } from './src/polaroid.js';
import { createTuning, mountSliders, mountPhotoMap, mountToggle } from './src/debug.js';

const polaroid = document.getElementById('polaroid');
const photoFrame = document.getElementById('photo-frame');
const stage = document.getElementById('stage');
const stageClip = document.getElementById('stage-clip');
const caption = document.getElementById('caption');
const tiltBtn = document.getElementById('tilt-button');
const debugPanel = document.getElementById('debug-panel');
const progress = document.getElementById('progress');

const tuning = createTuning({
  defaults: { sv: 25, sh: 12, dz: 2, d: 0.4, h: 0.5, inv: 1, hide: 0 },
});
mountToggle(debugPanel, tuning);
mountSliders(debugPanel, tuning, [
  { key: 'sv',  label: 'deg / (row/sec)',   min: 10, max: 40, step: 0.5, unit: '°' },
  { key: 'sh',  label: 'deg / (photo/sec)', min: 5,  max: 30, step: 0.5, unit: '°' },
  { key: 'dz',  label: 'deadzone',          min: 0,  max: 5,  step: 0.1, unit: '°' },
  { key: 'd',   label: 'tilt damping',      min: 0,  max: 1,  step: 0.05 },
  { key: 'h',   label: 'highlight',         min: 0,  max: 1,  step: 0.05 },
  { key: 'inv', label: 'invert',            min: 0,  max: 1,  step: 1 },
]);
let photoMap = null;

let CANVAS = 1568;
let rows = [];
let imgByFile = {};
let currentFile = null;
let currentRow = 0;
let currentCol = 0;
let rowFloat = 0;
let colFloat = 0;
let rafHandle = null;
let lastTickMs = 0;
let tiltSource = null;

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
  photoMap?.highlight(rowIdx, colIdx);
}

function isCoarsePointer() {
  return matchMedia('(hover: none) and (pointer: coarse)').matches;
}

function tick(nowMs) {
  const dt = Math.min((nowMs - lastTickMs) / 1000, 0.1); // cap dt to avoid jumps after tab blur
  lastTickMs = nowMs;

  const raw = tiltSource.latest();
  const sign = tuning.values.inv ? -1 : 1;
  const tilt = { db: raw.db * sign, dg: raw.dg * sign };

  const velocity = tiltToVelocity(tilt, {
    sv: tuning.values.sv,
    sh: tuning.values.sh,
    deadzone: tuning.values.dz,
  });

  const next = advance({ rowFloat, colFloat }, velocity, dt, rows);
  rowFloat = next.rowFloat;
  colFloat = next.colFloat;

  if (next.row !== currentRow || next.col !== currentCol) {
    setPhoto(next.row, next.col);
  }

  rafHandle = requestAnimationFrame(tick);
}

function startLoop() {
  if (rafHandle != null) return;
  lastTickMs = performance.now();
  rafHandle = requestAnimationFrame(tick);
}

function stopLoop() {
  if (rafHandle != null) {
    cancelAnimationFrame(rafHandle);
    rafHandle = null;
  }
}

function startPress(source) {
  tiltSource = source;
  source.startCalibrated();
  tiltBtn?.classList.add('active');
  startLoop();
}

function endPress(source) {
  stopLoop();
  applyTiltVisual(polaroid, { db: 0, dg: 0 }, { tiltDamping: tuning.values.d, highlightIntensity: tuning.values.h });
  tiltBtn?.classList.remove('active');
  source?.endCalibrated?.();
}

function onTiltVisual(ev) {
  applyTiltVisual(polaroid, ev, { tiltDamping: tuning.values.d, highlightIntensity: tuning.values.h });
}

function wireMobile(source, initialPermission) {
  let permission = initialPermission;

  // iOS Safari requires DeviceOrientationEvent.requestPermission() to be
  // called from a 'click' (or 'touchend')-level user gesture; calling it
  // from 'touchstart' is rejected as not-a-gesture. So request on click
  // (which fires on tap completion), and only run the press lifecycle on
  // touchstart/touchend after permission is granted.
  const handleClick = async () => {
    if (permission === 'granted') return;
    permission = await ensurePermission();
    if (permission !== 'granted') {
      tiltBtn.classList.add('denied');
      wireTouchDragFallback();
    }
  };

  const handleTouchStart = (e) => {
    if (permission !== 'granted') return;
    e.preventDefault();
    startPress(source);
  };

  const handleTouchEnd = () => {
    if (permission !== 'granted') return;
    endPress(source);
  };

  tiltBtn.addEventListener('click', handleClick);
  tiltBtn.addEventListener('touchstart', handleTouchStart, { passive: false });
  tiltBtn.addEventListener('touchend', handleTouchEnd);
  tiltBtn.addEventListener('touchcancel', handleTouchEnd);
  source.onTilt(onTiltVisual);
}

let touchFallbackInstalled = false;
function wireTouchDragFallback() {
  if (touchFallbackInstalled) return;
  touchFallbackInstalled = true;
  const fb = createPointerSource({ maxV: 30, maxH: 30 });
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
  fb.onPressEnd(() => endPress(fb));
  fb.onTilt(onTiltVisual);
}

function wireDesktop(source) {
  source.onPressStart(() => startPress(source));
  source.onPressEnd(() => endPress(source));
  source.onTilt(onTiltVisual);
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
  photoMap = mountPhotoMap(debugPanel, rows);
  setPhoto(0, 0);

  const initialPermission = await probePermission(500);
  if (isCoarsePointer()) {
    wireMobile(createGyroSource({ alpha: 0.18 }), initialPermission);
  } else {
    wireDesktop(createPointerSource({ maxV: 30, maxH: 30 }));
  }
}

init().catch(err => { caption.textContent = 'load error: ' + err.message; });
```

注意:
- `createPointerSource` 的 `maxV` / `maxH` 不再對應 sensitivity，改用固定 30°（讓拖曳到視窗邊緣產生 ±30° 虛擬傾斜），sensitivity 由 mapping 統一處理。
- `dt` capping 為 0.1 秒，避免分頁切換回來後 dt 過大造成位置跳躍。

- [ ] **步驟 3: 瀏覽器驗證 — 桌面拖曳**

驗證以下行為：
- 開啟頁面，看到第一張照片
- 按住滑鼠在頁面任意位置（不在 tilt 按鈕上）並拖曳，應啟動 fallback 模式
  - 拖曳到中央附近 → 點靜止（死區內）
  - 拖曳到右側 → 持續往右翻照片（持續按住的期間 colFloat 在累加）
  - 拖曳到右邊盡頭 → 翻到 row 的最右然後 wrap 回左邊
  - 拖曳到下方 → 持續切到下一個 row；wrap 上下
- 放開滑鼠 → 停止

實際做法：
1. `mcp__Claude_Preview__preview_eval` 確認頁面載入完成
2. `mcp__Claude_Preview__preview_snapshot` 看當前照片
3. 模擬拖曳：用 `mcp__Claude_Preview__preview_eval` 派發 `mousedown` 於中央、`mousemove` 於右側、等 ~2 秒、`mouseup`
4. `mcp__Claude_Preview__preview_snapshot` 確認 caption 顯示的照片有變化、且方向正確
5. `mcp__Claude_Preview__preview_console_logs` 檢查無錯誤

如有問題回去修 mapping.js 或 main.js，直到行為符合 spec「驗收觀察點」段落的桌面相關項目。

- [ ] **步驟 4: 瀏覽器驗證 — 跨 row 比例保留**

在 debug panel 觀察 photoMap 高亮：
1. 拖曳到較右側位置（如某 row 的中間靠右）
2. 短暫往下傾斜切到下一個 row
3. 確認 photoMap 高亮位置 — 短 row 應該落在比例對應的位置

這項驗證可能難以精準量測，可在 `advance` 函式或 `setPhoto` 加暫時 `console.log` 印出 `rowFloat`/`colFloat`/`rows[row].photos.length` 比對。驗證後移除 log。

- [ ] **步驟 5: Commit**

```bash
git add app/src/mapping.js app/main.js
git commit -m "Switch tilt mapping from position to velocity with edge wrap"
```

---

## Task 3: debug.js — `deadzone` slider 與 sv/sh 標籤更新

**檔案:**
- 修改: [app/src/debug.js](../../../app/src/debug.js)

> 大部分變更已在 Task 2 的 `main.js` 內透過 `mountSliders` 設定 (`dz` slider、新 label、新範圍)。本 task 處理 `debug.js` 模組本體若需要更動的部分。

- [ ] **步驟 1: 檢視目前 `debug.js`**

打開 [app/src/debug.js](../../../app/src/debug.js)，確認：
- `createTuning` 接受 `defaults` 物件並產生 `values` reactive object — 若已支援動態 keys（如 `dz`），不需要改動
- `mountSliders` 依傳入的 spec 陣列建立 slider — 若已支援任意 keys，不需要改動

若兩者都已是泛型實作，本 task 不需要程式碼變動，可直接跳到步驟 3 驗證。

- [ ] **步驟 2: 必要時調整**

若 `debug.js` 有 hardcode 的 slider key（如只認 `sv`、`sh`），改成從傳入 spec 動態建立 slider 並寫入 `values`。具體改法依現況決定，遵循「跟現有 pattern 一致」原則。

- [ ] **步驟 3: 瀏覽器驗證**

1. 開啟 debug panel（顯示 / 隱藏 toggle）
2. 確認 5 個 slider 都出現：`deg / (row/sec)`、`deg / (photo/sec)`、`deadzone`、`tilt damping`、`highlight`、`invert`
3. 拖曳 `deadzone` slider 從 0 提到 5，再做拖曳測試，確認:
   - `dz = 0` 時拖到中央偏一點點 → 緩慢移動
   - `dz = 5` 時拖到中央偏一點點 → 不動
4. 拖曳 `deg / (photo/sec)` 從 5 到 30，測試低值 → 翻得快、高值 → 翻得慢

- [ ] **步驟 4: Commit**

```bash
git add app/src/debug.js
git commit -m "Adjust debug sliders for velocity-based tuning params"
```

若 Task 3 沒有實際變動，跳過 commit。

---

## Task 4: 實機驗證與微調（如需要）

**檔案:** 視微調結果而定

- [ ] **步驟 1: 手機實機測試（可選，若使用者要求）**

由使用者實機測試，回報感受。常見可能要調的參數：
- `sv` / `sh` 預設值（手機抖動範圍與 desktop 拖曳的對應點可能不同）
- `deadzone` 預設值
- 視覺 damping

- [ ] **步驟 2: 依回饋微調預設值並 commit**

例：

```js
defaults: { sv: 30, sh: 15, dz: 3, ... }
```

```bash
git add app/main.js
git commit -m "Tune velocity defaults from device test"
```

---

## 驗收觀察點對照（呼應 spec）

| Spec 觀察點 | 對應 task |
|---|---|
| 手持靜止（死區內）→ 點不漂移 | Task 2 步驟 3 / Task 3 步驟 3 |
| 微傾 → 緩慢移動、大傾 → 快速移動 | Task 2 步驟 3 |
| 角度回 0 → 停止 | Task 2 步驟 3 |
| 短 row 整體繞得快、長 row 翻得慢 | Task 2 步驟 4 |
| 跨 row col 比例保留 | Task 2 步驟 4 |
| 兩軸獨立 wrap | Task 2 步驟 3 |
| 反方向傾斜 → 反方向移動 | Task 2 步驟 3 |
