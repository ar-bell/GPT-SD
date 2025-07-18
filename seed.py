# seed.py
from werkzeug.security import generate_password_hash
from app import app, db, User

with app.app_context():
    db.create_all()
    # explicitly choose pbkdf2:sha256 rather than the new scrypt default
    pw = generate_password_hash("MySecret123!", method="pbkdf2:sha256")
    if not User.query.filter_by(email="test@gmail.com").first():
        u = User(email="test@gmail.com", password_hash=pw)
        db.session.add(u)
        db.session.commit()
        print("Seeded test@gmail.com / MySecret123!")
    else:
        print("User already exists.")

