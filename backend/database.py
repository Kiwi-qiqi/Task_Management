import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_users(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, userID, username, email, role, full_name, site, competency, title, mobile FROM users WHERE is_active = 1')
            return cursor.fetchall()
    
    def get_projects(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, c.name as category_name, c.type as category_type 
                FROM projects p 
                JOIN categories c ON p.category_id = c.id
            ''')
            return cursor.fetchall()
    
    def get_tasks(self, filters=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT t.*, 
                       u.username as assignee_username, u.full_name as assignee_full_name,
                       p.name as project_name, c.name as category_name, c.type as category_type
                FROM tasks t
                LEFT JOIN users u ON t.assignee_id = u.id
                JOIN projects p ON t.project_id = p.id
                JOIN categories c ON p.category_id = c.id
                WHERE 1=1
            '''
            params = []
            
            if filters:
                if filters.get('status') and filters['status'] != 'all':
                    query += ' AND t.status = ?'
                    params.append(filters['status'])
                
                if filters.get('assignee') and filters['assignee'] != 'all':
                    query += ' AND t.assignee_id = ?'
                    params.append(filters['assignee'])
                
                if filters.get('project') and filters['project'] != 'all':
                    query += ' AND t.project_id = ?'
                    params.append(filters['project'])
                
                if filters.get('priority') and filters['priority'] != 'all':
                    query += ' AND t.priority = ?'
                    params.append(filters['priority'])
                
                if filters.get('search_text'):
                    query += ' AND (t.title LIKE ? OR t.description LIKE ?)'
                    search_term = f"%{filters['search_text']}%"
                    params.extend([search_term, search_term])
            
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_task(self, task_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT t.*, 
                       u.username as assignee_username, u.full_name as assignee_full_name,
                       p.name as project_name, p.category_id, 
                       c.name as category_name, c.type as category_type
                FROM tasks t
                LEFT JOIN users u ON t.assignee_id = u.id
                JOIN projects p ON t.project_id = p.id
                JOIN categories c ON p.category_id = c.id
                WHERE t.id = ?
            ''', (task_id,))
            return cursor.fetchone()
    
    def get_comments(self, task_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, u.username as author_username, u.full_name as author_full_name
                FROM comments c
                JOIN users u ON c.author_id = u.id
                WHERE c.task_id = ?
                ORDER BY c.created_at DESC
            ''', (task_id,))
            return cursor.fetchall()
    
    def add_comment(self, task_id, author_id, content):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO comments (content, task_id, author_id, created_at) VALUES (?, ?, ?, ?)',
                (content, task_id, author_id, datetime.now().isoformat())
            )
            conn.commit()
            return cursor.lastrowid
    
    def create_task(self, task_data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 处理日期字段
            start_date = task_data.get('start_date')
            due_date = task_data.get('due_date')
            
            if start_date:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).isoformat()
            if due_date:
                due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00')).isoformat()
            
            cursor.execute('''
                INSERT INTO tasks (title, description, type, status, priority, severity, 
                                  start_date, due_date, assignee_id, project_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_data['title'],
                task_data.get('description'),
                task_data.get('type', 'task'),
                task_data.get('status', 'todo'),
                task_data.get('priority', 'medium'),
                task_data.get('severity', 'normal'),
                start_date,
                due_date,
                task_data.get('assignee_id'),
                task_data['project_id'],
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()
            return cursor.lastrowid
    
    def update_task(self, task_id, task_data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 处理日期字段
            start_date = task_data.get('start_date')
            due_date = task_data.get('due_date')
            
            if start_date:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).isoformat()
            if due_date:
                due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00')).isoformat()
            
            cursor.execute('''
                UPDATE tasks 
                SET title = ?, description = ?, type = ?, status = ?, priority = ?, severity = ?,
                    start_date = ?, due_date = ?, assignee_id = ?, project_id = ?, updated_at = ?
                WHERE id = ?
            ''', (
                task_data['title'],
                task_data.get('description'),
                task_data.get('type'),
                task_data.get('status'),
                task_data.get('priority'),
                task_data.get('severity'),
                start_date,
                due_date,
                task_data.get('assignee_id'),
                task_data['project_id'],
                datetime.now().isoformat(),
                task_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        
        
    def get_project_task_counts(self):
        """获取每个项目的任务数量统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id AS project_id, p.name AS project_name, COUNT(t.id) AS task_count
                FROM projects p
                LEFT JOIN tasks t ON p.id = t.project_id
                GROUP BY p.id
                ORDER BY task_count DESC
                LIMIT 10
            ''')
            return cursor.fetchall()
    
    def get_user_task_distribution(self):
        """获取用户任务分布统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id AS user_id, u.full_name, u.username, COUNT(t.id) AS task_count
                FROM users u
                LEFT JOIN tasks t ON u.id = t.assignee_id
                GROUP BY u.id
                ORDER BY task_count DESC
            ''')
            return cursor.fetchall()
    
    def get_total_projects(self):
        """获取总项目数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM projects")
            result = cursor.fetchone()
            return result['total'] if result else 0

    def get_total_tasks(self):
        """获取总任务数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM tasks")
            result = cursor.fetchone()
            return result['total'] if result else 0

    def get_active_projects(self):
        """获取进行中项目数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM projects WHERE status = 'active'")
            result = cursor.fetchone()
            return result['total'] if result else 0

    def get_delayed_tasks(self):
        """获取延迟任务数"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) AS total 
                FROM tasks 
                WHERE due_date < DATE('now') 
                AND status NOT IN ('done', 'completed')
            """)
            result = cursor.fetchone()
            return result['total'] if result else 0