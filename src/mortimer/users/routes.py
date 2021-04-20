# -*- coding: utf-8 -*-
import string, random

from flask import Blueprint, current_app
from flask import render_template, url_for, flash, redirect, request, abort
from mortimer import bcrypt
from mortimer.forms import (
    RegistrationForm,
    LoginForm,
    UpdateAccountForm,
    RequestResetForm,
    ResetPasswordForm,
)
from mortimer.models import User, WebExperiment
from mortimer.utils import send_reset_email, create_fernet
from flask_login import login_user, current_user, logout_user, login_required

# pylint: disable=no-member
users = Blueprint("users", __name__)


@users.route("/register", methods=["GET", "POST"])
def register():

    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegistrationForm()

    if form.validate_on_submit():
        if User.objects(username=form.username.data):
            flash("Username already taken. Please choose a different one.", "error")
            return redirect(url_for("users.register"))
        elif User.objects(email=form.email.data):
            flash("Email already taken. Please choose a different one.", "error")
            return redirect(url_for("users.register"))

        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        user.encryption_key = User.generate_encryption_key()
        user.set_db_config()

        # save user
        user.save()
        flash("Account created for %s." % form.username.data, "success")
        return redirect(url_for("users.login"))

    password_hint = "This is a password hint"

    # the named arguments here will be passed to the .html file
    # this way, they can be accessed in jinja2 templates
    return render_template(
        "register.html", title="Register", form=form, password_hint=password_hint
    )


@users.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.objects(email=form.email.data).first()  # pylint: disable=no-member

        if user is not None and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")
            flash("Login Successful.", "success")

            # for backwards compatibility, generate encryption key if there isnt already one
            if not user.encryption_key:
                user.encryption_key = User.generate_encryption_key()
                user.save()

            return redirect(next_page) if next_page else redirect(url_for("main.home"))
        else:
            flash("Login Unsuccessful. Please check username and password", "danger")

    return render_template("login.html", title="Login", form=form)


@users.route("/logout")
def logout():

    logout_user()
    flash("Succesfully logged out", "info")

    return redirect(url_for("main.home"))


@users.route("/account", methods=["GET", "POST"])
@login_required  # this route can only be accessed by logged in users
def account():
    # pylint: disable=no-member
    form = UpdateAccountForm()

    if form.validate_on_submit():  # if all field are filled out correctly

        if current_user.username != form.username.data:
            for exp in WebExperiment.objects(author=current_user.username):
                exp.author = form.username.data
                exp.save()

        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.save()  # save updates to database
        flash("Your account has been updated.", "success")
        return redirect(url_for("users.account"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.email.data = current_user.email

    return render_template(
        "account.html", title="Account", form=form, user=current_user
    )


@users.route("/request_password_reset", methods=["GET", "POST"])
def request_password_reset():

    if current_user.is_authenticated:
        flash("You are currently logged in.", "info")
        return redirect(url_for("main.home"))

    if not current_app.config["MAIL_USE"]:
        flash("Automatic password reset is disabled. Please contact the administrator.", "warning")
        return redirect(url_for("main.home"))

    form = RequestResetForm()

    if form.validate_on_submit():
        user = User.objects(email=form.email.data).first()  # pylint: disable=no-member
        send_reset_email(user)
        flash("An email has been sent with instructions to reset your password", "info")
        return redirect(url_for("users.login"))

    return render_template("request_password_reset.html", title="Reset Password", form=form)


@users.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):

    if current_user.is_authenticated:
        flash("You are currently logged in.", "info")
        return redirect(url_for("main.home"))

    user = User.verify_reset_token(token)

    if user is None:
        flash("The reset token is either invalid or expired", "warning")
        return redirect(url_for("users.request_password_reset"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user.password = hashed_password
        user.save()
        flash("Your password has been updated.", "success")
        return redirect(url_for("users.login"))

    return render_template("reset_password.html", title="Reset Password", form=form)
