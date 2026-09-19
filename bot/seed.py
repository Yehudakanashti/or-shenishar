"""טוען את קטלוג מוצרי החגים ואת התמונות מתוך assets/products.

הרצה:  python seed.py
אפשר להריץ שוב — הוא מעדכן לפי slug ולא יוצר כפילויות.
"""
import shutil
import sys
from pathlib import Path

from app.config import BASE_DIR, UPLOAD_DIR
from app.db import add_image, connect, get_product_by_slug, init_db, log_event, upsert_product

ASSETS = BASE_DIR / "assets" / "products"

# מה שחסר ויש להשלים בממשק
TODO = "להשלים בממשק: מחיר (לשיחה בפרטי בלבד) ומידות."

# הוראה קשיחה — הבוט לא יזכיר את זה בשום ניסוח
AVOID = (
    "סוג התאורה, מקור הכוח וכמה זמן זה דולק; "
    "זמני אספקה, משלוח ופרטי הזמנה — כל אלה נסגרים בשיחה בפרטי ולא בתגובה; "
    "מחיר בתגובה ציבורית."
)

# נקודת המכירה החזקה: הכיתוב נקבע לפי ההזמנה
CUSTOM = (
    "הכיתוב על הפריט דינמי לחלוטין — אפשר להדפיס כל שם, ברכה או משפט אישי "
    "לפי ההזמנה, במקום הכיתוב שמופיע בתמונות."
)

SHARED = {
    "line": "holiday",
    "occasion": "סוכות",
    "season_start": "2026-09-25",
    "season_end": "2026-10-02",
    "lead_time": "",
    "shipping": "",
    "avoid": AVOID,
    "active": 1,
}

LIGHTING = (
    "מודפס בתלת־ממד מחומר לבן שקוף למחצה, ומואר מבפנים — הכיתוב והסמלים נדלקים "
    "יחד עם הגוף, בכמה צבעים."
)

