
# login_page.py
from flask import Flask, render_template, request, redirect, url_for, session
import os

app = Flask(__name__)
app.secret_key = '88443'

# routes
@app.route('/')
def index():
    """Redirect to login page"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email and password:
            session['user'] = email
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/home')
def home():
    """Home page with deck list"""
    if 'user' not in session:
        return redirect(url_for('login'))
    
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
    'Card deck page'
    if request.method == 'POST':
        termInput = request.form.get('term', '').strip()
        defInput = request.form.get('definition', '').strip()


        if not termInput and not defInput:
            flash('Both term and definition are required.', 'error')
            return render_template('createcard.html', termInput=term, defInput=definition)

    #TODO: save your new deck/card here

        return redirect(url_for('home'))
     #GET   
    return render_template('createcard.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('user', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
