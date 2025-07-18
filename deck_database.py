from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///deck.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    decks = relationship("Deck", back_populates="owner")

class Deck(Base):
    __tablename__ = "decks"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="decks")
    cards = relationship("Card", back_populates="deck", cascade="all, delete-orphan")

class Card(Base):
    __tablename__ = "cards"
    
    id = Column(Integer, primary_key=True)
    term = Column(String, nullable=False)
    definition = Column(Text, nullable=False)
    deck_id = Column(Integer, ForeignKey("decks.id"))
    image_url = Column(String)
    audio_url = Column(String)
    
    deck = relationship("Deck", back_populates="cards")
    study_sessions = relationship("StudySession", back_populates="card")

class StudySession(Base):
    __tablename__ = "study_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    card_id = Column(Integer, ForeignKey("cards.id"))
    mode = Column(String)  # study or visual
    correct = Column(Boolean)

    card = relationship("Card", back_populates="study_sessions")

def init_db(app):
    from flask_sqlalchemy import SQLAlchemy
    db = SQLAlchemy(app)
    return db

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

