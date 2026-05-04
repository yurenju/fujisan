"""SIFT + ORB fallback alignment with CLAHE preprocessing.
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

# Sanity bounds — outside these we treat as failure.
# We trust the transform itself more than the inlier count: a plausible scale
# with a tiny rotation is a strong signal RANSAC locked onto something real,
# even with few inliers (e.g. when the photo overlaps the reference only
# partially due to different framing/zoom).
MIN_SCALE, MAX_SCALE = 0.3, 5.0
MAX_ROTATION_DEG = 10.0
MIN_INLIERS = 3
LOWE_RATIO = 0.8


# CLAHE pulls detail out of dark/silhouetted regions (e.g. sunset buildings),
# giving SIFT/ORB more keypoints in the parts of the photo we actually want
# to match (the buildings, not the smooth sky gradient).
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))


def preprocess(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return clahe.apply(gray)


ref = cv2.imread(str(SRC / REF_NAME))
H, W = ref.shape[:2]
print(f"Reference: {REF_NAME}  size={W}x{H}")

ref_proc = preprocess(ref)

sift = cv2.SIFT_create(nfeatures=4000)
orb = cv2.ORB_create(nfeatures=4000)

# Mask out the top half of the reference: clouds and sky generate many SIFT
# keypoints that drift between photos, drowning the real landmarks (buildings,
# pylons, horizon) in noise. Restricting reference keypoints to the bottom
# half forces matching against stable structure.
ref_mask = np.zeros((H, W), dtype=np.uint8)
ref_mask[H // 2:, :] = 255

kp_ref_sift, des_ref_sift = sift.detectAndCompute(ref_proc, ref_mask)
kp_ref_orb, des_ref_orb = orb.detectAndCompute(ref_proc, ref_mask)
print(f"Reference keypoints: SIFT={len(kp_ref_sift)}  ORB={len(kp_ref_orb)}")

# FLANN for SIFT (float), brute force Hamming for ORB (binary)
flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=64))
bf_orb = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)


def estimate_transform(kp, des, kp_ref, des_ref, matcher, knn=True):
    """Returns dict with status/reason and transform fields, or None for hard fail."""
    if des is None or len(kp) < 20:
        return {"status": "fail", "reason": "too_few_keypoints", "keypoints": len(kp) if kp else 0}

    raw = matcher.knnMatch(des, des_ref, k=2)
    good = []
    for pair in raw:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < LOWE_RATIO * n.distance:
            good.append(m)

    if len(good) < 4:
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
    }

    if n_in < MIN_INLIERS:
        return {**info, "status": "fail", "reason": "too_few_inliers"}

    # Two-tier sanity bounds: with many inliers we trust the transform even
    # at extremes (e.g. heavy zoom). With few inliers, RANSAC can lock onto
    # a degenerate fit, so require the transform to match the typical pattern
    # (most photos sit at scale 0.5–2.5, rot near zero — handheld tilt is small).
    if n_in >= 8:
        s_min, s_max, r_max = MIN_SCALE, MAX_SCALE, MAX_ROTATION_DEG
    else:
        s_min, s_max, r_max = 0.5, 2.5, 3.0

    if not (s_min <= scale <= s_max):
        return {**info, "status": "fail", "reason": "scale_out_of_range"}
    if abs(rot_deg) > r_max:
        return {**info, "status": "fail", "reason": "rotation_out_of_range"}

    return {**info, "status": "ok"}


def align_one(img_path):
    img = cv2.imread(str(img_path))
    proc = preprocess(img)

    kp_s, des_s = sift.detectAndCompute(proc, None)
    sift_res = estimate_transform(kp_s, des_s, kp_ref_sift, des_ref_sift, flann)

    if sift_res["status"] == "ok":
        return {**sift_res, "detector": "sift", "src_w": img.shape[1], "src_h": img.shape[0]}

    # Fallback: ORB sometimes succeeds where SIFT fails on low-contrast/silhouette
    kp_o, des_o = orb.detectAndCompute(proc, None)
    orb_res = estimate_transform(kp_o, des_o, kp_ref_orb, des_ref_orb, bf_orb)

    if orb_res["status"] == "ok":
        return {**orb_res, "detector": "orb", "src_w": img.shape[1], "src_h": img.shape[0]}

    # Both failed — return whichever has more diagnostic info, prefer SIFT
    chosen = sift_res if "matrix" in sift_res else orb_res
    return {**chosen, "detector": "sift+orb_failed",
            "src_w": img.shape[1], "src_h": img.shape[0]}


files = sorted(SRC.glob("*.jpg"))
results = {}
t0 = time.time()

for i, f in enumerate(files, 1):
    r = align_one(f)
    results[f.name] = r
    tag = "OK  " if r["status"] == "ok" else "FAIL"
    extra = ""
    if "scale" in r:
        extra = f"  scale={r['scale']:.3f}  rot={r['rotation_deg']:+.2f}  in={r.get('inliers','-')}  via={r.get('detector','')}"
    reason = "" if r["status"] == "ok" else f"  [{r['reason']}]"
    print(f"[{i:3d}/{len(files)}] {tag} {f.name}{extra}{reason}")

elapsed = time.time() - t0

ok_count = sum(1 for r in results.values() if r["status"] == "ok")
fail_count = len(results) - ok_count

via_count = {}
for r in results.values():
    if r["status"] == "ok":
        via_count[r.get("detector", "?")] = via_count.get(r.get("detector", "?"), 0) + 1

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
        "lowe_ratio": LOWE_RATIO,
    },
    "stats": {
        "total": len(files), "ok": ok_count, "fail": fail_count,
        "elapsed_sec": round(elapsed, 1),
        "ok_by_detector": via_count,
    },
    "fail_by_reason": {k: len(v) for k, v in fail_reasons.items()},
    "items": results,
}

with open(OUT_DIR / "alignments.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n=== Summary ===")
print(f"Total: {len(files)}  OK: {ok_count}  Fail: {fail_count}  ({elapsed:.1f}s)")
print(f"OK by detector: {via_count}")
print(f"Failure breakdown:")
for reason, names in fail_reasons.items():
    print(f"  {reason}: {len(names)}")
print(f"\nWrote: {OUT_DIR / 'alignments.json'}")
