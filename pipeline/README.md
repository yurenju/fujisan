# Pipeline — 對齊資料的歷史與重現

`app/` 裡那兩份檔案 `app/data/photos.json` 與 `app/data/alignments.json`(以及 `app/images/*.webp`)的來源都在這個目錄底下。本文件記錄整條管線怎麼跑、對齊技術細節、以及資料格式。

> 平常**不需要**重跑這些腳本——成品已經 commit 進 git 了。只在以下情況才會用到:加新照片、調整對齊、改變 row 切分邏輯。

## 第一階段:對齊處理

| 項目 | 數量 |
|---|---|
| 照片總數 | 125 |
| 自動對齊 | 114 |
| 手動修正 | 11 |
| 未對齊 | 0 |

對齊基準:`PXL_20250905_074912986.RAW-02.ORIGINAL.jpg`(一張多雲、富士山與大樓都清楚可見的照片)。

### 流水線

```
alignment/images/                         原始照片
   │  resize.py
   ▼
alignment/images-resized/                 長邊縮到 1568px
   │  align_all.py                        SIFT + ORB fallback + CLAHE + ROI mask
   ▼
alignment/aligned-all/alignments.json     自動對齊結果(含失敗清單)
   │  merge_alignments.py                 合併手動 overrides
   ▼
alignment/aligned-all/alignments-final.json   像素座標版(過渡格式)
   │  normalize_alignments.py             tx/ty 轉成畫布長邊的比例
   ▼
alignment/aligned-all/alignments-normalized.json  ★ 標準格式(解析度無關)
   │  build_viewer.py
   ▼
alignment/viewer.html                     瀏覽 + 微調工具
```

從專案根目錄跑完整流程:

```bash
python pipeline/alignment/resize.py
python pipeline/alignment/align_all.py
python pipeline/alignment/merge_alignments.py
python pipeline/alignment/normalize_alignments.py
python pipeline/alignment/build_viewer.py
```

之後若要繼續微調,**只需要 viewer + build_viewer.py 兩步**:在 viewer 裡按 `D` 下載 `alignments-normalized.json` → 覆蓋 → 重 build。

### 對齊技術

- **SIFT 特徵點匹配**:每張照片找上千個關鍵點,跟參考照片配對,RANSAC 求出相似變換(4 自由度:tx, ty, 旋轉, 縮放)
- **CLAHE 局部對比增強**:把陰影裡的大樓細節拉出來,讓日落剪影也找得到特徵
- **ORB 後備**:SIFT 卡住時改用 ORB 重試
- **ROI mask**:參考照片只在下半部找特徵,避開會變動的雲層
- **雙層合理性檢查**:inliers ≥ 8 → 寬鬆門檻;inliers < 8 → 嚴格門檻避免退化解
- **失敗鄰居種子**:對齊失敗的照片,用時間最近的成功照(同方向)參數當手動修正起點

### 對齊資料格式

`alignments-normalized.json` 是 canonical 來源:

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

- `tx`, `ty`:占畫布長邊的比例(解析度無關)
- `a, b, c, d`:旋轉 + 等比縮放(無因次,任何解析度通用)
- `src_aspect`:原始照片寬高比

**任何解析度套用方式**(假設正方形畫布長邊 K):

```js
const K = 1080;  // 任意像素
const M = item.matrix;
const tx = M[0][2] * K;
const ty = M[1][2] * K;
const a = M[0][0], b = M[0][1], c = M[1][0], d = M[1][1];
img.style.transform = `matrix(${a}, ${c}, ${b}, ${d}, ${tx}, ${ty})`;
// 圖片 src 用長邊 = K 的版本
```

### Viewer 操作

啟動:在 VS Code 按 `F5` 選 Edge 或 Chrome;或手動在專案根目錄跑 `python -m http.server 8765` 後開 <http://localhost:8765/pipeline/alignment/viewer.html>

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
| 修正 | `←` `→` `↑` `↓` | 移動 1px(Shift = 10px)|
|  | `Z` `X` | 旋轉 ±0.1°(Shift = ±1°)|
|  | `-` `=` | 縮放 ×0.99 / ×1.01(Shift = ×0.95 / ×1.05)|
|  | `R` | 重置這張的編輯 |
|  | `T` 或 `Esc` | 退出修正模式 |

修正內容會自動存到 localStorage,按 `D` 下載完整 JSON、覆蓋 `pipeline/alignment/aligned-all/alignments-normalized.json` 即可永久生效。

## 第二階段:把對齊資料餵給 app

### 資料分佈

從三鷹這個窗看出去,富士山幾乎只在晚秋到早春可見,所以 125 張照片分佈非常不均:

| 月份 | 張數 |
|---|---:|
| 2025-09 / 10 | 5 |
| 2025-11 | 9 |
| 2025-12 | 23 |
| **2026-01** | **80** |
| 2026-02 | 7 |
| 2026-05 | 1 |

**77% 的照片集中在 16:00–17:30 JST(日落帶)**,其餘是早上抬頭的散張。1 月底有 3 天連續長序列(10、30、20 張),剛好對應太陽掃過富士山頂的鑽石富士窗口。

### 連續日落序列(≥7 張)

| 日期 | 起 → 訖 | 跨距 | 張數 | 太陽相對山頂 |
|---|---|---:|---:|---|
| 2025-12-31 | 16:26 → 16:29 | 3m10s | 7 | 偏左肩 |
| 2026-01-19 | 16:39 → 16:42 | 2m45s | 10 | **正切山頂(鑽石近似)** |
| 2026-01-22 | 16:43 → 16:50 | 7m36s | 30 | **完整切過山頂** |
| 2026-01-26 | 16:42 → 16:53 | 10m46s | 20 | 已過山頂往右 |

### 上下散張的排序:天空色相

兩條散張帶不再用拍攝時間排,改用**天空顏色**的冷暖度排序。流程:

1. 取每張照片的上半部(天空區域)
2. 算上半部的平均 L\*a\*b\* 顏色
3. 按 b 軸(黃 ↔ 藍)為主、a 軸(紅 ↔ 綠)為次序排序

這是個 1D 線性投影,避開了「色相角的環形不連續」與「近中性色相不穩定」問題,做出來的是穩定的「冷天空 → 中性 → 暖橘紅」漸變。05/04 水墨那張仍強制錨在尾端。

腳本:`pipeline/poc/sort_rest_by_color.py`(`--apply` 寫回 `data.json`,平常輸出 `pipeline/poc/rest_color_order.html` 供肉眼驗證)。

### Build app 的兩支腳本

```bash
python pipeline/scripts/build_app_data.py    # poc/data.json → app/data/photos.json(切 6 列、副檔名換 webp)
python pipeline/scripts/build_app_images.py  # alignment/images/*.jpg → app/images/*.webp + app/images-thumb/*.webp,並把 alignments.json 鍵改 webp
```

兩支都從 `pipeline/alignment/images/`(本地檔案、不進 git)讀原始 JPEG。

## 探索工具

```bash
python pipeline/distribution.py                  # 08-18 JST,5 分鐘 bin
python pipeline/distribution.py --zoom sunset    # 16-18,1 分鐘 bin
python pipeline/distribution.py --bin 2          # 自訂
```

印出照片時間分佈的 ASCII 圖,本身只是探索用、跟管線輸出無關。

## 環境需求

- Python 3.12+
- `pip install opencv-python numpy pillow`
- 看 viewer 需要任一現代瀏覽器(Chrome / Edge / Firefox)
