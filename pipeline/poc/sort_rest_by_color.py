"""Sort topRest / bottomRest in data.json by color similarity (preview only).

Writes:
  - stdout: ordered filename lists
  - poc/rest_color_order.html: thumbnail strip for visual review

Does NOT modify data.json. After eyeballing the output you can paste the new
order into data.json (or extend build_data.py).

Algorithm:
  1. Mean L*a*b* over the top half (sky region) of each image.
  2. Sort along the cool→warm axis: primarily by b (yellow vs blue), with a
     (red vs green) as tiebreaker. This is a single linear projection so it
     avoids the wraparound problem of hue angle, and stays sensible for
     near-neutral photos whose hue would otherwise be dominated by noise.
  3. Bottom rest: ink-wash photo (20260504) is forced to the very end.
"""
import json
import math
import os
import sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG_DIR = os.path.join(ROOT, "alignment", "images-resized")
DATA = os.path.join(HERE, "data.json")
OUT_HTML = os.path.join(HERE, "rest_color_order.html")

THUMB = 64


def mean_lab(filename):
    """Mean L*a*b* over the top half of the image (sky region)."""
    path = os.path.join(IMG_DIR, filename)
    with Image.open(path) as im:
        w, h = im.size
        sky = im.crop((0, 0, w, h // 2))
        sky.thumbnail((THUMB, THUMB))
        lab = sky.convert("LAB")
        px = lab.getdata()
        n = len(px)
        sl = sa = sb = 0
        for L, A, B in px:
            sl += L; sa += A; sb += B
        return (sl / n, sa / n, sb / n)


def warmth_key(lab):
    """Cool→warm projection: b primary (yellow/blue), a secondary (red/green)."""
    _, a, b = lab
    return (b, a)


def warmth_sort(items):
    """Sort items along the cool→warm axis. Items: [(filename, lab)]."""
    return sorted(items, key=lambda it: warmth_key(it[1]))


def render_html(top_ordered, bottom_ordered, output):
    def strip(title, items):
        cells = []
        for f, lab in items:
            short = f.replace("PXL_", "").replace(".RAW-02.ORIGINAL.jpg", "")
            cells.append(
                f'<div class="cell">'
                f'<img src="../alignment/images-resized/{f}" loading="lazy">'
                f'<div class="lab">L{lab[0]:.0f} a{lab[1]:.0f} b{lab[2]:.0f}</div>'
                f'<div class="name">{short}</div>'
                f"</div>"
            )
        return (
            f'<section><h2>{title} · {len(items)} photos</h2>'
            f'<div class="strip">{"".join(cells)}</div></section>'
        )

    html = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<title>Rest color order preview</title>
<style>
  body {{ background:#111; color:#ddd; font-family:-apple-system,sans-serif; margin:20px; }}
  h1, h2 {{ font-weight:500; color:#fff; }}
  h2 {{ font-size:14px; color:#999; margin-top:24px; letter-spacing:.05em; text-transform:uppercase; }}
  .strip {{ display:flex; flex-wrap:wrap; gap:6px; }}
  .cell {{ width:120px; }}
  .cell img {{ width:120px; height:80px; object-fit:cover; border-radius:2px; display:block; }}
  .lab, .name {{ font-family:"SF Mono",Consolas,monospace; font-size:9px; color:#777; margin-top:2px; word-break:break-all; }}
  .name {{ color:#555; }}
</style></head><body>
<h1>Rest color order — preview</h1>
<p style="color:#888;font-size:12px">Sorted along cool→warm axis: primary b (yellow/blue), secondary a
(red/green), of top-half mean L*a*b*. Bottom: ink-wash (20260504) forced last.</p>
{strip("Top rest", top_ordered)}
{strip("Bottom rest", bottom_ordered)}
</body></html>"""
    with open(output, "w", encoding="utf-8") as fp:
        fp.write(html)


def main():
    with open(DATA, encoding="utf-8") as fp:
        data = json.load(fp)
    top = data["topRest"]
    bottom = data["bottomRest"]

    print(f"Computing LAB for {len(top)} top + {len(bottom)} bottom photos...", file=sys.stderr)
    top_items = [(f, mean_lab(f)) for f in top]
    bottom_items = [(f, mean_lab(f)) for f in bottom]

    top_ordered = warmth_sort(top_items)

    # Bottom: cool→warm sort, then force ink-wash to the very end
    ink = [it for it in bottom_items if "20260504" in it[0]]
    rest = [it for it in bottom_items if "20260504" not in it[0]]
    bottom_ordered = warmth_sort(rest) + ink

    print("\n=== topRest (color-sorted) ===")
    for f, lab in top_ordered:
        print(f"  {f}  # L={lab[0]:.0f} a={lab[1]:.0f} b={lab[2]:.0f}")
    print("\n=== bottomRest (color-sorted, ink-wash last) ===")
    for f, lab in bottom_ordered:
        print(f"  {f}  # L={lab[0]:.0f} a={lab[1]:.0f} b={lab[2]:.0f}")

    render_html(top_ordered, bottom_ordered, OUT_HTML)
    print(f"\nWrote preview: {OUT_HTML}", file=sys.stderr)

    if "--apply" in sys.argv:
        data["topRest"]    = [f for f, _ in top_ordered]
        data["bottomRest"] = [f for f, _ in bottom_ordered]
        with open(DATA, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        print(f"Applied color order to {DATA}", file=sys.stderr)


if __name__ == "__main__":
    main()
