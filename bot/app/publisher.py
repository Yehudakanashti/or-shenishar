"""פרסום פוסטים מאושרים לדף הפייסבוק."""
from datetime import datetime
from typing import Any

from . import ai, db, facebook, policy, timing
from .config import UPLOAD_DIR


def create_draft(product_id: int, angle: str, scheduled_for: str = "", note: str = "") -> dict[str, Any]:
    product = db.get_product(product_id)
    if not product:
        return {"ok": False, "reason": "לא נמצא מוצר"}

    try:
        draft, meta = ai.draft_post(product, angle, note)
    except Exception as exc:  # noqa: BLE001
        db.log_event("ai_error", "שגיאה בניסוח פוסט", {"error": str(exc)[:600]})
        return {"ok": False, "reason": "שגיאה בקריאה ל-Claude", "detail": str(exc)[:300]}

    text, notes = policy.check_post(draft.text, db.setting_bool("allow_price_in_post"))
    image = db.primary_image_for(product_id)
    post_id = db.insert_scheduled_post({
        "product_id": product_id,
        "image_id": image["id"] if image else None,
        "angle": angle,
        "text": text,
        "scheduled_for": scheduled_for,
        "status": "draft",
        "engine": meta["engine"],
        "policy_notes": notes,
    })
    db.log_event("post_drafted", f"נוסחה טיוטת פוסט #{post_id}", {"product": product["name"], "angle": angle})
    return {"ok": True, "post_id": post_id, "reasoning": draft.reasoning}


def publish(post_id: int) -> tuple[bool, str]:
    """מפרסם פוסט בדף. מחזיר (הצליח, הודעה בעברית)."""
    post = db.get_scheduled_post(post_id)
    if not post:
        return False, "הפוסט לא נמצא"
    if post["status"] == "published":
        return False, "הפוסט כבר פורסם"
    if not post["text"].strip():
        return False, "אין טקסט לפרסום"

    try:
        if post["image"]:
            path = UPLOAD_DIR / post["image"]["filename"]
            if not path.exists():
                return False, "קובץ התמונה חסר"
            result = facebook.publish_photo(path, post["text"])
        else:
            result = facebook.publish_text(post["text"])
    except facebook.FacebookNotConfigured as exc:
        return False, str(exc)
    except Exception as exc:  # noqa: BLE001
        db.mark_post_failed(post_id, str(exc))
        db.log_event("post_failed", f"פרסום נכשל לפוסט #{post_id}", {"error": str(exc)[:400]})
        return False, f"הפרסום נכשל: {exc}"

    fb_id = str(result.get("post_id") or result.get("id") or "")
    db.mark_post_published(post_id, fb_id)
    db.log_event("post_published", f"פורסם פוסט #{post_id}", {"fb_post_id": fb_id})
    return True, f"הפוסט פורסם בדף (מזהה {fb_id})"


def publish_due() -> list[tuple[int, bool, str]]:
    """מפרסם כל פוסט מאושר שהגיע זמנו, חוץ משבת, חג וזמנים חסומים."""
    moment = db.now_local()
    blocked = timing.blocked_reason(moment)
    if blocked:
        return [(0, False, f"לא מפרסמים עכשיו — {blocked}. הפוסטים ימתינו.")]

    results = []
    for post in db.due_posts(moment.strftime("%Y-%m-%d %H:%M")):
        ok, message = publish(post["id"])
        results.append((post["id"], ok, message))
    return results
