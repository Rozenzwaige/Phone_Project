# routes.py
import os
import ssl
import smtplib
from email.mime.text import MIMEText

from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from app import app
import config
from models import EnvUser

# ===== דפים =====

@app.route("/")
def home():
    return redirect(url_for("dashboard") if current_user.is_authenticated else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("dashboard")

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()

        if not user or not bcrypt.check_password_hash(user.password, password):
            flash("פרטים שגויים", "danger")
            return render_template("login.html", next_url=next_url), 401

        if not user.is_approved:
            flash("המשתמש ממתין לאישור מנהל/ת.", "warning")
            return render_template("login.html", next_url=next_url), 403

        login_user(user, remember=False)
        # אם הוגדר next בפרמטרים – נכבד אותו
        return redirect(request.form.get("next") or next_url)

    # GET
    return render_template("login.html", next_url=next_url)


@app.route("/login", methods=["GET","POST"])
def login():
    next_url = request.args.get("next") or url_for("dashboard")
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        rec = config.load_user_record(email, app.config.get("USERS_JSON"))

        if not rec or not rec.get("active", True):
            flash("האימייל לא מורשה", "danger")
            return render_template("login.html", next_url=next_url), 401

        ok = False
        if rec.get("hash"):            # מצב מאובטח (hash)
            ok = check_password_hash(rec["hash"], password)
        elif rec.get("password"):      # מצב פשוט (plaintext ב-ENV)
            ok = (password == rec["password"])
        if not ok:
            flash("סיסמה שגויה", "danger")
            return render_template("login.html", next_url=next_url), 401

        login_user(EnvUser(rec["email"], active=rec.get("active", True)), remember=False)
        return redirect(request.form.get("next") or next_url)

    return render_template("login.html", next_url=next_url)

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", email=current_user.email)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# אופציונלי: נטרל לגמרי רישום (אין DB)
@app.route("/register")
def register_disabled():
    return redirect(url_for("login"))


# ===== שליחת מייל לאדמין על רישום חדש (דרך ENV) =====

def send_email_notification(user_email: str):
    """
    שולח הודעה לאדמין על רישום חדש.
    הגדר ב-ENV:
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ADMIN_EMAIL, FROM_EMAIL (אופציונלי)
    אם חסר קונפיג – נדלג בשקט עם אזהרה ללוג.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))  # 587 ל-STARTTLS
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    admin_email = os.getenv("ADMIN_EMAIL")
    from_email = os.getenv("FROM_EMAIL") or smtp_user

    # אם אין קונפיג מלא – לא נעצור את הזרימה
    if not all([smtp_host, smtp_user, smtp_pass, admin_email]):
        app.logger.warning("SMTP env vars missing; skipping email notification")
        return

    subject = "New User Registration Request"
    body = f"A new user has registered with email: {user_email}. Please review and approve."
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = admin_email

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
