"""Helper to get a public direct-download URL for a local video file via Dropbox.

Instagram's Graph API requires a publicly reachable video URL — it will not accept
a raw file upload. We reuse your Dropbox account (the same one used for the
cloud-synced watch folder) as simple, free public hosting: upload the clip, create
a shared link, and rewrite it into a direct-download URL.
"""
import time
from pathlib import Path
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError
from . import config


def _client() -> dropbox.Dropbox:
    if not config.DROPBOX_ACCESS_TOKEN:
        raise RuntimeError("DROPBOX_ACCESS_TOKEN is not set in .env")
    return dropbox.Dropbox(config.DROPBOX_ACCESS_TOKEN)


def upload_and_get_public_url(local_path: str, dest_folder: str = "/ceotuko_public") -> str:
    dbx = _client()
    name = Path(local_path).name
    dest = f"{dest_folder}/{int(time.time())}_{name}"

    with open(local_path, "rb") as f:
        dbx.files_upload(f.read(), dest, mode=WriteMode("overwrite"))

    try:
        link = dbx.sharing_create_shared_link_with_settings(dest)
        url = link.url
    except ApiError:
        links = dbx.sharing_list_shared_links(path=dest, direct_only=True).links
        url = links[0].url

    # Dropbox share links open a preview page by default; dl=1 forces a raw stream,
    # which is what Instagram/TikTok need to actually fetch the video bytes.
    if "dl=0" in url:
        url = url.replace("dl=0", "dl=1")
    elif "?" not in url:
        url += "?dl=1"
    else:
        url += "&dl=1"
    return url


def get_public_url_for_existing(dropbox_path: str) -> str:
    """Same as above, but for a file already sitting in Dropbox (no re-upload)."""
    dbx = _client()
    try:
        link = dbx.sharing_create_shared_link_with_settings(dropbox_path)
        url = link.url
    except ApiError:
        links = dbx.sharing_list_shared_links(path=dropbox_path, direct_only=True).links
        url = links[0].url
    if "dl=0" in url:
        url = url.replace("dl=0", "dl=1")
    elif "?" not in url:
        url += "?dl=1"
    else:
        url += "&dl=1"
    return url


def download_to_temp(dropbox_path: str, dest_dir: str) -> str:
    dbx = _client()
    name = Path(dropbox_path).name
    dest = str(Path(dest_dir) / name)
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        metadata, res = dbx.files_download(dropbox_path)
        f.write(res.content)
    return dest
