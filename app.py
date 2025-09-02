import os
import sqlite3
import logging
import functools
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, flash, g
from werkzeug.security import check_password_hash
from datetime import datetime
from backend.database import DatabaseManager  # Import DatabaseManager class

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['DATABASE_PATH'] = 'databases/taskmanager.db'

# Configure logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Ensure database directory exists
os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)

# Initialize DatabaseManager instance
db_manager = DatabaseManager(app.config['DATABASE_PATH'])

#region Database Connection Management
def get_db():
    """Get a database connection (reuses connection within same request context)"""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE_PATH'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    """Close database connection at end of request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()
#endregion

#region Authentication Decorators
def login_required(view):
    """View decorator that redirects anonymous users to login page"""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'userID' not in session:
            if request.path.startswith('/api'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view
#endregion

#region Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login authentication"""
    if request.method == 'POST':
        userID = request.form['userID'].strip()
        password_input = request.form['password'].strip()
        
        db = get_db()
        try:
            cursor = db.cursor()
            cursor.execute('SELECT * FROM users WHERE userID = ?', (userID,))
            user = cursor.fetchone()
            
            if user:
                if user['password_hash'] == password_input:
                    # Update session with user data
                    session['userID']    = user['userID']
                    session['username']  = user['username']
                    session['full_name'] = user['full_name']
                    session['title']     = user['title']
                    return redirect(url_for('task_management'))
                else:
                    return render_template('login.html', error='Invalid credentials')
            else:
                return render_template('login.html', error='User not found')
                
        except Exception as e:
            print(f"Database error: {str(e)}")
            flash('System error, please try again later')

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Clear current user session"""
    session.clear()
    return redirect(url_for('login'))
#endregion

#region Main Page Routes
@app.route('/')
@login_required
def index():
    """Redirect to task management dashboard"""
    return redirect(url_for('task_management'))

@app.route('/task_management')
@login_required
def task_management():
    """Render main task management interface"""
    userID = session['userID']    
    username = session['username']  
    full_name = session['full_name'] 
    return render_template('task_management.html',
                           userID=userID,
                           username=username,
                           full_name=full_name)

@app.route('/api/task_manage', methods=['GET', 'POST'])
@login_required
def redirect_to_task_manage():
    """Redirect to task management interface"""
    return redirect(url_for('task_manage'))

@app.route('/task_manage')
@login_required
def task_manage():
    """Render task management page"""
    return render_template('task_manage.html')
#endregion

#region API Routes - User Management
@app.route('/api/users', methods=['GET'])
@login_required
def get_users_api():
    """API endpoint to retrieve all users"""
    try:
        users = db_manager.get_users()
        return jsonify([dict(user) for user in users])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
#endregion

#region API Routes - Project Management
@app.route('/api/projects', methods=['GET'])
@login_required
def get_projects_api():
    """API endpoint to retrieve all projects"""
    try:
        projects = db_manager.get_projects()
        result = []
        for project in projects:
            project_dict = dict(project)
            project_dict['category'] = {
                'name': project_dict.pop('category_name'),
                'type': project_dict.pop('category_type')
            }
            result.append(project_dict)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
#endregion

#region API Routes - Task Management
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks_api():
    """API endpoint to retrieve tasks with optional filters"""
    try:
        filters = {
            'status': request.args.get('status'),
            'assignee': request.args.get('assignee'),
            'project': request.args.get('project'),
            'priority': request.args.get('priority'),
            'search_text': request.args.get('search_text')
        }
        
        tasks = db_manager.get_tasks(filters)
        result = []
        for task in tasks:
            task_dict = dict(task)
            task_dict['assignee'] = {
                'id': task_dict['assignee_id'],
                'username': task_dict.pop('assignee_username'),
                'full_name': task_dict.pop('assignee_full_name')
            }
            task_dict['project'] = {
                'id': task_dict['project_id'],
                'name': task_dict.pop('project_name'),
                'category': {
                    'name': task_dict.pop('category_name'),
                    'type': task_dict.pop('category_type')
                }
            }
            result.append(task_dict)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task_api(task_id):
    """API endpoint to retrieve a single task by ID"""
    try:
        task = db_manager.get_task(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        task_dict = dict(task)
        task_dict['assignee'] = {
            'id': task_dict['assignee_id'],
            'username': task_dict.pop('assignee_username'),
            'full_name': task_dict.pop('assignee_full_name')
        }
        task_dict['project'] = {
            'id': task_dict['project_id'],
            'name': task_dict.pop('project_name'),
            'category': {
                'id': task_dict['category_id'],
                'name': task_dict.pop('category_name'),
                'type': task_dict.pop('category_type')
            }
        }
        return jsonify(task_dict)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task_api():
    """API endpoint to create a new task"""
    try:
        data = request.get_json()
        if not data or 'title' not in data or 'project_id' not in data:
            return jsonify({'error': 'Title and project ID are required'}), 400
        
        task_id = db_manager.create_task(data)
        return jsonify({'id': task_id, 'message': 'Task created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task_api(task_id):
    """API endpoint to update an existing task"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        success = db_manager.update_task(task_id, data)
        if success:
            return jsonify({'message': 'Task updated successfully'})
        else:
            return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500
#endregion

#region API Routes - Comment Management
@app.route('/api/tasks/<int:task_id>/comments', methods=['GET'])
@login_required
def get_comments_api(task_id):
    """API endpoint to retrieve comments for a task"""
    try:
        comments = db_manager.get_comments(task_id)
        result = []
        for comment in comments:
            comment_dict = dict(comment)
            comment_dict['author'] = {
                'id': comment_dict['author_id'],
                'username': comment_dict.pop('author_username'),
                'full_name': comment_dict.pop('author_full_name')
            }
            result.append(comment_dict)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
def add_comment_api(task_id):
    """API endpoint to add a new comment to a task"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        # Get current user from session
        author_id = session.get('user_id', 1)
        
        comment_id = db_manager.add_comment(task_id, author_id, data['content'])
        return jsonify({'id': comment_id, 'message': 'Comment added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
#endregion

#region Dashboard Routes
@app.route('/api/dashboard')
@login_required
def get_dashboard_content():
    """Render dashboard view for administrators"""
    app.logger.info(f"Dashboard requested by {session.get('username')} with title: {session.get('title')}")
    try:
        # Check admin privileges
        if session.get('title') != 'System Administrator':
            app.logger.warning(f"Unauthorized access attempt by {session.get('username')}")
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get dashboard statistics
        app.logger.info("Fetching dashboard statistics...")
        total_projects = db_manager.get_total_projects()
        total_tasks = db_manager.get_total_tasks()
        active_projects = db_manager.get_active_projects()
        delayed_tasks = db_manager.get_delayed_tasks()
        
        app.logger.info(f"Statistics: projects={total_projects}, tasks={total_tasks}, active={active_projects}, delayed={delayed_tasks}")
        
        # Render dashboard template
        return render_template('dashboard.html', 
                              total_projects=total_projects,
                              total_tasks=total_tasks,
                              active_projects=active_projects,
                              delayed_tasks=delayed_tasks)
    except Exception as e:
        app.logger.error(f"Error in get_dashboard_content: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

# Dashboard API endpoints
@app.route('/api/dashboard/project-task-counts', methods=['GET'])
@login_required
def get_project_task_counts():
    """API endpoint for project-task count statistics"""
    try:
        project_task_counts = db_manager.get_project_task_counts()
        return jsonify([dict(row) for row in project_task_counts])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/user-task-distribution', methods=['GET'])
@login_required
def get_user_task_distribution():
    """API endpoint for user task distribution data"""
    try:
        user_task_distribution = db_manager.get_user_task_distribution()
        return jsonify([dict(row) for row in user_task_distribution])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/total-projects', methods=['GET'])
@login_required
def get_total_projects():
    """API endpoint for total projects count"""
    try:
        total = db_manager.get_total_projects()
        return jsonify({'total': total})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/total-tasks', methods=['GET'])
@login_required
def get_total_tasks():
    """API endpoint for total tasks count"""
    try:
        total = db_manager.get_total_tasks()
        return jsonify({'total': total})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/active-projects', methods=['GET'])
@login_required
def get_active_projects():
    """API endpoint for active projects count"""
    try:
        active = db_manager.get_active_projects()
        return jsonify({'active': active})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/delayed-tasks', methods=['GET'])
@login_required
def get_delayed_tasks():
    """API endpoint for delayed tasks count"""
    try:
        delayed = db_manager.get_delayed_tasks()
        return jsonify({'delayed': delayed})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
#endregion

# Application Entry Point
if __name__ == '__main__':
    app.run(debug=True)