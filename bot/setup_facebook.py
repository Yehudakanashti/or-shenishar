"""חיבור הדף לפייסבוק בפקודה אחת.

מה שאתם צריכים להביא (שלבים 1–2 ב-SETUP-FACEBOOK.md):
  App ID, App Secret, וטוקן קצר מה-Graph API Explorer.

הסקריפט עושה את כל השאר: מאריך את הטוקן, מוצא את הדף, מקבל טוקן קבוע,
כותב את הכול ל-.env ומוודא שהחיבור עובד.

הרצה:  python setup_facebook.py
"""
import json
import sys
from getpass import getpass
from urllib import error, parse, request

from app.config import BASE_DIR, FB_API_VERSION

ENV_PATH = BASE_DIR / ".env"
GRAPH = "https://graph.facebook.com"


def call(path: str, params: dict) -> dict:
    url = f"{GRAPH}/{FB_API_VERSION}/{path}?{parse.urlencode(params)}"
    try:
        with request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(body)["error"]["message"]
        except (json.JSONDecodeError, KeyError):
            message = body[:300]
        raise SystemExit(f"\n  ✗ פייסבוק החזירה שגיאה:\n     {message}\n")


def write_env(values: dict[str, str]) -> None:
    """מעדכן מפתחות ב-.env בלי לדרוס את מה שכבר שם."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    seen = set()
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in values:
            out.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in values.items():
        if key not in seen:
            out.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    print("\n  חיבור הדף לפייסבוק")
    print("  לפני שמתחילים צריך App ID, App Secret וטוקן קצר — ראו SETUP-FACEBOOK.md\n")

    app_id = input("  App ID: ").strip()
    app_secret = getpass("  App Secret (לא יוצג): ").strip()
    short_token = getpass("  הטוקן הקצר מה-Explorer (לא יוצג): ").strip()
    if not (app_id and app_secret and short_token):
        print("\n  ✗ צריך למלא את שלושת הערכים.\n")
        return 1

    print("\n  מאריך את הטוקן…")
    long_token = call("oauth/access_token", {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    }).get("access_token", "")
    if not long_token:
        print("  ✗ לא התקבל טוקן ארוך.\n")
        return 1
    print("  ✓ הטוקן הוארך")

    print("  מחפש את הדפים שלך…")
    pages = call("me/accounts", {"access_token": long_token, "fields": "id,name,access_token"}).get("data", [])
    if not pages:
        print("\n  ✗ לא נמצאו דפים. ודאו שאישרתם את ההרשאה pages_show_list ושסימנתם את הדף.\n")
        return 1

    if len(pages) == 1:
        page = pages[0]
        print(f"  ✓ נמצא דף אחד: {page['name']}")
    else:
        print()
        for index, item in enumerate(pages, 1):
            print(f"     {index}. {item['name']}")
        choice = input("\n  איזה דף? מספר: ").strip()
        try:
            page = pages[int(choice) - 1]
        except (ValueError, IndexError):
            print("\n  ✗ בחירה לא תקינה.\n")
            return 1

    write_env({
        "FB_PAGE_ID": page["id"],
        "FB_PAGE_TOKEN": page["access_token"],
        "FB_APP_ID": app_id,
        "FB_APP_SECRET": app_secret,
        "FB_API_VERSION": FB_API_VERSION,
    })
    print(f"  ✓ נכתב ל-{ENV_PATH.name}: הדף ״{page['name']}״ (מזהה {page['id']})")
    print("\n  מאמת את החיבור…\n")

    from importlib import reload
    from app import config
    reload(config)
    import check_facebook
    reload(check_facebook)
    return check_facebook.main()


if __name__ == "__main__":
    sys.exit(main())
