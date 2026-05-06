# 傾斜驅動的富士山照片瀏覽器 — 設計文件

**日期：** 2026-05-06
**狀態：** 已通過、可進入實作計畫

## 目標

把現有的 `poc/index.html` 從 PoC 推進到接近上線的單頁體驗，放在新的 `app/` 目錄下。把桌機原本的浮動 pad 換成統一的輸入模型：

- **手機**：使用者按住右下角的紅色虛線圓圈，傾斜手機掃描整個照片網格。
- **桌機**：同樣的模型由滑鼠相對於按下時的錨點位置驅動。

Polaroid 本身會以 damped 的 3D 傾斜回應，並讓相紙上的 specular highlight 隨之移動，讓使用者覺得像是真的拿著一張實體照片；但照片內容本身是硬切換，沒有過場。

## 互動模型

| 項目 | 決定 |
|---|---|
| 觸發 | 按住右下紅色虛線圓圈（手機）；或在畫布上按下滑鼠（桌機）。 |
| 重新校準 | 按下的瞬間捕捉當下的裝置方向作為新的 neutral，後續所有傾斜都被解讀為相對 neutral 的 delta。放開時凍結照片的 row/column。再次按下會重新定義 neutral，使用者可以先把手轉回舒服的姿勢再繼續。 |
| 垂直軸 (Δβ) | 切換 6 個 row：top rest、4 個 sequence、bottom rest。 |
| 水平軸 (Δγ) | 在當前 row 內切換 column，依該 row 的照片數線性對應。 |
| 靈敏度 | 預設 ±20° 跨越全部範圍。左側有一條 debug slider 可即時微調，調整完之後直接寫死、移除 slider。 |
| 邊界行為 | 照片索引到邊界 clamp。Polaroid 的 3D 旋轉繼續跟著手轉，讓使用者感覺到「碰到牆」但畫面仍會回應動作。 |
| 照片切換 | 硬切換，無 crossfade。 |
| Polaroid 3D | Damped：裝置傾斜 20° 對應到 polaroid 約 8° 的旋轉。Specular highlight 與投影偏移同步變化。 |
| 權限 | 載入時靜默 probe `deviceorientation` 事件 500ms。如果有讀到，紅圈直接可用；否則第一次按下時在 user gesture 內呼叫 `DeviceOrientationEvent.requestPermission()`。 |
| 權限被拒 | Fallback：在畫布上觸控拖曳，產生同樣的 Δβ/Δγ 事件。 |
| 桌機輸入 | `pointer.js` 模擬傾斜：mouse-down 的位置作為 neutral；滑鼠移動時把 `(Δx / window.innerWidth, Δy / window.innerHeight)` 對應到模擬的 ±20° Δγ/Δβ 範圍。 |

## 目錄結構

```
app/
  index.html              # entry, minimal markup
  styles.css              # all styles (extracted from current inline)
  main.js                 # bootstrapping, event wiring
  src/
    loader.js             # fetch data + alignments, preload images
    gyro.js               # DeviceOrientation + permission detection + EMA filter
    pointer.js            # desktop mouse-position simulation (same interface as gyro)
    mapping.js            # tilt delta → (row, col) index
    polaroid.js           # 3D transform + specular highlight + shadow
    debug.js              # tunable sensitivity slider
  data/
    photos.json           # 6 rows × variable columns（檔名為 .webp）
    alignments.json       # copy of alignment/aligned-all/alignments-normalized.json（矩陣不變）
  images/                 # 125 張 1568×1568 WebP（從 alignment/images-resized/ 同尺寸轉碼）
```

`app/` 是自給自足的：執行階段不會引用 `alignment/` 或 `poc/` 下的任何檔案。

## 圖片資產處理

從原始 `alignment/images/*.jpg`（4748×4748，本地檔案、gitignore 排除）出發，鏡像 `alignment/resize.py` 的處理流程：`exif_transpose` → `thumbnail(1568, LANCZOS)` → 直接存成 **WebP quality 80**。

- 與 `alignment/resize.py` 採用同樣的 LANCZOS 縮圖 → alignments.json 的矩陣完全不用動
- 直接從原圖生成 WebP，避開「原 JPG → 1568 JPG → WebP」中間多一道 JPG 損失（漸層 / noise 細節較好）
- 實測每張 ~85KB（JPG 原始 ~210KB），全部 125 張約 **~10 MB**，4G 約 4 秒可全部下載
- 唯一檔名改動：`.jpg` → `.webp`（在 photos.json 與 alignments.json 都要同步改）

