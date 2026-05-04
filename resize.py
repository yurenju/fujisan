from pathlib import Path
from PIL import Image, ImageOps

SRC = Path(__file__).parent / "images"
DST = Path(__file__).parent / "images-resized"
DST.mkdir(exist_ok=True)

MAX_SIDE = 1568
QUALITY = 85

files = sorted(SRC.glob("*.jpg"))
for i, f in enumerate(files, 1):
    out = DST / f.name
    if out.exists():
        continue
    with Image.open(f) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        im.save(out, "JPEG", quality=QUALITY, optimize=True)
    print(f"[{i}/{len(files)}] {f.name} -> {im.size} {out.stat().st_size//1024}KB")
