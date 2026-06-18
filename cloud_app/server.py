"""ceotuko cloud poster — runs 24/7 on Railway.

Polls a Dropbox folder for new videos (the cloud equivalent of the local
watch-folder). Each new video shows up as a "pending" item on a small
password-protected web dashboard, where you fill in the optional description
and choose a post time. From there it generates the caption with Claude and
posts to Instagram + TikTok at the chosen time.
"""
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import dropbox
from fastapi import FastAPI, Form, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.append(str(Path(__file__).resolve().parent.parent))
from common import config, poster  # noqa: E402

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
scheduler = BackgroundScheduler()
scheduler.start()

# in-memory state is fine here: a handful of pending clips at a time
pending: dict[str, dict] = {}
seen_paths: set[str] = set()


def poll_dropbox():
    if not config.DROPBOX_ACCESS_TOKEN:
        print("DROPBOX_ACCESS_TOKEN not set — cloud watcher disabled.")
        return
    dbx = dropbox.Dropbox(config.DROPBOX_ACCESS_TOKEN)
    while True:
        try:
            result = dbx.files_list_folder(config.DROPBOX_WATCH_FOLDER)
            for entry in result.entries:
                if entry.path_lower in seen_paths:
                    continue
                if not entry.name.lower().endswith((".mp4", ".mov", ".mkv", ".avi")):
                    continue
                seen_paths.add(entry.path_lower)
                item_id = str(uuid4())[:8]
                pending[item_id] = {
                    "dropbox_path": entry.path_display,
                    "filename": entry.name,
                    "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                print(f"New video found in Dropbox: {entry.name}")
        except Exception as e:
            print(f"Dropbox poll error: {e}")
        time.sleep(20)


def run_job(item_id: str, description: str, scheduled_for_str: str):
    item = pending.pop(item_id, None)
    if not item:
        return
    try:
        caption = poster.build_caption(description, item["filename"])
    except Exception as e:
        print(f"Caption generation failed for {item['filename']}: {e}")
        caption = item["filename"]
    poster.post_everywhere_from_dropbox(item["dropbox_path"], item["filename"], caption, scheduled_for_str)


def check_auth(session: str | None) -> bool:
    return bool(config.DASHBOARD_PASSWORD) and session == config.DASHBOARD_PASSWORD


@app.on_event("startup")
def startup():
    threading.Thread(target=poll_dropbox, daemon=True).start()


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request, session: str | None = Cookie(default=None)):
    if check_auth(session):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(password: str = Form(...)):
    if password == config.DASHBOARD_PASSWORD:
        resp = RedirectResponse("/dashboard", status_code=302)
        resp.set_cookie("session", password, httponly=True, max_age=60 * 60 * 24 * 30)
        return resp
    return RedirectResponse("/?error=1", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, session: str | None = Cookie(default=None)):
    if not check_auth(session):
        return RedirectResponse("/")
    return templates.TemplateResponse("dashboard.html", {"request": request, "pending": pending})


@app.post("/post/{item_id}")
def post_item(item_id: str, description: str = Form(""), post_time: str = Form("now"),
              session: str | None = Cookie(default=None)):
    if not check_auth(session):
        return RedirectResponse("/")

    if post_time.strip().lower() in ("", "now"):
        target = datetime.now()
    else:
        try:
            hh, mm = post_time.split(":")
            target = datetime.now().replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if target < datetime.now():
                target += timedelta(days=1)
        except Exception:
            target = datetime.now()

    if target <= datetime.now() + timedelta(seconds=5):
        threading.Thread(target=run_job, args=(item_id, description, "now")).start()
    else:
        scheduler.add_job(run_job, "date", run_date=target,
                           args=[item_id, description, target.isoformat()])
        pending[item_id]["scheduled_for"] = target.strftime("%Y-%m-%d %H:%M")

    return RedirectResponse("/dashboard", status_code=302)


@app.get("/health")
def health():
    return {"status": "ok"}
