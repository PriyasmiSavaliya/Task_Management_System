from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime
from datetime import datetime
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user

from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/taskmanager"
app.secret_key = "your-secret-key-here"

mongo = PyMongo(app)


@app.route('/')
def home():
    return redirect(url_for('dashboard'))
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = mongo.db.users.find_one({'email': email})

        if user and check_password_hash(user['password'], password):
            login_user(User(user))
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
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        # Get all tasks for the logged-in user, sorted by due date
        tasks = list(mongo.db.tasks.find({'user_id': session['user_id']}).sort('due_date', 1))
        return render_template('reports.html', tasks=tasks)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'error')
        return render_template('reports.html', tasks=[])


@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('login'))

        return render_template('settings.html', current_user=user)
    except Exception as e:
        flash(f'Error loading settings: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Add these new routes to your app.py

@app.route('/get_task/<task_id>')
def get_task(task_id):
    try:
        task = mongo.db.tasks.find_one({'_id': ObjectId(task_id)})
        if task:
            # Convert ObjectId to string and datetime to string for JSON serialization
            task['_id'] = str(task['_id'])
            task['due_date'] = task['due_date'].strftime('%Y-%m-%d')
            return jsonify(task)
        else:
            return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/update_task_status/<task_id>', methods=['POST'])
def update_task_status(task_id):
    try:
        data = request.get_json()
        new_status = data.get('status')

        if new_status not in ['Pending', 'In Progress', 'Completed']:
            return jsonify({'success': False, 'error': 'Invalid status'})

        mongo.db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {'status': new_status}}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/update_task/<task_id>', methods=['POST'])
def update_task(task_id):
    try:
        data = request.get_json()

        update_data = {
            'title': data.get('title'),
            'category': data.get('category'),
            'due_date': datetime.strptime(data.get('due_date'), '%Y-%m-%d'),
            'priority': data.get('priority')
        }

        mongo.db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': update_data}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/delete_task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        result = mongo.db.tasks.delete_one({'_id': ObjectId(task_id)})
        if result.deleted_count == 1:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Task not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# Settings-related routes
@app.route('/get_user_settings')
def get_user_settings():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401

    try:
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
        if user:
            return jsonify({
                'email_notifications': user.get('email_notifications', True),
                'browser_notifications': user.get('browser_notifications', True),
                'reminder_time': user.get('reminder_time', '30'),
                'theme': user.get('theme', 'light'),
                'default_view': user.get('default_view', 'board'),
                'auto_archive': user.get('auto_archive', False)
            })
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authorized'}), 401

    try:
        data = request.get_json()
        mongo.db.users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {
                'username': data['username'],
                'email': data['email']
            }}
        )
        session['username'] = data['username']
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authorized'}), 401

    try:
        data = request.get_json()
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})

        if not user or not check_password_hash(user['password'], data['current_password']):
            return jsonify({'success': False, 'error': 'Current password is incorrect'}), 401

        if data['new_password'] != data['confirm_password']:
            return jsonify({'success': False, 'error': 'Passwords do not match'}), 400

        hashed_password = generate_password_hash(data['new_password'])
        mongo.db.users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {'password': hashed_password}}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/update_notification_settings', methods=['POST'])
def update_notification_settings():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authorized'}), 401

    try:
        data = request.get_json()
        mongo.db.users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {
                'email_notifications': data['email_notifications'],
                'browser_notifications': data['browser_notifications'],
                'reminder_time': data['reminder_time']
            }}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/update_app_preferences', methods=['POST'])
def update_app_preferences():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authorized'}), 401

    try:
        data = request.get_json()
        mongo.db.users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {
                'theme': data['theme'],
                'default_view': data['default_view'],
                'auto_archive': data['auto_archive']
            }}
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/export_data')
def export_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401

    try:
        # Get all user data
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
        tasks = list(mongo.db.tasks.find({'user_id': session['user_id']}))

        # Prepare export data
        export_data = {
            'user': {
                'username': user['username'],
                'email': user['email'],
                'settings': {
                    'email_notifications': user.get('email_notifications', True),
                    'browser_notifications': user.get('browser_notifications', True),
                    'reminder_time': user.get('reminder_time', '30'),
                    'theme': user.get('theme', 'light'),
                    'default_view': user.get('default_view', 'board'),
                    'auto_archive': user.get('auto_archive', False)
                }
            },
            'tasks': tasks
        }

        # Create response
        from io import BytesIO
        import json
        mem_file = BytesIO()
        mem_file.write(json.dumps(export_data, default=str).encode('utf-8'))
        mem_file.seek(0)

        return send_file(
            mem_file,
            as_attachment=True,
            download_name='taskmanager_export.json',
            mimetype='application/json'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/delete_account', methods=['DELETE'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authorized'}), 401

    try:
        # Delete all user data
        mongo.db.users.delete_one({'_id': ObjectId(session['user_id'])})
        mongo.db.tasks.delete_many({'user_id': session['user_id']})

        # Clear session
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
