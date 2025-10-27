import os, json

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = "sqlite:///database.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cookies (בפרודקשן): ברנדר זה HTTPS, אז True. לפיתוח מקומי אפשר להפוך ל-False.
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # רשימת משתמשים מאושרים כ־JSON (מ־ENV):
    # [{"email":"x@y.com","hash":"pbkdf2:sha256:...","active": true}]
    USERS_JSON = os.environ.get("USERS_JSON", "[]")


def load_user_record(email: str, users_json: str = None):
    """מחזיר את רשומת המשתמש לפי אימייל, או None אם לא נמצא/לא פעיל."""
    uj = users_json if users_json is not None else Config.USERS_JSON
    try:
        users = json.loads(uj)
    except Exception:
        users = []
    email = (email or "").strip().lower()
    for u in users:
        if u.get("email", "").strip().lower() == email and u.get("active", True):
            return u
    return None
