"""התאמת מוצר לפוסט לפי מילות מפתח ולפי העונה. משמש כגיבוי ל-AI וכבדיקה שלו."""
import re
from datetime import date, timedelta
from typing import Any

PUNCT_RE = re.compile(r"[^\w֐-׿ ]+")
NIQQUD_RE = re.compile(r"[֑-ׇ]")


def normalize(text: str) -> str:
    text = NIQQUD_RE.sub("", text or "")
    text = PUNCT_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def season_state(product: dict[str, Any], today: date | None = None, lead_days: int = 21) -> str:
    """מחזיר: active (העונה עכשיו), soon (מתקרבת), far (רחוקה), past (עברה), always (בלי תאריכים)."""
    start_raw, end_raw = (product.get("season_start") or ""), (product.get("season_end") or "")
    if not start_raw and not end_raw:
        return "always"
    today = today or date.today()
    try:
        start = date.fromisoformat(start_raw) if start_raw else None
        end = date.fromisoformat(end_raw) if end_raw else None
    except ValueError:
        return "always"
    if end and today > end:
        return "past"
    if start and today < start - timedelta(days=lead_days):
        return "far"
    if start and today < start:
        return "soon"
    return "active"


# ניקוד מינימלי כדי להחשיב מוצר כמתאים — מונע התאמה על סמך מילה אקראית
MIN_SCORE = 0.8


def score_product(post_text: str, product: dict[str, Any]) -> float:
    haystack = normalize(post_text)
    if not haystack:
        return 0.0
    score = 0.0
    for keyword in product.get("keywords") or []:
        needle = normalize(str(keyword))
        if needle and needle in haystack:
            score += 1.0 + 0.25 * len(needle.split())
    for field in ("name", "audience", "tagline", "occasion"):
        for word in normalize(product.get(field, "")).split():
            if len(word) > 3 and word in haystack:
                score += 0.35
    state = season_state(product)
    if state == "past":
        return 0.0  # מוצר שהעונה שלו נגמרה לא מוצע, גם אם הטקסט מתאים
    if score <= 0:
        return 0.0  # עונה פעילה לבדה אינה סיבה להתאים מוצר לפוסט
    score += {"active": 1.5, "soon": 1.2}.get(state, 0.0)
    return round(score, 3)


def rank_products(post_text: str, products: list[dict[str, Any]]) -> list[tuple[dict[str, Any], float]]:
    ranked = [(p, score_product(post_text, p)) for p in products if p.get("active")]
    return sorted(ranked, key=lambda pair: pair[1], reverse=True)


def best_product(post_text: str, products: list[dict[str, Any]]) -> dict[str, Any] | None:
    """המוצר המתאים ביותר, או None אם אף אחד לא באמת מתאים."""
    ranked = rank_products(post_text, products)
    if ranked and ranked[0][1] >= MIN_SCORE:
        return ranked[0][0]
    return None
