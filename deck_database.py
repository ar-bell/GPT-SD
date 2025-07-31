# deck_database.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    name          = db.Column(db.String(100), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    is_active     = db.Column(db.Boolean, default=True)
    decks         = db.relationship("Deck", back_populates="owner", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """Return the user ID as a string (required by Flask-Login)"""
        return str(self.id)

    def __repr__(self):
        return f'<User {self.email}>'

class Deck(db.Model):
    __tablename__ = "decks"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    category    = db.Column(db.String(50))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_public   = db.Column(db.Boolean, default=False)
    owner_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    owner       = db.relationship("User", back_populates="decks")
    cards       = db.relationship("Card", back_populates="deck", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def card_count(self):
        """Get the number of cards in this deck"""
        return self.cards.count()

    def mastery_percentage(self, user_id):
        """Calculate mastery percentage based on user's study progress"""
        if self.card_count == 0:
            return 0
        
        # Count how many cards in this deck the user has studied
        studied_cards = StudyProgress.query.filter_by(
            user_id=user_id,
            deck_id=self.id
        ).count()
        
        # Calculate percentage
        percentage = int((studied_cards / self.card_count) * 100)
        return min(100, max(0, percentage))

    def to_dict(self, user_id=None):
        """Convert deck to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'card_count': self.card_count,
            'mastery': self.mastery_percentage(user_id) if user_id else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Deck {self.name}>'

class Card(db.Model):
    __tablename__ = "cards"
    id          = db.Column(db.Integer, primary_key=True)
    term        = db.Column(db.String(200), nullable=False)
    definition  = db.Column(db.Text, nullable=False)
    image_url   = db.Column(db.String(500))
    audio_url   = db.Column(db.String(500))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deck_id     = db.Column(db.Integer, db.ForeignKey("decks.id"), nullable=False)
    deck        = db.relationship("Deck", back_populates="cards")

    def to_dict(self):
        """Convert card to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'term': self.term,
            'definition': self.definition,
            'image_url': self.image_url,
            'audio_url': self.audio_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Card {self.term}>'

class StudyProgress(db.Model):
    __tablename__ = "study_progress"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey("decks.id"), nullable=False)
    studied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User")
    card = db.relationship("Card")
    deck = db.relationship("Deck")
    
    # Unique constraint to prevent duplicate progress entries
    __table_args__ = (db.UniqueConstraint('user_id', 'card_id', name='unique_user_card_progress'),)
    
    def __repr__(self):
        return f'<StudyProgress user_id={self.user_id} card_id={self.card_id}>'


