# RISHI Publisher

One tool that takes a **batch** of finished episodes and publishes them to **YouTube, Facebook, Instagram and the website** together. Python 3.9+ standard library only; needs `ffmpeg`/`ffprobe` and `git` on PATH.

## The app (no terminal)
Double-click **`RISHI_Publisher.bat`** (or `python rishi_app.py`; `build_exe.bat` makes a standalone `RISHI_Publisher.exe`).
1. **Settings** - paste the platform keys, *Save*, then *Check tools and keys*.
2. **Batch** - *New batch from folder...*, set the first slot and episodes/day, double-click cells to fill in title, series, tags and times, *Save batch*.
3. **Publish** - tick platforms, then *Validate* -> *Dry run* -> *Publish now*. *Keep running until done* re-checks every 5 minutes so Instagram posts go out at their slot (leave the PC on). The table and log update live.

## Command line (same engine)
1. `copy .env.example .env` and fill in the keys (see *Credentials*). Run `python rishi_publisher.py doctor`.
2. Put the episode `.mp4` files in a folder (names like `rishi_ep034_part1_instagram.mp4`).
3. `python rishi_publisher.py scan "R:\INSTA\output\next" --start "2026-10-20 10:40"` writes `batch.json` with ep/part/file/publish time (1 episode/day, parts one minute apart; `--eps-per-day` to change).
4. Open `batch.json`, fill in `title`, `series_title`, `tags` for each item.
5. `python rishi_publisher.py validate batch.json`, then `python rishi_publisher.py run batch.json --dry-run`, then for real:
   `python rishi_publisher.py run batch.json --push --batch-size 10 --watch`

Alternatively `python rishi_publisher.py ui batch.json --push` opens a browser dashboard at http://127.0.0.1:8765 with *Publish batch* and *Dry run* buttons and live per-platform status.

## Phases (each batch)
| # | Phase | What happens |
|---|-------|--------------|
| 1 | Scan | `scan` builds the manifest from filenames |
| 2 | Validate | file exists, readable, vertical 9:16, h264, <= 90 s, < 1 GB, titles and times valid, no duplicates. Any error stops the run before anything is uploaded |
| 3 | Plan | sorts by publish time, splits into sub-batches (`--batch-size`), applies the YouTube daily cap |
| 4 | Publish | YouTube, Facebook and Instagram upload **in parallel** (`--workers`) per item |
| 5 | Website | thumbnail, `data/videos.json`, `supabase/seed.sql`, git commit + push -> Vercel redeploys |
| 6 | Report | per-item, per-platform status table |

Safe to stop and re-run at any time: progress is saved to `state/<batch>.json` after every step; finished steps are never repeated. `--only youtube,website` limits platforms; `status batch.json` prints the table.

## How scheduling works
- **YouTube**: uploaded now as private with `publishAt` = your slot (IST converted to UTC); goes public by itself.
- **Facebook**: Reel is uploaded with `SCHEDULED` + the slot time.
- **Instagram**: the Graph API cannot schedule Reels, so the item shows `waiting` and is published when its slot is due. Run with `--watch` (checks every `--interval` seconds) or re-run it on a schedule (Task Scheduler).
- **Website**: entries are added immediately; the site hides an episode until its publish time. When Instagram/YouTube links appear later, the next pass back-fills them into `videos.json`.

## Credentials (one-time)
- **YouTube**: Google Cloud project -> enable *YouTube Data API v3* -> OAuth client (Desktop) -> authorise once with scope `https://www.googleapis.com/auth/youtube.upload` and keep the refresh token. **Limits:** the default quota (10,000 units, ~1,600 per upload) allows about **6 uploads/day**, so `--yt-daily-limit` defaults to 6 and extra items show `deferred` and continue on the next day's run (request a quota increase for more). Videos uploaded through an API project that hasn't passed Google's audit are forced to **private**; submit the audit form before relying on scheduled public releases.
- **Facebook**: a long-lived **Page** access token with `pages_manage_posts` and `pages_read_engagement`, plus the numeric Page ID.
- **Instagram**: Business/Creator account linked to the Page; token with `instagram_content_publish`; the Instagram user ID (not the username). Reels: 9:16, <= 90 s.
- Tokens expire (Meta long-lived tokens ~60 days). `doctor` flags a rejected Facebook token; a failed item shows the API error in `status` and is retried on the next run.

## Not done / know before you rely on it
- The window was tested under a virtual display on Linux only; the Windows launcher and the `.exe` build were not run.
- The platform calls were tested against **mocked responses only** (no real accounts were available when this was built). Do the first run with 1 item on real accounts and check each platform.
- Comments, first-comment hashtags, YouTube custom thumbnails for Shorts, and the weekly compilations are not handled.
- `--push` publishes whatever changed in `data/`, `supabase/`, `thumbs/`; if you use Supabase for the episode list, also run the regenerated `supabase/seed.sql` there.
