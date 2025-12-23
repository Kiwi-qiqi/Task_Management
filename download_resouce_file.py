import requests
import os

def download_file(url, save_path):
    """
    从URL下载文件
    
    参数:
    - url: 文件的URL地址
    - save_path: 保存的本地路径
    """
    try:
        print(f"正在下载: {url}")
        
        # 发送GET请求
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # 检查请求是否成功
        
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 保存文件
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ 下载完成！文件已保存到: {save_path}")
        print(f"  文件大小: {len(response.content) / 1024:.2f} KB")
        
    except requests.exceptions.RequestException as e:
        print(f"✗ 下载失败: {e}")


import requests
import os
from pathlib import Path

def download_file(url, save_path):
    """下载单个文件"""
    try:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        return True, len(response.content)
    except Exception as e:
        return False, str(e)


def download_all_dependencies():
    """下载所有前端依赖"""
    
    files_to_download = {
        # Bootstrap CSS
        "static/css/bootstrap.min.css": 
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
        
        # Bootstrap JS
        "static/js/bootstrap.bundle.min.js": 
            "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js",
        
        # Bootstrap Icons CSS
        "static/css/bootstrap-icons.css": 
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css",
        
        # Bootstrap Icons 字体文件
        "static/css/fonts/bootstrap-icons.woff2": 
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff2",
        
        "static/css/fonts/bootstrap-icons.woff": 
            "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/fonts/bootstrap-icons.woff",
        
        # Font Awesome CSS
        "static/css/all.min.css": 
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
        
        # Font Awesome 字体文件（主要的几个）
        "static/webfonts/fa-solid-900.woff2": 
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2",
        
        "static/webfonts/fa-regular-400.woff2": 
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2",
        
        "static/webfonts/fa-brands-400.woff2": 
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2",
    }
    
    print("开始下载前端依赖文件...")
    print("="*60)
    
    success_count = 0
    fail_count = 0
    total_size = 0
    
    for save_path, url in files_to_download.items():
        filename = os.path.basename(save_path)
        print(f"\n下载: {filename}")
        print(f"  URL: {url}")
        
        success, result = download_file(url, save_path)
        
        if success:
            size_kb = result / 1024
            total_size += result
            print(f"  ✓ 成功 - {save_path} ({size_kb:.2f} KB)")
            success_count += 1
        else:
            print(f"  ✗ 失败 - {result}")
            fail_count += 1
    
    print("\n" + "="*60)
    print(f"下载完成！")
    print(f"  成功: {success_count} 个文件")
    print(f"  失败: {fail_count} 个文件")
    print(f"  总大小: {total_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    download_all_dependencies()


# # 使用示例
# if __name__ == "__main__":
    
#     url = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css"
#     save_path = "static/css/bootstrap-icons.css"
    
#     download_file(url, save_path)
