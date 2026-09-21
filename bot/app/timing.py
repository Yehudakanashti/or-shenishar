"""מתי לא מפרסמים: שבת, חגים, ושעות שהוגדרו כחסומות.

הבוט לא מפרסם בשבת ובחג. פוסט שזמנו נופל בתוך חלון חסום נדחה לזמן הפנוי
הבא, ולא מתפרסם באיחור באמצע החג.
"""
from datetime import date, datetime, time, timedelta

from . import db

# שבת: מיום שישי אחר הצהריים עד מוצאי שבת
SHABBAT_START = time(15, 0)   # שישי
SHABBAT_END = time(20, 30)    # שבת


def parse_blackouts(raw: str) -> list[tuple[date, date, str]]:
    """כל שורה: YYYY-MM-DD..YYYY-MM-DD תווית (התווית אופציונלית)."""
    ranges = []
    for line in (raw or "").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        label = parts[1].strip() if len(parts) > 1 else ""
        span = parts[0]
        try:
            if ".." in span:
                start_raw, end_raw = span.split("..", 1)
                ranges.append((date.fromisoformat(start_raw), date.fromisoformat(end_raw), label))
            else:
                single = date.fromisoformat(span)
                ranges.append((single, single, label))
        except ValueError:
            continue
    return ranges


def blocked_reason(moment: datetime) -> str:
    """מחזיר סיבה בעברית אם אסור לפרסם בזמן הזה, או מחרוזת ריקה."""
    weekday = moment.weekday()  # 4 = שישי, 5 = שבת
    if weekday == 4 and moment.time() >= SHABBAT_START:
        return "ערב שבת"
    if weekday == 5 and moment.time() < SHABBAT_END:
        return "שבת"

    for start, end, label in parse_blackouts(db.get_setting("blackout_dates", "")):
        if start <= moment.date() <= end:
            return label or "תאריך חסום"
    return ""


def next_free(moment: datetime, keep_time: bool = True) -> datetime:
    """הזמן הפנוי הבא. keep_time — לשמור על אותה שעה ביום הבא."""
    candidate = moment
    for _ in range(40):  # תקרת ביטחון
        reason = blocked_reason(candidate)
        if not reason:
            return candidate
        if keep_time:
            candidate = (candidate + timedelta(days=1)).replace(
                hour=moment.hour, minute=moment.minute, second=0, microsecond=0
            )
        else:
            candidate += timedelta(hours=1)
    return candidate
