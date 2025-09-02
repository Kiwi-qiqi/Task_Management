import sqlite3
from datetime import datetime, timedelta
import random

# 修正数据库连接字符串
conn = sqlite3.connect('databases/taskmanager.db')
cursor = conn.cursor()

projects = [
    (1, 'Honda 28M_800V_45CC', 'Honda Electric Compressor Project', 'planning', None, None, '2025-08-28T10:54:29', 'Outsourced', 'HET', 1),
    (2, 'Platform_400V_36CC', 'Platform 400V Compressor Project', 'planning', None, None, '2025-08-28T10:54:29', 'Outsourced', 'FristWise', 1),
    (3, 'Platform_800V_45CC', 'Platform 800V Compressor Project', 'planning', None, None, '2025-08-28T10:54:29', 'Outsourced', 'FeiYang', 1),
    (4, 'STELLANTIS_400V_45CC', 'STELLANTIS Compressor Project', 'planning', None, None, '2025-08-28T10:54:29', 'TBD', '', 1),
    (5, 'VW_800V_45CC', 'VW Compressor Project', 'planning', None, None, '2025-08-28T10:54:29', 'Internal', '', 1),
    (6, 'HD20_800V_57CC', 'HD20 Compressor Project', 'planning', None, None, '2025-08-28T10:54:29', 'Internal', '', 1),
    (7, 'Platform_Ti', 'Platform Ti Compressor Project', 'planning', None, None, '2025-08-28T10:54:29', 'Internal', '', 1),
    (8, 'HR18', 'HR18 Cooling Pump Project', 'planning', None, None, '2025-08-28T10:54:29', 'Internal', '', 2),
    (9, 'XCSP', 'XCSP Cooling Pump Project', 'planning', None, None, '2025-08-28T10:54:29', 'Internal', '', 2),
    (10, 'Platform_800V_2IN1_7kw', 'Platform 800V OBC&DCLV Project', 'planning', None, None, '2025-08-28T10:54:29', '', '', 4),
    (11, 'Platform_48V_DCLV_5kw', 'Platform 48V DCLV Project', 'planning', None, None, '2025-08-28T10:54:29', '', '', 4),
    (12, 'MMC_400V_3IN1_11kw', 'MMC 400V OBC&DCLV Project', 'planning', None, None, '2025-08-28T10:54:29', '', '', 4),
    (13, 'Bootloader', 'Bootloader Project', 'planning', None, None, '2025-08-28T10:54:29', '', '', 5),
    (14, 'Functional Safety', 'Functional Safety Project', 'planning', None, None, '2025-08-28T10:54:29', '', '', 6),
    (15, 'CyberSecurity', 'Cyber Security Project', 'planning', None, None, '2025-08-28T10:54:29', '', '', 7),
    (16, 'Toolchain', 'Toolchain Project', 'planning', None, None, '2025-08-28T10:54:29', '', '', 8),
    (17, 'Main Task', 'Main Task Project', 'planning', None, None, '2025-08-28T10:54:29', '', '', 9)
]

# 任务类型选项
task_types = ['development', 'testing', 'documentation', 'design', 'review', 'meeting', 'bugfix', 'research']
task_statuses = ['todo', 'in_progress', 'review', 'done']
priorities = ['low', 'medium', 'high']
severities = ['trivial', 'minor', 'major', 'critical', 'blocker']

# 任务标题模板
task_titles = [
    "Implement {} module",
    "Write test cases for {}",
    "Design {} architecture",
    "Review {} code",
    "Fix bugs in {}",
    "Optimize {} performance",
    "Create documentation for {}",
    "Research {} technologies",
    "Prepare {} presentation",
    "Coordinate {} integration"
]

# 任务描述模板
task_descriptions = [
    "This task involves working on the {} component of the project.",
    "Need to complete the {} functionality as per requirements.",
    "The task focuses on improving the {} aspect of the system.",
    "This is a critical task for the {} feature delivery.",
    "Work on {} needs to be completed by the due date.",
    "The {} module requires additional development and testing.",
    "This task is part of the {} milestone deliverables."
]

