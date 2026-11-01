# RISHI Automation Toolkit

How the **RISHI | Indian Stocks Explained** channel is produced and published on autopilot, packaged so you can run the
same workflow with **your own accounts and API keys**.

[![CI](https://github.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED/actions/workflows/ci.yml/badge.svg)](https://github.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## One file, one command
Download **one file**, [`rishi_setup.py`](rishi_setup.py), and run it. It needs only Python 3.10+ (and `ffmpeg`). It downloads the
toolkit, builds its own virtual environment, asks for **your own** keys, logs you in to YouTube, runs a health check and can schedule the daily job.

**Windows (PowerShell)**
```powershell
irm https://raw.githubusercontent.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED/master/automation/rishi_setup.py -OutFile rishi_setup.py; python rishi_setup.py
```
**macOS / Linux**
```bash
curl -fsSLO https://raw.githubusercontent.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED/master/automation/rishi_setup.py && python3 rishi_setup.py
```
Afterwards:
| Command | What it does |
|---|---|
| `python rishi_setup.py run` | make and upload one video now (private by default) |
| `python rishi_setup.py doctor` | health check |
| `python rishi_setup.py schedule` | (re)create the daily job |
| `python rishi_setup.py claude` | open Claude Code in the install folder to schedule Instagram/Facebook Reels |
| `python rishi_setup.py update` | get the newest toolkit, keeping your keys and login |

Everything installs into `~/rishi-autopilot` (change with `--dir`). Your keys stay in a local `.env` file and are never uploaded anywhere
except to the providers you configure. Read the script first if you like; it is one short file with no dependencies.

**Other ways to get it:** [latest release ZIP](https://github.com/Vedhrishi/RISHI-INDIAN-STOCKS-EXPLAINED/releases/latest) (what the script downloads), or `git clone` and open `automation/`.

## What is in the box
```
automation/
  youtube_pipeline/     RSS -> Claude script -> ElevenLabs voice -> Pexels + MoviePy video -> YouTube upload
  meta_scheduler/       Instagram + Facebook Reels scheduling with Claude Code + Claude in Chrome
  docs/                 credentials, scheduling runbook, reach playbook, deployment
```

```
          +---------------------------- youtube_pipeline (Python, runs daily) ----------------------------+
 RSS ---> | scraper -> script_gen (Claude) -> voice (ElevenLabs + word timings) -> visuals (Pexels, MoviePy) | --> YouTube
          +---------------------------------------------------------------------------------------------+
 videos + captions --> meta_scheduler (Claude Code drives Meta Business Suite in your Chrome) --> Instagram + Facebook
```

## Manual setup (YouTube pipeline), if you prefer not to use the installer
```bash
cd automation/youtube_pipeline
python -m venv venv && source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # fill in your keys (docs/01-credentials.md)
python auth_youtube.py                                 # one-time YouTube login
python doctor.py                                       # every line should say [ OK ]
python main.py                                         # first run uploads as PRIVATE
```
Then schedule it daily: [docs/04-deploy.md](docs/04-deploy.md).

## Quick start (Instagram + Facebook scheduling)
1. Install Claude Code and the Claude in Chrome extension; log in to Meta Business Suite in that Chrome profile.
2. Generate your slot list: `python meta_scheduler/build_manifest.py --videos ./videos --first-day 2026-11-02`.
3. Paste [`meta_scheduler/schedule_prompt.md`](meta_scheduler/schedule_prompt.md) into Claude Code with your values filled in.
4. Re-run verification any time with [`verify_scheduled.js`](meta_scheduler/verify_scheduled.js).

Full explanation: [docs/02-meta-reels-scheduling.md](docs/02-meta-reels-scheduling.md).

## Guides
| Guide | What it covers |
|---|---|
| [01 Credentials](docs/01-credentials.md) | Every API key, the Google Cloud/YouTube setup, the 7-day token trap, the API-audit private lock |
| [02 Meta scheduling](docs/02-meta-reels-scheduling.md) | The 29-day window, step-by-step flow, pitfalls, verification |
| [03 Reach playbook](docs/03-reach-playbook.md) | Hooks, caption layout, niche hashtags, how to test and measure |
| [04 Deploy](docs/04-deploy.md) | Windows Task Scheduler and a Linux server with cron |

## Responsible use
- You are responsible for your accounts and for following each platform's terms (YouTube, Meta, ElevenLabs, Pexels, Anthropic).
- The YouTube pipeline produces *drafts of original commentary*. Review before you make anything public.
- Financial content: educational only, never promise returns, disclose affiliate links, and follow your local rules (for example SEBI in India).
- Browser automation of a web UI can break whenever the UI changes. Verify with screenshots and re-check after Meta updates.

## Tests
```bash
cd automation/youtube_pipeline && pip install -r requirements-dev.txt && pytest -q
```
CI runs the same on every push.

## Contributing / security
Issues and pull requests are welcome. See [SECURITY.md](SECURITY.md) for how to report a vulnerability and what must never be committed.

## License
MIT for everything under `automation/` (see [LICENSE](LICENSE)). The rest of the repository is covered by the license in the repository root.
