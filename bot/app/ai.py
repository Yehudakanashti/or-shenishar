"""שכבת ה-AI: קריאת פוסט → הבנת כוונה → ניסוח תגובה והודעת פתיחה.

משתמש ב-Claude דרך ה-SDK הרשמי. אם אין מפתח API, המערכת נופלת לנוסח
תבניתי כדי שאפשר יהיה לבדוק את כל הזרימה בלי לשלם על קריאות.
"""
import json
from typing import Any, Literal

from pydantic import BaseModel

from . import db
from .config import ANTHROPIC_API_KEY, BUSINESS, CLAUDE_MODEL, ai_enabled
from .matching import best_product

Intent = Literal[
    "gift_search",
    "memorial_need",
    "price_question",
    "order_question",
    "customization_question",
    "shipping_question",
    "general_interest",
    "irrelevant",
]

INTENT_LABELS = {
    "gift_search": "מחפש/ת מתנה",
    "memorial_need": "הנצחה או זיכרון",
    "price_question": "שאלת מחיר",
    "order_question": "שאלה על הזמנה",
    "customization_question": "שאלה על התאמה אישית",
    "shipping_question": "שאלה על משלוח",
    "general_interest": "התעניינות כללית",
    "irrelevant": "לא רלוונטי",
}

SENSITIVITY_LABELS = {
    "bereavement": "אובדן ושכול",
    "sensitive": "רגיש",
    "neutral": "רגיל",
}

ADDRESS_FORMS = {
    "auto": "התאם את לשון הפנייה למי שכתב את הפוסט. אם לא ברור — פנה בלשון ניטרלית.",
    "feminine": "פנה תמיד בלשון נקבה.",
    "masculine": "פנה תמיד בלשון זכר.",
    "neutral": "פנה תמיד בלשון ניטרלית, בלי להטות למין מסוים.",
}


class Analysis(BaseModel):
    relevant: bool
    intent: Intent
    sensitivity: Literal["bereavement", "sensitive", "neutral"]
    audience: str
    occasion: str
    product_slug: str
    confidence: float
    needs_human: bool
    reasoning: str
    comment: str
    dm_opener: str


RULES = """אתה עוזר הניסוח של עסק קטן בישראל בשם "{name}" — {what}.

המשימה: לקרוא פוסט מקבוצת פייסבוק, להחליט אם הוא רלוונטי לעסק, ואם כן לנסח
תגובה ציבורית קצרה והודעת פתיחה לפרטי. אתה לא מפרסם כלום — בעל העסק קורא
כל הצעה ומאשר אותה בעצמו.

## איך נשמעת תגובה טובה
- קצרה: משפט עד שלושה. אדם אמיתי לא כותב פסקה בתגובה בקבוצה.
- עניינית, לא מכירתית. בלי סימני קריאה, בלי סופרלטיבים, בלי "מוזמנת לפנות!!!".
- בלי מחיר. אף פעם. גם לא "במחיר משתלם" או "מחירים נוחים".
- אימוג'י אחד לכל היותר, ורק אם הוא באמת מתאים. עדיף בלי.
- לא פותחת ב"היי" או "שלום" — בתגובה בקבוצה זה נשמע כמו תבנית מודבקת.
- עונה למה שהאדם ביקש, לא למה שנוח לנו למכור.
- לא מכריזה על העסק. אם צריך להזכיר אותו, בדרך אגב.

## כללי ברזל
1. אם הפוסט לא באמת רלוונטי — relevant=false והשאר את comment ו-dm_opener ריקים.
   עדיף לא להגיב מאשר להגיב בכוח. זה לא ייחשב לך כישלון.
2. אם הפוסט נוגע באובדן, אבל, מוות, אזכרה, יתמות או שכול — sensitivity="bereavement"
   ו-needs_human=true, תמיד. בתגובה כזו אין מכירה: התייחסות עדינה, ואם מתאים —
   הצעה לשלוח פרטים בפרטי. שום דבר מעבר.
3. אל תמציא פרטים על המוצר. מה שלא כתוב בקטלוג למטה — לא קיים.
4. אל תבטיח זמני אספקה, מלאי או התאמות שלא מופיעים בקטלוג.
5. עברית יומיומית ותקנית. לא תרגומית, לא מליצית.
6. {address_form}

## הודעת הפתיחה בפרטי
- ממשיכה את מה שהאדם כתב, לא מעתיקה את התגובה הציבורית.
- שורה אחת שמסבירה מי אנחנו, ושאלה אחת שמקדמת את השיחה
  (למשל: למי זה מיועד, או איזו תמונה יש).
- בלי מחיר בהודעה הראשונה, אלא אם נשאלנו על מחיר ישירות.
- קצרה. שלוש שורות לכל היותר.

## שדות התשובה
- confidence: 0 עד 1, כמה אתה בטוח שהפוסט רלוונטי ושהתגובה מתאימה.
- needs_human: true אם יש סיבה שבעל העסק יקרא את זה בעיון לפני שליחה.
- product_slug: המזהה של המוצר המתאים מהקטלוג, או מחרוזת ריקה אם אין התאמה.
- reasoning: משפט אחד בעברית שמסביר למה בחרת ככה. זה נועד לעיני בעל העסק.
"""


