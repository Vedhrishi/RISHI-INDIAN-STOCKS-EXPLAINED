"""Pre-flight check: python doctor.py

Verifies Python, ffmpeg, the subtitle font, installed packages and which credentials
are filled in. It never prints secret values and never calls a paid API.
"""
import importlib
import os
import shutil
import sys
from pathlib import Path

import config

OK, BAD = "[ OK ]", "[FAIL]"
failed = 0


def check(label: str, ok: bool, hint: str = "") -> None:
    global failed
    print(f"{OK if ok else BAD} {label}" + ("" if ok else f"  ->  {hint}"))
    failed += 0 if ok else 1


check("Python 3.10+", sys.version_info >= (3, 10), "install Python 3.10 or newer")
check("ffmpeg on PATH", shutil.which("ffmpeg") is not None, "install ffmpeg (winget install ffmpeg / apt install ffmpeg)")
check(f"Subtitle font exists ({config.FONT_PATH})", Path(config.FONT_PATH).exists(),
      "set FONT_PATH in .env to any .ttf file, e.g. C:/Windows/Fonts/arialbd.ttf")

for mod in ("feedparser", "trafilatura", "anthropic", "requests", "moviepy", "PIL",
            "dotenv", "googleapiclient", "google_auth_oauthlib"):
    try:
        importlib.import_module(mod)
        check(f"import {mod}", True)
    except ImportError:
        check(f"import {mod}", False, "pip install -r requirements.txt")

for key in ("ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "PEXELS_API_KEY"):
    check(f"{key} is set", bool(os.getenv(key)), "add it to .env")
check("client_secret.json present", config.CLIENT_SECRETS_FILE.exists(),
      "download the OAuth Desktop client from Google Cloud (see docs/01-credentials.md)")
check("token.json present (YouTube login done)", config.TOKEN_FILE.exists(), "run: python auth_youtube.py")

print()
print("All set. Run: python main.py" if not failed else f"{failed} item(s) need attention before running main.py.")
sys.exit(1 if failed else 0)
