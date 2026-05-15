# 將傾斜角度從「位置映射」改為「速度映射」設計

## 背景

目前的瀏覽模型把整個照片集視為 [0,1] × [0,1] 的矩形 ([app/src/mapping.js](../../../app/src/mapping.js))，傾斜角度直接對應到矩形上的位置，碰到邊緣 clamp 住。這意味著手持靜止時點不會移動、改變傾斜角度才會跳到新位置（position mapping）。

本次調整把映射改為「角度 → 速度」（velocity mapping），並在邊緣 wrap 而非 clamp。

## 心智模型

不再把照片集當成一個平面矩形，改成兩條獨立的 conveyor belt 加上一個跨 row 的比例保留規則：

- **左右**：在當前 row 內以「每秒 N 張照片」速度翻
- **上下**：以「每秒 N 個 row」速度切換 row
- **跨 row 瞬間**：col 位置依比例 (`colFloat / oldLen × newLen`) 重算，保留矩陣對齊感

副作用：短 row 整體翻得快、長 row 翻得慢。例：row 1 有 5 張、row 2 有 50 張，固定 2 張/秒下，row 1 約 2.5 秒繞一圈、row 2 要 25 秒。這是預期行為，因為使用者要的是「每張照片停留的時間固定」。

## 行為規格

### 死區 + 線性速度

```
速度(tilt) = 0,                                    當 |tilt| ≤ deadzone
速度(tilt) = sign(tilt) × (|tilt| - deadzone) / s, 其他
```

- 上下：`s = sv` （傾斜 sv 度時 = 1 row/sec）
- 左右：`s = sh` （傾斜 sh 度時 = 1 photo/sec）
- 預設 `sv = 25°`、`sh = 12°`、`deadzone = 2°`
- 角度本身已由 `gyro.js` 的 EMA 平滑過

### Wrap-around

兩軸獨立 wrap，不打字機換行：

- `rowFloat` 範圍 `[0, rowCount)`，超過則 mod 回去
- `colFloat` 範圍 `[0, currentRowLen)`，超過則 mod 回去
- 顯示用 `row = floor(rowFloat)`、`col = floor(colFloat)`

### 跨 row 的 col 重算

每幀偵測整數 row index 是否改變。一旦改變：

```
ratio = colFloat / rows[prevRow].photos.length    // [0, 1)
colFloat = ratio × rows[newRow].photos.length
```

用 `col01 = col / rowLen`（範圍 [0,1)，wrap 在 1 = 0 處）的公式，跟 wrap 行為自然對齊。

### 按壓生命週期

- **按下**：`gyro.startCalibrated()` 校正 neutral 角度；以**當前的** `rowFloat` / `colFloat` 接續累積；啟動 RAF loop
- **放開**：停止 RAF loop；`gyro.endCalibrated()`；視覺歸位
- 再次按下時從上次停下的位置續接（不再用 `baseRow01` / `baseCol01` 凍結點）

## 架構

### 元件邊界

| 元件 | 職責 | 介面 |
|---|---|---|
| `gyro.js` | 提供平滑後的 `{db, dg}`；新增 pull 介面 | `latest()` |
| `mapping.js` | 純函式：tilt → velocity；狀態推進 → 新位置 | `tiltToVelocity`、`advance` |
| `main.js` | RAF loop、狀態管理、串接 gyro/mapping/loader | — |
| `pointer.js` | 桌面/拖曳 fallback，輸出虛擬 `{db, dg}` | 可能新增 `latest()` |

### 資料流

```
deviceorientation event
  → gyro.js（EMA 平滑 + calibration）
  → 1. push 給 applyTiltVisual（即時視覺）
    2. 存在內部 state，等 RAF loop 用 latest() 拉

RAF loop（按下時啟動）
  → gyro.latest() → { db, dg }
  → tiltToVelocity → { vRow, vCol }
  → advance(state, velocity, dt, rows) → { rowFloat, colFloat, row, col }
  → setPhoto(row, col) 若整數變化
```

### 純函式介面

```js
// mapping.js
export function tiltToVelocity({ db, dg }, { sv, sh, deadzone }) {
  return {
    vRow: speedFrom(db, sv, deadzone),    // rows/sec
    vCol: speedFrom(dg, sh, deadzone),    // photos/sec
  };
}

export function advance(state, velocity, dt, rows) {
  // state: { rowFloat, colFloat }
  // velocity: { vRow, vCol }
  // 回傳 { rowFloat, colFloat, row, col }
  // 處理 row wrap、跨 row 比例重算、col wrap
}
```

