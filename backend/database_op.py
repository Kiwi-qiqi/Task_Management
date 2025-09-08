# ================= 用户管理函数 =================
def add_user(cursor, user_data):
    """
    添加新成员
    user_data: 字典格式 {
        'userID': str, 'username': str, 'email': str, 'password_hash': str,
        'role': str, 'full_name': str, 'site': str, 'competency': str, 
        'title': str, 'mobile': str
    }
    """
    query = '''
    INSERT INTO users (
        userID, username, email, password_hash, role, full_name, 
        site, competency, title, mobile
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        user_data['userID'], user_data['username'], user_data['email'],
        user_data['password_hash'], user_data['role'], user_data['full_name'],
        user_data['site'], user_data['competency'], user_data['title'],
        user_data['mobile']
    )
    cursor.execute(query, params)
    return cursor.lastrowid

def delete_user(cursor, user_identifier, by='userID'):
    """
    删除成员
    user_identifier: 用户唯一标识 (userID 或 username)
    by: 指定标识类型 'userID'(默认) 或 'username'
    """
    if by not in ['userID', 'username']:
        raise ValueError("Identifier must be 'userID' or 'username'")
    
    query = f"DELETE FROM users WHERE {by} = ?"
    cursor.execute(query, (user_identifier,))
    return cursor.rowcount


# ================= 类别管理函数 =================
def add_category(cursor, category_data):
    """
    添加新类别
    category_data: 字典格式 {
        'name': str, 'type': str, 
        'description': str (可选), 'status': str (可选)
    }
    """
    query = '''
    INSERT INTO categories (name, type, description, status)
    VALUES (?, ?, ?, ?)
    '''
    params = (
        category_data['name'],
        category_data['type'],
        category_data.get('description', None),
        category_data.get('status', 'active')
    )
    cursor.execute(query, params)
    return cursor.lastrowid

def delete_category(cursor, category_name):
    """删除指定名称的类别"""
    query = "DELETE FROM categories WHERE name = ?"
    cursor.execute(query, (category_name,))
    return cursor.rowcount

def update_category(cursor, category_name, update_data):
    """
    修改类别信息
    category_name: 要修改的类别名称
    update_data: 包含更新字段的字典 (可包含: 'name', 'type', 'description', 'status')
    """
    set_clauses = []
    params = []
    
    for field in ['name', 'type', 'description', 'status']:
        if field in update_data:
            set_clauses.append(f"{field} = ?")
            params.append(update_data[field])
    
    if not set_clauses:
        return 0  # 无更新字段
    
    params.append(category_name)
    query = f"UPDATE categories SET {', '.join(set_clauses)} WHERE name = ?"
    cursor.execute(query, tuple(params))
    return cursor.rowcount


# ================= 项目管理函数 =================
def add_project(cursor, project_data):
    """
    添加新项目
    project_data: 字典格式 {
        'name': str, 
        'description': str (可选),
        'status': str (可选, 默认'planning'),
        'start_date': datetime (可选),
        'end_date': datetime (可选),
        'main_rd': str (可选),
        'supplier': str (可选),
        'category_id': int
    }
    """
    query = '''
    INSERT INTO projects (
        name, description, status, start_date, end_date, 
        main_rd, supplier, category_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    params = (
        project_data['name'],
        project_data.get('description', None),
        project_data.get('status', 'planning'),
        project_data.get('start_date', None),
        project_data.get('end_date', None),
        project_data.get('main_rd', None),
        project_data.get('supplier', None),
        project_data['category_id']
    )
    cursor.execute(query, params)
    return cursor.lastrowid

def delete_project(cursor, project_name):
    """删除指定名称的项目"""
    query = "DELETE FROM projects WHERE name = ?"
    cursor.execute(query, (project_name,))
    return cursor.rowcount

def update_project(cursor, project_name, update_data):
    """
    修改项目信息
    project_name: 要修改的项目名称
    update_data: 包含更新字段的字典 (可包含: 'name', 'description', 'status', 
                'start_date', 'end_date', 'main_rd', 'supplier', 'category_id')
    """
    allowed_fields = [
        'name', 'description', 'status', 'start_date', 
        'end_date', 'main_rd', 'supplier', 'category_id'
    ]
    set_clauses = []
    params = []
    
    for field in allowed_fields:
        if field in update_data:
            set_clauses.append(f"{field} = ?")
            params.append(update_data[field])
    
    if not set_clauses:
        return 0  # 无更新字段
    
    params.append(project_name)
    query = f"UPDATE projects SET {', '.join(set_clauses)} WHERE name = ?"
    cursor.execute(query, tuple(params))
    return cursor.rowcount


# ================ Example ==================
def users_operations(cursor):
    # 1. 用户管理示例
    # 添加用户
    new_user = {
        'userID'       : 'M0123456',
        'username'     : 'admin',
        'email'        : 'admin@example.com',
        'password_hash': 'Mahle123456',
        'role'         : 'admin',
        'full_name'    : 'System Administrator',
        'site'         : 'MATS',
        'competency'   : 'System Management',
        'title'        : 'System Administrator',
        'mobile'       : '00000000000'
    }
    add_user(cursor, new_user)

    # 删除用户
    delete_user(cursor, 'M0123456')  # 按userID删除
    delete_user(cursor, 'admin', by='username')  # 按username删除


def category_opeations(cursor):
    # 2. 类别管理示例
    # 添加类别
    new_category = {
        'name': 'Compressor',
        'type': 'product',
        'description': 'Electric Compressor'
    }
    add_category(cursor, new_category)

    # 更新类别
    update_category(cursor, 'Main Task', {
        'name': 'Main Task',
        'status': 'inactive'
    })

    # 删除类别
    delete_category(cursor, 'Main Task')


def project_operations(cursor):
    # 3. 项目管理示例
    # 添加项目
    new_project = {
        'name'       : 'Honda 28M_800V_45CC',
        'category_id': 5,
        'description': 'Honda Electric Compressor Project',
        'status'     : 'planning',
    }
    add_project(cursor, new_project)

    # 更新项目
    update_project(cursor, 'Honda 28M_800V_45CC', {
        'name': 'Honda 28M_800V_45CC New',
        'status': 'delayed'
    })

    # 删除项目
    delete_project(cursor, 'Honda 28M_800V_45CC')



if __name__ == "__main__":
    # 连接数据库（示例）
    import sqlite3
    conn = sqlite3.connect('databases/taskmanager.db')
    cursor = conn.cursor()

    

    # 提交事务
    conn.commit()