前置條件：本機要有 `alignment/images/` 原始檔案。轉碼後的 `app/images/` 也是 gitignore 排除，部署時另外推送。

## 預載策略

- 進場時 `<img>` 全部建立並 attach 到 stage（`display:none`），但 src 不一次全發
- **先 fetch row 0 col 0 那一張**，等它 loaded 後才 render polaroid（防止使用者看到空畫面）
- 之後 6 個並行 worker 依序 fetch 剩下 124 張，順序按 row 0 → row 5 內 left-to-right
- UI 上一個小 progress indicator（caption 行末小字 `47 / 125`）顯示載入進度，全部載完後淡出
- 進度未滿時使用者仍可互動 — 切到尚未載入的照片時，`<img>` 顯示瀏覽器預設的「待 src」狀態（透明），polaroid 會看到底色而非照片，但這個視窗很短

## 行動裝置 viewport

`<meta name="viewport">` 加上 `maximum-scale=1, user-scalable=no`，避免使用者意外 pinch zoom 把 polaroid 放大、破壞 3D transform 的 perspective。

## 資料 Schema

`app/data/photos.json` 把現有的 top-rest / sequences / bottom-rest 三段攤平成一個統一的 row 陣列。每個 row 帶有 id、label、有序的 photos 陣列。Row 內的 column 就是陣列索引。

```json
{
  "rows": [
    { "id": "top-rest",    "label": "早上的散張",  "photos": ["..."] },
    { "id": "seq-1",       "label": "2025/12/31", "photos": ["..."] },
    { "id": "seq-2",       "label": "2026/01/19", "photos": ["..."] },
    { "id": "seq-3",       "label": "2026/01/22", "photos": ["..."] },
    { "id": "seq-4",       "label": "2026/01/26", "photos": ["..."] },
    { "id": "bottom-rest", "label": "其他散張",    "photos": ["..."] }
  ]
}
```

各 row 的照片數：29、7、10、30、20、29，總共 125 張，正好對應 `alignment/images-resized/` 的全部檔案。

`alignments.json` 從 `alignment/aligned-all/alignments-normalized.json` 原封不動複製過來，用法跟現有 PoC 一樣 — 用 `calibration_unit_px` 反正規化，再把 matrix 套到 `#stage` 內每張 `<img>` 的 CSS transform。

## 模組介面

### `loader.js`

```
loadAll() → { rows, alignment, imgByFile }
```
載入 `data/photos.json` 與 `data/alignments.json`，為每個被引用的檔案建立一個 `<img>`，把對齊矩陣套到那個 `<img>` 的 CSS transform 上，全部隱藏地掛到 stage 上。回傳完整結構。

### `gyro.js`

```
probePermission()       → Promise<'granted' | 'unknown'>
ensurePermission()      → Promise<'granted' | 'denied'>     // call from user gesture
createGyroSource()      → { onTilt(cb), startCalibrated(), stop() }
```
`createGyroSource` 包裝 `deviceorientation`，對 β/γ 套用 EMA filter（`α ≈ 0.18`），emit `{Δβ, Δγ}` — delta 是相對於最後一次 `startCalibrated()` 時的方向。

### `pointer.js`

跟 `createGyroSource` 同樣的介面（`onTilt`、`startCalibrated`、`stop`），但由滑鼠事件驅動。桌機使用，也作為 iOS 拒絕方向權限時的 touch-drag fallback。

### `mapping.js`

```
tiltToIndex({Δβ, Δγ}, baseRow01, baseCol01, sensitivityDeg, rows) → { row, col }
```
純函式：套用 index 公式並 clamp。`baseRow01` / `baseCol01` 是按下瞬間的正規化 [0,1] 位置，這樣再次按下時可以保持凍結點。

### `polaroid.js`

```
applyTiltVisual({Δβ, Δγ}, { tiltDamping, highlightIntensity }) → void
```
更新 polaroid 元素的 `transform`、`box-shadow`，以及 `--shine-x` / `--shine-y` / `--shine-opacity` 三個 CSS variable。按住期間每幀呼叫一次；放開時用 `{0,0}` 呼叫一次，讓 CSS transition 自動回到 neutral。

### `debug.js`

把靈敏度 / damping / highlight 三條 slider 渲染在畫面左側，把值持久化到 `location.hash`，並對外提供一個其他模組可以讀的 reactive 物件。

## Mapping 數學

設 `S = sensitivityDeg`（預設 20）：