兩個都是純函式，便於單元測試（給定輸入 → 預期輸出）。

### gyro.js 變動

新增 pull 方法，原本的 push listener 仍保留（給 `applyTiltVisual`）：

```js
return {
  onTilt(fn) { ... },                   // 不變
  latest() {
    return calibrated
      ? { db: smoothedBeta - neutralBeta, dg: smoothedGamma - neutralGamma }
      : { db: 0, dg: 0 };
  },
  startCalibrated() { ... },            // 不變
  endCalibrated() { ... },              // 不變
  stop() { ... },                       // 不變
};
```

### main.js 變動

- 新增模組級 state：`rowFloat = 0`、`colFloat = 0`、`rafHandle = null`、`lastTickMs = 0`
- 移除：`baseRow01`、`baseCol01`、`currentRow`、`currentCol`（後兩者改由 `Math.floor(rowFloat/colFloat)` 計算）
- 新增 `startLoop()` / `stopLoop()`
- `startPress` 改為呼叫 `startLoop()`；`endPress` 改為呼叫 `stopLoop()`
- 移除 `onTiltUpdate` 對 mapping 的呼叫（mapping 改由 RAF loop 拉值執行）；`applyTiltVisual` 仍由 push event 觸發

## 參數

| 參數 | 意義 | 預設 | slider 範圍 |
|---|---|---|---|
| `sv` | 達到 1 row/sec 的傾斜度數 | 25° | 10–40 |
| `sh` | 達到 1 photo/sec 的傾斜度數 | 12° | 5–30 |
| `deadzone` | 死區度數 | 2° | 0–5 |
| `inv` | 反轉方向 | 1 | 0/1 |
| `d`、`h` | tilt visual damping / highlight | 不變 | 不變 |

預設值是起跳值，實機時用 slider 微調。

## 不變的部分

- 照片載入 (`loader.js`)、DOM 結構、polaroid 視覺傾斜 (`polaroid.js`、`applyTiltVisual`)
- 校正流程（按下校 neutral）、iOS 權限請求流程
- debug panel 的 photo map 高亮機制
- `applyTiltVisual` 仍由 push event 驅動，跟 mapping 解耦（保證視覺即時跟手）

## 驗收觀察點

實機開啟瀏覽器時應觀察到：

- 手持靜止（死區內）→ 點不會漂移
- 微傾（剛超過死區）→ 緩慢移動
- 大角度傾斜 → 快速移動
- 角度回到 0 → 停止
- 短 row 整體快速繞一圈、長 row 翻得慢
- 跨 row 切換時 col 比例保留（例：在 50 張的 row 第 30 張往上 → 跳到 5 張的 row 第 3 張）
- 兩軸獨立 wrap：到右邊盡頭從左邊出來、到最下面從最上面出來
- 反方向傾斜 → 反方向移動

## 影響的檔案

| 檔案 | 變動 |
|---|---|
| [app/src/mapping.js](../../../app/src/mapping.js) | 重寫：`tiltToVelocity` + `advance`；移除 `tiltToIndex` |
| [app/main.js](../../../app/main.js) | 新增 RAF loop、`rowFloat`/`colFloat` state、移除 `baseRow01`/`baseCol01` |
| [app/src/gyro.js](../../../app/src/gyro.js) | 新增 `latest()` 方法 |
| [app/src/pointer.js](../../../app/src/pointer.js) | 視介面情況新增 `latest()` 方法 |
| [app/src/debug.js](../../../app/src/debug.js) | 新增 `deadzone` slider；`sv` / `sh` 標籤改為「度數 / (rows or photos)/sec」 |

## 不採用的方向

- **velocity 用曲線（二次/指數）**：YAGNI，線性 + 死區先試，不夠細膩再加曲線
- **打字機換行 wrap**（右盡頭跳到下一 row 開頭）：使用者明確要兩軸獨立 wrap
- **跨 row 不重算 col**（保持 col 整數 index）：與「矩陣對齊感」訴求衝突
- **左右回到「走完全程 / 秒」模型**：與「每張照片停留時間固定」訴求衝突
