# app.py
import os
from dotenv import load_dotenv
from flask import (
    Flask, render_template, redirect, url_for,
    flash, session, request
)
from werkzeug.security import check_password_hash
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField,
    SelectField, TextAreaField
)
from wtforms.validators import DataRequired, Email
from deck_database import db, User, Deck, Card

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///deck.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

class LoginForm(FlaskForm):
    email    = StringField("Email",    validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit   = SubmitField("Sign In")

class CardForm(FlaskForm):
    deck_id    = SelectField("Deck", coerce=int, validators=[DataRequired()])
    term       = StringField("Term",       validators=[DataRequired()])
    definition = TextAreaField("Definition", validators=[DataRequired()])
    submit     = SubmitField("Create Card")

def get_current_user():
    email = session.get("user_email")
    return User.query.filter_by(email=email).first() if email else None

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session["user_email"] = user.email
            flash("Logged in successfully!", "success")
            return redirect(url_for("home"))
        flash("Invalid credentials", "danger")
    return render_template("login.html", form=form)

@app.route("/logout")
def logout():
    session.pop("user_email", None)
    flash("Logged out", "info")
    return redirect(url_for("login"))

@app.route("/", methods=["GET"])
@app.route("/home", methods=["GET"])
def home():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    decks_data = []
    for d in Deck.query.filter_by(owner_id=user.id):
        decks_data.append({
            "id": d.id,
            "name": d.name,
            "cards": len(d.cards),
            "mastery": 0  # placeholder
        })
    return render_template("home.html", user=user.email, decks=decks_data)

@app.route("/cards/new", methods=["GET", "POST"])
def create_card():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    form = CardForm()
    form.deck_id.choices = [
        (d.id, d.name) for d in Deck.query.filter_by(owner_id=user.id)
    ]

    if form.validate_on_submit():
        card = Card(
            deck_id    = form.deck_id.data,
            term       = form.term.data,
            definition = form.definition.data
        )
        db.session.add(card)
        db.session.commit()
        flash(f"Card '{card.term}' created!", "success")
        return redirect(url_for("home"))

    return render_template("create_card.html", form=form)

@app.route("/decks/<int:deck_id>/study", methods=["GET"])
def study_deck(deck_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    deck = Deck.query.filter_by(id=deck_id, owner_id=user.id).first_or_404()
    return render_template("study.html", deck=deck, cards=deck.cards)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=8000)
