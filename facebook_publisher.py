"""Facebook Graph API publishing helpers."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v19.0")


def _graph_url(page_id: str, edge: str) -> str:
    return f"https://graph.facebook.com/{GRAPH_VERSION}/{page_id}/{edge}"


def handle_post_error(data: dict[str, Any] | Any) -> str:
    error = data.get("error") if isinstance(data, dict) else None
    if not error:
        return str(data)[:500]

    parts = [error.get("message", "Unknown Facebook error")]
    if error.get("code") is not None:
        parts.append(f"code={error.get('code')}")
    if error.get("error_subcode") is not None:
        parts.append(f"subcode={error.get('error_subcode')}")
    if error.get("fbtrace_id"):
        parts.append(f"fbtrace_id={error.get('fbtrace_id')}")
    return " | ".join(parts)


def _response_json(response: requests.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError:
        return {"error": {"message": response.text[:500], "code": response.status_code}}


def post_text(page_id: str, token: str, message: str, retries: int = 1) -> dict[str, Any]:
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                _graph_url(page_id, "feed"),
                data={"message": message, "access_token": token},
                timeout=30,
            )
            data = _response_json(response)
            print(f"  FB text response: {data}")
            if "id" in data:
                return {"success": True, "id": data["id"], "method": "text"}
            if attempt == retries:
                return {"success": False, "error": handle_post_error(data), "method": "text"}
        except Exception as exc:
            if attempt == retries:
                return {"success": False, "error": str(exc), "method": "text"}
    return {"success": False, "error": "Facebook text post failed", "method": "text"}


def post_image(page_id: str, token: str, img_bytes: bytes, caption: str, retries: int = 1) -> dict[str, Any]:
    for attempt in range(retries + 1):
        try:
            upload_response = requests.post(
                _graph_url(page_id, "photos"),
                data={"access_token": token, "published": "false"},
                files={"source": ("post.jpg", img_bytes, "image/jpeg")},
                timeout=45,
            )
            upload_data = _response_json(upload_response)
            photo_id = upload_data.get("id")
            if not photo_id:
                if attempt == retries:
                    print(f"  Photo upload failed: {handle_post_error(upload_data)}")
                    return post_text(page_id, token, caption)
                continue

            print(f"  Photo uploaded: {photo_id}")
            feed_response = requests.post(
                _graph_url(page_id, "feed"),
                data={
                    "message": caption,
                    "published": "true",
                    "attached_media[0]": json.dumps({"media_fbid": photo_id}),
                    "access_token": token,
                },
                timeout=30,
            )
            feed_data = _response_json(feed_response)
            if "id" in feed_data:
                print(f"  Feed post created: {feed_data['id']}")
                return {"success": True, "id": feed_data["id"], "method": "image"}
            if attempt == retries:
                return {
                    "success": False,
                    "error": f"Photo uploaded but feed post failed: {handle_post_error(feed_data)}",
                    "photo_id": photo_id,
                    "method": "image",
                }
        except Exception as exc:
            if attempt == retries:
                return {"success": False, "error": str(exc), "method": "image"}
    return {"success": False, "error": "Facebook image post failed", "method": "image"}


def merge_slides(slides: list[bytes]) -> bytes:
    from PIL import Image
    import io

    target_w = 1080
    images = []
    for slide in slides:
        try:
            img = Image.open(io.BytesIO(slide)).convert("RGB")
            if img.width != target_w:
                ratio = target_w / img.width
                img = img.resize((target_w, int(img.height * ratio)), Image.LANCZOS)
            images.append(img)
        except Exception as exc:
            print(f"  Slide merge warning: {exc}")

    if not images:
        return b""

    merged = Image.new("RGB", (target_w, sum(img.height for img in images)), (13, 13, 13))
    y = 0
    for img in images:
        merged.paste(img, (0, y))
        y += img.height

    buffer = io.BytesIO()
    merged.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def post_carousel(page_id: str, token: str, slides: list[bytes], caption: str) -> dict[str, Any]:
    if not slides:
        return {"success": False, "error": "No carousel slides generated", "method": "carousel"}

    photo_ids = []
    for index, img_bytes in enumerate(slides):
        try:
            response = requests.post(
                _graph_url(page_id, "photos"),
                data={"access_token": token, "published": "false"},
                files={"source": (f"slide_{index + 1}.jpg", img_bytes, "image/jpeg")},
                timeout=45,
            )
            data = _response_json(response)
            photo_id = data.get("id")
            if photo_id:
                photo_ids.append(photo_id)
                print(f"  Slide {index + 1} uploaded: {photo_id}")
            else:
                print(f"  Slide {index + 1} failed: {handle_post_error(data)}")
        except Exception as exc:
            print(f"  Slide {index + 1} exception: {exc}")

    if photo_ids:
        payload = {"message": caption, "access_token": token}
        for index, photo_id in enumerate(photo_ids):
            payload[f"attached_media[{index}]"] = json.dumps({"media_fbid": photo_id})
        try:
            response = requests.post(_graph_url(page_id, "feed"), data=payload, timeout=30)
            data = _response_json(response)
            print(f"  FB carousel response: {data}")
            if "id" in data:
                return {"success": True, "id": data["id"], "method": "carousel"}
            print(f"  Carousel feed failed: {handle_post_error(data)}")
        except Exception as exc:
            print(f"  Carousel feed exception: {exc}")

    merged = merge_slides(slides)
    if merged:
        print("  Falling back to merged image")
        result = post_image(page_id, token, merged, caption)
        result.setdefault("method", "merged_image")
        return result

    return {"success": False, "error": "Carousel upload failed", "method": "carousel"}


post_text_to_facebook = post_text
post_image_to_facebook = post_image
post_carousel_to_facebook = post_carousel
