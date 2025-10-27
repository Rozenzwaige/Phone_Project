# models.py
from flask_login import UserMixin

class EnvUser(UserMixin):
    """
    מודל משתמש פשוט עבור הזדהות מבוססת ENV (USERS_JSON), בלי DB.
    """
    def __init__(self, email: str, active: bool = True):
        self.id = (email or "").strip().lower()
        self.email = self.id
        self._active = active

    def is_active(self):
        return self._active
