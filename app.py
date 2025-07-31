
import os
from flask import current_app
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


 
 # Mock deck data for presentation
decks_data = [
    {
      "id": 1,
      "name": "Biology Basics",
      "cards": [
        { "id": 1, "term": "Mitochondria", "definition": "The powerhouse of the cell.", "image_url": "https://images.unsplash.com/photo-1634618383211-731d7a03c0c8?q=80&w=3132&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
            ,}
      ],
      "mastery": 100
    },
    {
        "id": 2,
        "name": "Spanish Vocabulary",
        "cards": [
            {"id": 1, "term": "Hola",          "definition": "Hello.",                                     "image_url":"https://images.unsplash.com/photo-1529783167753-ee7cfc0bdf53?w=512&h=384&fit=crop"},
            {"id": 3, "term": "Gracias",       "definition": "Thank you.",                                 "image_url": "https://images.unsplash.com/photo-1542596768-5d1d21f1cf98?w=512&h=384&fit=crop"},
            {"id": 4, "term": "Por favor",     "definition": "Please.",                                    "image_url": "https://images.unsplash.com/photo-1518611507436-f9221403cca2?w=512&h=384&fit=crop"},
        ],
        "mastery": 40
    },
    {
      "id": 3,
      "name": "Data Structures",
      "cards": [],    # start empty
      "mastery": 85
    }
]



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
@app.route("/home")

def home():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    # use the module‐level decks_data!
    global decks_data

    # (optional) merge in real DB decks if you like:
    try:
        real_decks = Deck.query.all()
        if real_decks:
            decks_data = [{
                "id": d.id,
                "name": d.name,
                "cards": len(d.cards) if d.cards else 0,
                "mastery": 75
            } for d in real_decks]
    except:
        pass

    return render_template("home.html", decks=decks_data, user=user.email)



@app.route("/cards/new", methods=["GET","POST"])
def create_card_global():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    form = CardForm()
    # build the dropdown choices from your in‑memory or DB decks:
    form.deck_id.choices = [(d["id"], d["name"]) for d in decks_data]

    #  ⬇️  pre‑select deck if ?deck_id=… is passed
    pre = request.args.get("deck_id", type=int)
    if pre and any(d["id"] == pre for d in decks_data):
        form.deck_id.data = pre

    if form.validate_on_submit():
        deck_id    = form.deck_id.data
        term       = form.term.data
        definition = form.definition.data
        image_url  = generate_image_for_term(term, definition)

        # insert into the correct deck
        target = next(d for d in decks_data if d["id"] == deck_id)
        cards  = target.setdefault("cards", [])
        new_id = max((c["id"] for c in cards), default=0) + 1
        cards.append({
          "id":         new_id,
          "term":       term,
          "definition": definition,
          "image_url":  image_url
        })

        flash(f"Added “{term}” to {target['name']}", "success")
        return redirect(url_for("study_deck", deck_id=deck_id))

    return render_template("create_card.html", form=form)

    

@app.route("/decks/<int:deck_id>/create_card", methods=["GET", "POST"])
def create_card_for_deck(deck_id):
    global decks_data

    # look up the deck in your in‑memory list
    deck = next((d for d in decks_data if d["id"] == deck_id), None)
    if not deck:
        flash(f"Deck {deck_id} not found", "warning")
        return redirect(url_for("home"))

    # use your existing CardForm
    form = CardForm()

    # wire up the deck selector if needed (optional)
    form.deck_id.choices = [(deck["id"], deck["name"])]

    if form.validate_on_submit():
        # append the new card
        deck.setdefault("cards", []).append({
            "id": len(deck["cards"]) + 1,
            "term": form.term.data,
            "definition": form.definition.data,
            "image_url": None
        })
        flash(f"Added “{form.term.data}” to {deck['name']}", "success")
        return redirect(url_for("study_deck", deck_id=deck_id))

    return render_template("create_card.html", form=form, deck=deck)



@app.route("/decks/<int:deck_id>/study", methods=["GET"])
def study_deck(deck_id):
   # find the deck by id
    deck = next((d for d in decks_data if d["id"] == deck_id), None)
    if deck is None:
        abort(404)
    # extract the cards list (might be empty)
    cards = deck.get("cards", [])
    return render_template("study.html", deck=deck, cards=cards)

@app.route('/createdeck', methods=['GET', 'POST'])
def create_deck():
    'Card deck page'
    global decks_data

    if request.method == "POST":
        term = request.form.get("term", "").strip()
        definition = request.form.get("definition", "").strip()

        if not term or not definition:
            flash("Both term and definition are required.", "error")
            return render_template("create_deck.html",
                                   term=term,
                                   definition=definition)

        # assign a new id
        new_id = max(d["id"] for d in decks_data) + 1 if decks_data else 1

        decks_data.append({
            "id":       new_id,
            "name":     term,
            "cards":    [],
            "mastery":  0,
            "category": ""
        })
        flash(f"Created deck '{term}'", "success")
        return redirect(url_for("home"))

    # GET
    return render_template("create_deck.html")

@app.route("/api/decks/<int:deck_id>", methods=["DELETE"])
def api_delete_deck(deck_id):
    # If real DB: Deck.query.filter_by(id=deck_id).delete(); db.session.commit()
    global decks_data
    before = len(decks_data)
    decks_data = [d for d in decks_data if d["id"] != deck_id]
    if len(decks_data) == before:
        return ("Not found", 404)
    return ("", 204)



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