PRODUCTS = [
    {
        "slug": "sukkah-lamp",
        "name": "סוכה מוארת",
        "tagline": "סוכה קטנה שנדלקת על השולחן, עם גג סכך וכיתובי החג.",
        "description": (
            "קובייה בצורת סוכה עם גג סכך מודפס, דפנות עם חלון ושורת קישוטים תלויים, "
            "וסמלי החג — לולב ואתרוג, ענבים, רימון ומגן דוד.\n\n" + LIGHTING + "\n\n"
            "הכיתובים על הדפנות: ״בסוכות תשבו שבעת ימים״, ״ושמחת בחגך״, "
            "״ופרוש עלינו סוכת שלומך״, ״זמן שמחתנו״, ועל דופן אחת שמות האושפיזין — "
            "אברהם, יצחק, יעקב, משה, אהרן, יוסף ודוד. כל אחד מהכיתובים ניתן להחלפה בהזמנה."
        ),
        "audience": "קישוט לשולחן בסוכה, מתנה לחג, מתנה למארחים, מתנה לגננת או למורה",
        "customization": CUSTOM,
        "keywords": [
            "שם אישי", "כיתוב אישי", "מותאם אישית", "בהתאמה אישית",
            "קישוט לסוכה", "קישוטים לסוכה", "נוי סוכה", "מה תולים בסוכה", "רעיונות לסוכה",
            "אושפיזין", "סוכה", "מתנה למארחים", "מתנה לחג", "עיצוב שולחן חג",
            "מנורה לסוכה", "תאורה לסוכה", "משהו מיוחד לסוכה",
        ],
        "images": [
            ("sukkah-green.jpg", "הסוכה המוארת — ״ושמחת בחגך, ופרוש עלינו סוכת שלומך״", True),
            ("sukkah-ushpizin.jpg", "דופן האושפיזין — אברהם יצחק יעקב משה, אהרן יוסף דוד", False),
            ("sukkah-roof.jpg", "גג הסכך המודפס", False),
            ("trio-lit.jpg", "שלושת הפריטים יחד", False),
        ],
    },
    {
        "slug": "etrog-lamp",
        "name": "אתרוג מואר",
        "tagline": "אתרוג שיושב בתוך עלים ונדלק מבפנים.",
        "description": (
            "גוף בצורת אתרוג על בסיס עלים פתוחים.\n\n" + LIGHTING + "\n\n"
            "הכיתובים: ״חג סוכות שמח״, ״זמן שמחתנו״, ״ולקחתם לכם ביום הראשון״."
        ),
        "audience": "קישוט לשולחן החג, מתנה קטנה לחג, מתנה לאירוח",
        "customization": CUSTOM,
        "keywords": [
            "אתרוג", "ארבעת המינים", "קישוט לסוכה", "מתנה לחג", "מתנה קטנה לחג",
            "עיצוב שולחן חג", "נוי סוכה", "סוכות",
        ],
        "images": [
            ("etrog-lit.jpg", "האתרוג המואר", True),
            ("trio-colors.jpg", "בצבעים משתנים, לצד שאר הפריטים", False),
        ],
    },
    {
        "slug": "pomegranate-lamp",
        "name": "רימון מואר",
        "tagline": "רימון עם כתר, מואר מבפנים, עם ברכות החג מסביב.",
        "description": (
            "גוף רימון עגול עם כתר, על בסיס.\n\n" + LIGHTING + "\n\n"
            "הכיתובים מסביב: ״חג סוכות שמח״, ״בסוכות תשבו שבעת ימים״, ״ושמחת בחגך״, "
            "״מועדים לשמחה״, ושמות האושפיזין."
        ),
        "audience": "קישוט לשולחן החג, מתנה לחג, מתנה לראש השנה ולסוכות",
        "customization": CUSTOM,
        "keywords": [
            "רימון", "קישוט לסוכה", "מתנה לחג", "שנה טובה", "מתנה לראש השנה",
            "נוי סוכה", "עיצוב שולחן חג", "סוכות",
        ],
        "images": [
            ("trio-lit.jpg", "הרימון מימין, מואר", True),
            ("trio-colors.jpg", "הרימון בצבע חם", False),
        ],
    },
    {
        "slug": "sukkot-plaque",
        "name": "שלט ״חג סוכות שמח״",
        "tagline": "שלט עומד קטן עם ברכת החג.",
        "description": (
            "שלט עומד עם הכיתוב ״חג סוכות שמח״ ו״מועדים לשמחה״, "
            "וסמלי אתרוג וסוכה בחלק העליון.\n\n" + LIGHTING
        ),
        "audience": "מתנה קטנה לחג, שי לעובדים, קישוט לשולחן",
        "customization": CUSTOM,
        "keywords": [
            "שלט לסוכה", "ברכה לחג", "שי לעובדים", "מתנה קטנה לחג", "מתנות לחג לעובדים",
            "קישוט לסוכה", "סוכות",
        ],
        "images": [("plaque.jpg", "השלט העומד", True)],
    },
]


def install_images(product_id: int, images: list[tuple[str, str, bool]]) -> int:
    with connect() as conn:
        conn.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    added = 0
    for filename, caption, primary in images:
        source = ASSETS / filename
        if not source.exists():
            print(f"    ! חסרה תמונה: {filename}")
            continue
        target = f"{product_id}-{filename}"
        shutil.copy(source, UPLOAD_DIR / target)
        add_image(product_id, target, caption, primary)
        added += 1
    return added


def main() -> int:
    init_db()
    if not ASSETS.exists():
        print(f"לא נמצאה התיקייה {ASSETS}")
        return 1

    for spec in PRODUCTS:
        existing = get_product_by_slug(spec["slug"])
        product_id = upsert_product(
            {
                **SHARED,
                "slug": spec["slug"],
                "name": spec["name"],
                "tagline": spec["tagline"],
                "description": spec["description"],
                "audience": spec["audience"],
                "customization": spec["customization"],
                "price_from": existing["price_from"] if existing else None,
                "price_to": existing["price_to"] if existing else None,
                "order_url": existing["order_url"] if existing else "",
                "keywords": spec["keywords"],
                "notes": TODO,
            },
            existing["id"] if existing else None,
        )
        count = install_images(product_id, spec["images"])
        print(f"  ✓ {spec['name']:22} {count} תמונות")

    log_event("seed", f"נטענו {len(PRODUCTS)} מוצרי סוכות עם תמונות")
    print("\nהקטלוג נטען. מה שחסר ומופיע בהערות של כל מוצר:")
    print(f"  {TODO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