# 评论内容模板
comments_content = [
    "Good progress on this task. Keep it up!",
    "Please provide more details on the implementation approach.",
    "I've reviewed the code and have some suggestions for improvement.",
    "This task is blocked by dependency on another module.",
    "The testing phase revealed some issues that need to be addressed.",
    "Documentation needs to be updated to reflect the latest changes.",
    "This is a high priority item that requires immediate attention.",
    "The implementation looks good and meets all requirements.",
    "Need clarification on the requirements before proceeding.",
    "This task is completed and ready for review.",
    "Found a potential performance issue that needs optimization.",
    "The design approach needs to be discussed with the team.",
    "Additional resources might be needed to complete this on time.",
    "This task is related to the recent change request #{}.",
    "The customer has provided feedback that affects this task."
]

# 生成50个任务
tasks = []
for i in range(1, 51):
    project_id = random.randint(1, 17)
    assignee_id = random.randint(2, 14)  # 排除admin用户
    task_type = random.choice(task_types)
    status = random.choice(task_statuses)
    priority = random.choice(priorities)
    severity = random.choice(severities)
    
    # 生成任务标题和描述
    project_name = projects[project_id-1][1]
    title_template = random.choice(task_titles)
    title = title_template.format(project_name)
    
    desc_template = random.choice(task_descriptions)
    description = desc_template.format(project_name)
    
    # 生成日期
    created_at = datetime(2025, 1, 1) + timedelta(days=random.randint(0, 240))
    start_date = created_at + timedelta(days=random.randint(0, 5))
    
    if status == 'done':
        due_date = start_date + timedelta(days=random.randint(1, 30))
        updated_at = due_date + timedelta(days=random.randint(0, 5))
    else:
        due_date = start_date + timedelta(days=random.randint(5, 60))
        updated_at = created_at + timedelta(days=random.randint(1, (due_date - created_at).days))
    
    tasks.append((
        title, description, task_type, status, priority, severity,
        start_date.strftime('%Y-%m-%d %H:%M:%S'),
        due_date.strftime('%Y-%m-%d %H:%M:%S'),
        created_at.strftime('%Y-%m-%d %H:%M:%S'),
        updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        assignee_id, project_id
    ))

# 插入任务时不指定ID，让数据库自动生成
cursor.executemany('''
INSERT INTO tasks (title, description, type, status, priority, severity, start_date, due_date, created_at, updated_at, assignee_id, project_id)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', tasks)

# 获取最后插入的任务ID
cursor.execute("SELECT last_insert_rowid()")
last_id = cursor.fetchone()[0]
first_task_id = last_id - len(tasks) + 1

# 为任务生成评论
comments = []
for task_index in range(len(tasks)):
    task_id = first_task_id + task_index
    
    # 每个任务有1-4条评论
    for _ in range(random.randint(1, 4)):
        author_id = random.randint(2, 14)  # 排除admin用户
        content = random.choice(comments_content)
        if "{}" in content:
            content = content.format(random.randint(100, 999))
        
        # 评论时间在任务创建时间和更新时间之间
        task_created = datetime.strptime(tasks[task_index][7], '%Y-%m-%d %H:%M:%S')
        task_updated = datetime.strptime(tasks[task_index][8], '%Y-%m-%d %H:%M:%S')
        
        time_diff = (task_updated - task_created).days
        comment_date = task_created + timedelta(days=random.randint(0, time_diff if time_diff > 0 else 1))
        
        comments.append((
            content, comment_date.strftime('%Y-%m-%d %H:%M:%S'), task_id, author_id
        ))

cursor.executemany('''
INSERT INTO comments (content, created_at, task_id, author_id)
VALUES (?, ?, ?, ?)
''', comments)

# 提交更改
conn.commit()

print(f"成功插入 {len(tasks)} 个任务和 {len(comments)} 条评论")

# 关闭连接
conn.close()