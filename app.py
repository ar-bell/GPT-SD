from flask import Flask, jsonify, render_template, redirect, request, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from werkzeug.security import check_password_hash
import os

from deck_database import Card, Deck
from home_page import get_current_user

# Setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret") # MAKE SURE THIS IS HANDLED
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///deck.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Login Form
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")

# Routes
@app.route("/", methods=["GET"])
@app.route("/home", methods=["GET"])
@login_required
def home():
    return render_template("home.html")

@app.route("/search")
def search():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    query = request.args.get("query", "").strip()
    if len(query) < 2:
        return jsonify({"error": "Query too short"}), 400

    term = f"%{query}%"
    decks = Deck.query.filter(
        Deck.owner_id == user.id,
        (Deck.name.ilike(term) | Deck.description.ilike(term))
    ).all()
    cards = Card.query.join(Deck).filter(
        Deck.owner_id == user.id,
        (Card.term.ilike(term) | Card.definition.ilike(term))
    ).all()

    return jsonify({
        "decks": [{"id": d.id, "name": d.name} for d in decks],
        "cards": [{"id": c.id, "term": c.term} for c in cards]
    })

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for("home"))
        flash("Invalid credentials", "danger")
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
