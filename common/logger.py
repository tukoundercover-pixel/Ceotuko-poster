import csv
from datetime import datetime
from pathlib import Path
from . import config

FIELDS = ["timestamp", "video_file", "caption", "scheduled_for", "platform", "status", "detail"]


def _ensure_log():
    path = Path(config.LOG_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(FIELDS)
    return path


def log_post(video_file: str, caption: str, scheduled_for: str, platform: str, status: str, detail: str = ""):
    path = _ensure_log()
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.now().isoformat(timespec="seconds"),
            video_file,
            caption.replace("\n", " | "),
            scheduled_for,
            platform,
            status,
            detail,
        ])
