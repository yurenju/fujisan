"""Build poc/data.json from the resized image directory.

Sequences = days with >=7 sunset photos within a continuous burst (gap <= 5 min).
Top rest  = non-sequence photos before 15:00 JST.
Bottom rest = non-sequence photos at/after 15:00 JST. 05-04 forced to the very end.
"""
import json
import os
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG_DIR = os.path.join(ROOT, "alignment", "images-resized")
OUT = os.path.join(HERE, "data.json")

MIN_SEQ = 7
GAP_SEC = 300
SUNSET_HOUR_RANGE = (16, 18)


def parse_dt(name):
    p = name.split("_")
    d, t = p[1], p[2][:6]
    return datetime(
        int(d[:4]), int(d[4:6]), int(d[6:8]),
        int(t[:2]), int(t[2:4]), int(t[4:6]),
        tzinfo=timezone.utc,
    ).astimezone(JST)


def main():
    files = sorted(f for f in os.listdir(IMG_DIR) if f.endswith(".jpg"))

    by_day = {}
    for f in files:
        dt = parse_dt(f)
        by_day.setdefault(dt.date(), []).append((dt, f))
    for day in by_day:
        by_day[day].sort()

    # Find ≥MIN_SEQ-photo bursts in sunset window
    sequences = []
    in_seq = set()
    for day in sorted(by_day):
        pts = [(dt, f) for dt, f in by_day[day] if SUNSET_HOUR_RANGE[0] <= dt.hour < SUNSET_HOUR_RANGE[1]]
        if not pts:
            continue
        bursts = [[pts[0]]]
        for prev, cur in zip(pts, pts[1:]):
            if (cur[0] - prev[0]).total_seconds() > GAP_SEC:
                bursts.append([cur])
            else:
                bursts[-1].append(cur)
        for b in bursts:
            if len(b) >= MIN_SEQ:
                sequences.append({
                    "date": day.isoformat(),
                    "start": b[0][0].strftime("%H:%M:%S"),
                    "end": b[-1][0].strftime("%H:%M:%S"),
                    "photos": [f for _, f in b],
                })
                in_seq.update(f for _, f in b)

    rest = [f for f in files if f not in in_seq]
    top, bottom = [], []
    for f in rest:
        (top if parse_dt(f).hour < 15 else bottom).append(f)
    top.sort(key=parse_dt)
    bottom.sort(key=parse_dt)

    # Force the May 4 ink-wash photo to the far end of bottom row.
    ink = [f for f in bottom if "20260504" in f]
    bottom = [f for f in bottom if "20260504" not in f] + ink

    data = {
        "imageBase": "../alignment/images-resized/",
        "sequences": sequences,
        "topRest": top,
        "bottomRest": bottom,
    }
    with open(OUT, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)

    print(f"Sequences: {len(sequences)}")
    for s in sequences:
        print(f'  {s["date"]}  {s["start"]}-{s["end"]}  {len(s["photos"])} photos')
    print(f"Top rest: {len(top)}")
    print(f"Bottom rest: {len(bottom)} (ink-wash anchored last: {len(ink)})")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
