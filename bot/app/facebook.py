"""מתאם ל-Graph API של פייסבוק.

המודול הזה רדום עד שיהיה דף עסקי וטוקן ב-.env. הוא קיים כדי שברגע שיהיה דף,
החיבור יהיה החלפת שני משתנים ולא כתיבה מחדש של המערכת.

מה שה-API הרשמי מאפשר (רק על הדף שלכם): פרסום פוסטים, קריאת תגובות, תגובה
פומבית, והודעה פרטית אחת למגיב בתוך 7 ימים (דורש אישור Meta).
מה שהוא לא מאפשר: קריאה או פרסום בקבוצות של אחרים. זה נסגר ב-2024.
"""
import json
import mimetypes
import uuid
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from .config import FB_API_VERSION, FB_PAGE_ID, FB_PAGE_TOKEN, facebook_enabled

GRAPH = "https://graph.facebook.com"


class FacebookNotConfigured(RuntimeError):
    pass


def _require() -> None:
    if not facebook_enabled():
        raise FacebookNotConfigured(
            "אין דף עסקי מחובר. מלאו FB_PAGE_ID ו-FB_PAGE_TOKEN בקובץ .env כדי להפעיל את החלק הזה."
        )


def _url(path: str) -> str:
    return f"{GRAPH}/{FB_API_VERSION}/{path.lstrip('/')}"


def _call(path: str, params: dict[str, Any] | None = None, method: str = "GET") -> dict[str, Any]:
    _require()
    payload = {**(params or {}), "access_token": FB_PAGE_TOKEN}
    if method == "GET":
        req = request.Request(_url(path) + "?" + parse.urlencode(payload), method="GET")
    else:
        req = request.Request(_url(path), data=parse.urlencode(payload).encode("utf-8"), method="POST")
    try:
        with request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"פייסבוק החזירה שגיאה ({exc.code}): {detail[:400]}") from exc


def _multipart(path: str, fields: dict[str, str], file_path: Path, file_field: str = "source") -> dict[str, Any]:
    _require()
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body = bytearray()
    for key, value in {**fields, "access_token": FB_PAGE_TOKEN}.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
    body += (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
        f"filename=\"{file_path.name}\"\r\nContent-Type: {mime}\r\n\r\n"
    ).encode()
    body += file_path.read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = request.Request(
        _url(path),
        data=bytes(body),
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"פייסבוק החזירה שגיאה ({exc.code}): {detail[:400]}") from exc


def verify() -> dict[str, Any]:
    """בדיקה שהטוקן חי ושייך לדף הנכון."""
    return _call(FB_PAGE_ID, {"fields": "id,name,followers_count"})


def publish_text(message: str) -> dict[str, Any]:
    return _call(f"{FB_PAGE_ID}/feed", {"message": message}, method="POST")


def publish_photo(image_path: Path, caption: str = "") -> dict[str, Any]:
    return _multipart(f"{FB_PAGE_ID}/photos", {"caption": caption, "published": "true"}, Path(image_path))


def list_posts(limit: int = 25) -> list[dict[str, Any]]:
    data = _call(f"{FB_PAGE_ID}/posts", {"fields": "id,message,created_time", "limit": limit})
    return data.get("data", [])


def list_comments(post_id: str, limit: int = 50) -> list[dict[str, Any]]:
    data = _call(
        f"{post_id}/comments",
        {"fields": "id,message,created_time,from{id,name},parent", "limit": limit, "order": "reverse_chronological"},
    )
    return data.get("data", [])


def reply_to_comment(comment_id: str, message: str) -> dict[str, Any]:
    return _call(f"{comment_id}/comments", {"message": message}, method="POST")


def private_reply(comment_id: str, message: str) -> dict[str, Any]:
    """הודעה פרטית אחת למגיב. חלון של 7 ימים, הודעה אחת בלבד לכל תגובה.

    דורש הרשאת pages_messaging שמאושרת ב-App Review אחרי אימות עסקי.
    """
    return _call(
        f"{FB_PAGE_ID}/messages",
        {"recipient": json.dumps({"comment_id": comment_id}), "message": json.dumps({"text": message})},
        method="POST",
    )
