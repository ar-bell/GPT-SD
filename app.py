import os
from flask import current_app
from dotenv import load_dotenv
from flask import (
    Flask, render_template, redirect, url_for,
    flash, session, request, jsonify, send_file, abort
)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField,
    SelectField, TextAreaField
)
from wtforms.validators import DataRequired, Email, EqualTo, Length
from deck_database import db, User, Deck, Card, StudyProgress
import requests
import json
import io
import base64
import uuid
import logging
from PIL import Image
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from google import genai
from google.genai import types

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///deck.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# TTS Configuration
IBM_TTS_API_KEY = os.getenv("IBM_TTS_API_KEY")
IBM_TTS_URL = os.getenv("IBM_TTS_URL")

if IBM_TTS_API_KEY and IBM_TTS_URL:
    authenticator = IAMAuthenticator(IBM_TTS_API_KEY)
    tts = TextToSpeechV1(authenticator=authenticator)
    tts.set_service_url(IBM_TTS_URL)
else:
    tts = None
    print("Warning: IBM TTS credentials not found. TTS functionality will be disabled.")

# GenAI Configuration for Image Generation
GENAI_KEY = os.getenv("GENAI_KEY")
if GENAI_KEY:
    genai_client = genai.Client(api_key=GENAI_KEY)
    logging.basicConfig(level=logging.INFO)
else:
    genai_client = None
    print("Warning: GENAI_KEY not found. AI image generation will fall back to placeholder images.")


 
# Database-driven application - no more mock data needed!



class LoginForm(FlaskForm):
    email    = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit   = SubmitField("Sign In")

class RegisterForm(FlaskForm):
    name     = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=100)])
    email    = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[
        DataRequired(), 
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    password2 = PasswordField("Confirm Password", validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    submit   = SubmitField("Register")

class DeckForm(FlaskForm):
    name        = StringField("Deck Name", validators=[DataRequired(), Length(min=1, max=120)])
    description = TextAreaField("Description (Optional)")
    category    = StringField("Category (Optional)", validators=[Length(max=50)])
    submit      = SubmitField("Create Deck")

class CardForm(FlaskForm):
    deck_id    = SelectField("Deck", coerce=int, validators=[DataRequired()])
    term       = StringField("Term", validators=[DataRequired(), Length(min=1, max=200)])
    definition = TextAreaField("Definition", validators=[DataRequired()])
    submit     = SubmitField("Create Card")

# Authentication routes

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data.lower()).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'danger')
            return render_template('register.html', form=form)
        
        # Create new user
        user = User(
            name=form.name.data,
            email=form.email.data.lower()
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html', form=form)

@app.route("/synthesize", methods=["POST"])
def synthesize():
    """Text-to-speech endpoint"""
    if not tts:
        return jsonify({"error": "TTS service not available"}), 503
    
    data = request.get_json()
    text = data.get("text")
    voice = data.get("voice", "en-US_AllisonV3Voice")

    if not text or not isinstance(text, str):
        return jsonify({"error": "Missing or invalid 'text'"}), 400

    try:
        response = tts.synthesize(
            text,
            voice=voice,
            accept="audio/mp3"
        ).get_result()
        audio_bytes = response.content
        return send_file(
            io.BytesIO(audio_bytes),
            mimetype="audio/mp3",
            as_attachment=False,
            download_name="speech.mp3"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def generate_image_for_term(term, definition):
    """Generate a contextual image using Google Gemini AI or fallback to placeholders"""
    
    if genai_client:
        try:
            # Create a detailed prompt combining term and definition
            prompt = f"Create an educational illustration that visually represents the concept of '{term}' (which means: {definition}). The image should be clear, visually appealing, and help students understand the concept through visual representation only. IMPORTANT: Do not include any text, words, letters, or written definitions in the image. Use only visual elements, symbols, diagrams, or illustrations to convey the meaning. Style: educational, clean, professional illustration suitable for learning materials, no text overlay."
            
            # Generate image using Gemini AI
            resp = genai_client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])
            )
            
            # Extract the image data
            part = next(p for p in resp.candidates[0].content.parts if p.inline_data)
            img_data = part.inline_data.data
            
            # Save image to static folder with unique name
            filename = f"generated_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join("static", "images", filename)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save the image
            with open(filepath, "wb") as f:
                f.write(img_data)
            
            # Return the URL path
            return f"/static/images/{filename}"
            
        except Exception as e:
            logging.error(f"AI image generation failed for term '{term}': {e}")
            # Fall through to fallback
    
    # Fallback to high-quality placeholder images if AI generation fails
    fallback_images = {
        # Biology terms
        "mitochondria": "https://picsum.photos/600/400?random=101",
        "cell": "https://picsum.photos/600/400?random=102", 
        "dna": "https://picsum.photos/600/400?random=103",
        "photosynthesis": "https://picsum.photos/600/400?random=104",
        "ecosystem": "https://picsum.photos/600/400?random=105",
        "protein": "https://picsum.photos/600/400?random=106",
        
        # Chemistry terms
        "atom": "https://picsum.photos/600/400?random=201",
        "molecule": "https://picsum.photos/600/400?random=202",
        "element": "https://picsum.photos/600/400?random=203",
        "compound": "https://picsum.photos/600/400?random=204",
        
        # Language terms
        "hola": "https://picsum.photos/600/400?random=301",
        "gracias": "https://picsum.photos/600/400?random=302",
        "por favor": "https://picsum.photos/600/400?random=303",
        "hello": "https://picsum.photos/600/400?random=304",
        "goodbye": "https://picsum.photos/600/400?random=305",
        
        # Math/Computer Science terms
        "algorithm": "https://picsum.photos/600/400?random=401",
        "function": "https://picsum.photos/600/400?random=402",
        "variable": "https://picsum.photos/600/400?random=403",
        "equation": "https://picsum.photos/600/400?random=404",
    }
    
    term_lower = term.lower()
    
    # Try exact match first
    if term_lower in fallback_images:
        return fallback_images[term_lower]
    
    # Try partial matches for compound terms
    for key in fallback_images:
        if key in term_lower or term_lower in key:
            return fallback_images[key]
    
    # Generate a consistent random image based on term hash
    import hashlib
    term_hash = int(hashlib.md5(term.encode()).hexdigest()[:6], 16)
    random_id = 500 + (term_hash % 400)
    
    return f"https://picsum.photos/600/400?random={random_id}"

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Logged in successfully!", "success")
            
            # Redirect to the page they were trying to access
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for("home"))
        flash("Invalid email or password", "danger")
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out", "info")
    return redirect(url_for("login"))

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route("/home")
@login_required
def home():
    # Get user's decks from database
    decks = current_user.decks.all()
    deck_data = [deck.to_dict(current_user.id) for deck in decks]
    return render_template("home.html", decks=deck_data, user=current_user)



