# Fujisan

從同一個窗戶拍的 125 張富士山照片，讓它們在畫面中對齊起來，作為視覺展示的素材。

GitHub: <https://github.com/yurenju/fujisan>

## 授權

- **程式碼**：MIT License — 詳見 [LICENSE](LICENSE)
- **照片**：CC BY-NC 4.0（姓名標示-非商業性使用）— 詳見 [LICENSE-PHOTOS](LICENSE-PHOTOS)

## 目前狀態

**第一階段：資料清理 — 完成。**

| 項目 | 數量 |
|---|---|
| 照片總數 | 125 |
| 自動對齊 | 114 |
| 手動修正 | 11 |
| 未對齊 | 0 |

對齊基準：`PXL_20250905_074912986.RAW-02.ORIGINAL.jpg`（一張多雲、富士山與大樓都清楚可見的照片）。

## 目錄結構

```
fujisan/
├── alignment/                    第一階段：對齊處理（本階段全部成果）
│   ├── images/                   原始照片（~1.2 GB，不進 git）
│   ├── images-resized/           長邊 1568px JPEG（不進 git，可重生）
│   ├── aligned-all/              對齊資料
│   │   ├── alignments.json           自動對齊原始輸出（不進 git）
│   │   ├── alignments-final.json     像素座標版
│   │   ├── alignments-normalized.json  ★ 標準格式（解析度無關）
│   │   └── overrides.json            第一輪手工修正（歷史保留）
│   ├── viewer.html               build 產物（不進 git）
│   ├── resize.py
│   ├── align_test.py             早期 ORB 實驗（保留）
│   ├── align_all.py
│   ├── merge_alignments.py
│   ├── normalize_alignments.py
│   └── build_viewer.py
├── README.md
├── .gitignore
├── .vscode/                      F5 啟動 viewer (Edge/Chrome)
└── .claude/                      Claude Code preview 設定
```

## 流水線

照片從原檔到可用對齊資料的處理順序：

```
images/                          原始照片
   │  resize.py
   ▼
images-resized/                  長邊縮到 1568px
   │  align_all.py               SIFT + ORB fallback + CLAHE + ROI mask
   ▼
aligned-all/alignments.json      自動對齊結果（含失敗清單）
   │  merge_alignments.py        合併手動 overrides
   ▼
aligned-all/alignments-final.json  像素座標版（過渡格式）
   │  normalize_alignments.py    tx/ty 轉成畫布長邊的比例
   ▼
aligned-all/alignments-normalized.json  ★ 標準格式（解析度無關）
   │  build_viewer.py
   ▼
viewer.html                      瀏覽 + 微調工具
```

實際完整流程跑一次（從專案根目錄）：

```bash
python alignment/resize.py
python alignment/align_all.py
python alignment/merge_alignments.py
python alignment/normalize_alignments.py
python alignment/build_viewer.py
```

之後若要繼續微調，**只需要 viewer + build_viewer.py 兩步即可**：在 viewer 裡按 `D` 下載 `alignments-normalized.json` → 覆蓋 → 重 build。

## 對齊技術

- **SIFT 特徵點匹配**：每張照片找上千個關鍵點，跟參考照片配對，RANSAC 求出相似變換（4 自由度：tx, ty, 旋轉, 縮放）
- **CLAHE 局部對比增強**：把陰影裡的大樓細節拉出來，讓日落剪影也找得到特徵
- **ORB 後備**：SIFT 卡住時改用 ORB 重試
- **ROI mask**：參考照片只在下半部找特徵，避開會變動的雲層
- **雙層合理性檢查**：inliers ≥ 8 → 寬鬆門檻；inliers < 8 → 嚴格門檻避免退化解
- **失敗鄰居種子**：對齊失敗的照片，用時間最近的成功照（同方向）參數當手動修正起點

## 對齊資料格式

`alignments-normalized.json` 是 canonical 來源：

```json
{
  "reference": "PXL_20250905_074912986.RAW-02.ORIGINAL.jpg",
  "calibration_unit_px": 1568,
  "items": {
    "PXL_xxx.jpg": {
      "matrix": [[a, b, tx_norm], [c, d, ty_norm]],
      "scale": 1.5, "rotation_deg": 0.3,
      "tx": 0.0512, "ty": -0.0123,
      "src_aspect": 0.752,
      "source": "auto"
    }
  }
}
```

- `tx`, `ty`：占畫布長邊的比例（解析度無關）
- `a, b, c, d`：旋轉 + 等比縮放（無因次，任何解析度通用）
- `src_aspect`：原始照片寬高比

**任何解析度套用方式**（假設正方形畫布長邊 K）：

```js
const K = 1080;  // 任意像素
const M = item.matrix;
const tx = M[0][2] * K;
const ty = M[1][2] * K;
const a = M[0][0], b = M[0][1], c = M[1][0], d = M[1][1];
img.style.transform = `matrix(${a}, ${c}, ${b}, ${d}, ${tx}, ${ty})`;
// 圖片 src 用長邊 = K 的版本
```

## Viewer 操作

啟動：在 VS Code 按 `F5` 選 Edge 或 Chrome；或手動在專案根目錄跑 `python -m http.server 8765` 後開 http://localhost:8765/alignment/viewer.html

| 模式 | 鍵 | 動作 |
|---|---|---|
| 檢視 | `←` `→` | 切換照片 |
|  | `A` | 對齊開關 |
|  | `O` | 半透明疊參考圖 |
|  | `F` | 只看已對齊 |
|  | `G` | 只看未對齊 |
|  | `T` | 進入修正模式 |
|  | `D` | 下載完整 `alignments-normalized.json` |
|  | `C` | 清除本地編輯 |
| 修正 | `←` `→` `↑` `↓` | 移動 1px（Shift = 10px）|
|  | `Z` `X` | 旋轉 ±0.1°（Shift = ±1°）|
|  | `-` `=` | 縮放 ×0.99 / ×1.01（Shift = ×0.95 / ×1.05）|
|  | `R` | 重置這張的編輯 |
|  | `T` 或 `Esc` | 退出修正模式 |

修正內容會自動存到 localStorage，按 `D` 下載完整 JSON、覆蓋 `alignment/aligned-all/alignments-normalized.json` 即可永久生效。

## 環境需求

- Python 3.12+
- `pip install opencv-python numpy pillow`
- 看 viewer 需要任一現代瀏覽器（Chrome / Edge / Firefox）

## 第二階段：視覺展示（進行中）

把對齊資料做成一個視覺/互動的數位藝術展示。POC 仍在迭代，目前確定的方向：**單張 polaroid 為主視覺，pad 縮成左下浮動的小工具**。

### 資料分佈的關鍵發現

從三鷹這個窗看出去，富士山幾乎只在晚秋到早春可見，所以 125 張照片分佈非常不均：

| 月份 | 張數 |
|---|---:|
| 2025-09 / 10 | 5 |
| 2025-11 | 9 |
| 2025-12 | 23 |
| **2026-01** | **80** |
| 2026-02 | 7 |
| 2026-05 | 1 |

**77% 的照片集中在 16:00–17:30 JST（日落帶）**，其餘是早上抬頭的散張。1 月底有 3 天連續長序列（10、30、20 張），剛好對應太陽掃過富士山頂的鑽石富士窗口。

### 連續日落序列（≥7 張）

| 日期 | 起 → 訖 | 跨距 | 張數 | 太陽相對山頂 |
|---|---|---:|---:|---|
| 2025-12-31 | 16:26 → 16:29 | 3m10s | 7 | 偏左肩 |
| 2026-01-19 | 16:39 → 16:42 | 2m45s | 10 | **正切山頂（鑽石近似）** |
| 2026-01-22 | 16:43 → 16:50 | 7m36s | 30 | **完整切過山頂** |
| 2026-01-26 | 16:42 → 16:53 | 10m46s | 20 | 已過山頂往右 |

### 目前的版面構想

```
┌──────────────────────────────────────────────┐
│  top rest（早上的散張，~29 張）                │
├──────────────────────────────────────────────┤
│ Row 1  12/31 │ ●○○○○○○                       │  7 張
│ Row 2  01/19 │ ●○○○○○○○○○                    │ 10 張
│ Row 3  01/22 │ ●○○○○○○○○○○○○○○○○○○○○○○○○○○ │ 30 張
│ Row 4  01/26 │ ●○○○○○○○○○○○○○○○○○○○○        │ 20 張
├──────────────────────────────────────────────┤
│  bottom rest（其他散張，05/04 水墨在最右）     │
└──────────────────────────────────────────────┘
       早（太陽高）  ─────────→  晚（太陽低）
```

