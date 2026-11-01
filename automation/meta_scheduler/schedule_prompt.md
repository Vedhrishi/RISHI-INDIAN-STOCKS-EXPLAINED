# Prompt for Claude Code: top up the Reels schedule

Copy everything in the block into Claude Code (with the Claude in Chrome extension connected and Business Suite
open in the logged-in Chrome profile). Replace the `<...>` values.

```
Top up my Instagram + Facebook Reels schedule in Meta Business Suite, up to Meta's 29-day limit.

Context
- Page/Instagram: <name>. Composer: https://business.facebook.com/latest/reels_composer/?asset_id=<PAGE_ID>&business_id=<BUSINESS_ID>
- Cadence: <2 per day, 07:00 and 19:00, Asia/Kolkata>
- Videos: <folder>, named <ep012_part1_slug_instagram.mp4>. Captions: <file>.
- Follow automation/docs/02-meta-reels-scheduling.md exactly. Caption layout: automation/meta_scheduler/caption_template.md.

Do
1. Read the Scheduled list (run automation/meta_scheduler/verify_scheduled.js) and find the last scheduled slot.
2. List the open slots between that slot and now + 29 days. Never schedule a slot that already exists.
3. For each open slot: copy the video to a temp folder, upload it, type the caption, confirm the Edit step has no music,
   click the Schedule tab (never "Share now"), set date and time on BOTH the Facebook and Instagram rows, zoom to
   confirm, then Schedule and wait for the confirmation dialog.
4. When done, re-run verify_scheduled.js for the full range, including today, and report missing or extra slots.

Rules
- Stop and ask if anything looks different from the runbook (login prompt, new dialog, a slot already filled).
- Do not change posts that are already scheduled. Do not publish anything immediately.
- Keep token use low: batch actions, prefer text/JS reads over screenshots, screenshot only to confirm dates and times.
```
