"""טוען חמישה פוסטי פתיחה לדף — טיוטות עם תמונה ותאריך, ממתינות לאישור.

הרצה:  python seed_posts.py
הטקסטים נכתבו ידנית ולא על ידי המודל — אפשר ומומלץ לערוך אותם בממשק.
"""
import sys

from app.db import (
    get_product_by_slug, init_db, insert_scheduled_post, list_scheduled_posts, log_event,
)

# (slug של המוצר, שם קובץ התמונה, מתי, הטקסט)
LAUNCH_POSTS = [
    (
        "sukkah-lamp", "trio-lit.jpg", "2026-09-20 19:00",
        "נעים להכיר — אנחנו מדפיסים מוצרי חג בתלת־ממד.\n\n"
        "כל פריט נבנה שכבה אחר שכבה, ובערב, כשהאור נדלק מבפנים, "
        "הכיתוב והסמלים עולים מתוך החומר.\n\n"
        "הכיתוב הוא החלק שלכם — שם, ברכה או משפט משלכם, לפי ההזמנה.\n\n"
        "מוזמנים לשלוח הודעה ונראה יחד מה מתאים."
    ),
    (
        "sukkah-lamp", "sukkah-green.jpg", "2026-09-21 19:30",
        "סוכה קטנה שעומדת על שולחן החג.\n\n"
        "גג סכך, חלון, שורת קישוטים, ועל הדפנות — ״בסוכות תשבו שבעת ימים״, "
        "״ושמחת בחגך״, ״ופרוש עלינו סוכת שלומך״.\n\n"
        "היא לא תופסת מקום, ובחושך היא הדבר היחיד שרואים על השולחן."
    ),
    (
        "sukkah-lamp", "sukkah-ushpizin.jpg", "2026-09-22 19:30",
        "על הדופן הזו כתובים שמות האושפיזין — אברהם, יצחק, יעקב, משה, אהרן, יוסף ודוד.\n\n"
        "אבל זו רק ברירת המחדל. אפשר להחליף אותם בשמות של הילדים, "
        "בשם המשפחה, או בכל משפט שתרצו.\n\n"
        "זה מה שהופך את זה מקישוט למשהו ששומרים."
    ),
    (
        "etrog-lamp", "etrog-lit.jpg", "2026-09-23 19:30",
        "אתרוג שיושב בתוך עלים.\n\n"
        "״זמן שמחתנו״ למעלה, ״ולקחתם לכם ביום הראשון״ למטה, "
        "והכול נדלק יחד עם החושך.\n\n"
        "יש גם רימון ושלט קטן לברכת החג. מי שרוצה לראות — שלחו הודעה."
    ),
    (
        "sukkah-lamp", "trio-colors.jpg", "2026-09-24 11:00",
        "רגע לפני החג.\n\n"
        "מי שרוצה פריט עם כיתוב אישי — זה הזמן להגיד, כדי שנספיק.\n\n"
        "שלחו הודעה עם מה שתרצו שיהיה כתוב, ונחזור אליכם."
    ),
]


def main() -> int:
    init_db()
    if list_scheduled_posts():
        print("  ! כבר יש פוסטים במערכת — לא נגעתי בכלום.")
        print("    כדי לטעון בכל זאת, מחקו קודם את הקיימים בממשק.\n")
        return 0

    for slug, image_name, when, text in LAUNCH_POSTS:
        product = get_product_by_slug(slug)
        if not product:
            print(f"  ! לא נמצא המוצר {slug} — הריצו קודם python seed.py")
            continue
        image = next(
            (img for img in product["images"] if img["filename"].endswith(image_name)),
            product["images"][0] if product["images"] else None,
        )
        post_id = insert_scheduled_post({
            "product_id": product["id"],
            "image_id": image["id"] if image else None,
            "angle": "showcase",
            "text": text,
            "scheduled_for": when,
            "status": "draft",
            "engine": "נכתב ידנית",
            "policy_notes": [],
        })
        print(f"  ✓ פוסט #{post_id} — {when} — {text.splitlines()[0][:44]}…")

    log_event("seed", f"נטענו {len(LAUNCH_POSTS)} פוסטי פתיחה")
    print("\n  חמש טיוטות ממתינות במסך ״פוסטים״. עברו עליהן, ערכו ואשרו.")
    print("  פוסט מאושר יתפרסם כשיגיע זמנו — אחרי שהדף יחובר.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
