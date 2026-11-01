"""Run ONCE on a machine with a browser:  python auth_youtube.py
Creates token.json (contains a refresh token). Copy it to your server."""
from google_auth_oauthlib.flow import InstalledAppFlow

import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file(str(config.CLIENT_SECRETS_FILE), SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
config.TOKEN_FILE.write_text(creds.to_json())
print(f"Saved {config.TOKEN_FILE}")
