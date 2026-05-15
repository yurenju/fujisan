# Intro Modal 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目標：** 在 Fujisan 進場時加入 native `<dialog>` modal，承載策展引言與依裝置而異的操作說明；桌機在非 debug 模式下完全擋住，iPhone 的陀螺儀權限請求綁在 modal 主按鈕的 click 上。

**架構：** Modal 結構直接寫在 [app/index.html](../../../app/index.html)，靠 `data-device` 屬性切換三種裝置（desktop / android / ios）的內容可見性。新增 `app/src/intro-modal.js` 負責裝置偵測、QR code 產生、按鈕 wiring，匯出一個 `showIntroModal({ debug })` 回傳 Promise，main.js 在 `init()` 流程內 await 它，取得 mode 後再決定要 wire 哪條互動路徑。

**技術選擇：** 原生 `<dialog>` + `showModal()`、vanilla ES modules（沿用專案既有風格）、vendored [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) 產出 SVG QR code。

**驗收方式：** 依照 [memory/feedback_no_tdd_for_visual.md](../../../memory/feedback_no_tdd_for_visual.md)，視覺/互動程式不寫 unit test，每個 task 結尾用 Claude Preview 在瀏覽器確認行為。

---

## 檔案結構

| 檔案 | 動作 | 用途 |
|---|---|---|
| `app/vendor/qrcode.js` | 新增 | qrcode-generator 套件 vendored 進來 |
| `app/src/intro-modal.js` | 新增 | Modal 全部邏輯：裝置偵測、內容設定、QR 產生、按鈕事件、permission 流程 |
| `app/index.html` | 修改 | 新增 `<dialog id="intro-modal">` 結構 |
| `app/styles.css` | 修改 | Modal 樣式、`::backdrop`、三種裝置內容切換 |
| `app/main.js` | 修改 | 在 `init()` 內 await modal，依回傳 mode 決定後續流程 |

---

## Task 1：Vendor qrcode-generator

**檔案：**
- 新增：`app/vendor/qrcode.js`

- [ ] **Step 1：取得套件原始碼**

