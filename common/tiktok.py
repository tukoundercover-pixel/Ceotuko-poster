"""TikTok Content Posting API.

Unaudited apps can only post as PRIVATE drafts to the authenticated creator's
account (TikTok requires you to tap "Post" inside the app). Once your app
passes TikTok's Content Posting API audit, change PRIVACY_LEVEL below to
"PUBLIC_TO_EVERYONE" and posts go out fully automatically — no other code
changes needed.
"""
import time
import requests
from pathlib import Path
from . import config

PRIVACY_LEVEL = "SELF_ONLY"  # change to "PUBLIC_TO_EVERYONE" once TikTok approves your app

API_BASE = "https://open.tiktokapis.com/v2"


class TikTokPostError(Exception):
    pass


def _refresh_access_token() -> str:
    resp = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": config.TIKTOK_CLIENT_KEY,
            "client_secret": config.TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": config.TIKTOK_REFRESH_TOKEN,
        },
    ).json()
    if "access_token" not in resp:
        raise TikTokPostError(f"Could not refresh TikTok token: {resp}")
    return resp["access_token"]


def post_video(local_video_path: str, caption: str) -> str:
    if not config.TIKTOK_CLIENT_KEY or not config.TIKTOK_REFRESH_TOKEN:
        raise TikTokPostError("TikTok credentials missing from .env")

    access_token = _refresh_access_token()
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"}

    video_size = Path(local_video_path).stat().st_size

    init_resp = requests.post(
        f"{API_BASE}/post/publish/video/init/",
        headers=headers,
        json={
            "post_info": {
                "title": caption,
                "privacy_level": PRIVACY_LEVEL,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        },
    ).json()

    if "data" not in init_resp or "upload_url" not in init_resp["data"]:
        raise TikTokPostError(f"Init failed: {init_resp}")

    upload_url = init_resp["data"]["upload_url"]
    publish_id = init_resp["data"]["publish_id"]

    with open(local_video_path, "rb") as f:
        video_bytes = f.read()

    upload_resp = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        },
        data=video_bytes,
    )
    if upload_resp.status_code not in (200, 201):
        raise TikTokPostError(f"Video upload failed: {upload_resp.status_code} {upload_resp.text}")

    for _ in range(18):  # up to ~3 min
        status = requests.post(
            f"{API_BASE}/post/publish/status/fetch/",
            headers=headers,
            json={"publish_id": publish_id},
        ).json()
        state = status.get("data", {}).get("status")
        if state == "PUBLISH_COMPLETE":
            return publish_id
        if state == "FAILED":
            raise TikTokPostError(f"TikTok publish failed: {status}")
        time.sleep(10)

    raise TikTokPostError("Timed out waiting for TikTok to confirm publish")
