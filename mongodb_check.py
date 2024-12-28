'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-13 15:44:39
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-13 15:45:57
FilePath: \Case_KB\mongodb_check.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from mongo_handler import MongoHandler

def check_database():
    mongo = MongoHandler()
    
    # 检查总案例数
    total_count = mongo.cases.count_documents({})
    print(f"数据库中总案例数: {total_count}")
    
    # 检查案例结构
    sample = mongo.cases.find_one()
    print(f"样本案例结构: {sample}")
    
    # 检查待审核案例
    pending = mongo.cases.find({
        '$or': [
            {'case_score': {'$lt': 0.8}},
            {'case_review': {'$in': ['待审核', 'pending']}},
            {'category': {'$exists': False}},
            {'category': {'$size': 0}},
            {'category': None}
        ]
    })
    
    print(f"待审核案例数: {len(list(pending))}")

# 运行检查
check_database()