```
rowIndex01 = clamp(baseRow01 + Δβ / S, 0, 1)
colIndex01 = clamp(baseCol01 + Δγ / S, 0, 1)

row = round(rowIndex01 * 5)               // 0..5
col = floor(colIndex01 * rows[row].photos.length)
col = clamp(col, 0, rows[row].photos.length - 1)
```

`baseRow01 = pressedRowIndex / 5`、`baseCol01 = pressedCol / (rowLen - 1)` 在 `pressstart` 觸發的瞬間捕捉。這樣即使使用者放開後旋轉手機，再次按下時 neutral 重新對齊，照片仍停在同一張。

## 視覺 Transform 數學

設 `D = tiltDamping`（預設 0.4）、`I = highlightIntensity`（預設 0.5）：

```
polaroid.transform =
  rotateX(-Δβ * D deg) rotateY(Δγ * D deg)

shineX = 50 - Δγ * 1.5     // %
shineY = 30 - Δβ * 1.5     // %
shineOpacity = 0.35 + min(0.4, (|Δβ| + |Δγ|) * 0.015) * (I / 0.5)

shadowOffsetX = -Δγ * 0.6  px
shadowOffsetY =  12 + Δβ * 0.4  px

box-shadow: ${shadowOffsetX}px ${shadowOffsetY}px 40px rgba(0,0,0,0.55),
            ${shadowOffsetX/3}px ${shadowOffsetY/4}px 6px rgba(0,0,0,0.4)
```

Polaroid 放在一個有 `perspective: 1200px` 的父層下。Specular highlight 是 `::after` overlay 上的 `radial-gradient`，用 `mix-blend-mode: screen` 疊上去。

放開按壓時，以上所有屬性以 300ms `ease-out` 平滑回到 neutral。

## 權限流程

1. 載入頁面 → 呼叫 `probePermission()`。Probe 掛一個 `deviceorientation` listener 500ms；若任一事件帶有非 null 的 β 或 γ，resolve `'granted'`。
2. 若 `'granted'`：紅圈以 `idle` 狀態渲染，立即可用，不會跳對話框。
3. 若 `'unknown'`：紅圈仍以 `idle` 狀態渲染。第一次 `pressstart` handler 內 `await ensurePermission()` 之後再訂閱 `gyro.js`。
   - 若 `requestPermission()` 回 `'granted'`：訂閱、繼續。
   - 若 `'denied'`：fallback 到 `pointer.js`、由 polaroid 表面的 touch event 驅動；紅圈切換到 `denied` 狀態。
4. 沒有 `requestPermission` 的瀏覽器（Android Chrome 等）直接跳過第 3 步。

## 紅色虛線圓圈 UX（手機限定）

- 位置：`position: fixed; right: 24px; bottom: 24px`
- 直徑：80 px
- Style：`border: 2px dashed #d34d4d; background: rgba(211,77,77,0.08); border-radius: 50%`
- 內容：中央一個小 icon（兩個交叉的傾斜箭頭，或 3×3 的點陣，暗示陀螺儀），下方 11px 文字「按住傾斜」
- 狀態：
  - **idle** — opacity 0.7→1.0 的呼吸 loop，2s 一次
  - **active** — 實線紅框 + 紅色微光，呼吸停止
  - **denied** — 虛線褪色，icon 換成手指拖曳示意

桌機不顯示（桌機上整個畫布都是 `pointer.js` 的偵測區）。

## Debug Slider（暫時性）

左側固定一條 vertical strip，調校期間在手機與桌機都顯示：

- Sensitivity range — ±10° 到 ±40°（預設 ±20°）
- Tilt damping — 0.0 到 1.0（預設 0.4）
- Highlight intensity — 0.0 到 1.0（預設 0.5）

值持久化到 `location.hash`（`#s=20&d=0.4&h=0.5`），重新整理會保留上次的設定。等手感調定之後，slider 移除、把常數寫死到對應模組裡。

## 可調整常數總表

| Constant | 預設值 | 所在模組 |
|---|---|---|
| `SENSITIVITY_DEG` | 20 | `mapping.js` |
| `TILT_DAMPING` | 0.4 | `polaroid.js` |
| `HIGHLIGHT_INTENSITY` | 0.5 | `polaroid.js` |
| `EMA_ALPHA` | 0.18 | `gyro.js` |
| `IDLE_TRANSITION_MS` | 300 | CSS |

## Out of Scope

- Row 之間的動畫過場（例如垂直 scroll 的感覺）。只用硬切換。
- 切換時的音效或 haptic。
- 持久化使用者上次看到的照片。
- 上線部署相關設定。
- 移除或改寫 `poc/`。原 PoC 保留作為歷史紀錄。
