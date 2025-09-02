# create_database.py
import sqlite3
import json
import os
from datetime import datetime

def create_tables(cursor):
    """创建数据库表结构"""
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userID VARCHAR(80) UNIQUE NOT NULL,
        username VARCHAR(80) UNIQUE NOT NULL,
        email VARCHAR(120) UNIQUE NOT NULL,
        password_hash VARCHAR(128),
        role VARCHAR(20) NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        full_name VARCHAR(100) NOT NULL,
        site VARCHAR(50),
        competency VARCHAR(50),
        title VARCHAR(100),
        mobile VARCHAR(20),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建类别表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL,
        type VARCHAR(20) NOT NULL,
        description TEXT,
        status VARCHAR(20) DEFAULT 'active',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建项目表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        status VARCHAR(20) DEFAULT 'planning',
        start_date DATETIME,
        end_date DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        main_rd VARCHAR(50),
        supplier VARCHAR(100),
        category_id INTEGER NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')
    
    # 创建任务表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(200) NOT NULL,
        description TEXT,
        type VARCHAR(50),
        status VARCHAR(20) DEFAULT 'todo',
        priority VARCHAR(20) DEFAULT 'medium',
        severity VARCHAR(20) DEFAULT 'normal',
        start_date DATETIME,
        due_date DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        assignee_id INTEGER,
        project_id INTEGER NOT NULL,
        FOREIGN KEY (assignee_id) REFERENCES users (id),
        FOREIGN KEY (project_id) REFERENCES projects (id)
    )
    ''')
    
    # 创建评论表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_at DATIME DEFAULT CURRENT_TIMESTAMP,
        task_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks (id),
        FOREIGN KEY (author_id) REFERENCES users (id)
    )
    ''')
    
    print("数据库表结构创建成功！")

def load_json_data(file_path):
    """从JSON文件加载数据"""
    if not os.path.exists(file_path):
        print(f"错误: {file_path} 不存在")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"从 {file_path} 加载了 {len(data)} 条记录")
        return data
    except Exception as e:
        print(f"加载 {file_path} 时出错: {e}")
        return None

def insert_categories(cursor, categories_data):
    """插入类别数据"""
    if not categories_data:
        print("错误: 没有类别数据可插入")
        return False
    
    for category in categories_data:
        cursor.execute(
            'INSERT INTO categories (name, type, description, status) VALUES (?, ?, ?, ?)',
            (
                category.get('name'),
                category.get('type'),
                category.get('description'),
                category.get('status', 'active')
            )
        )
    
    print(f"插入了 {len(categories_data)} 条类别记录")
    return True

def insert_users(cursor, users_data):
    """插入用户数据"""
    if not users_data:
        print("错误: 没有用户数据可插入")
        return False
    
    for user in users_data:
        cursor.execute(
            'INSERT INTO users (userID, username, email, password_hash, role, full_name, site, competency, title, mobile, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                user.get('userID'),
                user.get('username'),
                user.get('email'),
                user.get('password_hash'),
                user.get('role'),
                user.get('full_name'),
                user.get('site'),
                user.get('competency'),
                user.get('title'),
                user.get('mobile'),
                user.get('is_active', True)
            )
        )
    
    print(f"插入了 {len(users_data)} 条用户记录")
    return True

def insert_projects(cursor, projects_data):
    """插入项目数据"""
    if not projects_data:
        print("错误: 没有项目数据可插入")
        return False
    
    for project in projects_data:
        cursor.execute(
            'INSERT INTO projects (name, description, status, start_date, end_date, main_rd, supplier, category_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                project.get('name'),
                project.get('description'),
                project.get('status', 'planning'),
                project.get('start_date'),
                project.get('end_date'),
                project.get('main_rd'),
                project.get('supplier'),
                project.get('category_id')
            )
        )
    
    print(f"插入了 {len(projects_data)} 条项目记录")
    return True

def insert_tasks(cursor, tasks_data):
    """插入任务数据"""
    if not tasks_data:
        print("错误: 没有任务数据可插入")
        return False
    
    for task in tasks_data:
        cursor.execute(
            '''INSERT INTO tasks (title, description, type, status, priority, severity, 
               start_date, due_date, assignee_id, project_id) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                task.get('title'),
                task.get('description'),
                task.get('type'),
                task.get('status', 'todo'),
                task.get('priority', 'medium'),
                task.get('severity', 'normal'),
                task.get('start_date'),
                task.get('due_date'),
                task.get('assignee_id'),
                task.get('project_id')
            )
        )
    
    print(f"插入了 {len(tasks_data)} 条任务记录")
    return True

def insert_comments(cursor, comments_data):
    """插入评论数据"""
    if not comments_data:
        print("错误: 没有评论数据可插入")
        return False
    
    for comment in comments_data:
        cursor.execute(
            'INSERT INTO comments (content, task_id, author_id, created_at) VALUES (?, ?, ?, ?)',
            (
                comment.get('content'),
                comment.get('task_id'),
                comment.get('author_id'),
                comment.get('created_at')
            )
        )
    
    print(f"插入了 {len(comments_data)} 条评论记录")
    return True

def create_database():
    """创建数据库并插入数据"""
    # 连接到 SQLite 数据库（如果不存在则会创建）
    conn = sqlite3.connect('databases/taskmanager.db')
    cursor = conn.cursor()
    
    try:
        # 创建表结构
        create_tables(cursor)
        
        # 从JSON文件加载数据
        categories_data = load_json_data('database_backup/categories.json')
        users_data = load_json_data('database_backup/users.json')
        projects_data = load_json_data('database_backup/projects.json')
        tasks_data = load_json_data('database_backup/tasks.json')
        comments_data = load_json_data('database_backup/comments.json')
        
        # 检查所有必需的数据文件是否存在
        if not all([categories_data, users_data, projects_data]):
            print("错误: 缺少必需的数据文件")
            return False
        
        # 插入数据（按正确的顺序）
        if not insert_categories(cursor, categories_data):
            return False
        
        if not insert_users(cursor, users_data):
            return False
        
        if not insert_projects(cursor, projects_data):
            return False
        
        # 任务和评论是可选的
        if tasks_data:
            insert_tasks(cursor, tasks_data)
        
        if comments_data:
            insert_comments(cursor, comments_data)
        
        # 提交更改
        conn.commit()
        print("数据库创建成功！")
        return True
        
    except Exception as e:
        print(f"创建数据库时出错: {e}")
        conn.rollback()
        return False
    finally:
        # 关闭连接
        conn.close()

if __name__ == "__main__":
    success = create_database()
    if not success:
        print("数据库创建失败！")
        exit(1)