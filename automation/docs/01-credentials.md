# Credentials: what you need and where to get it

You bring your own keys. Nothing is bundled, and nothing leaves your machine except the calls you make to each provider.
Put values in `automation/youtube_pipeline/.env` (copy `.env.example`). `.env`, `token.json` and `client_secret.json` are git-ignored; never commit them.

| Service | Get it at | Notes |
|---|---|---|
| Anthropic (Claude) | console.anthropic.com -> API keys | Set a monthly spend limit. One script costs a few cents. |
| ElevenLabs | elevenlabs.io -> Profile -> API keys | About 2,500 characters per video. Check your plan's commercial-use terms. |
| Pexels | pexels.com/api | Free. 200 requests/hour. |
| YouTube Data API v3 | Google Cloud Console (below) | OAuth "Desktop app" client. |

## Google Cloud / YouTube upload setup
1. https://console.cloud.google.com -> create a project.
2. **APIs & Services -> Library** -> enable **YouTube Data API v3**.
3. **OAuth consent screen** (Google Auth Platform): user type **External**, add your email as a **test user**, add the scope `.../auth/youtube.upload`.
4. **Publish the app (In production).** In *Testing* mode, refresh tokens expire after **7 days** and the daily job silently stops working. A personal-use app does not need Google verification; you will see an "unverified app" screen once when you log in.
5. **Credentials -> Create credentials -> OAuth client ID -> Desktop app.** Download the JSON as `client_secret.json` into `automation/youtube_pipeline/`.
6. On a machine with a browser: `python auth_youtube.py`, log in as the channel owner, allow. This creates `token.json`.
7. **API audit lock:** videos uploaded through API projects created after July 2020 stay **private** until the project passes YouTube's API compliance audit (https://support.google.com/youtube/contact/yt_api_form). Until then, uploads work but are private; that is why `YOUTUBE_PRIVACY` defaults to `private`.
8. Quota: an upload costs 1,600 of the 10,000 free daily units. New channels also have a daily upload cap; verify the channel by phone to raise it.

## Instagram and Facebook
No API credentials. [02-meta-reels-scheduling.md](02-meta-reels-scheduling.md) uses your own logged-in browser session through Claude in Chrome.

## Safe handling
- Use a separate Google account/channel while you are testing.
- Rotate any key that ever appears in a commit, a screenshot or a chat.
- If a token suddenly stops working (`invalid_grant`, "session has been invalidated"), re-run the login step; do not retry in a loop.
