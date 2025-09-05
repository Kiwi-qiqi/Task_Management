import sqlite3

def update_user_info(user_identifier, update_fields):
    """
    根据userID或username更新用户信息
    
    参数:
    user_identifier: 字典，包含用于识别用户的字段 (userID 或 username)
    update_fields: 字典，包含要更新的字段及其新值
    
    示例调用:
    update_user_info(
        {'username': 'john_doe'}, 
        {'email': 'new_email@example.com', 'role': 'admin'}
    )
    """
    conn = sqlite3.connect('databases/taskmanager.db')
    cursor = conn.cursor()
    
    try:
        # 确定使用哪个字段作为条件 (优先使用userID)
        if 'userID' in user_identifier:
            condition = "userID = :id_value"
            params = {'id_value': user_identifier['userID']}
        elif 'username' in user_identifier:
            condition = "username = :name_value"
            params = {'name_value': user_identifier['username']}
        else:
            return "错误：必须提供userID或username作为识别条件"
        
        # 构建SET子句
        set_clause = ", ".join([f"{k} = :{k}" for k in update_fields.keys()])
        
        # 合并参数
        params.update(update_fields)
        
        # 执行更新
        query = f"UPDATE users SET {set_clause} WHERE {condition}"
        cursor.execute(query, params)
        conn.commit()
        
        return "用户信息更新成功"
        
    except sqlite3.Error as e:
        return f"数据库错误: {str(e)}"
    finally:
        conn.close()
        
if __name__ == "__main__":
    result = update_user_info(
        {'userID': 'M0144096'},
        {'title': 'System Administrator'}
    )
    print(result)  # 输出: 用户信息更新成功