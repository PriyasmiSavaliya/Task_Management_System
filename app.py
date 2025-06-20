from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/taskmanager"
app.secret_key = "your-secret-key-here"

mongo = PyMongo(app)


@app.route('/')
def home():
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = mongo.db.users.find_one({'email': email})

        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']  # Make sure this is set
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')

    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    return render_template('login.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'error')
        elif mongo.db.users.find_one({'email': email}):
            flash('Email already exists', 'error')
        else:
            hashed_password = generate_password_hash(password)
            mongo.db.users.insert_one({
                'username': username,
                'email': email,
                'password': hashed_password,
                'created_at': datetime.now()
            })
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        user_id = session['user_id']

        # Count tasks with the exact status values as they exist in your database
        pending_count = mongo.db.tasks.count_documents({
            'user_id': user_id,
            'status': 'pending'
        })

        in_progress_count = mongo.db.tasks.count_documents({
            'user_id': user_id,
            '$or': [
                {'status': 'in_progr'},  # Matches your existing status
                {'status': 'In_Progr'}  # Matches alternative spelling in your data
            ]
        })

        completed_count = mongo.db.tasks.count_documents({
            'user_id': user_id,
            'status': 'completed'  # Add if you have this status in your data
        })

        return render_template('dashboard.html',
                               pending=pending_count,
                               in_progress=in_progress_count,
                               completed=completed_count,
                               username=session.get('username'))
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html',
                               pending=0,
                               in_progress=0,
                               completed=0,
                               username=session.get('username'))


@app.route('/board')
def board():
    try:
        tasks = {
            'pending': list(mongo.db.tasks.find({'status': 'Pending'}).sort('due_date', 1)),
            'in_progress': list(mongo.db.tasks.find({'status': 'In Progress'}).sort('due_date', 1)),
            'completed': list(mongo.db.tasks.find({'status': 'Completed'}).sort('due_date', 1))
        }
        return render_template('board.html', tasks=tasks)
    except Exception as e:
        flash(f'Error loading board: {str(e)}', 'error')
        return render_template('board.html', tasks={'pending': [], 'in_progress': [], 'completed': []})


@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        task = {
            'title': request.form['title'],
            'category': request.form.get('category', 'General'),
            'due_date': datetime.strptime(request.form['due_date'], '%Y-%m-%d'),
            'status': request.form['status'],  # Keep original status values
            'priority': request.form.get('priority', 'Medium'),
            'created_at': datetime.now(),
            'user_id': session['user_id']
        }
        mongo.db.tasks.insert_one(task)
        flash('Task added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding task: {str(e)}', 'error')
    return redirect(url_for('board'))


@app.route('/calendar')
def calendar():
    try:
        # Get all tasks with due dates
        tasks = list(mongo.db.tasks.find({
            'due_date': {'$exists': True}
        }).sort('due_date', 1))

        # Format tasks for calendar
        calendar_events = []
        for task in tasks:
            calendar_events.append({
                'title': task['title'],
                'start': task['due_date'].strftime('%Y-%m-%d'),
                'status': task['status'],
                'id': str(task['_id'])
            })

        return render_template('calendar.html', events=calendar_events)
    except Exception as e:
        flash(f'Error loading calendar: {str(e)}', 'error')
        return render_template('calendar.html', events=[])

@app.route('/reports')
def reports():
    return render_template('reports.html')  # You'll need to create this template

@app.route('/settings')
def settings():
    return render_template('settings.html')  # You'll need to create this template

if __name__ == '__main__':
    app.run(debug=True)
