'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 17:15:16
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-09 16:00:47
FilePath: \test\test_connections.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from mongo_handler import MongoHandler
from knowledge_graph import KnowledgeGraph
from dotenv import load_dotenv
import os

def test_connections():
    # 加载环境变量
    load_dotenv()
    
    print("=== 测试连接 ===")
    
    # 测试MongoDB
    try:
        mongo = MongoHandler()
        mongo.cases.find_one()
        print("✓ MongoDB连接成功")
    except Exception as e:
        print(f"✗ MongoDB连接失败: {str(e)}")
    
    # 测试Neo4j
    try:
        kg = KnowledgeGraph()
        if not kg.verify_data():
            raise Exception("知识图谱数据库验证失败，请检查数据")
        kg.get_category_hierarchy()
        print("✓ Neo4j连接成功")
    except Exception as e:
        print(f"✗ Neo4j连接失败: {str(e)}")
    
    # 检查环境变量
    print("\n=== 环境变量检查 ===")
    env_vars = [
        'MODEL_NAME',
        'AZURE_OPENAI_API_KEY_2',
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_VERSION'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var} 已设置")
        else:
            print(f"✗ {var} 未设置")

if __name__ == "__main__":
    test_connections() 