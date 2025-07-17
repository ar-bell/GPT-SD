from flask import Blueprint, request, session, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from deck_database import db, User, Deck, Card, StudySession

home_page = Blueprint("home_page", __name__)

# Helper function to get current user

def get_current_user():
    user_email = session.get("user_email")
    if not user_email:
        return None
    return User.query.filter_by(email=user_email).first()

@home_page.route("/")
def home():
    return "Welcome to GPT.SD Flashcards!"

@home_page.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    total_decks = Deck.query.filter_by(owner_id=user.id).count()
    total_cards = Card.query.join(Deck).filter(Deck.owner_id == user.id).count()

    sessions = StudySession.query.filter_by(user_id=user.id).all()
    if sessions:
        correct = sum(1 for s in sessions if s.correct)
        accuracy_rate = correct / len(sessions)
    else:
        accuracy_rate = 0.0


    return jsonify({
        "total_decks": total_decks,
        "total_cards": total_cards,
        "accuracy_rate": accuracy_rate,
    })

@home_page.route("/search")
def search():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    query = request.args.get("query", "")
    if len(query.strip()) < 2:
        return jsonify({"error": "Query too short"}), 400

    term = f"%{query.strip()}%"

    decks = Deck.query.filter(
        Deck.owner_id == user.id,
        (Deck.name.ilike(term) | Deck.description.ilike(term))
    ).all()

    cards = Card.query.join(Deck).filter(
        Deck.owner_id == user.id,
        (Card.term.ilike(term) | Card.definition.ilike(term))
    ).all()

    return jsonify({
        "decks": [deck.name for deck in decks],
        "cards": [card.term for card in cards]
    })
