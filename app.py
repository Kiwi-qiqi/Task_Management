# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Category, Project, Task, Comment
from datetime import datetime
import json

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
    # Get query parameters
    status = request.args.get('status')
    assignee = request.args.get('assignee')
    project = request.args.get('project')
    
    # Build query
    query = Task.query
    
    if status and status != 'all':
        query = query.filter_by(status=status)
    if assignee and assignee != 'all':
        query = query.filter_by(assignee_id=assignee)
    if project and project != 'all':
        query = query.filter_by(project_id=project)
    
    tasks = query.order_by(Task.due_date.asc()).all()
    
    # Convert to JSON format
    tasks_data = []
    for task in tasks:
        task_data = {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'severity': task.severity,
            'start_date': task.start_date.isoformat() if task.start_date else None,
            'due_date': task.due_date.isoformat() if task.due_date else None,
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
            'comment_count': len(task.comments)
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create default admin user (if not exists)
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
        
        # Add employee data (if not exists)
        employees = [
            {'username': 'lilong.xu', 'email': 'lilong.xu@mahle.com', 'full_name': 'Lilong Xu',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Manager', 'mobile': '18114906812'},
            {'username': 'alex.zhu', 'email': 'alex.zhu@mahle.com', 'full_name': 'Alex Zhu',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '15850690925'},
            {'username': 'xin.guo', 'email': 'xin.guo@mahle.com', 'full_name': 'Xin Guo',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': ''},
            {'username': 'jordan.zhou', 'email': 'jordan.zhou@mahle.com', 'full_name': 'Jordan Zhou',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '15751018155'},
            {'username': 'mingyu.ma', 'email': 'mingyu.ma@mahle.com', 'full_name': 'Mingyu Ma',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '17315372380'},
            {'username': 'alex.li', 'email': 'alex.a.li@mahle.com', 'full_name': 'Alex Li',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '18503397615'},
            {'username': 'feihao.liu', 'email': 'feihao.liu@mahle.com', 'full_name': 'Feihao Liu',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '17768046903'},
            {'username': 'libo.zhu', 'email': 'libo.zhu@mahle.com', 'full_name': 'Libo Zhu',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '18651181168'},
            {'username': 'bin.huang', 'email': 'bin.b.huang@mahle.com', 'full_name': 'Bin Huang',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': ''},
            {'username': 'stephen.zeng', 'email': 'stephen.zeng@mahle.com', 'full_name': 'Stephen Zeng',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '18166038355'},
            {'username': 'jason.zhang', 'email': 'jason.c.zhang@mahle.com', 'full_name': 'Jason Zhang',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '18993573429'},
            {'username': 'min.xiong', 'email': 'min.xiong@mahle.com', 'full_name': 'Min Xiong',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '13313843160'},
            {'username': 'shenglin.chen', 'email': 'shenglin.chen@mahle.com', 'full_name': 'Shenglin Chen',
             'site': 'MATS', 'competency': 'SW', 'title': 'Software Engineer', 'mobile': '18662237910'}
        ]
        
        for emp in employees:
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
                # Set default password for all employees
                employee.set_password('password123')
                db.session.add(employee)
        
        # Create categories (products and functions)
        if not Category.query.first():
            categories = [
                {'name': 'E-Compressor', 'type': 'product', 'description': 'Electric Compressor'},
                {'name': 'E-CoolingPump', 'type': 'product', 'description': 'Electric Cooling Pump'},
                {'name': 'E-CoolingFan', 'type': 'product', 'description': 'Electric Cooling Fan'},
                {'name': 'OBC&DCLV', 'type': 'product', 'description': 'On-Board Charger & DC Low Voltage Converter'},
                {'name': 'Bootloader', 'type': 'function', 'description': 'Bootloader functionality'},
                {'name': 'Functional Safety', 'type': 'function', 'description': 'Functional Safety'},
                {'name': 'CyberSecurity', 'type': 'function', 'description': 'Cyber Security'},
                {'name': 'Toolchain', 'type': 'function', 'description': 'Toolchain'},
                {'name': 'Main Task', 'type': 'function', 'description': 'Main Task'}
            ]
            
            for cat in categories:
                category = Category(
                    name=cat['name'],
                    type=cat['type'],
                    description=cat['description']
                )
                db.session.add(category)
            db.session.commit()
        
        # Create projects
        if not Project.query.first():
            categories = Category.query.all()
            category_map = {cat.name: cat.id for cat in categories}
            
            projects = [
                {'name': 'Honda 28M_800V_45CC', 'category': 'E-Compressor', 'main_rd': 'Outsourced', 'supplier': 'HET', 'status': 'in_progress'},
                {'name': 'Platform_400V_36CC', 'category': 'E-Compressor', 'main_rd': 'Outsourced', 'supplier': 'FristWise', 'status': 'in_progress'},
                {'name': 'Platform_800V_45CC', 'category': 'E-Compressor', 'main_rd': 'Outsourced', 'supplier': 'FeiYang', 'status': 'in_progress'},
                {'name': 'STELLANTIS_400V_45CC', 'category': 'E-Compressor', 'main_rd': 'TBD', 'supplier': '', 'status': 'not_start'},
                {'name': 'VW_800V_45CC', 'category': 'E-Compressor', 'main_rd': 'Internal', 'supplier': '', 'status': 'not_start'},
                {'name': 'HD20_800V_57CC', 'category': 'E-Compressor', 'main_rd': 'Internal', 'supplier': '', 'status': 'in_progress'},
                {'name': 'Platform_Ti', 'category': 'E-Compressor', 'main_rd': 'Internal', 'supplier': '', 'status': 'in_progress'},
                {'name': 'HR18', 'category': 'E-CoolingPump', 'main_rd': 'Internal', 'supplier': '', 'status': 'in_progress'},
                {'name': 'XCSP', 'category': 'E-CoolingPump', 'main_rd': 'Internal', 'supplier': '', 'status': 'in_progress'},
                {'name': 'Platform_800V_2IN1_7kw', 'category': 'OBC&DCLV', 'main_rd': '', 'supplier': '', 'status': ''},
                {'name': 'Platform_48V_DCLV_5kw', 'category': 'OBC&DCLV', 'main_rd': '', 'supplier': '', 'status': ''},
                {'name': 'MMC_400V_3IN1_11kw', 'category': 'OBC&DCLV', 'main_rd': '', 'supplier': '', 'status': ''},
                {'name': 'Bootloader', 'category': 'Bootloader', 'main_rd': '', 'supplier': '', 'status': ''},
                {'name': 'Functional Safety', 'category': 'Functional Safety', 'main_rd': '', 'supplier': '', 'status': ''},
                {'name': 'CyberSecurity', 'category': 'CyberSecurity', 'main_rd': '', 'supplier': '', 'status': ''},
                {'name': 'Toolchain', 'category': 'Toolchain', 'main_rd': '', 'supplier': '', 'status': ''},
                {'name': 'Main Task', 'category': 'Main Task', 'main_rd': '', 'supplier': '', 'status': ''}
            ]
            
            for proj in projects:
                project = Project(
                    name=proj['name'],
                    category_id=category_map[proj['category']],
                    main_rd=proj['main_rd'],
                    supplier=proj['supplier'],
                    status=proj['status'] if proj['status'] else 'planning'
                )
                db.session.add(project)
            db.session.commit()
        
        # Create sample tasks
        if not Task.query.first():
            # Get some employees and projects
            employees = User.query.filter_by(role='employee').all()
            projects = Project.query.all()
            
            tasks = [
                {
                    'title': 'Honda Compressor Communication Protocol Development',
                    'description': 'Develop communication protocol for Honda 28M_800V_45CC project',
                    'type': 'feature',
                    'status': 'in_progress',
                    'priority': 'high',
                    'severity': 'major',
                    'start_date': datetime(2024, 2, 1),
                    'due_date': datetime(2024, 5, 31),
                    'assignee_id': employees[0].id,
                    'project_id': projects[0].id
                },
                {
                    'title': 'Platform 400V Compressor Control Algorithm Optimization',
                    'description': 'Optimize control algorithm for Platform_400V_36CC project',
                    'type': 'improvement',
                    'status': 'todo',
                    'priority': 'medium',
                    'severity': 'normal',
                    'start_date': datetime(2024, 3, 15),
                    'due_date': datetime(2024, 6, 30),
                    'assignee_id': employees[1].id,
                    'project_id': projects[1].id
                },
                {
                    'title': 'Bootloader Security Verification',
                    'description': 'Verify security mechanisms for Bootloader project',
                    'type': 'test',
                    'status': 'review',
                    'priority': 'high',
                    'severity': 'critical',
                    'start_date': datetime(2024, 1, 15),
                    'due_date': datetime(2024, 4, 30),
                    'assignee_id': employees[2].id,
                    'project_id': projects[13].id
                },
                {
                    'title': 'Cyber Security Vulnerability Fix',
                    'description': 'Fix vulnerabilities found in CyberSecurity project',
                    'type': 'bug',
                    'status': 'in_progress',
                    'priority': 'urgent',
                    'severity': 'critical',
                    'start_date': datetime(2024, 3, 1),
                    'due_date': datetime(2024, 3, 31),
                    'assignee_id': employees[3].id,
                    'project_id': projects[15].id
                }
            ]
            
            for task_data in tasks:
                task = Task(**task_data)
                db.session.add(task)
            
            db.session.commit()
            
            # Add comments to some tasks
            tasks = Task.query.all()
            for i, task in enumerate(tasks):
                comment = Comment(
                    content=f'Initial comment for task #{i+1}. Task created and assigned to relevant personnel.',
                    task_id=task.id,
                    author_id=1  # admin
                )
                db.session.add(comment)
            
            db.session.commit()
    
    app.run(debug=True)