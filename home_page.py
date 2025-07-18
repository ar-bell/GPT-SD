from flask import Flask, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///deck.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

from deck_database import User, Deck, Card, StudySession

def get_current_user():
    user_email = session.get("user_email")
    if not user_email:
        return None
    return User.query.filter_by(email=user_email).first()

@app.route("/")
def home():
    return "Welcome to GPT.SD Flashcards!"

@app.route("/home")
def dashboard():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    total_decks = Deck.query.filter_by(owner_id=user.id).count()
    total_cards = Card.query.join(Deck).filter(Deck.owner_id == user.id).count()

    sessions = StudySession.query.filter_by(user_id=user.id).all()
    if sessions:
        correct = sum(1 for s in sessions if s.correct)
        accuracy_rate = round(correct / len(sessions) * 100, 1)
    else:
        accuracy_rate = 0.0

    return jsonify({
        "total_decks": total_decks,
        "total_cards": total_cards,
        "accuracy_rate": accuracy_rate,
    })

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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
