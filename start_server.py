from waitress import serve
from app import app  # 导入您的 Flask 应用实例

if __name__ == "__main__":
    # 监听所有网络接口，端口 5000
    serve(app, host='0.0.0.0', port=5000)