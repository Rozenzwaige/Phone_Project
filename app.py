# app.py
import os
import smtplib
from email.mime.text import MIMEText

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.middleware.proxy_fix import ProxyFix

from forms import LoginForm
import config  # נטען ממנו את Config

app = Flask(__name__)
app.config.from_object("config.Config")  # <-- חשוב: טוען SECRET_KEY, DB, cookies וכו'
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)  # מאחורי פרוקסי (Render)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"


# === מודל משתמש בסיסי: אימייל/סיסמה/אישור אדמין ===
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password = db.Column(db.String(150), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<User {self.email} approved={self.is_approved}>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# === דפים ===
@app.route("/")
def home():
    # אם מחובר/ת – לדשבורד; אחרת לטופס התחברות
    return redirect(url_for("dashboard") if current_user.is_authenticated else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    next_url = request.args.get("next") or request.form.get("next") or url_for("dashboard")

    if form.validate_on_submit():
        email = (form.email.data or "").strip().lower()
        password = form.password.data or ""
        user = User.query.filter_by(email=email).first()

        if not user or not bcrypt.check_password_hash(user.password, password):
            flash("פרטים שגויים", "danger")
            return render_template("login.html", form=form, next_url=next_url), 401

        if not user.is_approved:
            flash("המשתמש ממתין לאישור מנהל/ת.", "warning")
            return render_template("login.html", form=form, next_url=next_url), 403

        login_user(user, remember=False)
        return redirect(next_url)

    return render_template("login.html", form=form, next_url=next_url)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash("חסר אימייל או סיסמה.", "danger")
            return render_template("register.html")

        # בדיקה אם קיים
        if User.query.filter_by(email=email).first():
            flash("אימייל זה כבר רשום.", "warning")
            return render_template("register.html")

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(email=email, password=hashed_password, is_approved=False)
        db.session.add(new_user)
        db.session.commit()

        # שליחת התראה לאדמין (אופציונלי)
        try:
            send_email_notification(email)
        except Exception as e:
            # לא חוסם את הזרימה אם המייל נכשל
            app.logger.warning(f"Email notification failed: {e}")

        flash("הבקשה נרשמה. המתן/י לאישור מנהל/ת.", "info")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", email=current_user.email)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# === שליחת מייל לאדמין על רישום חדש (ENV) ===
def send_email_notification(user_email: str):
    """
    שולח הודעה לאדמין על רישום חדש.
    הגדר ב-ENV (ברנדר):
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ADMIN_EMAIL, FROM_EMAIL
    אם אין, הפונקציה תרים חריגה וניתפס למעלה בלוג.
    """
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ["SMTP_USER"]
    smtp_pass = os.environ["SMTP_PASS"]
    admin_email = os.environ["ADMIN_EMAIL"]
    from_email = os.environ.get("FROM_EMAIL", smtp_user)

    subject = "New User Registration Request"
    body = f"A new user has registered with email: {user_email}. Please review and approve."
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = admin_email

    # STARTTLS (587). אם אתה משתמש ב-SSL (465) – שנה בהתאם ל-SMTP שלך.
    import ssl, smtplib
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


# === אתחול DB מקומי בלבד (לנוחות פיתוח) ===
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
