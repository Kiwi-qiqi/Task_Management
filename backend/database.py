"""
Database Manager Module
Handles all SQLite database operations for the Task Management System
"""

import sqlite3
import logging
from datetime import datetime

# Configure module logger
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manage connections and queries against the SQLite database.
    
    All methods use short-lived connections via context managers to ensure
    proper resource cleanup and thread safety.
    """

    def __init__(self, db_path):
        """
        Initialize the database manager.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        # logger.info(f"DatabaseManager initialized with path: {db_path}")
    
    def get_connection(self):
        """
        Create and return a new database connection.
        
        Returns:
            sqlite3.Connection: Database connection with Row factory
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ==================================================================
    # User Management
    # ==================================================================
    
    def get_users(self):
        """
        Retrieve all active users except system admin (id=1).
        
        Returns:
            list: List of user records as sqlite3.Row objects
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, userID, username, email, role, full_name, site, '
                'competency, title, mobile FROM users WHERE is_active = 1 AND id != 1'
            )
            users = cursor.fetchall()
            # logger.info(f"Retrieved {len(users)} active users")
            return users
    
    # ==================================================================
    # Project Management
    # ==================================================================
    
    def get_projects(self):
        """
        Retrieve all projects with their category information.
        
        Returns:
            list: List of project records with category details
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, c.name AS category_name, c.type AS category_type
                FROM projects p
                JOIN categories c ON p.category_id = c.id
            ''')
            projects = cursor.fetchall()
            # logger.info(f"Retrieved {len(projects)} projects")
            return projects
    
    def get_total_projects(self):
        """
        Get total count of all projects.
        
        Returns:
            int: Total number of projects
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM projects")
            result = cursor.fetchone()
            total = result['total'] if result else 0
            # logger.info(f"Total projects: {total}")
            return total
    
    def get_project_task_counts(self):
        """
        Get task count per project (top 10).
        
        Returns:
            list: Projects with task counts, sorted by count descending
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id AS project_id, p.name AS project_name, 
                       COUNT(t.id) AS task_count
                FROM projects p
                LEFT JOIN tasks t ON p.id = t.project_id
                GROUP BY p.id
                ORDER BY task_count DESC
                LIMIT 10
            ''')
            results = cursor.fetchall()
            # logger.info(f"Retrieved task counts for {len(results)} projects")
            return results
    
    # ==================================================================
    # Task Management - CRUD Operations
    # ==================================================================
    
    def add_task(self, task_data):
        """
        Create a new task in the database.
        
        Args:
            task_data (dict): Task information including title, description,
                            status, priority, dates, assignee, and project
        
        Returns:
            int: ID of newly created task, or None if creation failed
        """
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
                    task_data.get('description', ''),
                    task_data.get('type'),
                    task_data.get('status', 'todo'),
                    task_data.get('priority', 'medium'),
                    task_data.get('severity', 'normal'),
                    task_data.get('start_date'),
                    task_data.get('due_date'),
                    task_data.get('assignee_id'),
                    task_data['project_id']
                ))
                conn.commit()
                task_id = cursor.lastrowid
                # logger.info(f"Task created successfully: ID={task_id}, Title='{task_data['title']}'")
                return task_id
            except sqlite3.Error as e:
                # logger.error(f"Failed to create task: {str(e)}")
                conn.rollback()
                return None
    
    def get_task_by_id(self, task_id):
        """
        Retrieve a single task by its ID with full details.
        
        Args:
            task_id (int): Task ID
        
        Returns:
            dict: Task record with assignee, project, and category info,
                 or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    t.id, t.title, t.description, t.type, t.status, 
                    t.priority, t.severity, t.start_date, t.due_date, 
                    t.created_at, t.updated_at,
                    t.assignee_id, t.project_id,
                    u.username AS assignee_username, 
                    u.full_name AS assignee_full_name,
                    p.name AS project_name,
                    c.name AS category_name, 
                    c.type AS category_type
                FROM tasks t
                LEFT JOIN users u ON t.assignee_id = u.id
                JOIN projects p ON t.project_id = p.id
                JOIN categories c ON p.category_id = c.id
                WHERE t.id = ?
            ''', (task_id,))
            row = cursor.fetchone()
            
            if row:
                # logger.info(f"Task retrieved: ID={task_id}")
                return dict(row)
            
            # logger.warning(f"Task not found: ID={task_id}")
            return None
    
    def get_tasks(self, filters=None):
        """
        Retrieve tasks with optional filtering.
        
        Args:
            filters (dict, optional): Filter criteria including:
                - allowed_assignees: List of userIDs for permission filtering
                - status: Task status filter
                - assignee: Specific assignee ID
                - project: Project ID
                - priority: Priority level
                - search_text: Text search in title/description
        
        Returns:
            list: Filtered task records with user and project details
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Base query with joins
            query = '''
                SELECT t.*,
                    u.username AS assignee_username, 
                    u.full_name AS assignee_full_name,
                    u.userID AS assignee_user_id,
                    p.name AS project_name, 
                    c.name AS category_name, 
                    c.type AS category_type
                FROM tasks t
                LEFT JOIN users u ON t.assignee_id = u.id
                JOIN projects p ON t.project_id = p.id
                JOIN categories c ON p.category_id = c.id
                WHERE 1=1
            '''
            params = []

            # Apply filters if provided
            if filters:
                # Permission-based filtering (highest priority)
                if filters.get('allowed_assignees'):
                    allowed_ids = filters['allowed_assignees']
                    placeholders = ','.join(['?'] * len(allowed_ids))
                    query += f' AND u.userID IN ({placeholders})'
                    params.extend(allowed_ids)
                    # logger.debug(f"Applied assignee permission filter: {allowed_ids}")
                
                # Status filter
                if filters.get('status') and filters['status'] != 'all':
                    query += ' AND t.status = ?'
                    params.append(filters['status'])
                
                # Assignee filter (specific user)
                if filters.get('assignee') and filters['assignee'] != 'all':
                    query += ' AND (t.assignee_id = ? OR u.userID = ?)'
                    params.extend([filters['assignee'], filters['assignee']])
                
                # Project filter
                if filters.get('project') and filters['project'] != 'all':
                    query += ' AND t.project_id = ?'
                    params.append(filters['project'])
                
                # Priority filter
                if filters.get('priority') and filters['priority'] != 'all':
                    query += ' AND t.priority = ?'
                    params.append(filters['priority'])
                
                # Text search filter
                if filters.get('search_text'):
                    query += ' AND (t.title LIKE ? OR t.description LIKE ?)'
                    search_term = f"%{filters['search_text']}%"
                    params.extend([search_term, search_term])

            # Order by creation date (newest first)
            query += ' ORDER BY t.created_at DESC'
            
            cursor.execute(query, params)
            tasks = cursor.fetchall()
            # logger.info(f"Retrieved {len(tasks)} tasks with filters: {filters}")
            return tasks
    
    def update_task(self, task_id, update_data):
        """
        Update an existing task with new data.
        
        Args:
            task_id (int): ID of task to update
            update_data (dict): Fields to update (only allowed fields)
        
        Returns:
            bool: True if update successful, False otherwise
        """
        # Define allowed update fields
        allowed_fields = {
            'title', 'description', 'type', 'status', 'priority', 'severity',
            'start_date', 'due_date', 'assignee_id', 'project_id'
        }
        
        # Filter to only allowed fields
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not update_fields:
            # logger.warning(f"No valid fields to update for task {task_id}")
            return False
        
        # Build dynamic UPDATE query
        set_clause = ', '.join([f"{field} = ?" for field in update_fields])
        values = list(update_fields.values())
        values.append(task_id)
        
        query = f"UPDATE tasks SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        # logger.debug(f"Executing update query: {query}")
        # logger.debug(f"With values: {values}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values)
                conn.commit()
                rows_affected = cursor.rowcount
                
                if rows_affected > 0:
                    # logger.info(f"Task updated successfully: ID={task_id}, Fields={list(update_fields.keys())}")
                    return True
                else:
                    # logger.warning(f"Task update affected 0 rows: ID={task_id}")
                    return False
                    
            except sqlite3.Error as e:
                # logger.error(f"Failed to update task {task_id}: {str(e)}")
                conn.rollback()
                return False
    
    def delete_task(self, task_id):
        """
        Delete a task and all associated comments and attachments.
        
        This performs a cascading delete:
        1. Find all comments for the task
        2. Delete all attachments for those comments
        3. Delete all comments
        4. Delete the task itself
        
        Note: Physical files are NOT deleted automatically and should be
        handled separately by the caller if needed.
        
        Args:
            task_id (int): ID of task to delete
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Find all comments for this task
                cursor.execute("SELECT id FROM comments WHERE task_id = ?", (task_id,))
                comments = cursor.fetchall()
                
                # Delete attachments for each comment
                for comment in comments:
                    cursor.execute(
                        "DELETE FROM attachments WHERE comment_id = ?", 
                        (comment['id'],)
                    )
                
                # Delete all comments
                cursor.execute("DELETE FROM comments WHERE task_id = ?", (task_id,))
                
                # Delete the task itself
                cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                
                conn.commit()
                # logger.info(f"Task deleted successfully: ID={task_id}, Comments={len(comments)}")
                
            except sqlite3.Error as e:
                # logger.error(f"Failed to delete task {task_id}: {str(e)}")
                conn.rollback()
                raise
    
    def get_total_tasks(self):
        """
        Get total count of all tasks.
        
        Returns:
            int: Total number of tasks
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM tasks")
            result = cursor.fetchone()
            total = result['total'] if result else 0
            # logger.info(f"Total tasks: {total}")
            return total
    
    def get_active_tasks(self):
        """
        Get count of active tasks (not done).
        
        Returns:
            int: Number of tasks with status != 'done'
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) AS total FROM tasks WHERE status NOT IN ('done')"
            )
            result = cursor.fetchone()
            total = result['total'] if result else 0
            # logger.info(f"Active tasks: {total}")
            return total
    
    def get_delayed_tasks(self):
        """
        Get count of delayed tasks.
        
        A task is delayed when:
        - due_date is in the past (< current date)
        - status is not 'done' or 'completed'
        
        Returns:
            int: Number of delayed tasks
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
            total = result['total'] if result else 0
            # logger.info(f"Delayed tasks: {total}")
            return total
    
    def get_user_task_distribution(self):
        """
        Get task distribution across users.
        
        Returns:
            list: User records with task counts, sorted by count descending
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id AS user_id, u.full_name, u.username, 
                       COUNT(t.id) AS task_count
                FROM users u
                LEFT JOIN tasks t ON u.id = t.assignee_id
                GROUP BY u.id
                ORDER BY task_count DESC
            ''')
            results = cursor.fetchall()
            # logger.info(f"Retrieved task distribution for {len(results)} users")
            return results
    
    # ==================================================================
    # Comment Management
    # ==================================================================
    
    def add_comment(self, task_id, author_id, content):
        """
        Add a new comment to a task.
        
        Args:
            task_id (int): ID of the task
            author_id (int): ID of the comment author (user.id)
            content (str): Comment text content
        
        Returns:
            int: ID of newly created comment
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO comments (content, task_id, author_id, created_at) '
                'VALUES (?, ?, ?, ?)',
                (content, task_id, author_id, datetime.now().isoformat())
            )
            conn.commit()
            comment_id = cursor.lastrowid
            # logger.info(f"Comment created: ID={comment_id}, Task={task_id}, Author={author_id}")
            return comment_id
    
    def get_comments(self, task_id):
        """
        Retrieve all comments for a specific task.
        
        Args:
            task_id (int): Task ID
        
        Returns:
            list: Comment records with author information, newest first
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, 
                       u.userID AS author_userID, 
                       u.username AS author_username, 
                       u.full_name AS author_full_name
                FROM comments c
                JOIN users u ON c.author_id = u.id
                WHERE c.task_id = ?
                ORDER BY c.created_at DESC
            ''', (task_id,))
            comments = cursor.fetchall()
            # logger.info(f"Retrieved {len(comments)} comments for task {task_id}")
            return comments
    
    def get_comment_by_ID(self, comment_id):
        """
        Retrieve a single comment by ID.
        
        Args:
            comment_id (int): Comment ID
        
        Returns:
            dict: Comment record with author details, or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    c.id, c.content, c.created_at, c.task_id, c.author_id,
                    u.id AS author_db_id, 
                    u.userID AS author_userID, 
                    u.username AS author_username, 
                    u.full_name AS author_full_name
                FROM comments c
                JOIN users u ON c.author_id = u.id
                WHERE c.id = ?
            ''', (comment_id,))
            row = cursor.fetchone()
            
            if row:
                # logger.info(f"Comment retrieved: ID={comment_id}")
                return dict(row)
            
            # logger.warning(f"Comment not found: ID={comment_id}")
            return None
    
    def get_comment_with_attachments_by_ID(self, comment_id):
        """
        Retrieve a comment with all its attachments.
        
        Args:
            comment_id (int): Comment ID
        
        Returns:
            dict: Comment record with 'attachments' list, or None if not found
        """
        # Get basic comment info
        comment = self.get_comment_by_ID(comment_id)
        if not comment:
            return None
        
        # Get associated attachments
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, filename, filepath, content_type, created_at
                FROM attachments
                WHERE comment_id = ?
            ''', (comment_id,))
            attachments = cursor.fetchall()
        
        # Add attachments to comment dict
        comment['attachments'] = [dict(att) for att in attachments]
        
        # logger.info(f"Comment with {len(comment['attachments'])} attachments retrieved: ID={comment_id}")
        return comment
    
    def delete_comment(self, comment_id):
        """
        Delete a comment record from database.
        
        Note: Attachments should be deleted separately before calling this.
        
        Args:
            comment_id (int): Comment ID to delete
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
            conn.commit()
            # logger.info(f"Comment deleted: ID={comment_id}")
    
    # ==================================================================
    # Attachment Management
    # ==================================================================
    
    def add_attachment(self, comment_id, filename, filepath, content_type=None):
        """
        Add attachment metadata to database.
        
        The actual file must be stored on filesystem separately.
        This only stores the metadata linking file to comment.
        
        Args:
            comment_id (int): ID of parent comment
            filename (str): Original filename
            filepath (str): Relative path to file in upload directory
            content_type (str, optional): MIME type of file
        
        Returns:
            int: ID of newly created attachment record
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO attachments (filename, filepath, content_type, '
                'created_at, comment_id) VALUES (?, ?, ?, ?, ?)',
                (filename, filepath, content_type, datetime.now().isoformat(), comment_id)
            )
            conn.commit()
            attachment_id = cursor.lastrowid
            # logger.info(f"Attachment created: ID={attachment_id}, File='{filename}', Comment={comment_id}")
            return attachment_id
    
    def get_attachment(self, attachment_id):
        """
        Retrieve a single attachment by ID.
        
        Args:
            attachment_id (int): Attachment ID
        
        Returns:
            sqlite3.Row: Attachment record or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM attachments WHERE id = ?', (attachment_id,))
            attachment = cursor.fetchone()
            
            if attachment:
                # logger.info(f"Attachment retrieved: ID={attachment_id}")
                pass
            else:
                # logger.warning(f"Attachment not found: ID={attachment_id}")
                pass
            
            return attachment
    
    def get_attachments_by_comment(self, comment_id):
        """
        Retrieve all attachments for a specific comment.
        
        Args:
            comment_id (int): Comment ID
        
        Returns:
            list: Attachment records, newest first
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM attachments WHERE comment_id = ? ORDER BY created_at DESC',
                (comment_id,)
            )
            attachments = cursor.fetchall()
            # logger.info(f"Retrieved {len(attachments)} attachments for comment {comment_id}")
            return attachments
    
    def get_attachments_by_task(self, task_id):
        """
        Retrieve all attachments under a task (across all comments).
        
        Args:
            task_id (int): Task ID
        
        Returns:
            list: Attachment records, newest first
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.* 
                FROM attachments a
                JOIN comments c ON a.comment_id = c.id
                WHERE c.task_id = ?
                ORDER BY a.created_at DESC
            ''', (task_id,))
            attachments = cursor.fetchall()
            # logger.info(f"Retrieved {len(attachments)} attachments for task {task_id}")
            return attachments
    
    def delete_attachments_for_comment(self, comment_id):
        """
        Delete all attachment records for a comment.
        
        Note: This only deletes database records.
        Physical files must be deleted separately.
        
        Args:
            comment_id (int): Comment ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM attachments WHERE comment_id = ?', (comment_id,))
            rows_deleted = cursor.rowcount
            conn.commit()
            # logger.info(f"Deleted {rows_deleted} attachment records for comment {comment_id}")
