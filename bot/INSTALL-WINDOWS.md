# התקנה על ווינדוס

להעתיק ולהדביק ל-Command Prompt, שורה אחרי שורה.

## פעם אחת — הורדת הקוד והתקנה

```cmd
cd %USERPROFILE%
git clone -b claude/facebook-bot-planning-zu6ld6 https://github.com/Yehudakanashti/or-shenishar.git
cd or-shenishar\bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python seed.py
```

**אם `git` לא מוכר** — להוריד ZIP במקום:
<https://github.com/Yehudakanashti/or-shenishar/archive/refs/heads/claude/facebook-bot-planning-zu6ld6.zip>

לחלץ לשולחן העבודה, ואז:

```cmd
cd %USERPROFILE%\Desktop\or-shenishar-claude-facebook-bot-planning-zu6ld6\bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python seed.py
```

## מפתח Claude

לפתוח את `bot\.env` בפנקס רשימות ולהדביק את המפתח בשורה המתאימה:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## חיבור הדף

אחרי שיש App ID, App Secret וטוקן קצר (ראו SETUP-FACEBOOK.md):

```cmd
python setup_facebook.py
```

## הפעלה יומיומית

```cmd
cd %USERPROFILE%\or-shenishar\bot
venv\Scripts\activate
python run.py
```

ואז לפתוח בדפדפן: <http://127.0.0.1:5000>

---

## אם משהו נתקע

| הודעה | מה לעשות |
|---|---|
| `can't open file ... setup_facebook.py` | אתם לא בתיקייה הנכונה. `cd %USERPROFILE%\or-shenishar\bot` |
| `'git' is not recognized` | להוריד ZIP לפי הקישור למעלה |
| `'python' is not recognized` | להתקין פייתון מ-python.org ולסמן **Add to PATH** |
| `'pip' is not recognized` | שכחתם `venv\Scripts\activate` |
| `ModuleNotFoundError: flask` | אותו דבר — להפעיל את ה-venv ואז `pip install -r requirements.txt` |
