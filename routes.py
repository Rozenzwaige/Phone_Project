from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app import db, bcrypt
from models import User
from forms import RegistrationForm, LoginForm

auth = Blueprint("auth", __name__)

@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            if not user.is_approved:
                flash("Your account is pending approval.", "warning")
                return redirect(url_for("auth.login"))
            login_user(user)
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)

@auth.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User(email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash("Your account has been created! Please wait for admin approval.", "info")
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)

@auth.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@auth.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
