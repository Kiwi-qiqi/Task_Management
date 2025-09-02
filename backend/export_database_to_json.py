# export_database_to_json.py
import sqlite3
import json
import os
from datetime import datetime

def export_database_to_json(db_path='taskmanager.db', output_dir='database_backup'):
    """
    将 SQLite 数据库中的所有表导出为 JSON 文件
    
    参数:
        db_path (str): SQLite 数据库文件路径
        output_dir (str): 输出 JSON 文件的目录
    """
    
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 连接到 SQLite 数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 这样我们可以通过列名访问数据
    cursor = conn.cursor()
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    
    # 为每个表创建 JSON 文件
    for table in tables:
        # 获取表的所有数据
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        
        # 将行数据转换为字典列表
        data = []
        for row in rows:
            # 处理日期时间字段
            row_dict = {}
            for key in row.keys():
                value = row[key]
                # 如果是日期时间字符串，转换为 ISO 格式
                if isinstance(value, str) and ' ' in value and '-' in value and ':' in value:
                    try:
                        # 尝试解析为日期时间
                        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                        value = dt.isoformat()
                    except ValueError:
                        # 如果解析失败，保持原值
                        pass
                row_dict[key] = value
            data.append(row_dict)
        
        # 写入 JSON 文件
        output_file = os.path.join(output_dir, f"{table}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"表 {table} 已导出到 {output_file}")
    
    # 关闭数据库连接
    conn.close()
    
    # 创建元数据文件
    metadata = {
        "export_date": datetime.now().isoformat(),
        "database": db_path,
        "tables": tables
    }
    
    metadata_file = os.path.join(output_dir, "metadata.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"元数据已保存到 {metadata_file}")
    print("所有表已成功导出为 JSON 文件！")

if __name__ == "__main__":
    export_database_to_json()