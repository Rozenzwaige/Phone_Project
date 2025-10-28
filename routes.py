# routes.py
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash

from app import app
import config
from models import EnvUser


# === דף הבית (מוגן) ===
@app.route("/")
@login_required
def home():
    return render_template("home.html", email=current_user.email)


# === לוגין ===
@app.route("/login", methods=["GET", "POST"])
def login():
    # אחרי לוגין מפנים ל-home כברירת מחדל
    next_url = request.args.get("next") or url_for("home")

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        rec = config.load_user_record(email, app.config.get("USERS_JSON"))
        if not rec or not rec.get("active", True):
            flash("האימייל לא מורשה", "danger")
            return render_template("login.html", next_url=next_url), 401

        ok = False
        if rec.get("hash"):
            ok = check_password_hash(rec["hash"], password)
        elif rec.get("password"):
            ok = (password == rec["password"])

        if not ok:
            flash("סיסמה שגויה", "danger")
            return render_template("login.html", next_url=next_url), 401

        login_user(EnvUser(rec["email"], active=rec.get("active", True)), remember=False)
        return redirect(request.form.get("next") or next_url)

    # GET
    return render_template("login.html", next_url=next_url)


# === תאימות לאחור: /dashboard מפנה ל-Home ===
@app.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("home"))


# === לוגאאוט ===
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# === אין רישום בגרסת בלי-DB; שומרים endpoint="register" למקרה שיש קישורים ישנים ===
@app.route("/register", endpoint="register")
def register_disabled():
    return redirect(url_for("login"))
