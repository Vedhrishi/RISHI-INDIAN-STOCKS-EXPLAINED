import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


RSS_FEED_URL = os.getenv("RSS_FEED_URL", "https://feeds.bbci.co.uk/news/technology/rss.xml")
NICHE_HINT = os.getenv("NICHE_HINT", "technology news for a general audience")

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "private")
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "28")
CLIENT_SECRETS_FILE = BASE_DIR / os.getenv("CLIENT_SECRETS_FILE", "client_secret.json")
TOKEN_FILE = BASE_DIR / os.getenv("TOKEN_FILE", "token.json")

FONT_PATH = os.getenv("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
NOTIFY_WEBHOOK = os.getenv("NOTIFY_WEBHOOK", "")

STATE_FILE = BASE_DIR / "state" / "used.json"
OUTPUT_DIR = BASE_DIR / "output"
VIDEO_SIZE = (1920, 1080)
FPS = 24


def anthropic_key():
    return _req("ANTHROPIC_API_KEY")


def elevenlabs_key():
    return _req("ELEVENLABS_API_KEY")


def pexels_key():
    return _req("PEXELS_API_KEY")
