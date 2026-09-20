"""מפרסם פוסטים מאושרים שהגיע זמנם.

הרצה ידנית:  python publish_due.py
או בתזמון (cron / Task Scheduler) כל 15 דקות.
"""
import sys

from app.db import init_db, now_local
from app.publisher import publish_due


def main() -> int:
    init_db()
    print(f"  {now_local().strftime('%Y-%m-%d %H:%M')} — בודק פוסטים לפרסום")
    results = publish_due()
    if not results:
        print("  אין פוסטים שהגיע זמנם.")
        return 0
    failed = 0
    for post_id, ok, message in results:
        print(f"  {'✓' if ok else '✗'} פוסט #{post_id}: {message}")
        failed += 0 if ok else 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
