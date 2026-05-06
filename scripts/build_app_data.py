"""Build app/data/photos.json from poc/data.json by flattening into 6 rows.

Filenames in the output are switched from .jpg to .webp so the app loads
the transcoded assets.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
src = json.loads((REPO / "poc" / "data.json").read_text(encoding="utf-8"))

def to_webp(name: str) -> str:
    return name.rsplit(".", 1)[0] + ".webp"

rows = [
    {"id": "top-rest", "label": "早上的散張",
     "photos": [to_webp(p) for p in src["topRest"]]},
]
for i, seq in enumerate(src["sequences"], start=1):
    rows.append({
        "id": f"seq-{i}",
        "label": seq["date"],
        "photos": [to_webp(p) for p in seq["photos"]],
    })
rows.append({
    "id": "bottom-rest",
    "label": "其他散張",
    "photos": [to_webp(p) for p in src["bottomRest"]],
})

out_path = REPO / "app" / "data" / "photos.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")

total = sum(len(r["photos"]) for r in rows)
print(f"Wrote {out_path} with {len(rows)} rows, {total} photos")
