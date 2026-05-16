"""Merge alignments.json + overrides.json into alignments-final.json.
Overrides take priority. The output is a single canonical source of truth
for downstream tooling — every photo has a final matrix and a 'source' field
recording where it came from."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).parent
ALIGN = ROOT / "aligned-all" / "alignments.json"
OVERRIDES = ROOT / "aligned-all" / "overrides.json"
OUT = ROOT / "aligned-all" / "alignments-final.json"


def params_to_matrix(p):
    r = math.radians(p["rot"])
    s = p["scale"]
    a = s * math.cos(r)
    b = s * math.sin(r)
    c = -s * math.sin(r)
    d = s * math.cos(r)
    return [[a, b, p["tx"]], [c, d, p["ty"]]]


def matrix_to_params(M):
    a, b, _ = M[0]
    c, d, _ = M[1]
    scale = math.sqrt(a * a + b * b)
    rot = math.degrees(math.atan2(b, a))
    return scale, rot


align = json.load(open(ALIGN))
overrides = json.load(open(OVERRIDES)) if OVERRIDES.exists() else {}

items = {}
n_manual = 0
n_auto = 0
n_unaligned = 0

for name, r in align["items"].items():
    if name in overrides:
        p = overrides[name]
        items[name] = {
            "matrix": params_to_matrix(p),
            "scale": p["scale"],
            "rotation_deg": p["rot"],
            "tx": p["tx"],
            "ty": p["ty"],
            "src_w": r.get("src_w"),
            "src_h": r.get("src_h"),
            "source": "manual",
        }
        n_manual += 1
    elif r.get("status") == "ok" and r.get("matrix"):
        scale, rot = matrix_to_params(r["matrix"])
        items[name] = {
            "matrix": r["matrix"],
            "scale": scale,
            "rotation_deg": rot,
            "tx": r["matrix"][0][2],
            "ty": r["matrix"][1][2],
            "src_w": r.get("src_w"),
            "src_h": r.get("src_h"),
            "source": "auto",
            "inliers": r.get("inliers"),
            "detector": r.get("detector"),
        }
        n_auto += 1
    else:
        items[name] = {
            "matrix": None,
            "src_w": r.get("src_w"),
            "src_h": r.get("src_h"),
            "source": "unaligned",
            "reason": r.get("reason"),
        }
        n_unaligned += 1

final = {
    "reference": align["reference"],
    "canvas": align["canvas"],
    "stats": {
        "total": len(items),
        "manual": n_manual,
        "auto": n_auto,
        "unaligned": n_unaligned,
    },
    "items": items,
}

with open(OUT, "w") as f:
    json.dump(final, f, indent=2)

print(f"Wrote {OUT}")
print(f"  total:     {len(items)}")
print(f"  manual:    {n_manual}")
print(f"  auto:      {n_auto}")
print(f"  unaligned: {n_unaligned}")
