"""חוקי הניסוח: מה אסור שייצא החוצה בתגובה ציבורית.

הכללים כאן רצים אחרי ה-AI ולא במקומו — גם אם המודל טעה, הטקסט מנוקה כאן.
"""
import re

PRICE_WORDS = ("₪", 'ש"ח', "ש״ח", "שח ", "שקל", "שקלים", "מחיר", "מחירון", "עולה ", "עלות")
LINK_RE = re.compile(r"(https?://\S+|www\.\S+|\b\S+\.(?:co\.il|com|net|org|shop)\b)", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+972|0)\s*5\d[\s-]*\d{3}[\s-]*\d{4}|\b\d{9,10}\b")
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF\U0001F1E6-\U0001F1FF❤️]"
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+|\n+")
HYPE_WORDS = ("מדהים", "מהמם", "חובה", "הכי טוב בעולם", "מבצע", "הזדמנות אחרונה", "רק היום")


def _has_price(text: str) -> bool:
    lowered = f" {text} "
    return any(word in lowered for word in PRICE_WORDS)


def strip_prices(text: str) -> tuple[str, bool]:
    """מסיר משפטים שמזכירים מחיר. מחזיר (טקסט נקי, האם הוסר משהו)."""
    if not _has_price(text):
        return text, False
    kept = [s for s in SENTENCE_SPLIT_RE.split(text) if s.strip() and not _has_price(s)]
    cleaned = " ".join(part.strip() for part in kept).strip()
    return cleaned, True


def strip_links(text: str) -> tuple[str, bool]:
    if not LINK_RE.search(text):
        return text, False
    return LINK_RE.sub("", text).replace("  ", " ").strip(), True


def check_comment(text: str, allow_links: bool, max_chars: int) -> tuple[str, list[str]]:
    """מנקה תגובה ציבורית ומחזיר (טקסט, רשימת הערות בעברית על מה תוקן/נמצא)."""
    notes: list[str] = []
    cleaned = (text or "").strip()

    cleaned, removed_price = strip_prices(cleaned)
    if removed_price:
        notes.append("הוסר אזכור מחיר מהתגובה הציבורית")

    if not allow_links:
        cleaned, removed_link = strip_links(cleaned)
        if removed_link:
            notes.append("הוסר קישור מהתגובה הציבורית")

    if PHONE_RE.search(cleaned):
        cleaned = PHONE_RE.sub("", cleaned).strip()
        notes.append("הוסר מספר טלפון מהתגובה הציבורית")

    emojis = EMOJI_RE.findall(cleaned)
    if len(emojis) > 1:
        for extra in emojis[1:]:
            cleaned = cleaned.replace(extra, "", 1)
        cleaned = cleaned.strip()
        notes.append("צומצמו אימוג'ים (מקסימום אחד)")

    hype = [w for w in HYPE_WORDS if w in cleaned]
    if hype:
        notes.append("שפה שיווקית שכדאי לבדוק: " + ", ".join(hype))

    collapsed = re.sub(r"!{2,}", "!", cleaned)
    if collapsed.count("!") > 1:
        first = collapsed.find("!")
        collapsed = collapsed[: first + 1] + collapsed[first + 1 :].replace("!", ".")
    if collapsed != cleaned:
        notes.append("צומצמו סימני קריאה")
    cleaned = collapsed

    if len(cleaned) > max_chars:
        notes.append(f"התגובה ארוכה מ-{max_chars} תווים — כדאי לקצר")

    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\.!", ".", cleaned)
    cleaned = re.sub(r"!\.", "!", cleaned)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    cleaned = re.sub(r"\s+([.,!?])", r"\1", cleaned).strip()
    return cleaned, notes


def check_dm(text: str) -> tuple[str, list[str]]:
    """הודעת הפתיחה בפרטי — כאן מחיר מותר, אבל עדיין בלי ספאם."""
    notes: list[str] = []
    cleaned = re.sub(r"[ \t]{2,}", " ", (text or "").strip())
    if len(cleaned) > 500:
        notes.append("הודעת הפתיחה ארוכה מדי — כדאי לקצר")
    return cleaned, notes


def check_post(text: str, allow_price: bool, max_chars: int = 900) -> tuple[str, list[str]]:
    """פוסט בדף — כללים רכים יותר מתגובה: קישורים מותרים, אורך גדול יותר.

    מחיר מותר רק אם הוגדר כך בהגדרות.
    """
    notes: list[str] = []
    cleaned = (text or "").strip()

    if not allow_price:
        cleaned, removed = strip_prices(cleaned)
        if removed:
            notes.append("הוסר אזכור מחיר מהפוסט (אפשר לשנות בהגדרות)")

    emojis = EMOJI_RE.findall(cleaned)
    if len(emojis) > 3:
        for extra in emojis[3:]:
            cleaned = cleaned.replace(extra, "", 1)
        notes.append("צומצמו אימוג\'ים בפוסט")

    hype = [w for w in HYPE_WORDS if w in cleaned]
    if hype:
        notes.append("שפה שיווקית שכדאי לבדוק: " + ", ".join(hype))

    if len(cleaned) > max_chars:
        notes.append(f"הפוסט ארוך מ-{max_chars} תווים")

    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, notes