@app.route("/cards/new", methods=["GET","POST"])
@login_required
def create_card_global():
    form = CardForm()
    # Get user's decks for dropdown
    user_decks = current_user.decks.all()
    form.deck_id.choices = [(deck.id, deck.name) for deck in user_decks]

    # Pre-select deck if ?deck_id=... is passed
    pre_selected_deck_id = request.args.get("deck_id", type=int)
    if pre_selected_deck_id:
        # Verify the deck belongs to the current user
        if any(deck.id == pre_selected_deck_id for deck in user_decks):
            form.deck_id.data = pre_selected_deck_id

    if form.validate_on_submit():
        # Verify the selected deck belongs to the current user
        deck = Deck.query.filter_by(id=form.deck_id.data, owner_id=current_user.id).first()
        if not deck:
            flash("Invalid deck selection.", "danger")
            return render_template("create_card.html", form=form)

        # Generate image for the card
        image_url = generate_image_for_term(form.term.data, form.definition.data)

        # Create new card
        card = Card(
            term=form.term.data,
            definition=form.definition.data,
            image_url=image_url,
            deck_id=deck.id
        )

        try:
            db.session.add(card)
            db.session.commit()
            flash(f"Added '{card.term}' to {deck.name}", "success")
            return redirect(url_for("study_deck", deck_id=deck.id))
        except Exception as e:
            db.session.rollback()
            flash("Failed to create card. Please try again.", "danger")

    return render_template("create_card.html", form=form)

    

@app.route("/decks/<int:deck_id>/create_card", methods=["GET", "POST"])
@login_required
def create_card_for_deck(deck_id):
    # Get the deck and verify ownership
    deck = Deck.query.filter_by(id=deck_id, owner_id=current_user.id).first_or_404()

    form = CardForm()
    # Pre-set the deck choice
    form.deck_id.choices = [(deck.id, deck.name)]
    form.deck_id.data = deck.id

    if form.validate_on_submit():
        # Generate image for the new card
        image_url = generate_image_for_term(form.term.data, form.definition.data)
        
        # Create new card
        card = Card(
            term=form.term.data,
            definition=form.definition.data,
            image_url=image_url,
            deck_id=deck.id
        )

        try:
            db.session.add(card)
            db.session.commit()
            flash(f"Added '{card.term}' to {deck.name}", "success")
            return redirect(url_for("study_deck", deck_id=deck.id))
        except Exception as e:
            db.session.rollback()
            flash("Failed to create card. Please try again.", "danger")

    return render_template("create_card.html", form=form, deck=deck)



@app.route("/decks/<int:deck_id>/study", methods=["GET"])
@login_required
def study_deck(deck_id):
    # Get the deck and verify ownership
    deck = Deck.query.filter_by(id=deck_id, owner_id=current_user.id).first_or_404()
    
    # Get all cards for this deck
    cards = deck.cards.all()
    
    # Convert cards to dict format for the template
    cards_data = []
    for card in cards:
        card_dict = card.to_dict()
        # Generate image if not present
        if not card_dict['image_url']:
            card_dict['image_url'] = generate_image_for_term(card.term, card.definition)
            # Update the database with the generated image
            card.image_url = card_dict['image_url']
            try:
                db.session.commit()
            except:
                db.session.rollback()
        cards_data.append(card_dict)
    
    return render_template("study.html", deck=deck.to_dict(current_user.id), cards=cards_data)

