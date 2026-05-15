# Intro Modal 設計文件

日期：2026-05-15
作者：Yuren Ju（與 Claude 共筆）

## 背景

Fujisan 是一個用手機傾斜翻看富士山日落照片的小展覽。目前 [app/main.js](../../../app/main.js) 在 `init()` 一開始就直接啟動：載入照片、依裝置 wire 互動。使用者一進來面對的是一張 polaroid 跟一顆紅色按鈕，沒有任何脈絡說明這是什麼、也沒有操作提示。

桌機目前是用 [app/src/pointer.js](../../../app/src/pointer.js) 的滑鼠按住拖曳當 fallback，可以使用，但體驗跟作品想呈現的「實際傾斜手機」差距很大。

這份 spec 描述一個進場 modal，做兩件事：

1. **策展引言**——把作品的核心感受傳達給觀者
2. **依裝置交代使用方式**——桌機導去手機、Android 解釋操作、iPhone 額外解釋陀螺儀權限

## 目標

- 進場時用 native `<dialog>` 顯示 modal，承載引言與操作說明
- 桌機預設**完全擋住**，不提供進入互動的出口（不是作品設計的環境）
- iPhone 的陀螺儀權限請求綁在 modal 的主按鈕，利用使用者點擊作為合法的 user gesture
- `?debug=1` 給桌機開發者一個出口，但其他裝置在 debug 模式下行為與正式模式一致

## 非目標

- 不做「不要再顯示」的記憶（localStorage）
- 不做多語系
- 不做 modal 內的動畫教學或示意影片
- 不重構既有的 gyro / pointer 抽象

## 裝置分支與 modal 內容

### 共用引言

所有裝置的 modal 都先顯示這段：

```
# Fujisan
## 日落的位移

這些照片是在不同的日子裡，從同一個地點拍下的富士山。

拍著拍著才想起，地球科學課教過的事——日落的位置會隨著四季慢慢偏移。
要有一座夠顯眼的山當作參照，時間的流動與循環，才這樣歷歷在目。
```

### 桌機（預設）

引言下方接：

```
這個展覽需要傾斜手機來翻動照片，請用手機掃描下方 QR code 打開。

[QR code]
```

**沒有任何按鈕、沒有關閉鍵、Esc 也擋掉。** Modal 就是終點。

### 桌機（`?debug=1`）

同上，但 QR code 下方多一行小字與一顆按鈕：

```
Debug mode

[ 進入除錯模式 ]
```

按下後關閉 modal，跑既有的 pointer fallback + debug 面板路徑。

### Android 手機

引言下方接：

```
請用拇指捏住紅圈處，輕輕的傾斜手機，翻動不同時間的富士山。
放開拇指，照片就停下。

[ 開始 ]
```

按下「開始」關閉 modal，跑既有的 mobile 路徑（`wireMobile` + `createGyroSource`）。

### iPhone

引言下方接：

```
請用拇指捏住紅圈處，輕輕的傾斜手機，翻動不同時間的富士山。
放開拇指，照片就停下。

iPhone 需要你授權動作感應，才能偵測手機的傾斜。
按下下方按鈕後，畫面上會跳出系統提示，請選擇「允許」。

[ 允許動作感應並開始 ]
```

按下按鈕時，handler 在同一個 click event 內呼叫 [`ensurePermission()`](../../../app/src/gyro.js)，等使用者在系統 prompt 上選擇後：

- **允許**：關閉 modal、跑既有的 mobile 路徑
- **拒絕**：modal 不關閉，按鈕下方顯示「沒有動作感應權限就無法使用，請在 Safari 設定中重新允許」之類的訊息（細節待 UI 設計時定）

## 裝置偵測

