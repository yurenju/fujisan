"""Produce a resolution-independent version of alignments-final.json.

Translation values are normalized by the calibration canvas size so the same
file can be used at any target resolution. To apply at a target canvas size K
(assumes square canvas, which matches our reference):

    matrix = [[a, b, tx * K], [c, d, ty * K]]

Source photos must be resized so their long edge equals K (aspect preserved),
then the CSS transform `matrix(a, c, b, d, tx*K, ty*K)` aligns them.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "aligned-all" / "alignments-final.json"
OUT = ROOT / "aligned-all" / "alignments-normalized.json"

data = json.load(open(SRC))
W = data["canvas"]["w"]
H = data["canvas"]["h"]

if W != H:
    raise SystemExit(
        f"Canvas is not square ({W}x{H}); the normalization assumes a square "
        "canvas. Adjust this script if you actually need non-square."
    )

unit = W  # canvas long edge in calibration pixels

normalized = {}
for name, r in data["items"].items():
    M = r.get("matrix")
    if M is None:
        normalized[name] = {
            "matrix": None,
            "source": r.get("source", "unaligned"),
            "reason": r.get("reason"),
        }
        continue

    a, b, tx = M[0]
    c, d, ty = M[1]
    M_norm = [[a, b, tx / unit], [c, d, ty / unit]]
    normalized[name] = {
        "matrix": M_norm,
        "scale": r.get("scale"),
        "rotation_deg": r.get("rotation_deg"),
        "tx": tx / unit,
        "ty": ty / unit,
        "src_aspect": (r["src_w"] / r["src_h"]) if r.get("src_w") and r.get("src_h") else None,
        "source": r.get("source"),
    }

out = {
    "reference": data["reference"],
    "calibration_unit_px": unit,
    "stats": data.get("stats", {}),
    "coordinate_system": (
        "Square canvas, normalized to unit length 1.0. "
        "tx and ty are fractions of the canvas edge. "
        "To apply at canvas size K (square): scale tx, ty by K. "
        "a, b, c, d are dimensionless (rotation + uniform scale ratio) "
        "and apply unchanged at any resolution."
    ),
    "items": normalized,
}

with open(OUT, "w") as f:
    json.dump(out, f, indent=2)

aligned = sum(1 for r in normalized.values() if r["matrix"] is not None)
print(f"Wrote {OUT}")
print(f"  {aligned}/{len(normalized)} items normalized")
print(f"  calibration unit: {unit}px (square canvas)")
