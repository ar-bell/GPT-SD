from flask import Flask, request, jsonify, session
import sqlite3
import json
import random

app = Flask(__name__)
app.secret_key = 'key' # REMEMBER TO SET KEY
DB_PATH = 'flashcards.db'

def init_visual_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Session + preferences tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS visual_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            deck_id INTEGER NOT NULL,
            cards_viewed INTEGER DEFAULT 0,
            correct_matches INTEGER DEFAULT 0,
            session_data TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (deck_id) REFERENCES decks(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_visual_cards(user_id, deck_id, limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT c.id, c.term, c.image_url
        FROM cards c
        WHERE c.deck_id = ?
        ORDER BY RANDOM()
        LIMIT ?
    ''', (deck_id, limit))
    cards = [{'id': r[0], 'term': r[1], 'image_url': r[2]} for r in c.fetchall()]
    conn.close()
    return cards

def create_matching_pairs(cards):
    """Prepare matching pairs (image + term) for the matching game."""
    pairs = []
    for card in cards:
        pairs.append({'id': f"img_{card['id']}", 'image_url': card['image_url'], 'term_id': card['id'], 'type':'image'})
        pairs.append({'id': f"term_{card['id']}", 'text': card['term'], 'term_id': card['id'], 'type':'term'})
    random.shuffle(pairs)
    return pairs

@app.route('/visual/start/<int:deck_id>', methods=['POST'])
def start_visual_session(deck_id):
    if 'user_id' not in session:
        return jsonify({'error':'Not logged in'}), 401

    init_visual_db()
    user_id = session['user_id']
    cards = get_visual_cards(user_id, deck_id, limit=request.json.get('limit', 10))
    if not cards:
        return jsonify({'error':'No cards found'}), 404

    pairs = create_matching_pairs(cards)
    session_data = {'pairs': pairs}

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO visual_sessions (user_id, deck_id, session_data)
        VALUES (?, ?, ?)
    ''', (user_id, deck_id, json.dumps(session_data)))
    session_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'session_id': session_id, 'pairs': pairs})

@app.route('/visual/check', methods=['POST'])
def check_match():
    if 'user_id' not in session:
        return jsonify({'error':'Not logged in'}), 401

    data = request.json
    session_id = data.get('session_id')
    id1 = data.get('id1')
    id2 = data.get('id2')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT session_data, correct_matches FROM visual_sessions WHERE id = ? AND user_id = ?',
              (session_id, session['user_id']))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error':'Session not found'}), 404

    session_data, correct = json.loads(row[0]), row[1]
    # find selected items
    card1 = next((p for p in session_data['pairs'] if p['id'] == id1), None)
    card2 = next((p for p in session_data['pairs'] if p['id'] == id2), None)
    if not card1 or not card2:
        conn.close()
        return jsonify({'error':'Cards not found'}), 404

    is_match = (card1['term_id'] == card2['term_id'] and card1['type'] != card2['type'])
    if is_match:
        for p in session_data['pairs']:
            if p['term_id'] == card1['term_id']:
                p['matched'] = True
        correct += 1

    # update view count and matches
    c.execute('''
        UPDATE visual_sessions
        SET session_data = ?, cards_viewed = cards_viewed + 1, correct_matches = ?
        WHERE id = ?
    ''', (json.dumps(session_data), correct, session_id))
    conn.commit()
    conn.close()

    all_matched = all(p.get('matched') for p in session_data['pairs'] if p['type']=='image')
    return jsonify({'is_match': is_match, 'all_matched': all_matched, 'pairs': session_data['pairs']})

@app.route('/visual/end/<int:session_id>', methods=['POST'])
def end_visual_session(session_id):
    if 'user_id' not in session:
        return jsonify({'error':'Not logged in'}), 401

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE visual_sessions
        SET ended_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (session_id,))
    conn.commit()
    conn.close()
    return jsonify({'message':'Session ended'})

if __name__ == '__main__':
    app.run(debug=True)
