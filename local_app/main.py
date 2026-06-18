"""ceotuko local poster — watches a folder on this PC, prompts you in the terminal,
generates a caption with Claude, and posts to Instagram + TikTok now or at a
scheduled time.

Run with:  python -m local_app.main
"""
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import config, poster  # noqa: E402

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi"}
scheduler = BackgroundScheduler()


def wait_until_stable(path: Path, checks: int = 3, interval: float = 1.0):
    """Wait until file size stops changing (download/copy finished)."""
    last_size = -1
    stable_count = 0
    while stable_count < checks:
        time.sleep(interval)
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            stable_count = 0
            continue
        if size == last_size:
            stable_count += 1
        else:
            stable_count = 0
        last_size = size


def parse_time_input(raw: str) -> datetime:
    raw = raw.strip().lower()
    if raw in ("", "now"):
        return datetime.now()
    try:
        hh, mm = raw.split(":")
        target = datetime.now().replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        if target < datetime.now():
            target += timedelta(days=1)
        return target
    except Exception:
        print(f"Couldn't parse '{raw}', posting now instead.")
        return datetime.now()


def run_job(video_path: str, description: str, scheduled_for_str: str):
    filename = Path(video_path).name
    print(f"\n[{datetime.now():%H:%M:%S}] Generating caption for {filename}...")
    try:
        caption = poster.build_caption(description, filename)
    except Exception as e:
        print(f"  Caption generation failed: {e}")
        return
    print(f"  Caption:\n  {caption}\n")

    print("  Posting to Instagram + TikTok...")
    results = poster.post_everywhere(video_path, filename, caption, scheduled_for_str)
    for platform, (ok, detail) in results.items():
        status = "OK" if ok else "FAILED"
        print(f"  [{platform.upper()}] {status}: {detail}")
    print(f"  Logged to {config.LOG_FILE}\n")


class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() not in VIDEO_EXTS:
            return

        print(f"\nNew video detected: {path.name}")
        print("Waiting for the file to finish copying...")
        wait_until_stable(path)

        description = input("Short description (optional, press Enter to skip): ").strip()
        time_raw = input("When should this post? ('now' or e.g. 19:00): ").strip()
        target_time = parse_time_input(time_raw)

        if target_time <= datetime.now() + timedelta(seconds=5):
            run_job(str(path), description, "now")
        else:
            print(f"Scheduled for {target_time:%Y-%m-%d %H:%M}")
            scheduler.add_job(run_job, "date", run_date=target_time,
                               args=[str(path), description, target_time.isoformat()])


def main():
    watch_folder = Path(config.WATCH_FOLDER)
    watch_folder.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print(" ceotuko auto-poster — running")
    print(f" Watching: {watch_folder}")
    print(" Drop a video file into that folder to begin.")
    print(" Press Ctrl+C to stop.")
    print("=" * 50)

    scheduler.start()
    observer = Observer()
    observer.schedule(VideoHandler(), str(watch_folder), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        scheduler.shutdown()
    observer.join()


if __name__ == "__main__":
    main()
