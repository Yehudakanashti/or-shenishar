"""מנוע התגובות: פוסט נכנס → בדיקות בטיחות → ניתוח → התאמת מוצר → ניסוח → הצעה לאישור."""
from typing import Any

from . import ai, db, matching, policy, safety


def ingest(text: str, group_name: str = "", author_name: str = "", url: str = "", source: str = "manual") -> dict[str, Any]:
    text = (text or "").strip()
    group_name = (group_name or "").strip()
    author_name = (author_name or "").strip()

    gate = safety.check(text, group_name, author_name)
    if not gate.allowed:
        db.log_event("blocked", gate.reason, {"detail": gate.detail, "group": group_name, "author": author_name})
        return {"ok": False, "reason": gate.reason, "detail": gate.detail}

    products = db.list_products(active_only=True)

    try:
        analysis, meta = ai.analyze(text, group_name, author_name, products)
    except Exception as exc:  # noqa: BLE001 — כישלון של ה-API לא אמור להפיל את השרת
        db.log_event("ai_error", "שגיאה בקריאה ל-Claude", {"error": str(exc)[:800]})
        return {"ok": False, "reason": "שגיאה בקריאה ל-Claude", "detail": str(exc)[:400]}

    product = db.get_product_by_slug(analysis.product_slug) if analysis.product_slug else None
    if product is None and analysis.relevant:
        product = matching.best_product(text, products)
    image = db.primary_image_for(product["id"]) if product else None

    allow_links = db.setting_bool("allow_links_in_comment")
    max_chars = db.setting_int("max_comment_chars", 320)
    comment, comment_notes = policy.check_comment(analysis.comment, allow_links, max_chars)
    dm_text, dm_notes = policy.check_dm(analysis.dm_opener)

    notes = comment_notes + dm_notes
    min_confidence = db.setting_float("min_confidence", 0.55)
    needs_human = bool(analysis.needs_human)
    if analysis.sensitivity == "bereavement":
        needs_human = True
        notes.append("פוסט שנוגע באובדן — תמיד עובר אישור אנושי, גם במצב אוטומטי")
    if analysis.confidence < min_confidence:
        needs_human = True
        notes.append(f"ביטחון נמוך ({analysis.confidence:.2f}) מהסף שהוגדר ({min_confidence:.2f})")
    if product is None and analysis.relevant:
        notes.append("לא נמצא מוצר מתאים בקטלוג")

    post_id = db.insert_post(text, safety.post_hash(text), group_name, author_name, url, source)
    suggestion_id = db.insert_suggestion(
        {
            "post_id": post_id,
            "product_id": product["id"] if product else None,
            "image_id": image["id"] if image else None,
            "relevant": 1 if analysis.relevant else 0,
            "intent": analysis.intent,
            "sensitivity": analysis.sensitivity,
            "confidence": analysis.confidence,
            "comment_text": comment,
            "dm_text": dm_text,
            "reasoning": analysis.reasoning,
            "needs_human": 1 if needs_human else 0,
            "policy_notes": notes,
            "status": "pending",
            "engine": meta["engine"],
            "usage_in": meta["usage_in"],
            "usage_out": meta["usage_out"],
        }
    )
    db.log_event(
        "suggestion_created",
        f"הצעה #{suggestion_id} · {ai.INTENT_LABELS.get(analysis.intent, analysis.intent)}",
        {"group": group_name, "author": author_name, "relevant": analysis.relevant, "engine": meta["engine"]},
    )
    return {"ok": True, "suggestion_id": suggestion_id, "relevant": analysis.relevant}


def approve(suggestion_id: int, final_comment: str, final_dm: str) -> None:
    suggestion = db.get_suggestion(suggestion_id)
    if not suggestion:
        return
    final_comment = (final_comment or "").strip()
    final_dm = (final_dm or "").strip()
    db.decide_suggestion(suggestion_id, "approved", final_comment, final_dm)

    post_text = suggestion["post"].get("text", "")
    origin = "edited" if final_comment != suggestion["comment_text"] else "approved"
    db.add_example("comment", final_comment, post_text, origin)
    db.add_example("dm", final_dm, post_text, origin)
    db.log_event(
        "approved",
        f"אושרה הצעה #{suggestion_id}",
        {"edited": origin == "edited", "group": suggestion["post"].get("group_name", "")},
    )


def reject(suggestion_id: int, reason: str = "") -> None:
    db.decide_suggestion(suggestion_id, "rejected")
    db.log_event("rejected", f"נדחתה הצעה #{suggestion_id}", {"reason": reason})
