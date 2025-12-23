"""
Task Management System - Flask Backend
Handles authentication, task CRUD, comments, and dashboard APIs
"""

import os
import sqlite3
import logging
import functools
import json
from functools import lru_cache
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, flash, g, send_file
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from backend.database import DatabaseManager

# ==================================================================
# Application Configuration
# ==================================================================

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['DATABASE_PATH'] = 'databases/taskmanager.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
app.logger.setLevel(logging.INFO)

# Initialize database manager
db_manager = DatabaseManager(app.config['DATABASE_PATH'])

# Admin mapping configuration
CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'config')
ADMIN_MAPPING_FILE = os.path.join(CONFIG_DIR, 'admin_employee_mapping.json')

# ==================================================================
# Admin-Employee Mapping Functions
# ==================================================================

@lru_cache(maxsize=1)
def load_admin_employee_mapping():
    """
    Load admin-employee mapping from JSON configuration file
    Returns: Dictionary mapping admin userIDs to lists of employee userIDs
    """
    try:
        if not os.path.exists(ADMIN_MAPPING_FILE):
            app.logger.warning(f"Admin mapping file not found: {ADMIN_MAPPING_FILE}")
            return {}
        
        with open(ADMIN_MAPPING_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            mapping = data.get('admin_employee_mapping', {})
            app.logger.info(f"Loaded admin mapping with {len(mapping)} administrators")
            return mapping
    except Exception as e:
        app.logger.error(f"Failed to load admin mapping: {str(e)}")
        return {}

def reload_admin_mapping():
    """
    Clear cache and reload admin-employee mapping
    Used when configuration is updated
    """
    load_admin_employee_mapping.cache_clear()
    app.logger.info("Admin mapping cache cleared and reloaded")
    return load_admin_employee_mapping()

# ==================================================================
# Database Connection Management
# ==================================================================

def get_db():
    """
    Get database connection for current request context
    Reuses connection within same request
    """
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

# ==================================================================
# Authentication Decorator
# ==================================================================

def login_required(view):
    """
    Decorator to require authentication for views
    Redirects unauthenticated users to login page
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'userID' not in session:
            app.logger.warning(f"Unauthorized access attempt to {request.path}")
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

# ==================================================================
# Authentication Routes
# ==================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login authentication"""
    if request.method == 'POST':
        userID = request.form['userID'].strip()
        password_input = request.form['password'].strip()
        
        app.logger.info(f"Login attempt for userID: {userID}")
        
        db = get_db()
        try:
            cursor = db.cursor()
            cursor.execute('SELECT * FROM users WHERE userID = ?', (userID,))
            user = cursor.fetchone()
            
            if user:
                # Note: Using plain text password comparison (should use hash in production)
                if user['password_hash'] == password_input:
                    # Store user session data
                    session['id'] = user['id']
                    session['userID'] = user['userID']
                    session['username'] = user['username']
                    session['full_name'] = user['full_name']
                    session['title'] = user['title']
                    
                    app.logger.info(f"Login successful: {userID} ({user['title']})")
                    return redirect(url_for('task_management'))
                else:
                    app.logger.warning(f"Invalid password for userID: {userID}")
                    return render_template('login.html', error='Invalid credentials')
            else:
                app.logger.warning(f"User not found: {userID}")
                return render_template('login.html', error='User not found')
                
        except Exception as e:
            app.logger.error(f"Login database error: {str(e)}")
            flash('System error, please try again later')

    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Clear user session and redirect to login"""
    userID = session.get('userID', 'Unknown')
    session.clear()
    app.logger.info(f"User logged out: {userID}")
    return redirect(url_for('login'))

# ==================================================================
# Main Application Routes
# ==================================================================

@app.route('/')
@login_required
def index():
    """Root path redirects to task management"""
    return redirect(url_for('task_management'))

@app.route('/task_management')
@login_required
def task_management():
    """Render main task management interface"""
    userID = session['userID']
    username = session['username']
    full_name = session['full_name']
    
    app.logger.info(f"Task management accessed by: {userID}")
    
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

# ==================================================================
# User Management API
# ==================================================================

@app.route('/api/users', methods=['GET'])
@login_required
def get_users_api():
    """Get all users"""
    try:
        users = db_manager.get_users()
        app.logger.info(f"Retrieved {len(users)} users")
        return jsonify([dict(user) for user in users])
    except Exception as e:
        app.logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================================================================
# Project Management API
# ==================================================================

@app.route('/api/projects', methods=['GET'])
@login_required
def get_projects_api():
    """Get all projects with category information"""
    try:
        projects = db_manager.get_projects()
        result = []
        
        for project in projects:
            project_dict = dict(project)
            # Restructure category data
            project_dict['category'] = {
                'name': project_dict.pop('category_name'),
                'type': project_dict.pop('category_type')
            }
            result.append(project_dict)
        
        app.logger.info(f"Retrieved {len(result)} projects")
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error getting projects: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================================================================
# Task Management API
# ==================================================================

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks_api():
    """
    Get tasks with role-based access control
    - System Admin: Access all tasks
    - Secondary Admin: Access own tasks and managed employees' tasks
    - Employee: Access only own tasks
    """
    try:
        # Get current user information
        current_user_id = session.get('userID')
        current_user_title = session.get('title')
        
        app.logger.info(f"Task query by: {current_user_id} ({current_user_title})")
        
        # Build filter parameters
        filters = {
            'status': request.args.get('status'),
            'assignee': request.args.get('assignee'),
            'project': request.args.get('project'),
            'priority': request.args.get('priority'),
            'search_text': request.args.get('search_text')
        }
        
        # Apply role-based access control
        if current_user_title == "System Administrator":
            app.logger.info("System Administrator - Full access granted")
        else:
            # Load admin-employee mapping
            admin_map = load_admin_employee_mapping()
            
            if current_user_id in admin_map:
                # Secondary admin: Manage self and assigned employees
                managed_employee_ids = admin_map[current_user_id]
                allowed_user_ids = managed_employee_ids + [current_user_id]
                
                if filters.get('assignee'):
                    # Validate access to specified assignee
                    specified_assignee = filters['assignee']
                    if specified_assignee not in allowed_user_ids:
                        app.logger.warning(
                            f"Admin {current_user_id} attempted unauthorized access to {specified_assignee}"
                        )
                        return jsonify([]), 200
                else:
                    # Apply permission filter for "All Assignees" view
                    filters['allowed_assignees'] = allowed_user_ids
                    app.logger.info(f"Admin viewing {len(allowed_user_ids)} managed users")
            else:
                # Regular employee: Own tasks only
                filters['allowed_assignees'] = [current_user_id]
                app.logger.info(f"Employee viewing own tasks only")
        
        # Fetch tasks from database
        tasks = db_manager.get_tasks(filters)
        app.logger.info(f"Returned {len(tasks)} tasks")
        
        # Format response data
        result = []
        for task in tasks:
            task_dict = dict(task)
            
            # Structure assignee data
            task_dict['assignee'] = {
                'id': task_dict.get('assignee_id'),
                'userID': task_dict.get('assignee_user_id'),
                'username': task_dict.pop('assignee_username', None),
                'full_name': task_dict.pop('assignee_full_name', None)
            }
            
            # Structure project data
            task_dict['project'] = {
                'id': task_dict.get('project_id'),
                'name': task_dict.pop('project_name', None),
                'category': {
                    'name': task_dict.pop('category_name', None),
                    'type': task_dict.pop('category_type', None)
                }
            }
            
            result.append(task_dict)
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error in get_tasks_api: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task_api():
    """Create a new task"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['title', 'project_id']
        for field in required_fields:
            if field not in data or not data[field]:
                app.logger.warning(f"Missing required field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Prepare task data with defaults
        task_data = {
            'title': data['title'],
            'description': data.get('description', ''),
            'type': data.get('type'),
            'status': data.get('status', 'todo'),
            'priority': data.get('priority', 'medium'),
            'severity': data.get('severity', 'normal'),
            'start_date': data.get('start_date'),
            'due_date': data.get('due_date'),
            'assignee_id': data.get('assignee_id'),
            'project_id': data['project_id']
        }
        
        # Create task in database
        task_id = db_manager.add_task(task_data)
        if not task_id:
            app.logger.error("Failed to create task")
            return jsonify({'error': 'Failed to create task'}), 500
        
        # Retrieve newly created task
        new_task = db_manager.get_task_by_id(task_id)
        if not new_task:
            app.logger.error(f"Task {task_id} created but retrieval failed")
            return jsonify({'error': 'Task created but failed to retrieve details'}), 500
        
        app.logger.info(f"Task created successfully: ID={task_id} by {session.get('userID')}")
        return jsonify(dict(new_task)), 201
        
    except Exception as e:
        app.logger.error(f"Error creating task: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task_api(task_id):
    """Get single task by ID"""
    try:
        task = db_manager.get_task_by_id(task_id)
        if not task:
            app.logger.warning(f"Task not found: {task_id}")
            return jsonify({'error': 'Task not found'}), 404
        
        # Format response data
        task_dict = dict(task)
        
        # Structure assignee information
        assignee_info = {
            'id': task_dict.get('assignee_id'),
            'username': task_dict.pop('assignee_username', ''),
            'full_name': task_dict.pop('assignee_full_name', '')
        }
        
        # Structure project information
        project_info = {
            'id': task_dict.get('project_id'),
            'name': task_dict.pop('project_name', ''),
            'category': {
                'name': task_dict.pop('category_name', ''),
                'type': task_dict.pop('category_type', '')
            }
        }
        
        app.logger.info(f"Task retrieved: {task_id}")
        return jsonify({
            **task_dict,
            'assignee': assignee_info,
            'project': project_info
        })
        
    except Exception as e:
        app.logger.error(f"Error getting task {task_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task_api(task_id):
    """Update existing task"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Verify task exists
        existing_task = db_manager.get_task_by_id(task_id)
        if not existing_task:
            app.logger.warning(f"Task not found for update: {task_id}")
            return jsonify({'error': 'Task not found'}), 404
        
        # Prepare update data - only changed fields
        update_data = {}
        allowed_fields = [
            'title', 'description', 'type', 'status', 'priority', 'severity',
            'start_date', 'due_date', 'assignee_id', 'project_id'
        ]
        
        for field in allowed_fields:
            if field in data:
                # Skip None values unless original is also None
                if data[field] is None and existing_task.get(field) is not None:
                    app.logger.warning(f"Skipping {field}: cannot set to None")
                    continue
                
                # Only update if value changed
                if data[field] != existing_task.get(field):
                    update_data[field] = data[field]
        
        # Check if any changes exist
        if not update_data:
            app.logger.info(f"No changes detected for task {task_id}")
            return jsonify({'message': 'No changes detected'}), 200
        
        # Update task in database
        success = db_manager.update_task(task_id, update_data)
        if not success:
            app.logger.error(f"Failed to update task {task_id}")
            return jsonify({'error': 'Failed to update task'}), 500
        
        # Retrieve updated task
        updated_task = db_manager.get_task_by_id(task_id)
        if not updated_task:
            app.logger.error(f"Task {task_id} updated but retrieval failed")
            return jsonify({'message': 'Task updated successfully'})
        
        # Format response
        task_dict = dict(updated_task)
        
        assignee_info = {
            'id': task_dict.get('assignee_id'),
            'username': task_dict.pop('assignee_username', ''),
            'full_name': task_dict.pop('assignee_full_name', '')
        }
        
        project_info = {
            'id': task_dict.get('project_id'),
            'name': task_dict.pop('project_name', ''),
            'category': {
                'name': task_dict.pop('category_name', ''),
                'type': task_dict.pop('category_type', '')
            }
        }
        
        app.logger.info(f"Task updated successfully: {task_id} by {session.get('userID')}")
        return jsonify({
            **task_dict,
            'assignee': assignee_info,
            'project': project_info
        })
        
    except Exception as e:
        app.logger.error(f"Error updating task {task_id}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Delete task and associated data"""
    try:
        # Verify task exists
        task = db_manager.get_task_by_id(task_id)
        if not task:
            app.logger.warning(f"Task not found for deletion: {task_id}")
            return jsonify({'error': 'Task not found'}), 404
        
        # Delete task (database will cascade delete comments and attachments)
        db_manager.delete_task(task_id)
        
        app.logger.info(f"Task deleted: {task_id} by {session.get('userID')}")
        return jsonify({'message': 'Task deleted successfully'})
        
    except Exception as e:
        app.logger.error(f"Error deleting task {task_id}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# ==================================================================
# Comment Management API
# ==================================================================

@app.route('/api/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
def add_comment_api(task_id):
    """
    Add comment to task with optional file attachments
    Accepts multipart/form-data or JSON
    """
    try:
        # Extract content from request
        content = None
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            content = request.form.get('content')
        else:
            data = request.get_json(silent=True) or {}
            content = data.get('content')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        # Get author ID from session
        author_id = session.get('id')
        
        # Create comment in database
        comment_id = db_manager.add_comment(task_id, author_id, content)
        app.logger.info(f"Comment created: ID={comment_id} on task={task_id} by user={author_id}")
        
        uploaded_files = []
        
        # Handle file uploads
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            files = request.files.getlist('files')
            for f in files:
                if f and f.filename:
                    filename = secure_filename(f.filename)
                    
                    # Create task-specific upload directory
                    relative_task_path = f'task_{task_id}'
                    relative_file_path = os.path.join(relative_task_path, filename)
                    
                    abs_task_folder = os.path.join(app.config['UPLOAD_FOLDER'], relative_task_path)
                    os.makedirs(abs_task_folder, exist_ok=True)
                    
                    abs_dest_path = os.path.join(abs_task_folder, filename)
                    f.save(abs_dest_path)
                    
                    # Save attachment record with relative path
                    attachment_id = db_manager.add_attachment(
                        comment_id, filename, relative_file_path, f.content_type
                    )
                    
                    download_url = url_for('download_attachment', attachment_id=attachment_id)
                    uploaded_files.append({
                        'id': attachment_id,
                        'filename': filename,
                        'download_url': download_url
                    })
                    
                    app.logger.info(f"Attachment uploaded: {filename} for comment={comment_id}")
        
        return jsonify({
            'id': comment_id,
            'attachments': uploaded_files,
            'message': 'Comment added successfully'
        })
        
    except Exception as e:
        app.logger.error(f"Error adding comment to task {task_id}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/comments', methods=['GET'])
@login_required
def get_comments_api(task_id):
    """Get all comments for a task"""
    try:
        comments = db_manager.get_comments(task_id)
        result = []
        
        for c in comments:
            row = dict(c)
            
            # Structure author information
            author = {
                'id': row.get('author_id'),
                'username': row.get('author_username'),
                'full_name': row.get('author_full_name')
            }
            
            # Get attachments for this comment
            attachments = []
            atts = db_manager.get_attachments_by_comment(row['id'])
            for a in atts:
                arow = dict(a)
                try:
                    download_url = url_for('download_attachment', attachment_id=arow['id'])
                except Exception:
                    download_url = None
                    
                attachments.append({
                    'id': arow.get('id'),
                    'filename': arow.get('filename'),
                    'download_url': download_url
                })
            
            result.append({
                'id': row.get('id'),
                'content': row.get('content'),
                'created_at': row.get('created_at'),
                'author': author,
                'attachments': attachments
            })
        
        app.logger.info(f"Retrieved {len(result)} comments for task {task_id}")
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error fetching comments for task {task_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Delete comment and associated files"""
    try:
        # Get comment with attachments
        comment = db_manager.get_comment_with_attachments_by_ID(comment_id)
        if not comment:
            app.logger.warning(f"Comment not found for deletion: {comment_id}")
            return jsonify({'error': 'Comment not found'}), 404
        
        # Verify user permission
        current_user_id = session.get('id')
        if comment.get('author_id') != current_user_id:
            app.logger.warning(
                f"Unauthorized delete attempt: comment={comment_id} by user={current_user_id}"
            )
            return jsonify({'error': 'Unauthorized to delete this comment'}), 403
        
        # Delete physical files
        if 'attachments' in comment:
            for att in comment['attachments']:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], att['filepath'])
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        app.logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    app.logger.error(f"Error deleting file {file_path}: {str(e)}")
        
        # Delete database records
        db_manager.delete_attachments_for_comment(comment_id)
        db_manager.delete_comment(comment_id)
        
        app.logger.info(f"Comment deleted: {comment_id} by user={current_user_id}")
        return jsonify({'message': 'Comment deleted successfully'})
        
    except Exception as e:
        app.logger.error(f"Error deleting comment {comment_id}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/attachments/<int:attachment_id>', methods=['GET'])
@login_required
def download_attachment(attachment_id):
    """Download attachment file"""
    try:
        att = db_manager.get_attachment(attachment_id)
        if not att:
            app.logger.warning(f"Attachment not found: {attachment_id}")
            return jsonify({'error': 'Attachment not found'}), 404
        
        att_row = dict(att)
        relative_path = att_row.get('filepath')
        filename = att_row.get('filename')
        
        if not relative_path:
            app.logger.error(f"Attachment {attachment_id} missing filepath in database")
            return jsonify({'error': 'Attachment path missing in database'}), 500
        
        # Convert relative path to absolute path
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)
        
        if not os.path.exists(filepath):
            app.logger.error(f"Attachment file not found on disk: {filepath}")
            return jsonify({'error': 'File not found on server'}), 404
        
        app.logger.info(f"Attachment downloaded: {filename} by {session.get('userID')}")
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        app.logger.error(f"Error downloading attachment {attachment_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin-employee-map', methods=['GET'])
@login_required
def get_admin_employee_map():
    """Get admin-employee mapping configuration"""
    try:
        admin_employee_mapping = load_admin_employee_mapping()
        app.logger.info(f"Admin mapping retrieved by {session.get('userID')}")
        return jsonify(admin_employee_mapping), 200
    except Exception as e:
        app.logger.error(f"Error getting admin-employee mapping: {str(e)}")
        return jsonify({"error": "Failed to load admin-employee mapping"}), 500

# ==================================================================
# Dashboard API
# ==================================================================

@app.route('/api/dashboard')
@login_required
def get_dashboard_content():
    """Render dashboard for administrators"""
    user_title = session.get('title')
    username = session.get('username')
    
    app.logger.info(f"Dashboard accessed by: {username} ({user_title})")
    
    try:
        # Verify admin privileges
        if user_title != 'System Administrator':
            app.logger.warning(f"Unauthorized dashboard access by: {username}")
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get dashboard statistics
        total_projects = db_manager.get_total_projects()
        total_tasks = db_manager.get_total_tasks()
        active_tasks = db_manager.get_active_tasks()
        delayed_tasks = db_manager.get_delayed_tasks()
        
        app.logger.info(
            f"Dashboard stats - Projects: {total_projects}, "
            f"Tasks: {total_tasks}, Active: {active_tasks}, Delayed: {delayed_tasks}"
        )
        
        return render_template('dashboard.html',
                             total_projects=total_projects,
                             total_tasks=total_tasks,
                             active_tasks=active_tasks,
                             delayed_tasks=delayed_tasks)
                             
    except Exception as e:
        app.logger.error(f"Error in dashboard: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/dashboard/project-task-counts', methods=['GET'])
@login_required
def get_project_task_counts():
    """Get task count per project"""
    try:
        project_task_counts = db_manager.get_project_task_counts()
        return jsonify([dict(row) for row in project_task_counts])
    except Exception as e:
        app.logger.error(f"Error getting project task counts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/user-task-distribution', methods=['GET'])
@login_required
def get_user_task_distribution():
    """Get task distribution per user"""
    try:
        user_task_distribution = db_manager.get_user_task_distribution()
        return jsonify([dict(row) for row in user_task_distribution])
    except Exception as e:
        app.logger.error(f"Error getting user task distribution: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/total-projects', methods=['GET'])
@login_required
def get_total_projects():
    """Get total project count"""
    try:
        total = db_manager.get_total_projects()
        return jsonify({'total': total})
    except Exception as e:
        app.logger.error(f"Error getting total projects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/total-tasks', methods=['GET'])
@login_required
def get_total_tasks():
    """Get total task count"""
    try:
        total = db_manager.get_total_tasks()
        return jsonify({'total': total})
    except Exception as e:
        app.logger.error(f"Error getting total tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/active-tasks', methods=['GET'])
@login_required
def get_active_tasks():
    """Get active task count"""
    try:
        active = db_manager.get_active_tasks()
        return jsonify({'active': active})
    except Exception as e:
        app.logger.error(f"Error getting active tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/delayed-tasks', methods=['GET'])
@login_required
def get_delayed_tasks():
    """Get delayed task count"""
    try:
        delayed = db_manager.get_delayed_tasks()
        return jsonify({'delayed': delayed})
    except Exception as e:
        app.logger.error(f"Error getting delayed tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================================================================
# Application Entry Point
# ==================================================================

if __name__ == '__main__':
    import socket
    from netifaces import interfaces, ifaddresses, AF_INET
    
    port = 5008
    
    def get_lan_ip():
        """
        Get local area network IPv4 address
        Returns first non-loopback, non-link-local address
        """
        for interface in interfaces():
            addrs = ifaddresses(interface).get(AF_INET, [])
            for addr in addrs:
                ip = addr['addr']
                if not ip.startswith('127.') and not ip.startswith('169.254.'):
                    return ip
        return socket.gethostbyname(socket.gethostname())
    
    # Get computer name for NetBIOS access
    computer_name = socket.gethostname().strip().replace(' ', '_')
    lan_ip = get_lan_ip()
    
    # Display access URLs
    print("\n" + "=" * 60)
    print("Task Management System - Server Starting")
    print("=" * 60)
    print(f"Local Access:   http://localhost:{port}")
    print(f"Network Access: http://{computer_name}:{port}")
    print(f"IP Access:      http://{lan_ip}:{port}")
    print("=" * 60 + "\n")
    
    # Configure Windows Firewall (requires admin privileges)
    try:
        import subprocess
        subprocess.run(
            f'netsh advfirewall firewall add rule name="Flask Port {port}" '
            f'dir=in action=allow protocol=TCP localport={port}',
            shell=True,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("[INFO] Firewall rule configured successfully")
    except Exception as e:
        print("[WARNING] Could not configure firewall automatically")
        print("[WARNING] Run as administrator to enable automatic firewall configuration")
    
    # Start server
    try:
        # For production, use Waitress WSGI server
        from waitress import serve
        serve(app, host='0.0.0.0', port=port, threads=8)
        
        # For development, use Flask development server
        # app.run(host='0.0.0.0', port=port, debug=True)
        
    except KeyboardInterrupt:
        print("\n[INFO] Server shutting down gracefully...")
    except Exception as e:
        app.logger.error(f"Server error: {str(e)}", exc_info=True)
        print(f"\n[ERROR] Server failed to start: {str(e)}")
