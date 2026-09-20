"""בדיקה שהחיבור לדף הפייסבוק עובד.

הרצה:  python check_facebook.py
מדפיס מה עובד, מה חסר, ומתי הטוקן פג.
"""
import json
import sys
from urllib import error, parse, request

from app.config import (
    FB_API_VERSION, FB_APP_ID, FB_APP_SECRET, FB_PAGE_ID, FB_PAGE_TOKEN, facebook_enabled,
)

GRAPH = "https://graph.facebook.com"
OK, FAIL, WARN = "  ✓", "  ✗", "  !"


def call(path: str, params: dict) -> tuple[bool, dict]:
    url = f"{GRAPH}/{FB_API_VERSION}/{path.lstrip('/')}?{parse.urlencode(params)}"
    try:
        with request.urlopen(url, timeout=30) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return False, json.loads(body).get("error", {"message": body})
        except json.JSONDecodeError:
            return False, {"message": body[:300]}
    except Exception as exc:  # noqa: BLE001
        return False, {"message": str(exc)}


def main() -> int:
    print(f"\n  בדיקת חיבור לפייסבוק (Graph API {FB_API_VERSION})\n")

    if not facebook_enabled():
        print(f"{FAIL} אין FB_PAGE_ID או FB_PAGE_TOKEN בקובץ .env")
        print("     ראו את המדריך: SETUP-FACEBOOK.md\n")
        return 1

    ok, page = call(FB_PAGE_ID, {"fields": "id,name,followers_count,link", "access_token": FB_PAGE_TOKEN})
    if not ok:
        print(f"{FAIL} הטוקן או מזהה הדף לא תקינים")
        print(f"     {page.get('message', '')}\n")
        return 1
    print(f"{OK} מחובר לדף: {page.get('name')}  (מזהה {page.get('id')})")
    if page.get("followers_count") is not None:
        print(f"     עוקבים: {page['followers_count']}")

    ok, posts = call(f"{FB_PAGE_ID}/posts", {"fields": "id", "limit": 1, "access_token": FB_PAGE_TOKEN})
    print(f"{OK} קריאת פוסטים מהדף" if ok else f"{FAIL} אין הרשאה לקרוא פוסטים — {posts.get('message','')[:120]}")

    if FB_APP_ID and FB_APP_SECRET:
        ok, info = call("debug_token", {
            "input_token": FB_PAGE_TOKEN,
            "access_token": f"{FB_APP_ID}|{FB_APP_SECRET}",
        })
        data = info.get("data", {}) if ok else {}
        if ok and data:
            expires = data.get("expires_at", 0)
            print(f"{OK} תוקף הטוקן: {'לא פג' if not expires else f'פג ב-{expires}'}")
            scopes = data.get("scopes", [])
            print(f"     הרשאות: {', '.join(scopes) if scopes else 'לא דווחו'}")
            needed = {"pages_manage_posts", "pages_read_engagement", "pages_manage_engagement"}
            missing = needed - set(scopes)
            if missing:
                print(f"{WARN} חסרות הרשאות: {', '.join(sorted(missing))}")
            if "pages_messaging" not in scopes:
                print(f"{WARN} אין pages_messaging — הודעה בפרטי תעבוד רק אחרי אימות עסקי ו-App Review")
        else:
            print(f"{WARN} לא הצלחתי לבדוק את תוקף הטוקן")
    else:
        print(f"{WARN} בלי FB_APP_ID ו-FB_APP_SECRET אי אפשר לבדוק את תוקף הטוקן")

    print("\n  הכול מוכן. הבוט יכול לפרסם בדף ולקרוא תגובות.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
