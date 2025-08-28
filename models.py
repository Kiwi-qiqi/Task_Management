# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import pytz
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import Enum as SQLEnum

db = SQLAlchemy()

# 设置北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 任务类型枚举
class TaskType(Enum):
    FEATURE = 'feature'
    IMPROVEMENT = 'improvement'
    DESIGN = 'design'
    BUG_FIX = 'bug_fix'
    DOCUMENTATION = 'documentation'
    TESTING = 'testing'
    MAINTENANCE = 'maintenance'

# 严重性级别枚举
class SeverityLevel(Enum):
    TRIVIAL = 'trivial'
    MINOR = 'minor'
    NORMAL = 'normal'
    MAJOR = 'major'
    CRITICAL = 'critical'

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
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(BEIJING_TZ))
    
    # 关系
    tasks = db.relationship('Task', backref='assignee', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'email': self.email,
            'title': self.title,
            'mobile': self.mobile
        }

# 更新：将产品分为产品和功能两类
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'product' or 'function'
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')  # active, inactive
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(BEIJING_TZ))
    
    # 关系
    projects = db.relationship('Project', backref='category', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'status': self.status
        }

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='planning')  # planning, in_progress, completed, cancelled
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(BEIJING_TZ))
    
    # 新增字段
    main_rd = db.Column(db.String(50))  # Internal, Outsourced, TBD
    supplier = db.Column(db.String(100))
    
    # 外键
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # 关系
    tasks = db.relationship('Task', backref='project', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'category': self.category.to_dict() if self.category else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    type = db.Column(SQLEnum(TaskType), nullable=True)  # 使用枚举类型
    status = db.Column(db.String(20), default='todo')  # todo, in_progress, review, completed
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    severity = db.Column(SQLEnum(SeverityLevel), default=SeverityLevel.NORMAL)  # 使用枚举类型
    start_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(BEIJING_TZ))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(BEIJING_TZ), onupdate=lambda: datetime.now(BEIJING_TZ))
    
    # 外键
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    
    # 关系
    comments = db.relationship('Comment', backref='task', lazy=True, cascade='all, delete-orphan', order_by="Comment.created_at.desc()")
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type.value if self.type else None,
            'status': self.status,
            'priority': self.priority,
            'severity': self.severity.value if self.severity else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'assignee': self.assignee.to_dict() if self.assignee else None,
            'project': self.project.to_dict() if self.project else None,
            'comments': [comment.to_dict() for comment in self.comments]
        }

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(BEIJING_TZ))
    
    # 外键
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'author': self.author.to_dict() if self.author else None,
            'date': self.created_at.date().isoformat() if self.created_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }