"""Run SIFT-based alignment on all photos against a reference.
Outputs alignments.json and a failure report."""
from pathlib import Path
import cv2
import numpy as np
import json
import time

ROOT = Path(__file__).parent
SRC = ROOT / "images-resized"
OUT_DIR = ROOT / "aligned-all"
OUT_DIR.mkdir(exist_ok=True)

REF_NAME = "PXL_20250905_074912986.RAW-02.ORIGINAL.jpg"

# Sanity bounds — outside these we treat as failure
MIN_SCALE, MAX_SCALE = 0.25, 4.0
MAX_ROTATION_DEG = 15.0
MIN_INLIERS = 8
LOWE_RATIO = 0.75

ref = cv2.imread(str(SRC / REF_NAME))
H, W = ref.shape[:2]
print(f"Reference: {REF_NAME}  size={W}x{H}")

sift = cv2.SIFT_create(nfeatures=4000)
ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
kp_ref, des_ref = sift.detectAndCompute(ref_gray, None)
print(f"Reference SIFT keypoints: {len(kp_ref)}")

# FLANN matcher for SIFT (float descriptors)
index_params = dict(algorithm=1, trees=5)  # KDTree
search_params = dict(checks=64)
flann = cv2.FlannBasedMatcher(index_params, search_params)


def align_one(img_path):
    img = cv2.imread(str(img_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kp, des = sift.detectAndCompute(gray, None)
    if des is None or len(kp) < 20:
        return {"status": "fail", "reason": "too_few_keypoints", "keypoints": len(kp)}

    raw = flann.knnMatch(des, des_ref, k=2)
    good = []
    for pair in raw:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < LOWE_RATIO * n.distance:
            good.append(m)

    if len(good) < MIN_INLIERS:
        return {"status": "fail", "reason": "too_few_matches", "matches": len(good)}

    src_pts = np.float32([kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    M, inliers = cv2.estimateAffinePartial2D(
        src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=3.0
    )
    if M is None or inliers is None:
        return {"status": "fail", "reason": "ransac_failed", "matches": len(good)}

    n_in = int(inliers.sum())
    a, b, tx = M[0]
    c, d, ty = M[1]
    scale = float(np.sqrt(a * a + b * b))
    rot_deg = float(np.degrees(np.arctan2(b, a)))

    info = {
        "matches": len(good), "inliers": n_in,
        "scale": scale, "rotation_deg": rot_deg,
        "tx": float(tx), "ty": float(ty),
        "matrix": M.tolist(),
        "src_w": img.shape[1], "src_h": img.shape[0],
    }

    if n_in < MIN_INLIERS:
        return {**info, "status": "fail", "reason": "too_few_inliers"}
    if not (MIN_SCALE <= scale <= MAX_SCALE):
        return {**info, "status": "fail", "reason": "scale_out_of_range"}
    if abs(rot_deg) > MAX_ROTATION_DEG:
        return {**info, "status": "fail", "reason": "rotation_out_of_range"}

    return {**info, "status": "ok"}


files = sorted(SRC.glob("*.jpg"))
results = {}
t0 = time.time()

for i, f in enumerate(files, 1):
    r = align_one(f)
    results[f.name] = r
    tag = "OK  " if r["status"] == "ok" else "FAIL"
    extra = ""
    if "scale" in r:
        extra = f"  scale={r['scale']:.3f}  rot={r['rotation_deg']:+.2f}  in={r.get('inliers','-')}"
    reason = "" if r["status"] == "ok" else f"  [{r['reason']}]"
    print(f"[{i:3d}/{len(files)}] {tag} {f.name}{extra}{reason}")

elapsed = time.time() - t0

ok_count = sum(1 for r in results.values() if r["status"] == "ok")
fail_count = len(results) - ok_count

# Group failures by reason
fail_reasons = {}
for name, r in results.items():
    if r["status"] != "ok":
        fail_reasons.setdefault(r["reason"], []).append(name)

summary = {
    "reference": REF_NAME,
    "canvas": {"w": W, "h": H},
    "bounds": {
        "min_scale": MIN_SCALE, "max_scale": MAX_SCALE,
        "max_rotation_deg": MAX_ROTATION_DEG, "min_inliers": MIN_INLIERS,
    },
    "stats": {
        "total": len(files), "ok": ok_count, "fail": fail_count,
        "elapsed_sec": round(elapsed, 1),
    },
    "fail_by_reason": {k: len(v) for k, v in fail_reasons.items()},
    "items": results,
}

with open(OUT_DIR / "alignments.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n=== Summary ===")
print(f"Total: {len(files)}  OK: {ok_count}  Fail: {fail_count}  ({elapsed:.1f}s)")
print(f"Failure breakdown:")
for reason, names in fail_reasons.items():
    print(f"  {reason}: {len(names)}")
    for n in names:
        print(f"    - {n}")
print(f"\nWrote: {OUT_DIR / 'alignments.json'}")
