"""Build app/images/*.webp + app/images-thumb/*.webp from the originals.

Mirrors alignment/resize.py's geometry (exif_transpose + LANCZOS
thumbnail to 1568x1568) so alignments.json's matrices remain valid,
but encodes WebP q80 directly from the original to avoid the extra
JPG round-trip that alignment/images-resized/ has gone through.

Also writes a 200×200 LQIP thumbnail to app/images-thumb/<name>.webp.
The viewer keeps every thumb decoded in memory as a flicker-free
fallback while the hi-res image decodes on iOS Safari.

Also rewrites alignments.json's keys from .jpg to .webp.
"""
import json
from pathlib import Path
from PIL import Image, ImageOps

REPO = Path(__file__).resolve().parents[1]
SRC_DIR = REPO / "alignment" / "images"
OUT_DIR = REPO / "app" / "images"
THUMB_DIR = REPO / "app" / "images-thumb"
OUT_DIR.mkdir(parents=True, exist_ok=True)
THUMB_DIR.mkdir(parents=True, exist_ok=True)

MAX_SIDE = 1568
QUALITY = 80
THUMB_SIDE = 200
THUMB_QUALITY = 60
total_bytes = 0
thumb_bytes = 0
count = 0

for src in sorted(SRC_DIR.glob("*.jpg")):
    out = OUT_DIR / (src.stem + ".webp")
    thumb_out = THUMB_DIR / (src.stem + ".webp")
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        im.save(out, format="WEBP", quality=QUALITY, method=6)
        # LQIP thumbnail — small enough that all 125 can stay decoded
        # in memory simultaneously on iOS (~20MB total) without OOM.
        thumb = im.copy()
        thumb.thumbnail((THUMB_SIDE, THUMB_SIDE), Image.LANCZOS)
        thumb.save(thumb_out, format="WEBP", quality=THUMB_QUALITY, method=6)
    total_bytes += out.stat().st_size
    thumb_bytes += thumb_out.stat().st_size
    count += 1

print(f"Wrote {count} hi-res WebPs, total {total_bytes/1024/1024:.1f} MB, "
      f"avg {total_bytes/count/1024:.1f} KB")
print(f"Wrote {count} thumb WebPs,  total {thumb_bytes/1024/1024:.2f} MB, "
      f"avg {thumb_bytes/count/1024:.1f} KB")

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
