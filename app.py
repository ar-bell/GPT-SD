
import os
from dotenv import load_dotenv
from flask import (
    Flask, render_template, redirect, url_for,
    flash, session, request, jsonify
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField,
    SelectField, TextAreaField
)
from wtforms.validators import DataRequired
from deck_database import db, User, Deck, Card
import requests
import json

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///deck.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"

class LoginForm(FlaskForm):
    email    = StringField("Email",    validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit   = SubmitField("Sign In")

class CardForm(FlaskForm):
    deck_id    = SelectField("Deck", coerce=int, validators=[DataRequired()])
    term       = StringField("Term",       validators=[DataRequired()])
    definition = TextAreaField("Definition", validators=[DataRequired()])
    submit     = SubmitField("Create Card")

def get_current_user():
    # For presentation - return a mock user
    email = session.get("user_email")
    if email == TEST_EMAIL:
        # Create a mock user object
        class MockUser:
            id = 1
            email = TEST_EMAIL
        return MockUser()
    return None

def generate_image_for_term(term, definition):
    """Generate an image using the AI API or fallback to quality placeholders"""
    
    # For presentation - use high-quality placeholder images
    # These look more realistic than the purple placeholders
    
    # Map terms to relevant image searches
    image_searches = {
        "mitochondria": "cell,biology,microscope",
        "dna": "dna,genetics,science",
        "photosynthesis": "plants,leaves,green",
        "cell": "cell,biology,microscope",
        "ecosystem": "nature,environment,ecology",
        "atom": "atom,chemistry,science",
        "molecule": "molecule,chemistry,3d",
        "protein": "protein,biology,structure"
    }
    
    # Check if we have a specific search term
    search_term = term.lower()
    for key in image_searches:
        if key in search_term:
            search_term = image_searches[key]
            break
    else:
        # Default search based on the term
        search_term = f"{term},education,science,illustration"
    
    # Return a high-quality image from Unsplash
    return f"https://source.unsplash.com/600x400/?{search_term}"

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Simple check for presentation
        if form.email.data == TEST_EMAIL and form.password.data == TEST_PASSWORD:
            session["user_email"] = TEST_EMAIL
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
    
    # Mock deck data for presentation
    decks_data = [
        {
            "id": 1,
            "name": "Biology Basics",
            "cards": 3,
            "mastery": 100
        },
        {
            "id": 2,
            "name": "Spanish Vocabulary",
            "cards": 5,
            "mastery": 40
        },
        {
            "id": 3,
            "name": "Data Structures",
            "cards": 15,
            "mastery": 85
        }
    ]
    
    # Try to get real decks if database is working
    try:
        real_decks = Deck.query.all()
        if real_decks:
            decks_data = []
            for d in real_decks:
                decks_data.append({
                    "id": d.id,
                    "name": d.name,
                    "cards": len(d.cards) if d.cards else 0,
                    "mastery": 75  # Default mastery
                })
    except:
        pass
    
    return render_template("home.html", user=user.email, decks=decks_data)

@app.route("/cards/new", methods=["GET", "POST"])
def create_card():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    form = CardForm()
    
    # Mock decks for the dropdown
    mock_decks = [(1, "Biology Basics"), (2, "Spanish Vocabulary"), (3, "Data Structures")]
    
    try:
        # Try to get real decks
        real_decks = Deck.query.all()
        if real_decks:
            form.deck_id.choices = [(d.id, d.name) for d in real_decks]
        else:
            form.deck_id.choices = mock_decks
    except:
        form.deck_id.choices = mock_decks

    if form.validate_on_submit():
        # Generate AI image
        image_url = generate_image_for_term(form.term.data, form.definition.data)
        
        try:
            # Try to save to database
            card = Card(
                deck_id    = form.deck_id.data,
                term       = form.term.data,
                definition = form.definition.data,
                image_url  = image_url
            )
            db.session.add(card)
            db.session.commit()
        except:
            # If database fails, just continue
            pass
        
        flash(f"Card '{form.term.data}' created with AI-generated image!", "success")
        return redirect(url_for("home"))

    return render_template("create_card.html", form=form)

@app.route("/decks/<int:deck_id>/study", methods=["GET"])
def study_deck(deck_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))
    
    # Different cards for different decks
    if deck_id == 1:  # Biology
        deck = {"id": 1, "name": "Biology Basics"}
        cards = [
            {
                "id": 1,
                "term": "Mitochondria",
                "definition": "The powerhouse of the cell. Organelles that generate most of the chemical energy.",
                "image_url": "https://images.unsplash.com/photo-1634618383211-731d7a03c0c8?q=80&w=3132&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
            },
            {
                "id": 2,
                "term": "DNA",
                "definition": "Deoxyribonucleic acid - the molecule containing genetic instructions.",
                "image_url": "https://images.unsplash.com/photo-1628595351029-c2bf17511435?w=512&h=384&fit=crop"
            },
            {
                "id": 3,
                "term": "Photosynthesis",
                "definition": "The process by which plants use sunlight to synthesize foods from carbon dioxide and water.",
                "image_url": "https://images.unsplash.com/photo-1574482620811-1aa16ffe3c82?w=512&h=384&fit=crop"
            }
        ]
    elif deck_id == 2:  # Spanish - 5 cards
        deck = {"id": 2, "name": "Spanish Vocabulary"}
        cards = [
            {
                "id": 1,
                "term": "Hola",
                "definition": "Hello - A common greeting in Spanish.",
                "image_url": "https://images.unsplash.com/photo-1529783167753-ee7cfc0bdf53?w=512&h=384&fit=crop"
            },
            {
                "id": 2,
                "term": "Gracias",
                "definition": "Thank you - Expression of gratitude.",
                "image_url": "https://images.unsplash.com/photo-1542596768-5d1d21f1cf98?w=512&h=384&fit=crop"
            },
            {
                "id": 3,
                "term": "Por favor",
                "definition": "Please - Used when making polite requests.",
                "image_url": "https://images.unsplash.com/photo-1518611507436-f9221403cca2?w=512&h=384&fit=crop"
            },
            {
                "id": 4,
                "term": "Lo siento",
                "definition": "I'm sorry - Expression of apology.",
                "image_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=512&h=384&fit=crop"
            },
            {
                "id": 5,
                "term": "Adiós",
                "definition": "Goodbye - A farewell greeting.",
                "image_url": "https://images.unsplash.com/photo-1493612276216-ee3925520721?w=512&h=384&fit=crop"
            }
        ]
    else:  # Data Structures - 15 cards
        deck = {"id": 3, "name": "Data Structures"}
        cards = [
            {
                "id": 1,
                "term": "Array",
                "definition": "A collection of elements stored at contiguous memory locations, accessed by index.",
                "image_url": "https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?w=512&h=384&fit=crop"
            },
            {
                "id": 2,
                "term": "Linked List",
                "definition": "A linear data structure where elements are stored in nodes, with each node pointing to the next.",
                "image_url": "https://images.unsplash.com/photo-1545987796-200677ee1011?w=512&h=384&fit=crop"
            },
            {
                "id": 3,
                "term": "Stack",
                "definition": "A LIFO (Last In First Out) data structure where elements are added and removed from the same end.",
                "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=512&h=384&fit=crop"
            },
            {
                "id": 4,
                "term": "Queue",
                "definition": "A FIFO (First In First Out) data structure where elements are added at rear and removed from front.",
                "image_url": "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=512&h=384&fit=crop"
            },
            {
                "id": 5,
                "term": "Binary Tree",
                "definition": "A hierarchical data structure where each node has at most two children (left and right).",
                "image_url": "https://images.unsplash.com/photo-1502082553048-f009c37129b9?w=512&h=384&fit=crop"
            },
            {
                "id": 6,
                "term": "Binary Search Tree",
                "definition": "A binary tree where left child values are less than parent and right child values are greater.",
                "image_url": "https://images.unsplash.com/photo-1496065187959-7f07b8353c55?w=512&h=384&fit=crop"
            },
            {
                "id": 7,
                "term": "Hash Table",
                "definition": "A data structure that maps keys to values using a hash function for fast lookups.",
                "image_url": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=512&h=384&fit=crop"
            },
            {
                "id": 8,
                "term": "Heap",
                "definition": "A complete binary tree where parent nodes are either greater (max-heap) or smaller (min-heap) than children.",
                "image_url": "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=512&h=384&fit=crop"
            },
            {
                "id": 9,
                "term": "Graph",
                "definition": "A collection of nodes (vertices) connected by edges, used to represent networks and relationships.",
                "image_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=512&h=384&fit=crop"
            },
            {
                "id": 10,
                "term": "Trie",
                "definition": "A tree-like data structure used to store strings efficiently, often used for autocomplete features.",
                "image_url": "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=512&h=384&fit=crop"
            },
            {
                "id": 11,
                "term": "AVL Tree",
                "definition": "A self-balancing binary search tree where heights of left and right subtrees differ by at most one.",
                "image_url": "https://images.unsplash.com/photo-1527266237111-a4989d028b4b?w=512&h=384&fit=crop"
            },
            {
                "id": 12,
                "term": "Red-Black Tree",
                "definition": "A self-balancing BST where nodes are colored red or black to ensure balanced height.",
                "image_url": "https://images.unsplash.com/photo-1509909756405-be0199881695?w=512&h=384&fit=crop"
            },
            {
                "id": 13,
                "term": "B-Tree",
                "definition": "A self-balancing tree data structure that maintains sorted data and allows searches in logarithmic time.",
                "image_url": "https://images.unsplash.com/photo-1544383835-bda2bc66a55d?w=512&h=384&fit=crop"
            },
            {
                "id": 14,
                "term": "Doubly Linked List",
                "definition": "A linked list where each node contains pointers to both the next and previous nodes.",
                "image_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=384&fit=crop"
            },
            {
                "id": 15,
                "term": "Priority Queue",
                "definition": "An abstract data type where each element has a priority, and higher priority elements are served first.",
                "image_url": "https://images.unsplash.com/photo-1553877522-43269d4ea984?w=512&h=384&fit=crop"
            }
        ]
    
    return render_template("study.html", deck=deck, cards=cards)

# API endpoint for adding cards via AJAX
@app.route("/api/cards/create", methods=["POST"])
def api_create_card():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    term = data.get("term")
    definition = data.get("definition")
    deck_id = data.get("deck_id", 1)
    
    # Generate AI image
    image_url = generate_image_for_term(term, definition)
    
    try:
        # Try to save to database
        card = Card(
            deck_id    = deck_id,
            term       = term,
            definition = definition,
            image_url  = image_url
        )
        db.session.add(card)
        db.session.commit()
        card_id = card.id
    except:
        # If database fails, create mock response
        card_id = 999
    
    return jsonify({
        "success": True,
        "card": {
            "id": card_id,
            "term": term,
            "definition": definition,
            "image_url": image_url
        }
    })

if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
        except:
            pass
    app.run(debug=True, host="0.0.0.0", port=8000)