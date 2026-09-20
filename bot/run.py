"""נקודת הכניסה: python run.py ואז פותחים את הכתובת שמודפסת."""
from app.config import HOST, PORT, ai_enabled
from app.db import business, init_db
from app.web import create_app


def main() -> None:
    init_db()
    app = create_app()
    print(f"\n  {business()['business_name']} · מנוע התגובות")
    print(f"  פתחו בדפדפן:  http://{HOST}:{PORT}")
    print(f"  מצב AI: {'פעיל' if ai_enabled() else 'כבוי (נוסח תבניתי) — חסר ANTHROPIC_API_KEY ב-.env'}\n")
    app.run(host=HOST, port=PORT, debug=False)


if __name__ == "__main__":
    main()
