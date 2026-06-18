import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")

IG_ACCESS_TOKEN = env("IG_ACCESS_TOKEN")
IG_USER_ID = env("IG_USER_ID")

TIKTOK_CLIENT_KEY = env("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = env("TIKTOK_CLIENT_SECRET")
TIKTOK_ACCESS_TOKEN = env("TIKTOK_ACCESS_TOKEN")
TIKTOK_REFRESH_TOKEN = env("TIKTOK_REFRESH_TOKEN")

WATCH_FOLDER = env("WATCH_FOLDER", str(Path.home() / "Videos" / "ceotuko_uploads"))
LOG_FILE = env("LOG_FILE", str(ROOT / "logs" / "post_log.csv"))

DROPBOX_ACCESS_TOKEN = env("DROPBOX_ACCESS_TOKEN")
DROPBOX_WATCH_FOLDER = env("DROPBOX_WATCH_FOLDER", "/ceotuko_uploads")
DASHBOARD_PASSWORD = env("DASHBOARD_PASSWORD")
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL")
