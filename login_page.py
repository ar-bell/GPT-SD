from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from werkzeug.security import check_password_hash
import os

from deck_database import db, User

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///deck.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Login form
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")

# Routes
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session["user_email"] = user.email
            flash("Logged in successfully!", "success")
            return redirect(url_for("home"))  # update based on  route
        flash("Invalid credentials", "danger")
    return render_template("login.html", form=form)

@app.route("/logout")
def logout():
    session.pop("user_email", None)
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))

