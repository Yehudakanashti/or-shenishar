"""ממלא את הקטלוג מתוך האתר עצמו (index.html), כדי שהמחירים והדגמים יהיו אמיתיים.

הרצה:  python seed.py
אפשר להריץ שוב — הוא מעדכן לפי slug ולא יוצר כפילויות.
"""
import json
import re
import sys
from pathlib import Path

from app.config import BASE_DIR
from app.db import get_product_by_slug, init_db, log_event, upsert_product

SITE_HTML = BASE_DIR.parent / "index.html"
PRODUCT_RE = re.compile(r'\{[^{}]*"price"\s*:\s*\d+[^{}]*\}')

CANDLE_IDS = {"flame", "flame_slim", "bonfire", "flame_twin"}

FAMILIES = {
    "memorial-stone": {
        "name": "אבן זיכרון מוארת",
        "line": "memorial",
        "tagline": "אבן שהתמונה חקוקה בתוכה. ביום זה תבליט שקט, בלילה האור נדלק והפנים חוזרות.",
        "audience": "מי שמחפש דרך להנציח אדם אהוב, מתנה למשפחה אבלה, אזכרה, יום זיכרון",
        "keywords": [
            "אבן זיכרון", "הנצחה", "להנציח", "לזכרו", "לזכרה", "אזכרה", "יום הזיכרון",
            "מתנה מיוחדת", "משהו אישי", "תמונה מוארת", "דיוקן", "מתנה להורים",
            "מתנה לסבתא", "מתנה לסבא", "זיכרון", "שכול", "תמונה של אמא", "תמונה של אבא",
        ],
    },
    "memorial-pair": {
        "name": "אבן לשני דיוקנאות",
        "line": "memorial",
        "tagline": "שני דיוקנאות זה לצד זה וכיתוב משותף מתחתם — להורים, לזוג, לאחים.",
        "audience": "הנצחה של שני אנשים יחד, זוג הורים, אחים, בני זוג",
        "keywords": ["זוג הורים", "שני הורים", "אחים", "בני זוג", "שניהם", "זוג אבנים", "שני דיוקנאות"],
    },
    "memorial-candle": {
        "name": "נר נשמה מואר",
        "line": "memorial",
        "tagline": "להבה שדולקת בלי אש — אפשר להשאיר דולקת ברצף, גם בחדר של ילד.",
        "audience": "נר זיכרון קבוע, יארצייט, יום השנה, נר נשמה שלא נגמר",
        "keywords": ["נר נשמה", "נר זיכרון", "יארצייט", "יום השנה", "להבה", "נר שדולק", "נר חשמלי"],
    },
    "memorial-addon": {
        "name": "תוספות קטנות",
        "line": "memorial",
        "tagline": "פריטים קטנים שמתלווים לאבן — לב, טבעת מגן דוד, להבה קטנה.",
        "audience": "תוספת לאבן קיימת, מזכרת קטנה",
        "keywords": ["תוספת", "לב קטן", "מגן דוד", "מזכרת קטנה"],
    },
}

SHARED = {
    "lead_time": "ייצור בהזמנה אישית — מספר ימי עסקים, ואחריו יוצא המשלוח",
    "shipping": "משלוח לכל הארץ באריזה מרופדת; אם מגיע פגום — מוחלף ללא עלות",
    "customization": (
        "כל אבן נבנית סביב התמונה שלכם. אנחנו מסירים רקע, חותכים ומתאימים גוונים, "
        "ושולחים תצוגה מקדימה לאישור לפני הייצור. אפשר להוסיף שם, תאריך או משפט אישי, "
        "לבחור גופן וסמל (לב, מגן דוד, יונה, כוכב, פרח, אינסוף), ולבחור בין סוללות לחיבור לחשמל."
    ),
    "order_url": "https://or-shenishar.co.il",
    "notes": (
        "תאורת LED — בלי אש גלויה, בלי שעווה ובלי ריח, אפשר להשאיר דולק ברצף. "
        "ביטול אפשרי עד תחילת הייצור, כי כל פריט מיוצר אישית. "
        "התמונה מתקבלת מהלקוח אחרי ההזמנה. המחירים כוללים מע״מ ונועדו לשיחה בפרטי בלבד."
    ),
}


def family_of(item: dict) -> str:
    if item.get("power") == "accessory" or str(item.get("id", "")).startswith("addon_"):
        return "memorial-addon"
    if item.get("id") in CANDLE_IDS:
        return "memorial-candle"
    if item.get("cat") == "couple":
        return "memorial-pair"
    return "memorial-stone"


def load_site_products() -> list[dict]:
    if not SITE_HTML.exists():
        print(f"לא נמצא הקובץ {SITE_HTML} — דלגתי על הקטלוג מהאתר.")
        return []
    html = SITE_HTML.read_text(encoding="utf-8", errors="replace")
    items = []
    for match in PRODUCT_RE.finditer(html):
        try:
            items.append(json.loads(match.group(0)))
        except json.JSONDecodeError:
            continue
    return items


def main() -> int:
    init_db()
    items = load_site_products()
    if not items:
        print("לא נמצאו מוצרים באתר. אפשר להוסיף מוצרים ידנית בממשק.")
        return 1

    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(family_of(item), []).append(item)

    created = 0
    for slug, spec in FAMILIES.items():
        members = grouped.get(slug, [])
        if not members:
            continue
        prices = [m["price"] for m in members if isinstance(m.get("price"), int)]
        names = [m["name"] for m in members]
        sizes = {m["name"]: m.get("size", "") for m in members}
        description = spec["tagline"] + "\n\nדגמים זמינים: " + ", ".join(
            f"{n} ({sizes[n]})" if sizes.get(n) else n for n in names
        )
        existing = get_product_by_slug(slug)
        upsert_product(
            {
                "slug": slug,
                "name": spec["name"],
                "line": spec["line"],
                "tagline": spec["tagline"],
                "description": description,
                "audience": spec["audience"],
                "price_from": min(prices) if prices else None,
                "price_to": max(prices) if prices else None,
                "keywords": spec["keywords"],
                "active": 1,
                **SHARED,
            },
            existing["id"] if existing else None,
        )
        created += 1
        print(f"  ✓ {spec['name']} — {len(members)} דגמים, {min(prices)}–{max(prices)} ₪")

    log_event("seed", f"נטענו {created} משפחות מוצרים מתוך האתר")
    print(f"\nנטענו {created} מוצרים. פתחו את הממשק והשלימו תמונות.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
