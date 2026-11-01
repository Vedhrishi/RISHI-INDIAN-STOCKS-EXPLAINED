# YouTube pipeline

RSS -> Claude (script + title/description/tags) -> ElevenLabs (voice + word timings) -> Pexels + MoviePy (video + burned-in subtitles) -> YouTube upload.

```
main.py          orchestrator (the cron / Task Scheduler entry point)
scraper.py       RSS + article text, de-duplication (state/used.json)
script_gen.py    Claude: script, title, description, tags, stock-footage queries
voice.py         ElevenLabs TTS with timestamps -> word-level timings
visuals.py       Pexels download, MoviePy assembly, subtitles
uploader.py      YouTube Data API v3 resumable upload (private by default)
auth_youtube.py  one-time OAuth login
doctor.py        pre-flight checklist (never prints secrets)
tests/           offline tests (word timing parser, full render with fake footage)
```

Setup: [../docs/01-credentials.md](../docs/01-credentials.md). Deploy: [../docs/04-deploy.md](../docs/04-deploy.md). Overview: [../README.md](../README.md).

Needs Python 3.10+ and `ffmpeg` on the PATH. Set `FONT_PATH` in `.env` to a `.ttf` file (Windows example: `C:/Windows/Fonts/arialbd.ttf`).
