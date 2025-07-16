# login_page.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email
from werkzeug.security import check_password_hash
import os

from deck_database import db, User     # from your HEAD version
# If you also need the in-memory decks list, import or define it here
decks = [
    {'id': 1, 'name': 'JavaScript Fundamentals', 'cards': 45, 'mastery': 87, 'category': 'programming'},
    {'id': 2, 'name': 'Spanish Vocabulary',     'cards': 120,'mastery': 65, 'category': 'language'},
    {'id': 3, 'name': 'Data Structures',         'cards': 78, 'mastery': 92, 'category': 'programming'}
]

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret")
app.config["SQLALCHEMY_DATABASE_URI"]        = os.getenv("DATABASE_URL", "sqlite:///deck.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

#
# 1) Login form definition (WTForms)
#
class LoginForm(FlaskForm):
    email    = StringField("Email",    validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit   = SubmitField("Sign In")

#
# 2) Routes
#
@app.route('/', methods=["GET"])
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            session['user_email'] = user.email
            flash("Logged in successfully!", "success")
            return redirect(url_for("home"))
        flash("Invalid credentials", "danger")
    return render_template("login.html", form=form)

@app.route('/logout')
def logout():
    session.pop("user_email", None)
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    # Here you could also fetch decks from the database if you have a Deck model,
    # but for now we use the in-memory `decks` list:
    return render_template('home.html', user=session['user_email'], decks=decks)

@app.route('/study/<int:deck_id>')
def study(deck_id):
    if 'user_email' not in session:
        return redirect(url_for('login'))
    # dummy flashcards for now:
    flashcards = [{
        'term':       'Closure',
        'definition': 'A function that has access to variables in its outer scope',
        'image':      '/static/images/closure.png'
    }]
    return render_template('study.html', deck_id=deck_id, flashcards=flashcards)

@app.route('/createcard', methods=['GET', 'POST'])
def createcard():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        termInput = request.form.get('term', '').strip()
        defInput  = request.form.get('definition', '').strip()

        if not termInput or not defInput:
            flash('Both deck name and description are required.', 'error')
            return render_template('createcard.html',
                                   term=termInput,
                                   definition=defInput)

        new_id   = max(d['id'] for d in decks) + 1 if decks else 1
        new_deck = {
            'id':       new_id,
            'name':     termInput,
            'cards':    0,
            'mastery':  0,
            'category': ''
        }
        decks.append(new_deck)
        return redirect(url_for('home'))

    return render_template('createcard.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
