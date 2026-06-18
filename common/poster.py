"""Shared logic: generate caption, post to IG + TikTok, log results.
Used by both the local watcher and the cloud (Railway) worker.
"""
from . import caption as caption_mod
from . import instagram, tiktok, dropbox_link, logger


def build_caption(description: str, filename: str) -> str:
    return caption_mod.generate_caption(description, filename)


def post_everywhere(local_video_path: str, filename: str, caption: str, scheduled_for: str) -> dict:
    """Posts to Instagram and TikTok. Returns {"instagram": (ok, detail), "tiktok": (ok, detail)}."""
    results = {}

    try:
        public_url = dropbox_link.upload_and_get_public_url(local_video_path)
        media_id = instagram.post_reel(public_url, caption)
        results["instagram"] = (True, f"posted, media_id={media_id}")
        logger.log_post(filename, caption, scheduled_for, "instagram", "success", media_id)
    except Exception as e:
        results["instagram"] = (False, str(e))
        logger.log_post(filename, caption, scheduled_for, "instagram", "failed", str(e))

    try:
        publish_id = tiktok.post_video(local_video_path, caption)
        note = "posted (draft - open TikTok app to confirm)" if tiktok.PRIVACY_LEVEL == "SELF_ONLY" else "posted publicly"
        results["tiktok"] = (True, f"{note}, publish_id={publish_id}")
        logger.log_post(filename, caption, scheduled_for, "tiktok", "success", publish_id)
    except Exception as e:
        results["tiktok"] = (False, str(e))
        logger.log_post(filename, caption, scheduled_for, "tiktok", "failed", str(e))

    return results


def post_everywhere_from_dropbox(dropbox_path: str, filename: str, caption: str,
                                   scheduled_for: str, tmp_dir: str = "/tmp/ceotuko") -> dict:
    """Cloud variant: video already lives in Dropbox, so reuse it for the IG public
    URL instead of re-uploading, and download a temp copy for the TikTok byte upload."""
    results = {}

    try:
        public_url = dropbox_link.get_public_url_for_existing(dropbox_path)
        media_id = instagram.post_reel(public_url, caption)
        results["instagram"] = (True, f"posted, media_id={media_id}")
        logger.log_post(filename, caption, scheduled_for, "instagram", "success", media_id)
    except Exception as e:
        results["instagram"] = (False, str(e))
        logger.log_post(filename, caption, scheduled_for, "instagram", "failed", str(e))

    local_path = None
    try:
        local_path = dropbox_link.download_to_temp(dropbox_path, tmp_dir)
        publish_id = tiktok.post_video(local_path, caption)
        note = "posted (draft - open TikTok app to confirm)" if tiktok.PRIVACY_LEVEL == "SELF_ONLY" else "posted publicly"
        results["tiktok"] = (True, f"{note}, publish_id={publish_id}")
        logger.log_post(filename, caption, scheduled_for, "tiktok", "success", publish_id)
    except Exception as e:
        results["tiktok"] = (False, str(e))
        logger.log_post(filename, caption, scheduled_for, "tiktok", "failed", str(e))
    finally:
        if local_path:
            try:
                __import__("os").remove(local_path)
            except OSError:
                pass

    return results
