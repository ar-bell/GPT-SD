# deck_database.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    decks         = db.relationship("Deck", back_populates="owner")

class Deck(db.Model):
    __tablename__ = "decks"
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    owner_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    owner       = db.relationship("User", back_populates="decks")
    cards       = db.relationship("Card", back_populates="deck", cascade="all, delete-orphan")

class Card(db.Model):
    __tablename__ = "cards"
    id          = db.Column(db.Integer, primary_key=True)
    term        = db.Column(db.String(200), nullable=False)
    definition  = db.Column(db.Text, nullable=False)
    image_url   = db.Column(db.String(500))
    audio_url   = db.Column(db.String(500))
    deck_id     = db.Column(db.Integer, db.ForeignKey("decks.id"), nullable=False)
    deck        = db.relationship("Deck", back_populates="cards")


