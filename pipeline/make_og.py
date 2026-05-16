"""Generate Open Graph / Twitter social card from a hero photo."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "images" / "PXL_20260201_083714632.RAW-02.ORIGINAL.webp"
OUT = ROOT / "app" / "og-image.jpg"

W, H = 1200, 630

img = Image.open(SRC).convert("RGB")
iw, ih = img.size
# cover crop to 1200x630
scale = max(W / iw, H / ih)
nw, nh = int(iw * scale), int(ih * scale)
img = img.resize((nw, nh), Image.LANCZOS)
left = (nw - W) // 2
# bias crop downward so the Fuji silhouette + city lights stay in frame
top = min(nh - H, (nh - H) // 2 + int(nh * 0.12))
img = img.crop((left, top, left + W, top + H))

# darken left half with a horizontal gradient for text legibility
overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
od = ImageDraw.Draw(overlay)
for x in range(W):
    # strong on the left, fade out by ~65% width
    t = max(0.0, 1.0 - x / (W * 0.65))
    alpha = int(150 * t)
    od.line([(x, 0), (x, H)], fill=(0, 0, 0, alpha))
img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

draw = ImageDraw.Draw(img)

YUMIN = "C:/Windows/Fonts/yumin.ttf"
YUMIN_DB = "C:/Windows/Fonts/yumindb.ttf"
KAIU = "C:/Windows/Fonts/kaiu.ttf"

f_eyebrow = ImageFont.truetype(YUMIN, 28)
f_title = ImageFont.truetype(YUMIN_DB, 160)
f_subtitle = ImageFont.truetype(YUMIN, 56)
f_url = ImageFont.truetype(YUMIN, 26)

WARM = (245, 232, 210)
WARM_DIM = (220, 205, 180)

x0 = 80
y = 110

draw.text((x0, y), "一段攝影札記", font=f_eyebrow, fill=WARM_DIM)
# thin rule under eyebrow
y += 50
draw.line([(x0, y), (x0 + 60, y)], fill=WARM_DIM, width=2)

y += 30
draw.text((x0, y), "富士山", font=f_title, fill=WARM)

y += 195
draw.text((x0, y), "日落的位移", font=f_subtitle, fill=WARM)

# bottom-left url
draw.text((x0, H - 60), "fujisan.yurenju.me", font=f_url, fill=WARM_DIM)

img.save(OUT, "JPEG", quality=88, optimize=True, progressive=True)
print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
