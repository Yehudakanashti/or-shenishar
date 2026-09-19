"""יוצר שלדים למוצרי החגים עם חלונות העונה הנכונים.

זה לא ממלא תוכן — השמות, התיאורים, המחירים והתמונות נכנסים מהממשק.
המוצרים נוצרים כבויים, כדי שהבוט לא יציע מוצר שעדיין אין עליו מידע.

הרצה:  python seed.py
"""
import sys

from app.db import get_product_by_slug, init_db, log_event, upsert_product

# תאריכי החגים תשפ״ז
DRAFTS = [
    {
        "slug": "sukkot",
        "name": "מוצרי סוכות",
        "occasion": "סוכות",
        "season_start": "2026-09-25",
        "season_end": "2026-10-02",
        "keywords": [
            "קישוט לסוכה", "קישוטים לסוכה", "סוכה", "מה תולים בסוכה", "רעיונות לסוכה",
            "אושפיזין", "נוי סוכה", "שרשרת לסוכה", "מתנה לחג", "חג סוכות",
        ],
    },
    {
        "slug": "hanukkah",
        "name": "מוצרי חנוכה",
        "occasion": "חנוכה",
        "season_start": "2026-12-04",
        "season_end": "2026-12-12",
        "keywords": [
            "חנוכייה", "חנוכיה", "מתנה לחנוכה", "מתנות לחנוכה", "סביבון", "נרות חנוכה",
            "מסיבת חנוכה", "מתנה לגננת", "מתנה למורה", "מתנות לילדים בחנוכה", "חג החנוכה",
        ],
    },
]

PLACEHOLDER = "השלימו כאן: מה המוצר, למי הוא מתאים, וכל מה שחשוב שהבוט יֵדע."


def main() -> int:
    init_db()
    for draft in DRAFTS:
        existing = get_product_by_slug(draft["slug"])
        if existing:
            print(f"  · {draft['name']} כבר קיים — לא נגעתי")
            continue
        upsert_product(
            {
                "slug": draft["slug"],
                "name": draft["name"],
                "line": "holiday",
                "tagline": "",
                "description": PLACEHOLDER,
                "audience": "",
                "price_from": None,
                "price_to": None,
                "lead_time": "",
                "shipping": "",
                "customization": "",
                "order_url": "",
                "keywords": draft["keywords"],
                "occasion": draft["occasion"],
                "season_start": draft["season_start"],
                "season_end": draft["season_end"],
                "notes": "",
                "active": 0,
            }
        )
        print(f"  ✓ {draft['name']} — עונה {draft['season_start']} עד {draft['season_end']} (כבוי עד שתמלאו)")

    log_event("seed", "נוצרו שלדי מוצרי חגים")
    print("\nהמוצרים נוצרו כבויים. פתחו את מסך המוצרים, מלאו תיאור ומחירים,")
    print("העלו תמונות, וסמנו ״מוצר פעיל״ — רק אז הבוט יתחיל להציע אותם.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
