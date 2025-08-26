# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'employee'
    is_active = db.Column(db.Boolean, default=True)
    
    # 员工信息字段
    full_name = db.Column(db.String(100), nullable=False)
    site = db.Column(db.String(50))
    competency = db.Column(db.String(50))
    title = db.Column(db.String(100))
    mobile = db.Column(db.String(20))
    
    created_at = db.Column(db.DateTime, default=datetime.now())
    
    # 关系
    tasks = db.relationship('Task', backref='assignee', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 更新：将产品分为产品和功能两类
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'product' or 'function'
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    projects = db.relationship('Project', backref='category', lazy=True)

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='planning')  # planning, in_progress, completed, cancelled
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 新增字段
    main_rd = db.Column(db.String(50))  # Internal, Outsourced, TBD
    supplier = db.Column(db.String(100))
    
    # 外键
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # 关系
    tasks = db.relationship('Task', backref='project', lazy=True)

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(db.String(50))  # bug, feature, improvement, etc.
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, review, done
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    severity = db.Column(db.String(20), default='normal')  # trivial, minor, normal, major, critical
    start_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 外键
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # 关系
    comments = db.relationship('Comment', backref='task', lazy=True, cascade='all, delete-orphan')

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 外键
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)