- **中間 4 條 row**＝四天的連續日落，每條 row 內部 X 軸是時間
- **上下散張帶**＝其餘 ~58 張（上半早上、下半其他），**5/4 那張水墨感的照片放在右下角當作整年的尾聲**
- 由日期排序：12/31 → 1/19 → 1/22 → 1/26，剛好就是太陽從山左肩 → 切過山頂 → 滑過右側的順序
- 觀眾用游標（之後可改成手機陀螺儀）在這個矩形內移動，照片即時切換

### 上下散張的排序：天空色相

兩條散張帶不再用拍攝時間排，改用**天空顏色**的冷暖度排序。流程：

1. 取每張照片的上半部（天空區域）
2. 算上半部的平均 L\*a\*b\* 顏色
3. 按 b 軸（黃 ↔ 藍）為主、a 軸（紅 ↔ 綠）為次序排序

這是個 1D 線性投影，避開了「色相角的環形不連續」與「近中性色相不穩定」問題，做出來的是穩定的「冷天空 → 中性 → 暖橘紅」漸變。05/04 水墨那張仍強制錨在尾端。

腳本：`poc/sort_rest_by_color.py`（`--apply` 寫回 `data.json`，平常輸出 `poc/rest_color_order.html` 供肉眼驗證）。

### 視覺處理（已套用 POC）

每張照片以**寶麗來樣式**呈現，不只是純粹的影像顯示：

- **Polaroid 框**：米白底 (`#f5f1e8`)、下緣比較寬，右下方 caption 顯示日期時間（手寫風字體）
- **照片畫布留白**：對齊後沒被照片覆蓋的角落填**泛黃淺灰** (`#e8e1d0`)，模擬「未印滿的相紙」
- **紙膠帶**：藍/白斜條紋短條，自動釘在**可見照片內容的頂端中央**（用 alignment matrix + 圖片 natural size 即時計算位置）；當照片滿版接觸 canvas 上緣時自動隱藏
- **浮動 pad**：原本佔半個畫面的控制 pad 縮成 260px、釘在左下、半透明黑底加 backdrop blur，當作小型導覽工具

實作細節跟其他「未印滿區效果」的對比可看 `poc/print_effects.html`（A 純色 / B 純白 / ... / I 化學暈染共 9 種變體）。

### 互動長期目標

手機陀螺儀傾斜手機，「找到」中心的鑽石富士那一刻——體驗本身複製了攝影者在窗前等待對齊的動作。

## 目錄結構（第二階段相關）

```
fujisan/
├── poc/                       第二階段 POC（純滑鼠版，pad → 照片即時切換）
│   ├── build_data.py          從 alignment/images-resized 產生 data.json
│   ├── data.json              4 條序列 + 上下散張清單（散張按天空色相排序）
│   ├── sort_rest_by_color.py  天空色相排序腳本（--apply 寫回 data.json）
│   ├── index.html             ★ 主 POC：polaroid + 紙膠帶 + 浮動 pad
│   └── print_effects.html     未印滿區的 9 種視覺處理對比
├── distribution.py            探索工具：印出照片時間分佈的 ASCII 圖
└── ...（alignment/ 同前）
```

### POC 怎麼跑

```bash
python poc/build_data.py                  # 重建 data.json（照片或門檻變動時才需）
python poc/sort_rest_by_color.py --apply  # 重排上下散張的色相順序（可選）
python -m http.server 8765                # 從專案根目錄
# 開 http://localhost:8765/poc/index.html
```

中央是當前照片（polaroid 框 + 紙膠帶），左下角浮動 pad 是控制器。游標在 pad 內移動 → 照片切換 + 紙膠帶位置依照片 alignment 即時調整。pad 下方 info 條顯示目前落在哪一格（例如 `row3[19/30] 2026-01-22`），polaroid 下方 caption 顯示日期時間。

對比未印滿區的視覺處理可開 http://localhost:8765/poc/print_effects.html （9 種變體並排）。

### 探索工具：照片分佈

```bash
python distribution.py                  # 08-18 JST，5 分鐘 bin
python distribution.py --zoom sunset    # 16-18，1 分鐘 bin
python distribution.py --bin 2          # 自訂
```
