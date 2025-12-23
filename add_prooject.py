import sqlite3
from backend.database_op import add_project


def main(cursor, prj_name):
    new_project = {
        'name': prj_name,
    }
    add_project(cursor, new_project)

if __name__ == "__main__":
    # 连接数据库（示例）
    conn = sqlite3.connect('databases/taskmanager.db')
    cursor = conn.cursor()
    
    
    ############################### Add Project #####################################
    
    new_prject_name = "MCT SW Platform" # 仅修改这个参数即可
    main(cursor, new_prject_name)

    #################################################################################
    
    
    # 提交事务
    conn.commit()