# RISHI | Indian Stocks Explained

**Live site:** https://rishi-indian-stocks-explained.vercel.app

A content platform for an animated financial-literacy series: **365 daily episodes (730 short videos)** that explain savings, tax, scams, insurance and investing to Indian families through recurring characters (Rishi, Priya, Paati, Murugan, Ravi). The site gathers the series across Instagram, YouTube and Facebook.

## Highlights
- **Automated video pipeline (Python + Pillow + FFmpeg/NVENC):** procedurally animated 80-second vertical episodes with TTS narration and subtitles; 52 auto-generated 16:9 weekly compilations with chapters and thumbnails.
- **Multi-platform publishing:** per-platform caption/metadata generators (Instagram, YouTube Shorts with SEO tags, Facebook Reels) and scheduled automation keeping each calendar filled.
- **Website (this repo):** static, dependency-free front end (HTML/CSS/vanilla JS) deployed on **Vercel**; optional **Supabase** backend (Postgres + Row Level Security) for live episode data and a course waitlist.
- Release-aware episode grid (episodes appear after their posting time), topic search, weekly compilations, bonus "earn with skills" videos, and a locked course preview.

## Tech
HTML · CSS · JavaScript (ES modules) · Supabase (Postgres, RLS) · Vercel · Python · FFmpeg

## Structure
```
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
