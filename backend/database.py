"""
Database manager helpers.

This module provides a thin wrapper around an SQLite database used by the
task management application. It offers convenience methods to query users,
projects, tasks, comments and some lightweight statistics. The public
interface is intentionally small and designed to be used by other parts of
the application (web handlers, data export scripts, etc.).

Notes:
- Methods return sqlite3.Row or sequences of sqlite3.Row objects so callers
  can access columns by name (row['column_name']).
- The class does not change database schema or connection behavior.
"""

import sqlite3
from datetime import datetime

class DatabaseManager:
    """Manage connections and queries against the SQLite database.

    The constructor takes a single parameter `db_path` which is the path to
    the SQLite file. All methods open a short-lived connection with
    `get_connection()` and close it automatically using a context manager.
    """

    def __init__(self, db_path):
        """Initialize the manager with the SQLite database file path.

        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
    
    def get_connection(self):
        """Create and return a new sqlite3.Connection object.

        The returned connection uses `sqlite3.Row` as the row factory so
        callers can access columns by name (row['col']). Callers of the
        public API should not rely on the connection object itself; it is
        managed internally and closed after each operation.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_users(self):
        """Return all active users.

        Returns a sequence of rows containing selected user columns. Only
        users with `is_active = 1` are returned.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, userID, username, email, role, full_name, site, competency, title, mobile '
                'FROM users WHERE is_active = 1 AND id!=1'
            )
            return cursor.fetchall()
    
    def get_projects(self):
        """Return projects joined with their category information.

        Each returned row contains project columns and additional
        `category_name` and `category_type` fields from the categories table.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, c.name as category_name, c.type as category_type
                FROM projects p
                JOIN categories c ON p.category_id = c.id
            ''')
            return cursor.fetchall()
    
    def add_task(self, task_data):
        """Insert a new task into the database and return the task id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO tasks (
                        title, description, type, status, priority, severity, 
                        start_date, due_date, assignee_id, project_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_data['title'],
                    task_data['description'],
                    task_data['type'],
                    task_data['status'],
                    task_data['priority'],
                    task_data['severity'],
                    task_data['start_date'],
                    task_data['due_date'],
                    task_data['assignee_id'],
                    task_data['project_id']
                ))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                conn.rollback()
                return None

    def get_task_by_id(self, task_id):
        """Return a single task by ID as a dictionary."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    t.id, t.title, t.description, t.type, t.status, t.priority, t.severity,
                    t.start_date, t.due_date, t.created_at, t.updated_at,
                    t.assignee_id, t.project_id,
                    u.username AS assignee_username, u.full_name AS assignee_full_name,
                    p.name AS project_name,
                    c.name AS category_name, c.type AS category_type
                FROM tasks t
                LEFT JOIN users u ON t.assignee_id = u.id
                JOIN projects p ON t.project_id = p.id
                JOIN categories c ON p.category_id = c.id
                WHERE t.id = ?
            ''', (task_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        
    def get_tasks(self, filters=None):
        """Return tasks with optional filtering.

        The returned rows include task fields, assignee username/full name,
        project name and category info. The `filters` argument is a dict
        that may contain: 'status', 'assignee', 'project', 'priority',
        'search_text'. Values of 'all' are ignored for categorical filters.
        """
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
                # Add WHERE clauses only when a filter is provided and not 'all'
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
                    # Use LIKE to search title and description
                    query += ' AND (t.title LIKE ? OR t.description LIKE ?)'
                    search_term = f"%{filters['search_text']}%"
                    params.extend([search_term, search_term])

            cursor.execute(query, params)
            return cursor.fetchall()
    
    def get_task(self, task_id):
        """Return a single task by id with joined metadata.

        The returned row includes assignee username/full_name, project name,
        category id/name/type. Returns None if the task does not exist.
        """
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
        """Return comments for a task ordered by creation time (newest first)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Include the users.userID column as author_userID so callers can
            # map internal numeric ids to the external user identifier used
            # throughout the frontend (e.g. employee code).
            cursor.execute('''
                SELECT c.*, u.userID as author_userID, u.username as author_username, u.full_name as author_full_name
                FROM comments c
                JOIN users u ON c.author_id = u.id
                WHERE c.task_id = ?
                ORDER BY c.created_at DESC
            ''', (task_id,))
            return cursor.fetchall()
        
    def get_comment_by_ID(self, comment_id):
        """Return comment by comment_id as a dictionary."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    c.id, c.content, c.created_at, c.task_id, c.author_id,
                    u.id as author_db_id, 
                    u.userID as author_userID, 
                    u.username as author_username, 
                    u.full_name as author_full_name
                FROM comments c
                JOIN users u ON c.author_id = u.id
                WHERE c.id = ?
            ''', (comment_id,))
            row = cursor.fetchone()
            if row:
                # 将 Row 对象转换为字典
                return dict(row)
            return None

    def get_comment_with_attachments_by_ID(self, comment_id):
        """Return comment by comment_id with attachments as a dictionary."""
        # 获取评论基本信息
        comment = self.get_comment_by_ID(comment_id)
        if not comment:
            return None
        
        # 获取相关附件
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    id, filename, filepath, content_type, created_at
                FROM attachments
                WHERE comment_id = ?
            ''', (comment_id,))
            attachments = cursor.fetchall()
        
        # 将附件列表添加到评论字典
        comment['attachments'] = []
        for att in attachments:
            # 将每个附件转换为字典
            comment['attachments'].append(dict(att))
        
        return comment
    
    def delete_attachments_for_comment(self, comment_id):
        """删除评论的所有附件记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM attachments WHERE comment_id = ?', (comment_id,))
            conn.commit()

    def delete_comment(self, comment_id):
        """删除评论记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
            conn.commit()
            
    # ---------- Attachment helpers ----------
    def add_attachment(self, comment_id, filename, filepath, content_type=None):
        """Insert attachment metadata and return its id.

        Files themselves are stored on the filesystem; this stores the
        metadata linking an attachment to a comment.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO attachments (filename, filepath, content_type, created_at, comment_id) VALUES (?, ?, ?, ?, ?)',
                (filename, filepath, content_type, datetime.now().isoformat(), comment_id)
            )
            conn.commit()
            return cursor.lastrowid

    def get_attachments_by_comment(self, comment_id):
        """Return attachments for a given comment id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM attachments WHERE comment_id = ? ORDER BY created_at DESC', (comment_id,))
            return cursor.fetchall()

    def get_attachments_by_task(self, task_id):
        """Return attachments for all comments under a task."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.* FROM attachments a
                JOIN comments c ON a.comment_id = c.id
                WHERE c.task_id = ?
                ORDER BY a.created_at DESC
            ''', (task_id,))
            return cursor.fetchall()

    def get_attachment(self, attachment_id):
        """Return a single attachment row by id."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM attachments WHERE id = ?', (attachment_id,))
            return cursor.fetchone()
    
    def add_comment(self, task_id, author_id, content):
        """Insert a new comment and return its row id.

        created_at is stored as an ISO-8601 timestamp produced by
        datetime.now().isoformat(). This keeps the storage format
        consistent with other timestamps used in the application.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO comments (content, task_id, author_id, created_at) VALUES (?, ?, ?, ?)',
                (content, task_id, author_id, datetime.now().isoformat())
            )
            conn.commit()
            return cursor.lastrowid
    
    def create_task(self, task_data):
        """Create a new task using provided task_data dict.

        The function accepts an input dictionary with keys such as
        'title', 'description', 'start_date', 'due_date', 'assignee_id',
        'project_id' and optional fields like 'type', 'status', 'priority',
        'severity'. Dates provided in ISO format with a trailing 'Z' are
        converted to an offset-aware ISO string before insertion.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Normalize date fields: accept ISO timestamps and convert
            # trailing 'Z' to '+00:00' so datetime.fromisoformat() can parse it.
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
    
    def update_task(self, task_id, update_data):
        """Update an existing task in the database.
        Returns True if successful, False otherwise.
        """
        # 只更新允许的字段
        allowed_fields = {
            'title', 'description', 'type', 'status', 'priority', 'severity',
            'start_date', 'due_date', 'assignee_id', 'project_id'
        }
        
        # 过滤update_data，只保留允许的字段
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not update_fields:
            return False
            
        set_clause = ', '.join([f"{field} = ?" for field in update_fields])
        values = list(update_fields.values())
        values.append(task_id)  # 添加task_id作为WHERE子句的条件
        
        query = f"UPDATE tasks SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values)
                conn.commit()
                return cursor.rowcount > 0  # 如果更新了一行则返回True
            except sqlite3.Error as e:
                conn.rollback()
                return False
    
    def get_project_task_counts(self):
        """Return top 10 projects with their task counts.

        The function returns rows with 'project_id', 'project_name' and
        'task_count' fields ordered by task_count descending.
        """
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
        """Return task counts per user.

        Rows include 'user_id', 'full_name', 'username' and 'task_count'.
        """
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
        """Return total number of projects in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM projects")
            result = cursor.fetchone()
            return result['total'] if result else 0

    def get_total_tasks(self):
        """Return total number of tasks in the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM tasks")
            result = cursor.fetchone()
            return result['total'] if result else 0

    def get_active_projects(self):
        """Return number of projects with status = 'active'."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM projects WHERE status = 'active'")
            result = cursor.fetchone()
            return result['total'] if result else 0

    def get_delayed_tasks(self):
        """Return the count of delayed tasks.

        A task is considered delayed when its `due_date` is older than the
        current date and the status is not 'done' or 'completed'. The SQL
        compares the stored due_date with DATE('now') which returns the
        current calendar date in SQLite.
        """
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