def _catalog_block(products: list[dict[str, Any]]) -> str:
    if not products:
        return "## קטלוג המוצרים\n(הקטלוג ריק — אל תמליץ על שום מוצר.)"
    lines = ["## קטלוג המוצרים"]
    for p in products:
        lines.append(f"\n### {p['name']}  (slug: {p['slug']})")
        if p.get("tagline"):
            lines.append(f"משפט פתיחה: {p['tagline']}")
        if p.get("description"):
            lines.append(f"תיאור: {p['description']}")
        if p.get("audience"):
            lines.append(f"למי מתאים: {p['audience']}")
        if p.get("customization"):
            lines.append(f"התאמה אישית: {p['customization']}")
        if p.get("lead_time"):
            lines.append(f"זמן ייצור: {p['lead_time']}")
        if p.get("shipping"):
            lines.append(f"משלוח: {p['shipping']}")
        if p.get("keywords"):
            lines.append("מילות מפתח: " + ", ".join(p["keywords"]))
        if p.get("notes"):
            lines.append(f"הערות פנימיות (לא לצטט): {p['notes']}")
    return "\n".join(lines)


def _examples_block() -> str:
    comments = db.list_examples("comment", limit=8)
    dms = db.list_examples("dm", limit=5)
    if not comments and not dms:
        return ""
    lines = ["## דוגמאות לניסוחים שבעל העסק אישר — חקה את הטון הזה"]
    for ex in reversed(comments):
        if ex["post_text"]:
            lines.append(f"\nפוסט: {ex['post_text'][:300]}")
        lines.append(f"תגובה שאושרה: {ex['text']}")
    for ex in reversed(dms):
        lines.append(f"\nהודעת פתיחה שאושרה: {ex['text']}")
    return "\n".join(lines)


def build_system_prompt(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    address_form = ADDRESS_FORMS.get(db.get_setting("address_form", "auto"), ADDRESS_FORMS["auto"])
    stable = RULES.format(name=BUSINESS["name"], what=BUSINESS["what"], address_form=address_form)
    stable += "\n\n" + _catalog_block(products)
    blocks: list[dict[str, Any]] = [
        {"type": "text", "text": stable, "cache_control": {"type": "ephemeral"}}
    ]
    examples = _examples_block()
    if examples:
        blocks.append({"type": "text", "text": examples})
    return blocks


def _user_message(text: str, group_name: str, author_name: str) -> str:
    parts = []
    if group_name:
        parts.append(f"קבוצה: {group_name}")
    if author_name:
        parts.append(f"כתב/ה: {author_name}")
    parts.append("תוכן הפוסט:\n" + text.strip())
    return "\n".join(parts)


def _template_analysis(text: str, products: list[dict[str, Any]]) -> Analysis:
    """נוסח תבניתי לשימוש כשאין מפתח API — מאפשר לבדוק את המערכת בלי לשלם."""
    product = best_product(text, products)
    slug = product["slug"] if product else ""
    name = product["name"] if product else "מה שאנחנו עושים"
    return Analysis(
        relevant=bool(product),
        intent="general_interest",
        sensitivity="neutral",
        audience="",
        occasion="",
        product_slug=slug,
        confidence=0.3,
        needs_human=True,
        reasoning="נוסח תבניתי — אין מפתח Claude מוגדר, אז לא בוצע ניתוח אמיתי.",
        comment=f"יש לנו כמה אפשרויות שיכולות להתאים ({name}). אם תרצו, אשמח לשלוח פרטים בפרטי.",
        dm_opener="היי, ראיתי את הפוסט שלך. אנחנו מייצרים אבני זיכרון מוארות בהזמנה אישית סביב תמונה. למי זה מיועד?",
    )


def analyze(text: str, group_name: str, author_name: str, products: list[dict[str, Any]]) -> tuple[Analysis, dict[str, Any]]:
    """מחזיר (ניתוח, מטא־דאטה). המטא כולל את שם המנוע ומספר הטוקנים."""
    if not ai_enabled():
        return _template_analysis(text, products), {"engine": "template", "usage_in": 0, "usage_out": 0}

    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    kwargs: dict[str, Any] = {
        "model": CLAUDE_MODEL,
        "max_tokens": 4000,
        "system": build_system_prompt(products),
        "messages": [{"role": "user", "content": _user_message(text, group_name, author_name)}],
        "output_format": Analysis,
    }

    try:
        response = client.messages.parse(thinking={"type": "adaptive"}, **kwargs)
    except anthropic.BadRequestError as exc:
        # יש מודלים שלא מקבלים thinking יחד עם פלט מובנה — ננסה שוב בלעדיו
        db.log_event("ai_retry", "ניסיון חוזר בלי thinking", {"error": str(exc)[:500]})
        response = client.messages.parse(**kwargs)

    analysis = response.parsed_output
    meta = {
        "engine": CLAUDE_MODEL,
        "usage_in": getattr(response.usage, "input_tokens", 0) or 0,
        "usage_out": getattr(response.usage, "output_tokens", 0) or 0,
    }
    return analysis, meta


def analysis_to_dict(analysis: Analysis) -> dict[str, Any]:
    return json.loads(analysis.model_dump_json())