- **桌機 vs 手機**：沿用 [app/main.js:123 `isCoarsePointer()`](../../../app/main.js#L123)，`matchMedia('(hover: none) and (pointer: coarse)')`
- **iOS vs Android**：用 `typeof DeviceOrientationEvent?.requestPermission === 'function'`。這個 API 只在 iOS 13+ Safari 存在，是業界常用的 iOS 偵測方式，比 user-agent sniffing 穩定

## Debug 面板與 modal 的關係

兩者是獨立的：

| 情境 | Modal 出口 | Debug 面板 |
|---|---|---|
| 桌機 | 無 | 不顯示 |
| 桌機 `?debug=1` | 進入除錯模式 | 顯示 |
| Android | 開始 | 不顯示 |
| Android `?debug=1` | 開始 | 顯示 |
| iPhone | 允許動作感應並開始 | 不顯示 |
| iPhone `?debug=1` | 允許動作感應並開始 | 顯示 |

Debug 面板的掛載邏輯（[app/main.js:26-37](../../../app/main.js#L26)）完全不動。

## 技術設計

### 檔案結構

新增：

- `app/src/intro-modal.js`——modal 的所有邏輯（裝置偵測、內容裝填、QR 產生、按鈕 wiring）
- `app/vendor/qrcode.js`——bundle 進來的 [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) 純 JS 套件（離線可用、~10KB）

修改：

- [app/index.html](../../../app/index.html)——新增 `<dialog id="intro-modal">` 與三種裝置內容的容器
- [app/main.js](../../../app/main.js)——把 modal 流程接到 `init()` 前
- [app/styles.css](../../../app/styles.css)——modal 與 `::backdrop` 樣式

### Modal HTML 結構

寫在 [app/index.html](../../../app/index.html) 裡，三種裝置內容的可見性由 `data-device` 屬性切換（避免 JS 拼字串）：

```html
<dialog id="intro-modal">
  <header>
    <h1>Fujisan</h1>
    <p class="subtitle">日落的位移</p>
  </header>

  <section class="lede">
    <p>這些照片是在不同的日子裡，從同一個地點拍下的富士山。</p>
    <p>拍著拍著才想起，地球科學課教過的事——日落的位置會隨著四季慢慢偏移。要有一座夠顯眼的山當作參照，時間的流動與循環，才這樣歷歷在目。</p>
  </section>

  <section class="device device-desktop">
    <p>這個展覽需要傾斜手機來翻動照片，請用手機掃描下方 QR code 打開。</p>
    <div id="intro-qrcode"></div>
    <div class="debug-exit">
      <small>Debug mode</small>
      <button type="button" id="intro-debug-btn">進入除錯模式</button>
    </div>
  </section>

  <section class="device device-mobile">
    <p>請用拇指捏住紅圈處，輕輕的傾斜手機，翻動不同時間的富士山。放開拇指，照片就停下。</p>
    <p class="ios-only">iPhone 需要你授權動作感應，才能偵測手機的傾斜。按下下方按鈕後，畫面上會跳出系統提示，請選擇「允許」。</p>
    <button type="button" id="intro-start-btn">開始</button>
  </section>
</dialog>
```

CSS 規則用 `[data-device="..."]` 控制哪些 section 顯示、按鈕文案差異等。

### `intro-modal.js` API

```js
// Returns a promise that resolves with the device mode the user is entering with.
// Resolves with: 'mobile' (gyro), 'desktop-debug' (pointer fallback), or never (desktop blocked).
export async function showIntroModal({ debug }) { ... }
```

回傳值決定 main.js 接下來走哪條路：

```js
// main.js
const debugEnabled = ...;
if (debugEnabled) { /* mount debug panel — unchanged */ }

const mode = await showIntroModal({ debug: debugEnabled });
if (mode === 'mobile') {
  wireMobile(createGyroSource({ alpha: 0.18 }), initialPermission);
} else if (mode === 'desktop-debug') {
  wireDesktop(createPointerSource({ maxV: 30, maxH: 30 }));
}
// 桌機（非 debug）走不到這裡——promise 不 resolve，後續邏輯不執行。
```

### 裝置偵測與內容切換

`intro-modal.js` 在開啟前判斷裝置，設定 `dialog.dataset.device`：

- `desktop`——桌機，無 debug
- `desktop-debug`——桌機，有 debug
- `android`
- `ios`

CSS 規則範例：

```css
#intro-modal:not([data-device="desktop"]):not([data-device="desktop-debug"]) .device-desktop { display: none; }
#intro-modal[data-device="desktop"] .device-mobile,
#intro-modal[data-device="desktop-debug"] .device-mobile { display: none; }
#intro-modal:not([data-device="ios"]) .ios-only { display: none; }
#intro-modal[data-device="desktop"] .debug-exit { display: none; }
#intro-modal[data-device="ios"] #intro-start-btn::before { content: "允許動作感應並"; }
```

按鈕文案差異用 CSS `::before` 或在 JS 內直接設 `textContent`（後者比較直白，我傾向 JS 內處理）。

### iPhone 權限流程

主按鈕的 click handler（在 iOS 模式下）：

```js
startBtn.addEventListener('click', async () => {
  if (deviceMode === 'ios') {
    const permission = await ensurePermission();
    if (permission !== 'granted') {
      showPermissionError();  // 顯示一段「沒有權限就無法使用」的訊息
      return;
    }
  }
  dialog.close();
  resolveWith('mobile');
});
```

注意：`ensurePermission` 必須在 click handler 的同步路徑開頭就被呼叫，不能在 await 後面，否則 iOS Safari 會判定不是 user gesture 而拒絕。實作時要把 await 鏈寫對。

### 擋掉 Esc 與點擊 backdrop

桌機（非 debug）的 modal 不能被關掉：

```js
dialog.addEventListener('cancel', (e) => {
  if (deviceMode === 'desktop') e.preventDefault();
});
```

`<dialog>` 的 backdrop 點擊預設不會關閉，所以 backdrop 不用特別處理。

### QR Code

用 [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) bundle 到 `app/vendor/qrcode.js`，產出 SVG 注入到 `#intro-qrcode`。內容是 `location.href`（讓使用者在哪個版本掃 QR 就進到哪個版本）。

選這個套件的理由：

- 純 JS、無相依、~10KB
- 可以產出 SVG（比 canvas 更清晰、可縮放）
- 離線可用，不依賴外部服務

## 樣式方向

- 米色背景、跟 polaroid 的紙感呼應，但卡片本身偏中性、不要喧賓奪主
- 標題用襯線字（跟 caption 的字體呼應）、內文用系統 sans-serif
- `::backdrop` 用半透明深色，桌機因為沒有出口，backdrop 顏色可以更深一點
- Modal 寬度在桌機 max 560px、手機留 16px 邊距

具體的 typography、間距、配色等留到實作時用 Claude Preview 邊看邊調，這邊不寫死。

## 風險與待確認

| 風險 | 緩解 |
|---|---|
| iPhone Safari 對 `ensurePermission` 的 user gesture 判定很嚴格，await 順序錯了就會被拒絕 | 實作時參考 [app/main.js:194-201](../../../app/main.js#L194) 既有寫法，並在真實 iPhone 上驗證 |
| QR code 內容是 `location.href`，但本地開發 URL（localhost）掃了沒用 | 不處理。Debug mode 已經提供桌機開發者的出口，本機開發不需要靠 QR |
| `<dialog>` 在某些舊瀏覽器不支援 | 接受。展覽目標客群是現代手機瀏覽器（iOS Safari 15+、Chrome），都支援 |

## 驗收

實作完成後在三種真實裝置上驗證：

- **桌機（無 debug）**：modal 顯示、QR 可掃、Esc 與點擊外面都關不掉、沒有任何進入互動的路徑
- **桌機（`?debug=1`）**：modal 顯示、「進入除錯模式」按鈕能進入既有 pointer fallback、debug 面板正常運作
- **Android 手機**：modal 顯示操作說明、「開始」進入正常 gyro 流程
- **iPhone**：modal 顯示操作說明與權限說明、「允許動作感應並開始」觸發系統 permission prompt、允許後進入 gyro 流程、拒絕後顯示錯誤訊息

驗證方式照 [feedback_no_tdd_for_visual.md](../../../memory/feedback_no_tdd_for_visual.md)：用 Claude Preview 做瀏覽器行為驗收，不寫 unit test。
