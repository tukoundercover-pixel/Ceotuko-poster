"""Instagram API with Instagram Login — publish a Reel from a public video URL.

Uses the Instagram-scoped user access token directly (no Facebook Page Access
Token indirection): https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login
"""
import time
import requests
from . import config

GRAPH_BASE = "https://graph.instagram.com/v21.0"


class InstagramPostError(Exception):
    pass


def post_reel(video_url: str, caption: str) -> str:
    """Create + publish an IG Reels container. Returns the published media id."""
    if not config.IG_ACCESS_TOKEN or not config.IG_USER_ID:
        raise InstagramPostError("IG_ACCESS_TOKEN / IG_USER_ID missing from .env")

    create_url = f"{GRAPH_BASE}/{config.IG_USER_ID}/media"
    resp = requests.post(create_url, data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": config.IG_ACCESS_TOKEN,
    })
    data = resp.json()
    if "id" not in data:
        raise InstagramPostError(f"Container creation failed: {data}")
    container_id = data["id"]

    status_url = f"{GRAPH_BASE}/{container_id}"
    for _ in range(30):  # up to ~5 min: IG transcodes the video server-side
        status = requests.get(status_url, params={
            "fields": "status_code",
            "access_token": config.IG_ACCESS_TOKEN,
        }).json()
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise InstagramPostError(f"IG failed to process video: {status}")
        time.sleep(10)
    else:
        raise InstagramPostError("Timed out waiting for IG to finish processing the video")

    publish_url = f"{GRAPH_BASE}/{config.IG_USER_ID}/media_publish"
    pub_resp = requests.post(publish_url, data={
        "creation_id": container_id,
        "access_token": config.IG_ACCESS_TOKEN,
    }).json()
    if "id" not in pub_resp:
        raise InstagramPostError(f"Publish failed: {pub_resp}")
    return pub_resp["id"]
