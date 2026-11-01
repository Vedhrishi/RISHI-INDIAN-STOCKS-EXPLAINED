# RISHI Autopilot: instructions for Claude Code

You are helping the user run this toolkit with **their own** accounts and keys.

## Layout
- `youtube_pipeline/` Python pipeline (RSS -> Claude script -> ElevenLabs voice -> Pexels + MoviePy -> YouTube upload). Run through `python rishi_setup.py run`, which uses the project's virtual environment.
- `meta_scheduler/` Instagram + Facebook Reels scheduling via Meta Business Suite in the user's Chrome (Claude in Chrome extension).
- `docs/` guides. Read `docs/02-meta-reels-scheduling.md` before touching Business Suite.

## Rules
- Never print, log or commit secrets (`.env`, `token.json`, `client_secret.json`). Check a key is set, never show its value.
- Never publish anything immediately. In Business Suite always pick the **Schedule** tab, never "Share now", and confirm date/time on both the Facebook and Instagram rows.
- Meta only accepts slots between 20 minutes and 29 days ahead; schedule up to that limit, then stop and verify with `meta_scheduler/verify_scheduled.js`.
- Do not change posts that are already scheduled. Stop and ask if the UI differs from the runbook.
- Keep token use low: batch actions, read text/JS instead of screenshots, screenshot only to confirm dates and times.

## When the user says...
- "set up" / "install": run `python rishi_setup.py doctor` and fix whatever fails (see `docs/01-credentials.md`).
- "make a video": `python rishi_setup.py run` (uploads as the privacy level set in `youtube_pipeline/.env`, default private).
- "schedule reels": ask for the Page/Business IDs (they are in the Business Suite URL), cadence, video folder and caption file, then follow `meta_scheduler/schedule_prompt.md`.
