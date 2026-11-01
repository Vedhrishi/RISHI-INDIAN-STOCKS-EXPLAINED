# RISHI | Indian Stocks Explained

**Live site:** https://rishi-indian-stocks-explained.vercel.app

A content platform for an animated financial-literacy series: **100 episodes (200 short videos), released twice daily** that explain savings, tax, scams, insurance and investing to Indian families through recurring characters (Rishi, Priya, Paati, Murugan, Ravi). The site gathers the series across Instagram, YouTube and Facebook.

## Highlights
- **Automated video pipeline (Python + Pillow + FFmpeg/NVENC):** procedurally animated 80-second vertical episodes with TTS narration and subtitles; weekly 16:9 compilations with chapters and thumbnails (planned).
- **Multi-platform publishing:** per-platform caption/metadata generators (Instagram, YouTube Shorts with SEO tags, Facebook Reels) and scheduled automation keeping each calendar filled.
- **Website (this repo):** static, dependency-free front end (HTML/CSS/vanilla JS) deployed on **Vercel**; optional **Supabase** backend (Postgres + Row Level Security) for live episode data and a course waitlist.
- Release-aware episode grid (episodes appear after their posting time), topic search, weekly compilations, bonus "earn with skills" videos, and a locked course preview.

## Tech
HTML · CSS · JavaScript (ES modules) · Supabase (Postgres, RLS) · Vercel · Python · FFmpeg

## Automation toolkit (download and run it with your own accounts)
The same workflow that produces and schedules this channel is packaged in [`automation/`](automation/):

- **YouTube pipeline** - RSS -> Claude script -> ElevenLabs voice -> Pexels + MoviePy video with subtitles -> YouTube upload, on a daily schedule.
- **Instagram + Facebook Reels scheduler** - Claude Code drives Meta Business Suite in your own browser, fills every slot up to Meta's 29-day limit and verifies the whole calendar.
- **Guides** - API keys and Google Cloud setup, reach playbook, deployment on Windows or a Linux server.

**Get it with one file and one command** (needs Python 3.10+ and ffmpeg):
```powershell
# Windows PowerShell
irm https://raw.githubusercontent.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED/master/automation/rishi_setup.py -OutFile rishi_setup.py; python rishi_setup.py
```
```bash
# macOS / Linux
curl -fsSLO https://raw.githubusercontent.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED/master/automation/rishi_setup.py && python3 rishi_setup.py
```
[Download `rishi_setup.py`](https://raw.githubusercontent.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED/master/automation/rishi_setup.py) | [Latest release (ZIP)](https://github.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED/releases/latest) | [Read the guide](automation/README.md) | [Browse the code](automation/)

You bring your own API keys; nothing is bundled. MIT licensed (the `automation/` folder only).

## Structure
```
automation/                                  downloadable automation toolkit (YouTube + Meta scheduling)
.github/workflows/ci.yml                     tests for the toolkit
index.html, styles.css, app.js, config.js   front end
data/videos.json                             generated episode data
supabase/schema.sql, supabase/seed.sql       database schema + seed
tools/build_data.py                          data generator
thumbs/, comp_thumbs/, media/                images and videos
```

## Run locally
`python -m http.server 8000` in this folder, then open http://localhost:8000

## Supabase
Run `supabase/schema.sql`, then `supabase/seed.sql`, in the Supabase SQL editor, then put the project URL and anon key in `config.js`.

*Educational content only. Not financial advice.*
