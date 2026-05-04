# Fujisan

從同一個窗戶拍的 125 張富士山照片，讓它們在畫面中對齊起來，作為視覺展示的素材。

## 目前狀態

**第一階段：資料清理 — 完成。**

| 項目 | 數量 |
|---|---|
| 照片總數 | 125 |
| 自動對齊 | 114 |
| 手動修正 | 11 |
| 未對齊 | 0 |

對齊基準：`PXL_20250905_074912986.RAW-02.ORIGINAL.jpg`（一張多雲、富士山與大樓都清楚可見的照片）。

## 流水線

照片從原檔到可用對齊資料的處理順序：

```
images/                          原始照片（~1.2 GB，不進 git）
   │
   │  resize.py
   ▼
images-resized/                  長邊縮到 1568px
   │
   │  align_all.py               SIFT + ORB fallback + CLAHE + ROI mask
   ▼
aligned-all/alignments.json      自動對齊結果（含失敗清單）
   │
   │  merge_alignments.py        合併手動 overrides
   ▼
aligned-all/alignments-final.json  像素座標版（過渡格式）
   │
   │  normalize_alignments.py    tx/ty 轉成畫布長邊的比例
   ▼
aligned-all/alignments-normalized.json  ★ 標準格式（解析度無關）
   │
   │  build_viewer.py
   ▼
viewer.html                      瀏覽 + 微調工具
```

實際完整流程跑一次：

```bash
python resize.py
python align_all.py
python merge_alignments.py
python normalize_alignments.py
python build_viewer.py
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

啟動：在 VS Code 按 `F5` 選 Edge 或 Chrome；或手動 `python -m http.server 8765` 後開 http://localhost:8765/viewer.html

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

修正內容會自動存到 localStorage，按 `D` 下載完整 JSON、覆蓋 `aligned-all/alignments-normalized.json` 即可永久生效。

## 檔案說明

| 檔案 | 內容 | 進 git? |
|---|---|---|
| `images/` | 原始照片 | 否（太大） |
| `images-resized/` | 長邊 1568px JPEG | 否（可重生） |
| `aligned-all/alignments.json` | 純自動對齊原始輸出 | 否 |
| `aligned-all/alignments-final.json` | 像素座標版（已合併手工） | ✅ |
| `aligned-all/alignments-normalized.json` | **標準格式** | ✅ |
| `aligned-all/overrides.json` | 第一輪手工修正（歷史保留） | ✅ |
| `viewer.html` | build 產物 | 否 |

## 環境需求

- Python 3.12+
- `pip install opencv-python numpy pillow`
- 看 viewer 需要任一現代瀏覽器（Chrome / Edge / Firefox）

## 下一階段

第二階段：用對齊資料做出實際的視覺展示頁面（轉場、節奏、互動）。設計尚未開始。
