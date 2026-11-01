"""Generate a schedule manifest: which video goes to which slot.

Usage:
    python build_manifest.py --videos ./output --first-day 2026-11-02 --days 29 \
        --times 07:00 19:00 --out schedule_manifest.csv

Videos are matched by a file-name convention: ``<anything>_ep012_part1_<slug>_instagram.mp4``.
Episodes are scheduled in order, ``len(times)`` parts per day. Anything without a video is listed as MISSING
so you find the gap before Meta's 29-day window makes it expensive to fix.
"""
import argparse
import csv
import datetime as dt
import re
from pathlib import Path

PATTERN = re.compile(r"ep0*(\d+)_part(\d+)_.*_instagram\.mp4$", re.I)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", type=Path, required=True)
    ap.add_argument("--first-day", required=True, help="YYYY-MM-DD of the first slot")
    ap.add_argument("--first-episode", type=int, default=1)
    ap.add_argument("--days", type=int, default=29)
    ap.add_argument("--times", nargs="+", default=["07:00", "19:00"])
    ap.add_argument("--out", type=Path, default=Path("schedule_manifest.csv"))
    a = ap.parse_args()

    files = {}
    for f in a.videos.glob("*_instagram.mp4"):
        m = PATTERN.search(f.name)
        if m:
            files[(int(m.group(1)), int(m.group(2)))] = f.name

    day0 = dt.date.fromisoformat(a.first_day)
    rows, missing = [], 0
    for d in range(a.days):
        ep = a.first_episode + d
        for part, t in enumerate(a.times, start=1):
            name = files.get((ep, part), "MISSING")
            missing += name == "MISSING"
            rows.append({"episode": ep, "part": part, "date": (day0 + dt.timedelta(days=d)).isoformat(),
                         "time": t, "video_file": name})

    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} slots to {a.out} ({missing} missing videos)")


if __name__ == "__main__":
    main()
