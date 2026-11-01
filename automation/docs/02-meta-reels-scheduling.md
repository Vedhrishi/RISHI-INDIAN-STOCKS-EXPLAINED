# Scheduling Instagram + Facebook Reels (Meta Business Suite)

This is the exact flow used to keep a 2-Reels-a-day calendar filled up to Meta's limit, driven by
[Claude Code](https://claude.com/claude-code) with the **Claude in Chrome** extension controlling your own,
already-logged-in browser. No Meta developer app or API token is needed, which also means nothing here
breaks when a token expires.

> **Heads up.** This drives the Business Suite web UI. Meta can change that UI at any time, so treat the
> coordinates and quirks below as a starting point, and re-check each step with a screenshot. For a
> production setup the official Graph API is the more stable route (needs an app, review and
> long-lived tokens). Read Meta's platform terms before automating anything on your accounts.

## What you need
- An Instagram **professional** account linked to a Facebook Page (so one composer posts to both).
- Business Suite access: https://business.facebook.com/latest/home
- Claude Code with the Claude in Chrome extension connected to the Chrome profile where you are logged in.
- Rendered vertical videos (1080x1920, MP4, each **under 10 MB** for the browser upload tool) and a caption per video.

## The rule that shapes everything: the 29-day window
Business Suite accepts a scheduled Reel only between **20 minutes and 29 days** from the moment you create it.
So you can never schedule a whole season at once. Each day roughly two new slots open, and you top the
calendar up on a rolling basis. "Schedule till the limit ends" means: fill every slot up to
`now + 29 days`, then stop.

## One Reel, step by step
1. Open `https://business.facebook.com/latest/reels_composer/?asset_id=<PAGE_ID>&business_id=<BUSINESS_ID>`
   (your IDs are in the URL when you open Business Suite normally).
2. **Make the file input reachable.** The page creates its `<input type=file>` on the fly and never attaches it.
   Run this once per page load, then click **Add video**:
   ```js
   HTMLInputElement.prototype.click = function () {
     if (this.type === 'file') {
       if (!this.isConnected) document.body.appendChild(this);
       this.style.cssText = 'display:block;position:fixed;top:0;left:0;z-index:99999';
       return;
     }
     return HTMLElement.prototype.click.apply(this, arguments);
   };
   ```
3. Upload the file with the extension's `file_upload` tool (target the file input).
   Copy the video to a temp folder first; files that are hard-linked by a cloud-sync client can be rejected.
4. Scroll the form down and click the **Text** box, then type the caption (see
   [03-reach-playbook.md](03-reach-playbook.md)). Type with the keyboard action; injecting text with script
   scrambles the editor. Check the end of the caption afterwards: the last hashtag is the first thing to go missing.
5. **Next** -> **Edit** step: confirm no music was added ("Add audio" stays empty) and the copyright check passes.
6. **Next** -> **Share** step. The bottom button says **Share**, and pressing it publishes **now**.
   Do not press it yet. Scroll to **Scheduling options** and click the **Schedule** tab first; the button then reads **Schedule**.
7. Set the date and time. The composer shows **separate** Facebook and Instagram rows, so set both:
   - Date: triple-click the field, take a screenshot/zoom (otherwise the keystrokes are sometimes ignored),
     then type `dd/mm/yyyy`.
   - Time: typing `1900` into the time box does not work. Click the **hour** segment and press the keys
     `1` then `9`; click the **minutes** segment and press `0` then `0`. The minutes default to the current minute, so always set them.
   - Zoom into the section and confirm **both rows** show the right date and time before continuing.
8. Click **Schedule**. A dialog confirms: *"Your reel is scheduled to publish on <date> on Facebook and <date> on Instagram."*

## Verify the whole calendar
Open **Content -> Posts and reels -> Scheduled**. The list loads lazily, so collect rows while it loads:
[`verify_scheduled.js`](../meta_scheduler/verify_scheduled.js) scrolls the list, gathers every date/time, and
reports missing and unexpected slots against your cadence. Run it in the page (or through the extension's
JavaScript tool). The **Published** tab confirms what already went out.

## Files in this folder
| File | Purpose |
|---|---|
| [`meta_scheduler/schedule_prompt.md`](../meta_scheduler/schedule_prompt.md) | Copy-paste prompt that makes Claude Code do the routine end to end |
| [`meta_scheduler/verify_scheduled.js`](../meta_scheduler/verify_scheduled.js) | Collects and checks every scheduled slot |
| [`meta_scheduler/build_manifest.py`](../meta_scheduler/build_manifest.py) | Generates the slot list (episode, part, date, time, file) |
| [`meta_scheduler/caption_template.md`](../meta_scheduler/caption_template.md) | Reach-oriented caption layout |

## Known pitfalls (all hit in practice)
- **Share vs Schedule.** Always click the Schedule tab before the final button.
- **Silent date failures.** A tooltip or a too-fast click can swallow the date; one of the two rows may stay on today. Always zoom and read both rows.
- **Duplicates.** Before scheduling a slot, check the Scheduled list so you never create a second post for the same time.
- **Tokens expire, the browser session does not.** If you also run a Graph-API-based publisher, its token can be invalidated (for example after a password change); the browser route is the fallback.
- **"Share to Facebook story"** is switched on by default in the composer. Decide once whether you want it and keep it consistent.
