# app.py
from flask.cli import with_appcontext
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Category, Project, Task, Comment
from sqlalchemy.orm import joinedload
from datetime import datetime
import os
import json
import click

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///taskmanager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Flask-Login configuration
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Route definitions
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/tasks')
@login_required
def get_tasks():
    # Get all query parameters
    status = request.args.get('status', 'all')
    assignee = request.args.get('assignee', 'all')
    project = request.args.get('project', 'all')
    priority = request.args.get('priority', 'all')
    text = request.args.get('text', '').lower()
    
    # Build base query with eager loading
    query = Task.query.options(
        joinedload(Task.assignee),
        joinedload(Task.project).joinedload(Project.category),
        joinedload(Task.comments).joinedload(Comment.author)
    ).order_by(Task.due_date.asc())
    
    # Apply filters
    if status != 'all':
        query = query.filter(Task.status == status)
    if assignee != 'all':
        query = query.filter(Task.assignee_id == assignee)
    if project != 'all':
        query = query.filter(Task.project_id == project)
    if priority != 'all':
        query = query.filter(Task.priority == priority)
    
    # Execute query
    tasks = query.all()
    
    # Apply text search filter (case-insensitive)
    if text:
        filtered_tasks = []
        for task in tasks:
            # Extract text fields to search
            search_fields = [
                task.title,
                task.description or "",
                task.project.name,
                task.assignee.full_name if task.assignee else "",
                task.assignee.username if task.assignee else ""
            ]
            
            # Check if any field contains the search text
            if any(text in field.lower() for field in search_fields):
                filtered_tasks.append(task)
        tasks = filtered_tasks
    
    # Convert to JSON format
    tasks_data = []
    for task in tasks:
        comments = []
        for comment in task.comments:
            comments.append({
                'id': comment.id,
                'content': comment.content,
                'author': {
                    'id': comment.author.id,
                    'username': comment.author.username,
                    'full_name': comment.author.full_name
                },
                'date': comment.created_at.strftime('%Y-%m-%d')  # Only date part
            })
        
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'type': task.type.value if task.type else None,
            'status': task.status,
            'priority': task.priority,
            'severity': task.severity.value if task.severity else None,
            'start_date': task.start_date.isoformat() if task.start_date else None,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
            'assignee': {
                'id': task.assignee.id if task.assignee else None,
                'username': task.assignee.username if task.assignee else 'Unassigned',
                'full_name': task.assignee.full_name if task.assignee else None
            },
            'project': {
                'id': task.project.id,
                'name': task.project.name,
                'category': {
                    'id': task.project.category.id,
                    'name': task.project.category.name,
                    'type': task.project.category.type
                }
            },
            'comments': comments
        }
        tasks_data.append(task_data)
    
    return jsonify(tasks_data)

