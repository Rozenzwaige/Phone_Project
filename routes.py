# routes.py
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from bq import search_contacts
from bq import search_contacts, log_search_event

from app import app
import config
from models import EnvUser


# === דף הבית (מוגן): מציג את index.html שלך ===
@app.route("/")
@login_required
def home():
    return render_template("index.html", email=current_user.email)


# === לוגין לפי USERS_JSON (ENV) ===
@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("home")

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        rec = config.load_user_record(email, app.config.get("USERS_JSON"))
        if not rec or not rec.get("active", True):
            flash("האימייל לא מורשה", "danger")
            return render_template("login.html", next_url=next_url), 401

        ok = False
        if rec.get("hash"):         # מצב מאובטח (hash)
            ok = check_password_hash(rec["hash"], password)
        elif rec.get("password"):   # מצב פשוט (plaintext ב-ENV)
            ok = (password == rec["password"])

        if not ok:
            flash("סיסמה שגויה", "danger")
            return render_template("login.html", next_url=next_url), 401

        login_user(EnvUser(rec["email"], active=rec.get("active", True)), remember=False)
        return redirect(request.form.get("next") or next_url)

    # GET
    return render_template("login.html", next_url=next_url)


# === עמוד החיפוש (מוגן): מקבל את הטופס מ-index.html ומציג תוצאות ב-search.html ===

@app.route("/search", methods=["GET"])
@login_required
def search():
    search_type = request.args.get("search_type", "free")
    query = (request.args.get("query") or "").strip()

    rows = None
    if query:
        try:
            rows = search_contacts(search_type=search_type, q=query, limit=100)
        except Exception as e:
            # נרשום ללוג ונציג הודעה ידידותית
            app.logger.exception("BigQuery search failed")
            flash(f"שגיאת חיפוש: {e}", "danger")
            rows = []

    return render_template(
        "search.html",
        email=current_user.email,
        search_type=search_type,
        query=query,
        rows=rows,
    )
# === תאימות לאחור: /dashboard מפנה לעמוד הבית ===
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


# === אין רישום; משאירים endpoint="register" כדי שקישורים ישנים לא יפלו ===
@app.route("/register", endpoint="register")
def register_disabled():
    return redirect(url_for("login"))

@app.route("/__whoami__")
def whoami():
    import os, json
    with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), "r") as f:
        sa = json.load(f)
    return {"client_email": sa.get("client_email")}
@app.route("/__bqcfg__")
def bqcfg():
    import os
    return {
        "BQ_TABLE_FQ": os.getenv("BQ_TABLE_FQ"),
        "BQ_LOCATION": os.getenv("BQ_LOCATION"),
    }
