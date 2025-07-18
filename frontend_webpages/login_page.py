# login_page.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os


# Test credentials
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"

app = Flask(__name__)
app.secret_key = '88443'

decks = [
    {
        'id': 1,
        'name': 'JavaScript Fundamentals',
        'cards': 45,
        'mastery': 87,
        'category': 'programming'
    },
    {
        'id': 2,
        'name': 'Spanish Vocabulary',
        'cards': 120,
        'mastery': 65,
        'category': 'language'
    },
    {
        'id': 3,
        'name': 'Data Structures',
        'cards': 78,
        'mastery': 92,
        'category': 'programming'
    }
]

# routes
@app.route('/')
def index():
    """Redirect to login page"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        pwd = request.form.get('password', '').strip()
        
        if email == TEST_USER_EMAIL and pwd == TEST_USER_PASSWORD:
            session['user'] = email  # Changed to 'user' to match home() function
            flash("Logged in successfully!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials", "danger")
    
    # GET or failed POST
    return render_template("login.html")

@app.route('/home')
def home():
    """Home page with deck list"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return render_template('home.html', user=session['user'], decks=decks)

@app.route('/study/<int:deck_id>')
def study(deck_id):
    """Study mode page"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    flashcards = [
        {
            'term': 'Closure',
            'definition': 'A function that has access to variables in its outer scope',
            'image': '/static/images/closure.png'
        }
    ]
    
    return render_template('study.html', deck_id=deck_id, flashcards=flashcards)

@app.route('/createcard', methods=['GET', 'POST'])
def createcard():
    """Card deck page"""
    if 'user' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        termInput = request.form.get('term', '').strip()
        defInput = request.form.get('definition', '').strip()
        
        if not termInput or not defInput:  # Fixed: was 'and', should be 'or'
            flash('Both term and definition are required.', 'error')
            return render_template('createcard.html')  # Fixed: removed undefined variables
        
        # assign a new id
        new_id = max(d['id'] for d in decks) + 1 if decks else 1
        
        # build the new deck entry
        new_deck = {
            'id': new_id,
            'name': termInput,
            'cards': 0,
            'mastery': 0,
            'category': ''
        }
        
        decks.append(new_deck)
        flash(f"Created new deck: {termInput}", "success")
        return redirect(url_for('home'))
    
    # GET
    return render_template('createcard.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('user', None)
    flash("You have been logged out", "info")
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
