"""מעצב את הדף: תיאור, תמונת פרופיל ותמונת כיסוי.

הרצה:
    python setup_page.py              — מראה מה קיים ומה ישתנה, בלי לשנות
    python setup_page.py --apply      — מבצע בפועל

דורש חיבור לדף (setup_facebook.py) ואת ההרשאה pages_manage_metadata.
"""
import sys

from app import facebook
from app.config import BASE_DIR

PAGE_DIR = BASE_DIR / "assets" / "page"

ABOUT = "מוצרי חג מודפסים בתלת־ממד, מוארים מבפנים. הכיתוב — מה שתבחרו."

DESCRIPTION = """אנחנו מדפיסים מוצרי חג בתלת־ממד — סוכות, אתרוגים, רימונים ושלטי ברכה.
כל פריט נבנה שכבה אחר שכבה מחומר בהיר, וכשהאור נדלק מבפנים הכיתוב והסמלים עולים מתוך החומר.

הכיתוב הוא החלק שלכם: שם, ברכה או משפט אישי — מה שתבחרו, לפי ההזמנה.

לפרטים והזמנות — שלחו הודעה."""

PROFILE = PAGE_DIR / "profile-etrog.jpg"
COVER = PAGE_DIR / "cover.jpg"


def show_current() -> dict:
    details = facebook.get_details()
    print("\n  הדף כרגע:")
    print(f"     שם:      {details.get('name')}")
    print(f"     כתובת:   {details.get('link')}")
    print(f"     קטגוריה: {details.get('category') or '— לא הוגדרה —'}")
    print(f"     עוקבים:  {details.get('followers_count', 0)}")
    print(f"     תיאור:   {(details.get('about') or '— ריק —')[:70]}")
    return details


def main() -> int:
    apply = "--apply" in sys.argv
    try:
        show_current()
    except facebook.FacebookNotConfigured as exc:
        print(f"\n  ✗ {exc}\n")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\n  ✗ {exc}\n")
        return 1

    print("\n  מה יוגדר:")
    print(f"     תיאור קצר:  {ABOUT}")
    print(f"     תיאור מלא:  {DESCRIPTION.splitlines()[0]}…")
    print(f"     פרופיל:     {PROFILE.name}  {'✓' if PROFILE.exists() else '✗ חסר'}")
    print(f"     כיסוי:      {COVER.name}  {'✓' if COVER.exists() else '✗ חסר'}")

    if not apply:
        print("\n  זו תצוגה בלבד. להרצה בפועל:  python setup_page.py --apply\n")
        return 0

    print("\n  מבצע…")
    steps = [
        ("תיאור הדף", lambda: facebook.update_details(about=ABOUT, description=DESCRIPTION)),
        ("תמונת פרופיל", lambda: facebook.set_profile_picture(PROFILE)),
        ("תמונת כיסוי", lambda: facebook.set_cover_photo(COVER)),
    ]
    failed = 0
    for label, action in steps:
        try:
            action()
            print(f"     ✓ {label}")
        except Exception as exc:  # noqa: BLE001
            print(f"     ✗ {label}: {str(exc)[:240]}")
            failed += 1

    print()
    show_current()
    print()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
