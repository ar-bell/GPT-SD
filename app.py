from flask import Flask, render_template, redirect, url_for, flash, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import os

# load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///deck.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Import your models
from deck_database import User, Deck, Card

# --- Forms ---
class LoginForm(FlaskForm):
    email    = StringField("Email",    validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit   = SubmitField("Sign In")

# --- Authentication routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session["user_email"] = user.email
            flash("Logged in successfully!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("home"))
        flash("Invalid credentials", "danger")
    # Pass `next` into the template so it can preserve it across POST
    return render_template("login.html", form=form, next=request.args.get("next"))

@app.route("/logout")
def logout():
    session.pop("user_email", None)
    flash("Logged out successfully!", "info")
    return redirect(url_for("login"))

# --- Helper to fetch current user object ---
def get_current_user():
    email = session.get("user_email")
    if not email:
        return None
    return User.query.filter_by(email=email).first()

# --- Home / dashboard ---
@app.route("/", methods=["GET"])
@app.route("/home", methods=["GET"])
def home():
    user = get_current_user()
    if not user:
        # redirect back here after login
        return redirect(url_for("login", next="home"))
    # you'll likely want to load decks here too
    decks = Deck.query.filter_by(owner_id=user.id).all()
    return render_template("home.html", user=user.email, decks=decks)

# --- Create Card endpoint ---
@app.route("/cards/new", methods=["GET", "POST"])
def create_card():
    user = get_current_user()
    if not user:
        return redirect(url_for("login", next="cards.new"))

    if request.method == "POST":
        deck_id    = request.form.get("deck_id")
        term       = request.form.get("term", "").strip()
        definition = request.form.get("definition", "").strip()

        if not deck_id or not term or not definition:
            flash("All fields are required.", "warning")
        else:
            deck = Deck.query.filter_by(id=int(deck_id), owner_id=user.id).first()
            if not deck:
                flash("Invalid deck selection.", "danger")
            else:
                card = Card(deck_id=deck.id, term=term, definition=definition)
                db.session.add(card)
                db.session.commit()
                flash(f"Card '{term}' added to deck '{deck.name}'.", "success")
                return redirect(url_for("home"))

    # GET or invalid POST → show the form
    user_decks = Deck.query.filter_by(owner_id=user.id).all()
    return render_template("create_card.html", decks=user_decks)

# --- Study Deck endpoint ---
@app.route("/decks/<int:deck_id>/study", methods=["GET"])
def study_deck(deck_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login", next=f"decks/{deck_id}/study"))

    deck = Deck.query.filter_by(id=deck_id, owner_id=user.id).first_or_404()
    cards = Card.query.filter_by(deck_id=deck.id).all()
    return render_template("study.html", deck=deck, cards=cards)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=8000)


