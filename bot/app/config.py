"""הגדרות גלובליות. כל מה שסודי נקרא מקובץ .env ולא נשמר בגיט."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "bot.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

load_dotenv(BASE_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5").strip() or "claude-opus-5"

FB_PAGE_ID = os.getenv("FB_PAGE_ID", "").strip()
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN", "").strip()
FB_APP_ID = os.getenv("FB_APP_ID", "").strip()
FB_APP_SECRET = os.getenv("FB_APP_SECRET", "").strip()
FB_API_VERSION = os.getenv("FB_API_VERSION", "v25.0").strip()

HOST = os.getenv("BOT_HOST", "127.0.0.1").strip()
PORT = int(os.getenv("BOT_PORT", "5000"))

TIMEZONE = "Asia/Jerusalem"
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024

# ברירת מחדל בלבד — הערכים האמיתיים נערכים במסך ההגדרות ונשמרים במסד
BUSINESS_DEFAULTS = {
    "business_name": "מתנות לכל גיל",
    "business_what": "מוצרי חג מודפסים בתלת־ממד, מוארים מבפנים, עם כיתוב שנקבע לפי ההזמנה",
    "business_site": "",
}

# ברירות מחדל שנכתבות לטבלת settings בהתקנה ראשונה
DEFAULT_SETTINGS = {
    "auto_mode": "off",             # off = כל הצעה עוברת אישור שלך
    "kill_switch": "off",           # on = הבוט מפסיק לקלוט פוסטים
    "daily_cap": "12",              # מקסימום הצעות ליום
    "author_cooldown_days": "30",   # לא להציע שוב לאותו אדם בתוך X ימים
    "min_confidence": "0.55",       # מתחת לזה מסומן כדורש תשומת לב
    "allow_links_in_comment": "0",  # 0 = בלי קישורים בתגובה ציבורית
    "max_comment_chars": "320",
    "address_form": "auto",         # auto | feminine | masculine | neutral
    "allow_price_in_post": "0",      # מחיר בפוסט בדף (בתגובות — לעולם לא)
    "season_lead_days": "21",       # כמה ימים לפני תחילת העונה מוצר נחשב רלוונטי
    **BUSINESS_DEFAULTS,
}


def ai_enabled() -> bool:
    return bool(ANTHROPIC_API_KEY)


def facebook_enabled() -> bool:
    return bool(FB_PAGE_ID and FB_PAGE_TOKEN)
