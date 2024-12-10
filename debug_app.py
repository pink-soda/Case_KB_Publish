import sys
import traceback

def debug_flask_app():
    try:
        from app import app
        print("Flask应用导入成功")
        
        # 检查必要的包
        required_packages = [
            'flask',
            'flask_cors',
            'pymongo',
            'py2neo',
            'python-dotenv',
            'openai',
            'apscheduler',
            'pandas'
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"✓ {package} 导入成功")
            except ImportError as e:
                print(f"✗ {package} 导入失败: {str(e)}")
        
        # 尝试启动应用
        print("\n正在启动Flask应用...")
        app.run(debug=True)
        
    except Exception as e:
        print("\n=== 错误详情 ===")
        print(f"错误类型: {type(e)}")
        print(f"错误信息: {str(e)}")
        print("\n=== 完整堆栈跟踪 ===")
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = debug_flask_app()
    if exit_code != 0:
        print("\n应用启动失败，请检查上述错误信息")
    sys.exit(exit_code) 