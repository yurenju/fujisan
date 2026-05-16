"""Quick test: ORB feature matching to align photos to a reference.
Outputs aligned images + side-by-side comparison."""
from pathlib import Path
import cv2
import numpy as np
import json

ROOT = Path(__file__).parent
SRC = ROOT / "images-resized"
OUT = ROOT / "aligned-test"
OUT.mkdir(exist_ok=True)

# Reference image: clear Fuji + clear buildings, landscape
REF_NAME = "PXL_20250905_074912986.RAW-02.ORIGINAL.jpg"

# Test set: variety of conditions
TEST_NAMES = [
    "PXL_20250905_074912986.RAW-02.ORIGINAL.jpg",  # ref itself (sanity check)
    "PXL_20250905_074924593.RAW-02.ORIGINAL.jpg",  # close to ref time
    "PXL_20251029_073632657.RAW-02.ORIGINAL.jpg",  # sunset silhouette
    "PXL_20251101_014940448.RAW-02.ORIGINAL.jpg",
    "PXL_20251102_075737872.RAW-02.ORIGINAL.jpg",
    "PXL_20251110_080757847.RAW-02.ORIGINAL.jpg",
    "PXL_20251215_033057014.RAW-02.ORIGINAL.jpg",
    "PXL_20260126_074258124.RAW-02.ORIGINAL.jpg",  # portrait, sunset behind Fuji
    "PXL_20260126_074700138.RAW-02.ORIGINAL.jpg",  # portrait
    "PXL_20260201_001632855.RAW-02.ORIGINAL.jpg",
    "PXL_20260209_031345498.RAW-02.ORIGINAL.jpg",
]

# Output canvas: same size as reference
ref = cv2.imread(str(SRC / REF_NAME))
H, W = ref.shape[:2]
print(f"Reference: {REF_NAME}  size={W}x{H}")

orb = cv2.ORB_create(nfeatures=4000)
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
kp_ref, des_ref = orb.detectAndCompute(ref_gray, None)
print(f"Reference keypoints: {len(kp_ref)}")

results = {}

for name in TEST_NAMES:
    img = cv2.imread(str(SRC / name))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kp, des = orb.detectAndCompute(gray, None)
    if des is None or len(kp) < 20:
        print(f"[FAIL] {name}: too few features")
        continue

    # KNN match + Lowe ratio test
    raw = bf.knnMatch(des, des_ref, k=2)
    good = []
    for m_pair in raw:
        if len(m_pair) < 2:
            continue
        m, n = m_pair
        if m.distance < 0.75 * n.distance:
            good.append(m)

    if len(good) < 10:
        print(f"[FAIL] {name}: only {len(good)} good matches")
        continue

    src_pts = np.float32([kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    # Partial affine = similarity transform (translation + rotation + uniform scale)
    M, inliers = cv2.estimateAffinePartial2D(
        src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=3.0
    )
    if M is None:
        print(f"[FAIL] {name}: RANSAC failed")
        continue

    n_in = int(inliers.sum())
    a, b, tx = M[0]
    c, d, ty = M[1]
    scale = float(np.sqrt(a * a + b * b))
    rot_deg = float(np.degrees(np.arctan2(b, a)))

    print(
        f"[OK]   {name}: matches={len(good)} inliers={n_in}  "
        f"scale={scale:.3f}  rot={rot_deg:+.2f}deg  t=({tx:+.0f},{ty:+.0f})"
    )

    warped = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=(20, 20, 20))
    cv2.imwrite(str(OUT / f"aligned_{name}"), warped)

    # 50/50 blend with reference for visual check
    blend = cv2.addWeighted(ref, 0.5, warped, 0.5, 0)
    cv2.imwrite(str(OUT / f"blend_{name}"), blend)

    results[name] = {
        "matches": len(good), "inliers": n_in,
        "scale": scale, "rotation_deg": rot_deg, "tx": float(tx), "ty": float(ty),
        "matrix": M.tolist(),
    }

with open(OUT / "results.json", "w") as f:
    json.dump({"reference": REF_NAME, "items": results}, f, indent=2)

print(f"\nDone. Output: {OUT}")