@app.route('/api/tasks/<int:task_id>')
@login_required
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    task_data = {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'type': task.type,
        'status': task.status,
        'priority': task.priority,
        'severity': task.severity,
        'start_date': task.start_date.isoformat() if task.start_date else None,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'created_at': task.created_at.isoformat(),
        'updated_at': task.updated_at.isoformat(),
        'assignee': {
            'id': task.assignee.id if task.assignee else None,
            'username': task.assignee.username if task.assignee else 'Unassigned',
            'full_name': task.assignee.full_name if task.assignee else None,
            'title': task.assignee.title if task.assignee else None
        },
        'project': {
            'id': task.project.id,
            'name': task.project.name,
            'main_rd': task.project.main_rd,
            'supplier': task.project.supplier,
            'category': {
                'id': task.project.category.id,
                'name': task.project.category.name,
                'type': task.project.category.type
            }
        }
    }
    
    return jsonify(task_data)

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.json
    
    # Validate required fields
    required_fields = ['title', 'project_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Create new task
    new_task = Task(
        title=data['title'],
        description=data.get('description', ''),
        type=data.get('type', 'task'),
        status=data.get('status', 'todo'),
        priority=data.get('priority', 'medium'),
        severity=data.get('severity', 'normal'),
        project_id=data['project_id'],
        assignee_id=data.get('assignee_id'),
        start_date=datetime.fromisoformat(data['start_date']) if 'start_date' in data else None,
        due_date=datetime.fromisoformat(data['due_date']) if 'due_date' in data else None
    )
    
    db.session.add(new_task)
    db.session.commit()
    
    return jsonify({'message': 'Task created successfully', 'id': new_task.id}), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json
    
    # Update task fields
    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'type' in data:
        task.type = data['type']
    if 'status' in data:
        task.status = data['status']
    if 'priority' in data:
        task.priority = data['priority']
    if 'severity' in data:
        task.severity = data['severity']
    if 'assignee_id' in data:
        task.assignee_id = data['assignee_id']
    if 'project_id' in data:
        task.project_id = data['project_id']
    if 'start_date' in data:
        task.start_date = datetime.fromisoformat(data['start_date']) if data['start_date'] else None
    if 'due_date' in data:
        task.due_date = datetime.fromisoformat(data['due_date']) if data['due_date'] else None
    
    task.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Task updated successfully'})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'message': 'Task deleted successfully'})

@app.route('/api/tasks/<int:task_id>/comments')
@login_required
def get_comments(task_id):
    task = Task.query.get_or_404(task_id)
    comments = [
        {
            'id': comment.id,
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'author': {
                'id': comment.author.id,
                'username': comment.author.username
            }
        }
        for comment in task.comments
    ]
    
    return jsonify(comments)

@app.route('/api/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
def add_comment(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.json
    
    if 'content' not in data or not data['content'].strip():
        return jsonify({'error': 'Comment content is required'}), 400
    
    new_comment = Comment(
        content=data['content'],
        task_id=task_id,
        author_id=current_user.id
    )
    
    db.session.add(new_comment)
    db.session.commit()
    
    return jsonify({'message': 'Comment added successfully'}), 201

@app.route('/api/projects')
@login_required
def get_projects():
    projects = Project.query.all()
    projects_data = [
        {
            'id': project.id,
            'name': project.name,
            'main_rd': project.main_rd,
            'supplier': project.supplier,
            'category': {
                'id': project.category.id,
                'name': project.category.name,
                'type': project.category.type
            }
        }
        for project in projects
    ]
    
    return jsonify(projects_data)

@app.route('/api/categories')
@login_required
def get_categories():
    categories = Category.query.all()
    categories_data = [
        {
            'id': category.id,
            'name': category.name,
            'type': category.type,
            'description': category.description
        }
        for category in categories
    ]
    
    return jsonify(categories_data)

@app.route('/api/users')
@login_required
def get_users():
    users = User.query.filter_by(role='employee').all()
    users_data = [
        {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'title': user.title
        }
        for user in users
    ]
    
    return jsonify(users_data)


# 注册自定义命令行命令
def register_commands(app):
    @app.cli.command("init-db")
    @with_appcontext
    def init_db_command():
        """Initialize the database tables."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed-db")
    @with_appcontext
    def seed_db_command():
        """Add seed data to the database."""
        add_seed_data()
        click.echo("Seed data added to database.")

# 单独的假数据创建函数
def add_seed_data():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    
    # 创建默认admin用户 (如果不存在)
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin', 
            email='admin@example.com', 
            role='admin',
            full_name='System Administrator',
            site='MATS',
            competency='System Management',
            title='System Administrator',
            mobile='00000000000'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        click.echo("Admin user created")
    
    # 从JSON文件加载员工数据
    if not User.query.filter(User.username != 'admin').first():
        employees_path = os.path.join(base_dir, 'data_demo', 'employees.json')
        if os.path.exists(employees_path):
            with open(employees_path, 'r') as f:
                employees_data = json.load(f)
            
            for emp in employees_data:
                if not User.query.filter_by(username=emp['username']).first():
                    employee = User(
                        username=emp['username'],
                        email=emp['email'],
                        role='employee',
                        full_name=emp['full_name'],
                        site=emp['site'],
                        competency=emp['competency'],
                        title=emp['title'],
                        mobile=emp['mobile']
                    )
                    employee.set_password('password123')
                    db.session.add(employee)
            
            db.session.commit()
            click.echo(f"{len(employees_data)} employees created from JSON")
        else:
            click.echo("Employees JSON file not found.")
    
    # 从JSON文件加载类别
    if not Category.query.first():
        categories_path = os.path.join(base_dir, 'data_demo', 'categories.json')
        if os.path.exists(categories_path):
            with open(categories_path, 'r') as f:
                categories_data = json.load(f)
            
            for cat in categories_data:
                category = Category(
                    name=cat['name'],
                    type=cat['type'],
                    description=cat['description']
                )
                db.session.add(category)
            db.session.commit()
            click.echo(f"{len(categories_data)} categories created from JSON")
        else:
            click.echo("Categories JSON file not found.")
    
    # 从JSON文件加载项目
    if not Project.query.first():
        projects_path = os.path.join(base_dir, 'data_demo', 'projects.json')
        if os.path.exists(projects_path):
            with open(projects_path, 'r') as f:
                projects_data = json.load(f)
            
            categories = Category.query.all()
            category_map = {cat.name: cat.id for cat in categories}
            
            for proj in projects_data:
                # 获取类别ID
                category_id = category_map.get(proj['category'])
                if not category_id:
                    click.echo(f"Category {proj['category']} not found for project {proj['name']}")
                    continue
                    
                project = Project(
                    name=proj['name'],
                    category_id=category_id,
                    main_rd=proj['main_rd'],
                    supplier=proj['supplier'],
                    status=proj['status'] if proj['status'] else 'planning'
                )
                db.session.add(project)
            db.session.commit()
            click.echo(f"{len(projects_data)} projects created from JSON")
        else:
            click.echo("Projects JSON file not found.")
    
    # 从JSON文件加载任务（包括评论）
    if not Task.query.first():
        tasks_path = os.path.join(base_dir, 'data_demo', 'tasks.json')
        if os.path.exists(tasks_path):
            with open(tasks_path, 'r') as f:
                tasks_data = json.load(f)
            
            # 创建用户名到用户ID的映射
            user_map = {user.username: user.id for user in User.query.all()}
            # 创建项目名称到项目ID的映射
            project_map = {project.name: project.id for project in Project.query.all()}
            
            for task_data in tasks_data:
                # 获取分配人ID
                assignee_id = user_map.get(task_data['assignee_username'])
                if not assignee_id:
                    click.echo(f"Assignee {task_data['assignee_username']} not found for task {task_data['title']}")
                    continue
                
                # 获取项目ID
                project_id = project_map.get(task_data['project_name'])
                if not project_id:
                    click.echo(f"Project {task_data['project_name']} not found for task {task_data['title']}")
                    continue
                
                # 创建任务
                task = Task(
                    title=task_data['title'],
                    description=task_data['description'],
                    type=task_data['type'],
                    status=task_data['status'],
                    priority=task_data['priority'],
                    severity=task_data['severity'],
                    start_date=datetime.fromisoformat(task_data['start_date']),
                    due_date=datetime.fromisoformat(task_data['due_date']),
                    assignee_id=assignee_id,
                    project_id=project_id
                )
                db.session.add(task)
                db.session.flush()  # 获取任务ID
                
                # 添加评论
                for comment_data in task_data.get('comments', []):
                    author_id = user_map.get(comment_data['author_username'])
                    if not author_id:
                        click.echo(f"Author {comment_data['author_username']} not found for comment in task {task_data['title']}")
                        continue
                    
                    comment = Comment(
                        content=comment_data['content'],
                        task_id=task.id,
                        author_id=author_id,
                        created_at=datetime.fromisoformat(comment_data['created_at'])
                    )
                    db.session.add(comment)
            
            db.session.commit()
            click.echo(f"{len(tasks_data)} tasks with comments created from JSON")
        else:
            click.echo("Tasks JSON file not found.")

# 主函数
if __name__ == '__main__':
    # 注册命令行命令
    register_commands(app)
    
    # 运行应用
    app.run(debug=True)