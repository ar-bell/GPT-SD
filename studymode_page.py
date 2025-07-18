from flask import jsonify, session
from flask_login import current_user, login_required
from app import app, Card, Deck

@app.route('/api/decks/<int:deck_id>/cards', methods=['GET'])
def get_study_cards(deck_id):
    deck = Deck.query.filter_by(id=deck_id, owner_id=current_user.id).first()
    if not deck:
        return jsonify({"error": "Deck not found"}), 404

    cards = [{
        "id": c.id,
        "term": c.term,
        "definition": c.definition,
        "image_url": c.image_url,
        "audio_url": c.audio_url
    } for c in deck.cards]

    return jsonify({"deck": deck.name, "cards": cards})
