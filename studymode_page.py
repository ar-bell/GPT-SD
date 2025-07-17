from flask import request, jsonify
from flask_login import current_user, login_required
from deck_database import db, Deck, Card
from app import app

@app.route('/api/decks/<int:deck_id>/cards', methods=['GET'])
@login_required
def get_study_cards(deck_id):
    """Return all cards in a deck for flashcard study and visual quiz mode"""
    # Check if the deck exists and belongs to the current user
    deck = Deck.query.filter_by(id=deck_id, owner_id=current_user.id).first()
    if not deck:
        return jsonify({"error": "Deck not found"}), 404
    # Fetch all cards in the deck
    cards = Card.query.filter_by(deck_id=deck_id).all()
    result = []
    for card in cards:
        result.append({
            "id": card.id,
            "term": card.term,
            "definition": card.definition,
            "image_url": card.image_url,
            "audio_url": card.audio_url
        })
    return jsonify({"deck": deck.name, "cards": result})
