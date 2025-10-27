# app.py
import os
from flask import Flask
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

import config
from models import EnvUser  # מודל משתמש פשוט בלי DB

app = Flask(__name__)
app.config.from_object("config.Config")

# אם אתה מאחורי פרוקסי (Render), זה מבטיח שקוקיז מאובטחים יעבדו:
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"

@login_manager.user_loader
def load_user(user_id):
    rec = config.load_user_record(user_id, app.config.get("USERS_JSON"))
    if rec:
        return EnvUser(rec["email"], active=rec.get("active", True))
    return None

# חשוב: לייבא routes רק אחרי שהapp והlogin_manager מאותחלים
import routes  # noqa

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
