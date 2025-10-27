# routes.py
import os
import ssl
import smtplib
from email.mime.text import MIMEText

from flask import render_template, redirect, url_for, request, flash
from flask_login import (
    login_user, login_required, logout_user, current_user
)

from app import app, db, bcrypt          # נוצרו ב-app.py
from models import User                  # מודל המשתמש

# ===== דפים =====

@app.route("/")
def home():
    # אם מחובר/ת – לדשבורד; אחרת למסך התחברות
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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash("חסר אימייל או סיסמה.", "danger")
            return render_template("register.html")

        # כבר קיים?
        if User.query.filter_by(email=email).first():
            flash("אימייל זה כבר רשום.", "warning")
            return render_template("register.html")

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(email=email, password=hashed_password, is_approved=False)
        db.session.add(new_user)
        db.session.commit()

        try:
            send_email_notification(email)
        except Exception as e:
            app.logger.warning(f"Email notification failed: {e}")

        flash("הבקשה נרשמה. המתן/י לאישור מנהל/ת.", "info")
        return redirect(url_for("login"))

    # GET
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