從 [https://github.com/kazuhikoarase/qrcode-generator/blob/master/js/qrcode.js](https://github.com/kazuhikoarase/qrcode-generator/blob/master/js/qrcode.js) 下載最新版的 `qrcode.js`（MIT License）。

```bash
mkdir -p app/vendor
curl -L -o app/vendor/qrcode.js https://raw.githubusercontent.com/kazuhikoarase/qrcode-generator/master/js/qrcode.js
```

- [ ] **Step 2：包成 ES module**

`qrcode.js` 預設是 UMD（掛在 `window.qrcode`）。在檔案最末加一行：

```js
export default qrcode;
```

讓 `import qrcode from './vendor/qrcode.js'` 可以用。

- [ ] **Step 3：在檔案最頂端加 license header**

```js
// qrcode-generator by Kazuhiko Arase
// https://github.com/kazuhikoarase/qrcode-generator
// MIT License — vendored for offline use.
```

- [ ] **Step 4：在瀏覽器手動驗證匯入沒壞**

開 [app/index.html](../../../app/index.html) preview，在 console 執行：

```js
const m = await import('./vendor/qrcode.js');
const qr = m.default(0, 'M');
qr.addData('https://example.com');
qr.make();
console.log(qr.createSvgTag(4));
```

預期：印出一段 `<svg>...</svg>` 字串。

- [ ] **Step 5：Commit**

```bash
git add app/vendor/qrcode.js
git commit -m "Vendor qrcode-generator for offline QR code rendering"
```

---

## Task 2：Modal HTML 結構

**檔案：**
- 修改：`app/index.html`

- [ ] **Step 1：在 `<body>` 開頭、`<div id="scene">` 之前插入 dialog**

```html
<dialog id="intro-modal">
  <header class="intro-header">
    <h1>Fujisan</h1>
    <p class="intro-subtitle">日落的位移</p>
  </header>

  <section class="intro-lede">
    <p>這些照片是在不同的日子裡，從同一個地點拍下的富士山。</p>
    <p>拍著拍著才想起，地球科學課教過的事——日落的位置會隨著四季慢慢偏移。要有一座夠顯眼的山當作參照，時間的流動與循環，才這樣歷歷在目。</p>
  </section>

  <section class="intro-device intro-device-desktop">
    <p>這個展覽需要傾斜手機來翻動照片，請用手機掃描下方 QR code 打開。</p>
    <div id="intro-qrcode" aria-label="QR code"></div>
    <div class="intro-debug-exit">
      <small>Debug mode</small>
      <button type="button" id="intro-debug-btn">進入除錯模式</button>
    </div>
  </section>

  <section class="intro-device intro-device-mobile">
    <p>請用拇指捏住紅圈處，輕輕的傾斜手機，翻動不同時間的富士山。放開拇指，照片就停下。</p>
    <p class="intro-ios-only">iPhone 需要你授權動作感應，才能偵測手機的傾斜。按下下方按鈕後，畫面上會跳出系統提示，請選擇「允許」。</p>
    <button type="button" id="intro-start-btn">開始</button>
    <p class="intro-permission-error" hidden>沒有動作感應的權限就無法使用。請到 Safari 設定中重新允許，或重新整理頁面。</p>
  </section>
</dialog>
```

- [ ] **Step 2：暫時加最小 CSS 讓 dialog 看得到內容**

在 [app/styles.css](../../../app/styles.css) 末尾加：

```css
#intro-modal {
  max-width: 560px;
  padding: 24px;
  border: 1px solid #ccc;
  border-radius: 8px;
}
#intro-modal::backdrop {
  background: rgba(0, 0, 0, 0.6);
}
.intro-device { display: none; }
#intro-modal[data-device="desktop"] .intro-device-desktop,
#intro-modal[data-device="desktop-debug"] .intro-device-desktop { display: block; }
#intro-modal[data-device="android"] .intro-device-mobile,
#intro-modal[data-device="ios"] .intro-device-mobile { display: block; }
#intro-modal:not([data-device="ios"]) .intro-ios-only { display: none; }
#intro-modal:not([data-device="desktop-debug"]) .intro-debug-exit { display: none; }
```

- [ ] **Step 3：瀏覽器手動驗證**

開 preview，在 console 執行：

```js
const m = document.getElementById('intro-modal');
m.dataset.device = 'desktop';
m.showModal();
```

預期：modal 顯示，看到引言 + 桌機說明（沒有 debug 按鈕、沒有 mobile 區塊）。換 `desktop-debug` / `android` / `ios` 各試一次確認三種裝置的內容切換正確。

- [ ] **Step 4：Commit**

```bash
git add app/index.html app/styles.css
git commit -m "Add intro modal HTML structure with device-variant sections"
```

---

## Task 3：`intro-modal.js` 骨架與裝置偵測

**檔案：**
- 新增：`app/src/intro-modal.js`

- [ ] **Step 1：建立模組骨架**

寫入 `app/src/intro-modal.js`：

```js
// Intro modal: device detection, content selection, QR generation,
// and gating user entry into the appropriate interaction mode.
//
// Returns a Promise that resolves with the chosen mode:
//   'mobile'        — Android / iPhone, run the gyro flow
//   'desktop-debug' — Desktop with ?debug=1, run the pointer fallback
// The promise NEVER resolves for plain desktop — that's the block.

import qrcode from '../vendor/qrcode.js';
import { ensurePermission } from './gyro.js';

function detectDevice(debug) {
  const coarse = matchMedia('(hover: none) and (pointer: coarse)').matches;
  if (!coarse) return debug ? 'desktop-debug' : 'desktop';
  const D = window.DeviceOrientationEvent;
  if (D && typeof D.requestPermission === 'function') return 'ios';
  return 'android';
}

export function showIntroModal({ debug = false } = {}) {
  const dialog = document.getElementById('intro-modal');
  const device = detectDevice(debug);
  dialog.dataset.device = device;

  // Block Esc / cancel on plain desktop — there is no exit.
  dialog.addEventListener('cancel', (e) => {
    if (device === 'desktop') e.preventDefault();
  });

  dialog.showModal();

  return new Promise((resolve) => {
    // Wiring for each device variant is added in later tasks.
    // For now, just hold the promise open so the caller waits.
    dialog._resolveIntro = resolve;
  });
}
```

- [ ] **Step 2：在 main.js 暫時掛上去驗證入口**

修改 [app/main.js](../../../app/main.js) — 在檔案頂端 import 旁加：

```js
import { showIntroModal } from './src/intro-modal.js';
```

在 `init()` 函數開頭（`const data = await loadAll(...)` 之前）加：

```js
const debugEnabled = new URLSearchParams(location.search).get('debug') === '1';
const mode = await showIntroModal({ debug: debugEnabled });
console.log('[intro] mode =', mode);
```

注意：[app/main.js:26](../../../app/main.js#L26) 已經有一個 `debugEnabled` 宣告在檔案頂層，這個是新加的 local copy。實作時改成共用同一個 binding 或重新命名，避免重複。建議做法：把頂層的 `debugEnabled` 留著（debug 面板用），在 `init()` 內讀同一個變數即可。

具體改法：刪掉 init 內的 `const debugEnabled = ...`，直接用頂層那個。

- [ ] **Step 3：瀏覽器手動驗證**

開 preview，預期：
- 桌機（無 query）：Modal 顯示桌機版內容、Esc 關不掉、console 不 print mode（promise 沒 resolve、init 後續沒跑）
- 桌機 `?debug=1`：Modal 顯示桌機 debug 版內容、Esc 關不掉、console 不 print mode
- 用 devtools 切到 mobile emulation（iPhone）：Modal 顯示 iPhone 版內容
- 用 devtools 切到 mobile emulation（Android）：Modal 顯示 Android 版內容

（手機的 `'mobile'` resolve 在 Task 5 才接，這個 task 只驗證裝置偵測對不對、modal 開得起來。）

- [ ] **Step 4：Commit**

```bash
git add app/src/intro-modal.js app/main.js
git commit -m "Add intro modal skeleton with device detection"
```

---

## Task 4：桌機 QR Code

**檔案：**
- 修改：`app/src/intro-modal.js`

- [ ] **Step 1：加入 QR code 產生**

在 `showIntroModal` 內，`dialog.showModal()` 之前加：

```js
if (device === 'desktop' || device === 'desktop-debug') {
  const container = document.getElementById('intro-qrcode');
  const qr = qrcode(0, 'M');
  qr.addData(location.href);
  qr.make();
  // cellSize=6, margin=2 — tune in CSS task if needed
  container.innerHTML = qr.createSvgTag({ cellSize: 6, margin: 2, scalable: true });
}
```

- [ ] **Step 2：瀏覽器手動驗證**

開桌機 preview，預期：modal 內顯示 QR code（黑白方塊）。用手機掃，預期：開啟同一個 URL（本機開發是 localhost，掃不開沒關係，看到 QR 渲染出來即可）。

`?debug=1` 也測一次，預期：一樣顯示 QR + debug 按鈕區塊。

- [ ] **Step 3：Commit**

```bash
git add app/src/intro-modal.js
git commit -m "Render QR code in desktop intro modal"
```

---

## Task 5：Android 流程（「開始」按鈕）

**檔案：**
- 修改：`app/src/intro-modal.js`

- [ ] **Step 1：Wire 開始按鈕**

在 `showIntroModal` 的 promise return 之前加：

```js
if (device === 'android') {
  const startBtn = document.getElementById('intro-start-btn');
  startBtn.addEventListener('click', () => {
    dialog.close();
    dialog._resolveIntro('mobile');
  });
}
```

- [ ] **Step 2：在 main.js 接 mode 後 wire mobile**

修改 [app/main.js](../../../app/main.js) 的 `init()`——把既有的 `if (isCoarsePointer())` 分支改成依 `mode` 走：

```js
const initialPermission = await probePermission(500);
const mode = await showIntroModal({ debug: debugEnabled });
if (mode === 'mobile') {
  wireMobile(createGyroSource({ alpha: 0.18 }), initialPermission);
} else if (mode === 'desktop-debug') {
  wireDesktop(createPointerSource({ maxV: 30, maxH: 30 }));
}
```

注意：上面這段取代既有的 `if (isCoarsePointer()) { wireMobile(...) } else { wireDesktop(...) }` 區塊，整個換掉。`isCoarsePointer` 函數本身可以保留也可以刪——modal 已經做了等價判斷，但留著沒壞處。

- [ ] **Step 3：瀏覽器手動驗證**

devtools 切 Android 模擬，預期：
- Modal 顯示 mobile 內容、沒有 iOS 那段權限說明
- 按「開始」→ modal 關閉 → 看到 polaroid + tilt button
- 按住 tilt button 拖曳（觸控模擬）→ 照片翻動

- [ ] **Step 4：Commit**

```bash
git add app/src/intro-modal.js app/main.js
git commit -m "Wire Android start button to enter gyro flow"
```

---

## Task 6：iPhone 權限流程

**檔案：**
- 修改：`app/src/intro-modal.js`

- [ ] **Step 1：Wire 「允許動作感應並開始」按鈕**

擴充 Task 5 的按鈕邏輯，改成依 device 分支：

```js
if (device === 'android' || device === 'ios') {
  const startBtn = document.getElementById('intro-start-btn');
  const errorEl = dialog.querySelector('.intro-permission-error');
  if (device === 'ios') startBtn.textContent = '允許動作感應並開始';

  startBtn.addEventListener('click', async () => {
    if (device === 'ios') {
      // Must be the first await — ensurePermission needs to be called
      // synchronously in the click handler for iOS Safari to accept it
      // as a user gesture.
      const permission = await ensurePermission();
      if (permission !== 'granted') {
        errorEl.hidden = false;
        startBtn.disabled = true;
        return;
      }
    }
    dialog.close();
    dialog._resolveIntro('mobile');
  });
}
```

- [ ] **Step 2：瀏覽器手動驗證（桌機 emulation）**

devtools 切 iPhone Safari emulation，預期：
- Modal 顯示 mobile 內容 + iOS 權限說明那段
- 按鈕文案是「允許動作感應並開始」
- 按下按鈕（emulation 環境 `DeviceOrientationEvent.requestPermission` 不存在，會走到 `gyro.js` 的 fallback `return 'granted'`）→ modal 關閉

注意：真實 iPhone 上才測得到 prompt 與拒絕路徑，這個 task 的 Claude Preview 驗收只能確認 emulation 下流程沒爆。實機驗收留到最後 Task 10。

- [ ] **Step 3：Commit**

```bash
git add app/src/intro-modal.js
git commit -m "Wire iPhone gyro permission gate to modal start button"
```

---

## Task 7：桌機 Debug 模式出口

**檔案：**
- 修改：`app/src/intro-modal.js`

- [ ] **Step 1：Wire 「進入除錯模式」按鈕**

在 `showIntroModal` 內、`return new Promise(...)` 之前加：

```js
if (device === 'desktop-debug') {
  const debugBtn = document.getElementById('intro-debug-btn');
  debugBtn.addEventListener('click', () => {
    dialog.close();
    dialog._resolveIntro('desktop-debug');
  });
}
```

- [ ] **Step 2：瀏覽器手動驗證**

開 preview with `?debug=1`，預期：
- Modal 顯示桌機內容 + QR code + 「進入除錯模式」按鈕
- Debug 面板（既有的 sliders）在 modal 後面已經掛上、被 backdrop 蓋住
- 按「進入除錯模式」→ modal 關閉 → 看到 polaroid + tilt button + debug 面板
- 按住 tilt button 拖曳滑鼠 → 照片翻動

無 `?debug=1` 開 preview，預期：modal 顯示但沒有 debug 按鈕、Esc 關不掉、點外面也關不掉。

- [ ] **Step 3：Commit**

```bash
git add app/src/intro-modal.js
git commit -m "Wire desktop debug-mode escape hatch in intro modal"
```

---

## Task 8：Modal 樣式

**檔案：**
- 修改：`app/styles.css`

- [ ] **Step 1：用 Claude Preview 邊看邊調樣式**

這個 task 沒有「正確答案」，只有設計方向。先把 Task 2 暫時加的最小 CSS 取代成正式樣式，依以下方向調整：

- **背景與紙感**：modal 背景米色（接近 `#f7f1e3` 或 polaroid 同色系），可加極淡的紙紋
- **標題排印**：`Fujisan` 用襯線字（如果系統有），稍大；`日落的位移` 副標稍細、字距放寬
- **內文**：系統 sans-serif、行高 1.7、灰色而非純黑
- **QR code**：白底、適度邊框、置中、寬度約 200-240px
- **按鈕**：低調的填色按鈕，hover/active 有微反饋
- **`::backdrop`**：半透明深色（如 `rgba(20, 16, 12, 0.7)`），桌機因為沒有出口，可以再加 `backdrop-filter: blur(4px)`
- **手機 viewport**：modal 在小螢幕留 16px 邊距、內距縮為 20px
- **Debug 出口**：`.intro-debug-exit` 視覺上明顯次要——小字、按鈕用 outline 樣式

實作時開三個 device emulation（desktop、iPhone、Android）來回切，每個都看一遍。

- [ ] **Step 2：瀏覽器驗證三種裝置外觀**

- 桌機（無 debug）：lede 居中、QR code 顯眼、沒有任何按鈕
- 桌機 `?debug=1`：QR code 下方有低調的 debug exit 區塊
- Android：lede + 操作說明 + 主按鈕
- iPhone：上面 + 權限說明那段

確認文字不會在小螢幕被截斷、QR code 在桌機不會太小（手機要能掃得到）。

- [ ] **Step 3：Commit**

```bash
git add app/styles.css
git commit -m "Style intro modal with paper-toned, curatorial feel"
```

---

## Task 9：權限被拒的視覺處理

**檔案：**
- 修改：`app/styles.css`

- [ ] **Step 1：設計 `.intro-permission-error` 樣式**

在 `app/styles.css` 加：

```css
.intro-permission-error {
  margin-top: 12px;
  padding: 12px;
  background: rgba(200, 80, 60, 0.08);
  border-left: 3px solid rgba(200, 80, 60, 0.6);
  color: #6b2c1f;
  font-size: 0.9em;
  line-height: 1.5;
}
#intro-start-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

- [ ] **Step 2：瀏覽器驗證**

devtools 切 iPhone emulation，在 console 手動模擬拒絕路徑：

```js
const errorEl = document.querySelector('.intro-permission-error');
errorEl.hidden = false;
document.getElementById('intro-start-btn').disabled = true;
```

預期：紅色提示框顯示、按鈕變灰色不可點。

- [ ] **Step 3：Commit**

```bash
git add app/styles.css
git commit -m "Style permission-denied state on iOS intro modal"
```

---

## Task 10：跨裝置驗收

**檔案：** 無

這個 task 不寫 code，只是把整個流程從頭到尾在每種裝置上跑一次。

- [ ] **Step 1：桌機（無 debug）**

開正式 URL（或本機 + ngrok / cloudflared）：
- Modal 顯示策展引言 + 「需要傾斜手機」說明 + QR code
- Esc 按鍵：沒反應
- 點 backdrop：沒反應
- 沒有任何按鈕可以進入互動

- [ ] **Step 2：桌機 `?debug=1`**

- Modal 顯示同上 + 「進入除錯模式」按鈕
- 按按鈕：modal 關閉、polaroid 出現、tilt button 可按
- 按住 tilt button 拖曳滑鼠：照片翻動
- 螢幕上有 debug 面板（slider、photo map）

- [ ] **Step 3：Android 實機**

掃桌機 QR code 進入：
- Modal 顯示引言 + 操作說明（無 iOS 那段）
- 按「開始」：modal 關閉
- 按住紅圈、傾斜手機：照片翻動
- 放開：照片停下

- [ ] **Step 4：iPhone 實機**

掃桌機 QR code 進入：
- Modal 顯示引言 + 操作說明 + iOS 權限說明
- 按鈕文案是「允許動作感應並開始」
- 按下：系統跳出 DeviceOrientation 權限 prompt
  - 選「允許」：modal 關閉、可正常使用
  - 選「拒絕」：modal 不關、顯示紅色提示、按鈕變灰

- [ ] **Step 5：iPhone `?debug=1` 實機**

- 同 iPhone 流程，但進入後螢幕上看得到 debug 面板

- [ ] **Step 6：所有驗收通過後**

不需要額外 commit——之前每個 task 都已經 commit 過了。這個 task 是 review gate，發現問題回到對應 task 修。

---

## Notes

- **檔案大小**：`app/src/intro-modal.js` 預期 ~80-100 行，獨立、單一職責（modal 流程）。`app/main.js` 變動很少，只是把既有的 `if (isCoarsePointer())` 分支接到 modal 的 mode 上
- **既有 pointer fallback 在 wireMobile 內**：[app/main.js:198 `wireTouchDragFallback`](../../../app/main.js#L198) 是 iPhone 拒絕權限後的觸控拖曳 fallback，現在權限拒絕直接在 modal 擋下了，這條 fallback 路徑變成 dead code。**這次不動它**——刪除它屬於 cleanup、不在本 spec 範圍。可以開 follow-up task 處理
- **`isCoarsePointer`**：modal 內已做等價判斷，main.js 不再呼叫。函數可保留也可刪，傾向保留，避免無關 diff
