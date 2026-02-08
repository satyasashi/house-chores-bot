from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user
from app.models import AdminUser
from app.config import Config

auth_bp = Blueprint("auth", __name__)

@auth_bp.get("/login")
def login():
    return render_template("login.html")

@auth_bp.post("/login")
def login_post():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
        login_user(AdminUser())
        return redirect(url_for("admin.dashboard"))

    flash("Invalid credentials")
    return redirect(url_for("auth.login"))

@auth_bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
