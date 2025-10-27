import os, json

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    # אין DB בלוגין, אז אפשר להשמיט את שלוש השורות של SQLAlchemy
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    USERS_JSON = os.environ.get("USERS_JSON", "[]")

def load_user_record(email: str, users_json: str = None):
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
