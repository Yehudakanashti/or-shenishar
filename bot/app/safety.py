"""בולמי הנזק: מה עוצר את הבוט לפני שהוא מייצר הצעה."""
import hashlib
from dataclasses import dataclass

from . import db
from .matching import normalize


@dataclass
class Gate:
    allowed: bool
    reason: str = ""
    detail: str = ""


def post_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def check(text: str, group_name: str, author_name: str) -> Gate:
    if db.setting_bool("kill_switch"):
        return Gate(False, "עצירת חירום פעילה", "כבו את מתג העצירה בהגדרות כדי להמשיך.")

    if len((text or "").strip()) < 15:
        return Gate(False, "הטקסט קצר מדי", "הדביקו את גוף הפוסט המלא.")

    existing = db.find_post_by_hash(post_hash(text))
    if existing:
        return Gate(False, "כבר טיפלנו בפוסט הזה", f"נקלט בתאריך {existing['created_at']}. הבוט לא מגיב פעמיים לאותו פוסט.")

    blocks = db.list_blocklist()
    for block in blocks:
        value = block["value"].strip()
        if not value:
            continue
        if block["kind"] == "group" and group_name and value.lower() in group_name.lower():
            return Gate(False, "הקבוצה מוחרגת", f"‏{value} נמצאת ברשימת ההחרגות.")
        if block["kind"] == "author" and author_name and value.lower() in author_name.lower():
            return Gate(False, "המשתמש מוחרג", f"‏{value} נמצא ברשימת ההחרגות.")
        if block["kind"] == "keyword" and normalize(value) in normalize(text):
            return Gate(False, "מילת החרגה בפוסט", f"הפוסט מכיל ״{value}״.")

    cap = db.setting_int("daily_cap", 12)
    used = db.suggestions_today()
    if used >= cap:
        return Gate(False, "הגעתם לתקרה היומית", f"‏{used} מתוך {cap} הצעות היום. אפשר להעלות את התקרה בהגדרות.")

    cooldown = db.setting_int("author_cooldown_days", 30)
    recent = db.recent_author_suggestion(author_name, cooldown)
    if recent:
        return Gate(
            False,
            "כבר פנינו לאדם הזה לאחרונה",
            f"הצעה #{recent['id']} מתאריך {recent['created_at']}. זמן ההמתנה שהוגדר: {cooldown} ימים.",
        )

    return Gate(True)