@app.route("/decks/<int:deck_id>/quiz", methods=["GET"])
@login_required
def quiz_deck(deck_id):
    # Get the deck and verify ownership
    deck = Deck.query.filter_by(id=deck_id, owner_id=current_user.id).first_or_404()
    
    # Get all cards for this deck
    cards = deck.cards.all()
    
    # Convert cards to dict format for the template
    cards_data = []
    for card in cards:
        card_dict = card.to_dict()
        # Generate image if not present
        if not card_dict['image_url']:
            card_dict['image_url'] = generate_image_for_term(card.term, card.definition)
            # Update the database with the generated image
            card.image_url = card_dict['image_url']
            try:
                db.session.commit()
            except:
                db.session.rollback()
        cards_data.append(card_dict)
    
    return render_template("quiz.html", deck=deck.to_dict(current_user.id), cards=cards_data)

@app.route('/decks/new', methods=['GET', 'POST'])
@login_required
def create_deck():
    form = DeckForm()
    if form.validate_on_submit():
        deck = Deck(
            name=form.name.data,
            description=form.description.data,
            category=form.category.data,
            owner_id=current_user.id
        )
        try:
            db.session.add(deck)
            db.session.commit()
            flash(f"Created deck '{deck.name}' successfully!", "success")
            return redirect(url_for("home"))
        except Exception as e:
            db.session.rollback()
            flash("Failed to create deck. Please try again.", "danger")
    
    return render_template("create_deck.html", form=form)

@app.route('/decks/<int:deck_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_deck(deck_id):
    deck = Deck.query.filter_by(id=deck_id, owner_id=current_user.id).first_or_404()
    
    form = DeckForm(obj=deck)
    if form.validate_on_submit():
        deck.name = form.name.data
        deck.description = form.description.data
        deck.category = form.category.data
        
        try:
            db.session.commit()
            flash(f"Updated deck '{deck.name}' successfully!", "success")
            return redirect(url_for("home"))
        except Exception as e:
            db.session.rollback()
            flash("Failed to update deck. Please try again.", "danger")
    
    return render_template("edit_deck.html", form=form, deck=deck)

@app.route('/decks/<int:deck_id>/delete', methods=['POST'])
@login_required
def delete_deck(deck_id):
    deck = Deck.query.filter_by(id=deck_id, owner_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(deck)
        db.session.commit()
        flash(f"Deleted deck '{deck.name}' successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to delete deck. Please try again.", "danger")
    
    return redirect(url_for("home"))

@app.route("/api/decks/<int:deck_id>", methods=["DELETE"])
@login_required
def api_delete_deck(deck_id):
    deck = Deck.query.filter_by(id=deck_id, owner_id=current_user.id).first()
    if not deck:
        return ("Not found", 404)
    
    try:
        db.session.delete(deck)
        db.session.commit()
        return ("", 204)
    except Exception as e:
        db.session.rollback()
        return ("Server error", 500)

@app.route("/api/cards/<int:card_id>/study", methods=["POST"])
@login_required
def mark_card_studied(card_id):
    # Get the card and verify it belongs to the current user's deck
    card = Card.query.join(Deck).filter(
        Card.id == card_id,
        Deck.owner_id == current_user.id
    ).first()
    
    if not card:
        return ("Card not found", 404)
    
    try:
        # Check if progress already exists
        existing_progress = StudyProgress.query.filter_by(
            user_id=current_user.id,
            card_id=card_id
        ).first()
        
        if not existing_progress:
            # Create new study progress entry
            progress = StudyProgress(
                user_id=current_user.id,
                card_id=card_id,
                deck_id=card.deck_id
            )
            db.session.add(progress)
            db.session.commit()
        
        return ("", 204)
    except Exception as e:
        db.session.rollback()
        return ("Server error", 500)

# API endpoint for adding cards via AJAX
@app.route("/api/cards/create", methods=["POST"])
@login_required
def api_create_card():
    data = request.get_json()
    term = data.get("term")
    definition = data.get("definition")
    deck_id = data.get("deck_id")
    
    if not all([term, definition, deck_id]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Verify deck ownership
    deck = Deck.query.filter_by(id=deck_id, owner_id=current_user.id).first()
    if not deck:
        return jsonify({"error": "Deck not found or access denied"}), 404
    
    # Generate AI image
    image_url = generate_image_for_term(term, definition)
    
    try:
        card = Card(
            deck_id=deck_id,
            term=term,
            definition=definition,
            image_url=image_url
        )
        db.session.add(card)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "card": card.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create card"}), 500

if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
        except:
            pass
    app.run(debug=True, host="0.0.0.0", port=8000)