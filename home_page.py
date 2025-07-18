from flask import Flask, render_template, redirect, url_for, flash, session, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///deck.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    decks         = db.relationship("Deck", back_populates="owner")

class Deck(db.Model):
    __tablename__ = "decks"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String, nullable=False)
    owner_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    owner       = db.relationship("User", back_populates="decks")
    cards       = db.relationship("Card", back_populates="deck")

class Card(db.Model):
    __tablename__ = "cards"
    id       = db.Column(db.Integer, primary_key=True)
    term     = db.Column(db.String, nullable=False)
    deck_id  = db.Column(db.Integer, db.ForeignKey("decks.id"))
    deck     = db.relationship("Deck", back_populates="cards")

class StudySession(db.Model):
    __tablename__ = "study_sessions"
    id      = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    correct = db.Column(db.Boolean)

def get_current_user():
    email = session.get("user_email")
    return User.query.filter_by(email=email).first() if email else None

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/login", methods=["GET","POST"])
def login():
    pass

@app.route("/dashboard")
def api_dashboard():
    total_decks = Deck.query.filter_by(owner_id=current_user.id).count()
    total_cards = Card.query.join(Deck).filter(Deck.owner_id==current_user.id).count()
    sessions   = StudySession.query.filter_by(user_id=current_user.id).all()
    accuracy   = (sum(1 for s in sessions if s.correct)/ len(sessions)*100) if sessions else 0
    return jsonify({
        "total_decks": total_decks,
        "total_cards": total_cards,
        "accuracy_rate": round(accuracy,1)
    })

@app.route("/search")
def search():
    pass

if __name__=="__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

