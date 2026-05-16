"""Plot the time-of-day vs date distribution of fuji photos as ASCII chart.

Usage:
    python distribution.py
    python distribution.py --bin 1     # 1-minute bins (wide)
    python distribution.py --bin 10    # 10-minute bins (compact)
    python distribution.py --zoom sunset    # focus on 16:00-17:30
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
IMAGE_DIR = os.path.join(os.path.dirname(__file__), "alignment", "images-resized")

# Density characters: 0..8+ photos in a single bin (ASCII-only for Windows compatibility)
DENSITY = " .:-=+*#@"
EMPTY = " "


def parse_filename(name):
    """PXL_YYYYMMDD_HHMMSSmmm... -> aware datetime in JST."""
    parts = name.split("_")
    d, t = parts[1], parts[2][:6]
    dt_utc = datetime(
        int(d[:4]), int(d[4:6]), int(d[6:8]),
        int(t[:2]), int(t[2:4]), int(t[4:6]),
        tzinfo=timezone.utc,
    )
    return dt_utc.astimezone(JST)


def load_photos():
    files = [f for f in os.listdir(IMAGE_DIR) if f.endswith(".jpg")]
    return sorted(parse_filename(f) for f in files)


def render(photos, hour_start, hour_end, bin_minutes):
    total_minutes = (hour_end - hour_start) * 60
    n_cols = total_minutes // bin_minutes

    by_day = defaultdict(list)
    for dt in photos:
        by_day[dt.date()].append(dt)

    days = sorted(by_day)

    # Header: hour markers
    header = [" " * 11]
    for col in range(n_cols):
        minute_offset = col * bin_minutes
        h = hour_start + minute_offset // 60
        m = minute_offset % 60
        if m == 0:
            header.append(f"|{h:02d}")
        elif col + 1 < n_cols and (col * bin_minutes + bin_minutes) % 60 == 0:
            pass
        else:
            header.append(" ")
    print("".join(header[:1] + [c for c in "".join(header[1:])][:n_cols]))

    # Tick row
    tick = [" " * 11]
    for col in range(n_cols):
        minute_offset = col * bin_minutes
        m = minute_offset % 60
        tick.append("|" if m == 0 else "-" if m == 30 else " ")
    print("".join(tick))

    # Rows per day
    for day in days:
        row = [f"{day.strftime('%m-%d %a')}  "]
        bins = [0] * n_cols
        for dt in by_day[day]:
            minute_of_day = dt.hour * 60 + dt.minute
            offset = minute_of_day - hour_start * 60
            if 0 <= offset < total_minutes:
                col = offset // bin_minutes
                bins[col] += 1
        for c in bins:
            if c == 0:
                row.append(EMPTY)
            elif c < len(DENSITY):
                row.append(DENSITY[c])
            else:
                row.append("@")
        n = len(by_day[day])
        row.append(f"  ({n})")
        print("".join(row))

    # Legend
    print()
    print(f"Bin: {bin_minutes} min  |  Range: {hour_start:02d}:00 - {hour_end:02d}:00 JST")
    print(f"Density: {' '.join(f'{i}={DENSITY[i] if i<len(DENSITY) else chr(0x40)}' for i in range(1,9))}  '{EMPTY}' = empty")
    print(f"Total: {len(photos)} photos across {len(days)} days")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", type=int, default=5, help="minutes per column (default 5)")
    ap.add_argument("--zoom", choices=["full", "sunset", "morning"], default="full")
    args = ap.parse_args()

    if args.zoom == "sunset":
        hour_start, hour_end = 16, 18
        if args.bin == 5:
            args.bin = 1
    elif args.zoom == "morning":
        hour_start, hour_end = 8, 14
    else:
        hour_start, hour_end = 8, 18

    photos = load_photos()
    if not photos:
        print(f"No photos found in {IMAGE_DIR}", file=sys.stderr)
        sys.exit(1)

    render(photos, hour_start, hour_end, args.bin)


if __name__ == "__main__":
    main()
