import os
import sqlite3
import logging
import functools
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, flash, g
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from backend.database import DatabaseManager  # Import DatabaseManager class

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['DATABASE_PATH'] = 'databases/taskmanager.db'
# Directory to store uploaded comment attachments
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
            # if request.path.startswith('/api'):
            #     return jsonify({'error': 'Authentication required'}), 401
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
                    session['id']        = user['id']
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

#region User Management
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

#region Project Management
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

#region Task Management

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks_api():
    """API endpoint to retrieve tasks with optional filters"""
    try:
        filters = {
            'status'     : request.args.get('status'),
            'assignee'   : request.args.get('assignee'),
            'project'    : request.args.get('project'),
            'priority'   : request.args.get('priority'),
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

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task_api():
    """API endpoint to create a new task"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # 验证必填字段
        required_fields = ['title', 'project_id']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # 设置默认值
        task_data = {
            'title'      : data['title'],
            'description': data.get('description', ''),
            'type'       : data.get('type'),
            'status'     : data.get('status', 'todo'),
            'priority'   : data.get('priority', 'medium'),
            'severity'   : data.get('severity', 'normal'),
            'start_date' : data.get('start_date'),
            'due_date'   : data.get('due_date'),
            'assignee_id': data.get('assignee_id'),
            'project_id' : data['project_id']
        }
        
        # 创建任务
        task_id = db_manager.add_task(task_data)
        if not task_id:
            return jsonify({'error': 'Failed to create task'}), 500
        
        # 获取新创建的任务详情
        new_task = db_manager.get_task_by_id(task_id)
        if not new_task:
            return jsonify({'error': 'Task created but failed to retrieve details'}), 500
        
        return jsonify(dict(new_task)), 201
    except Exception as e:
        app.logger.exception('Error creating task')
        return jsonify({'error': str(e)}), 500


@app.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT'])
@login_required
def task_api(task_id):
    if request.method == 'GET':
        """API endpoint to get a single task by ID"""
        try:
            task = db_manager.get_task_by_id(task_id)
            if not task:
                return jsonify({'error': 'Task not found'}), 404
                
            # 格式化响应数据
            task_dict = dict(task)
            
            # 创建分配者信息
            assignee_info = {
                'id': task_dict.get('assignee_id'),
                'username': task_dict.pop('assignee_username', ''),
                'full_name': task_dict.pop('assignee_full_name', '')
            }
            
            # 创建项目信息
            project_info = {
                'id': task_dict.get('project_id'),
                'name': task_dict.pop('project_name', ''),
                'category': {
                    'name': task_dict.pop('category_name', ''),
                    'type': task_dict.pop('category_type', '')
                }
            }
            
            return jsonify({
                **task_dict,
                'assignee': assignee_info,
                'project': project_info
            })
        except Exception as e:
            app.logger.exception(f'Error getting task {task_id}')
            return jsonify({'error': str(e)}), 500
            
    elif request.method == 'PUT':
        """API endpoint to update an existing task"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            # 验证任务是否存在
            existing_task = db_manager.get_task_by_id(task_id)
            if not existing_task:
                return jsonify({'error': 'Task not found'}), 404
            
            # 准备更新数据
            update_data = {}
            allowed_fields = [
                'title', 'description', 'type', 'status', 'priority', 'severity',
                'start_date', 'due_date', 'assignee_id', 'project_id'
            ]
            
            # 只更新允许的字段和实际变化的字段
            for field in allowed_fields:
                if field in data and data[field] != existing_task.get(field):
                    update_data[field] = data[field]
            
            # 如果没有需要更新的字段
            if not update_data:
                return jsonify({'message': 'No changes detected'}), 200
            
            # 更新任务
            success = db_manager.update_task(task_id, update_data)
            if success:
                # 获取更新后的任务详情
                updated_task = db_manager.get_task_by_id(task_id)
                if updated_task:
                    # 格式化响应数据
                    task_dict = dict(updated_task)
                    
                    # 创建分配者信息
                    assignee_info = {
                        'id': task_dict.get('assignee_id'),
                        'username': task_dict.pop('assignee_username', ''),
                        'full_name': task_dict.pop('assignee_full_name', '')
                    }
                    
                    # 创建项目信息
                    project_info = {
                        'id': task_dict.get('project_id'),
                        'name': task_dict.pop('project_name', ''),
                        'category': {
                            'name': task_dict.pop('category_name', ''),
                            'type': task_dict.pop('category_type', '')
                        }
                    }
                    
                    return jsonify({
                        **task_dict,
                        'assignee': assignee_info,
                        'project': project_info
                    })
                return jsonify({'message': 'Task updated successfully'})
            else:
                return jsonify({'error': 'Failed to update task'}), 500
        except Exception as e:
            app.logger.exception(f'Error updating task {task_id}')
            return jsonify({'error': str(e)}), 500
        
 
@app.route('/api/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
def add_comment_api(task_id):
    """API endpoint to add a new comment to a task and optionally upload attachments.

    Accepts either JSON ({"content": "..."}) or multipart/form-data with
    'content' and one or more files under the 'files' field.
    """
    try:
        # Support multipart form uploads or raw JSON
        content = None
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            content = request.form.get('content')
        else:
            data = request.get_json(silent=True) or {}
            content = data.get('content')

        if not content:
            return jsonify({'error': 'Content is required'}), 400

        # Resolve author id from session (support different session keys)
        print(f"session: {session}")
        author_id = session.get('id')

        # Insert comment
        comment_id = db_manager.add_comment(task_id, author_id, content)

        uploaded_files = []

        # Handle uploaded files
        if request.content_type and request.content_type.startswith('multipart/form-data'):
            files = request.files.getlist('files')
            for f in files:
                if f and f.filename:
                    filename = secure_filename(f.filename)
                    # 创建相对于UPLOAD_FOLDER的路径
                    relative_task_path = f'task_{task_id}'
                    relative_file_path = os.path.join(relative_task_path, filename)
                    
                    # 实际保存文件的绝对路径
                    abs_task_folder = os.path.join(app.config['UPLOAD_FOLDER'], relative_task_path)
                    os.makedirs(abs_task_folder, exist_ok=True)
                    abs_dest_path = os.path.join(abs_task_folder, filename)
                    f.save(abs_dest_path)

                    # 在数据库中存储相对路径
                    attachment_id = db_manager.add_attachment(comment_id, filename, relative_file_path, f.content_type)
                    download_url = url_for('download_attachment', attachment_id=attachment_id)
                    uploaded_files.append({'id': attachment_id, 'filename': filename, 'download_url': download_url})

        return jsonify({'id': comment_id, 'attachments': uploaded_files, 'message': 'Comment added successfully'})
    except Exception as e:
        app.logger.exception('Error adding comment')
        return jsonify({'error': str(e)}), 500


# Return comments for a task (JSON)
@app.route('/api/tasks/<int:task_id>/comments', methods=['GET'])
@login_required
def get_comments_api(task_id):
    try:
        comments = db_manager.get_comments(task_id)
        result = []
        for c in comments:
            row = dict(c)
            # Normalize created_at to ISO if present
            created_at = row.get('created_at')
            # Map author to include external userID and names
            author = {
                'id': row.get('author_id'),
                'username': row.get('author_username'),
                'full_name': row.get('author_full_name')
            }
            # Attachments
            attachments = []
            atts = db_manager.get_attachments_by_comment(row['id'])
            for a in atts:
                arow = dict(a)
                try:
                    download_url = url_for('download_attachment', attachment_id=arow['id'])
                except Exception:
                    download_url = None
                attachments.append({'id': arow.get('id'), 'filename': arow.get('filename'), 'download_url': download_url})

            result.append({
                'id': row.get('id'),
                'content': row.get('content'),
                'created_at': created_at,
                'author': author,
                'attachments': attachments
            })
        return jsonify(result)
    except Exception as e:
        app.logger.exception('Error fetching comments')
        return jsonify({'error': str(e)}), 500


@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    try:
        # 获取评论及其附件信息
        comment = db_manager.get_comment_with_attachments_by_ID(comment_id)
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
            
        # 检查当前用户是否有权限删除该评论
        current_user_id = session.get('id')
        # 使用正确的作者ID字段
        if comment.get('author_id') != current_user_id:
            return jsonify({'error': 'Unauthorized to delete this comment'}), 403
            
        # 删除物理文件
        if 'attachments' in comment:
            for att in comment['attachments']:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], att['filepath'])
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    app.logger.error(f"Error deleting file {file_path}: {str(e)}")
        
        # 删除数据库中的附件记录
        db_manager.delete_attachments_for_comment(comment_id)
        
        # 删除评论本身
        db_manager.delete_comment(comment_id)
        
        return jsonify({'message': 'Comment deleted successfully'})
    except Exception as e:
        app.logger.exception('Error deleting comment')
        return jsonify({'error': str(e)}), 500

@app.route('/api/attachments/<int:attachment_id>', methods=['GET'])
@login_required
def download_attachment(attachment_id):
    try:
        att = db_manager.get_attachment(attachment_id)
        if not att:
            return jsonify({'error': 'Attachment not found'}), 404
            
        # 将结果转换为字典以便安全访问
        att_row = dict(att)
        relative_path = att_row.get('filepath')
        filename = att_row.get('filename')
        
        if not relative_path:
            return jsonify({'error': 'Attachment path missing in database'}), 500
        
        from flask import send_file

        # 将相对路径转换为绝对路径
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)
        
        if not os.path.exists(filepath):
            app.logger.error(f"Attachment file not found: {filepath}")
            return jsonify({'error': 'File not found on server'}), 404
            
        # 使用 send_file 发送文件
        return send_file(
            filepath, 
            as_attachment=True, 
            download_name=filename
        )
        
    except Exception as e:
        app.logger.exception('Error downloading attachment')
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

if __name__ == '__main__':
    app.run(debug=True)