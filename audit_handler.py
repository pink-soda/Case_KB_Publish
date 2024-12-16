'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 15:43:14
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-13 15:41:26
FilePath: \Case_KB\audit_handler.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from mongo_handler import MongoHandler
from datetime import datetime
import logging
import math

class AuditHandler:
    def __init__(self):
        self.mongo = MongoHandler()
        
    def get_pending_audits(self, confidence_threshold=0.8):
        """获取需要人工审核的分类结果"""
        try:
            logging.info("开始获取待审核案例")
            
            # 构建查询条件
            query = {
                '$or': [
                    {'case_score': {'$lt': confidence_threshold}},
                    {'case_review': {'$in': ['待审核', 'pending']}},
                    {'category': {'$exists': False}},
                    {'category': {'$size': 0}},
                    {'category': None},
                    {'category': []}
                ]
            }
            
            logging.info(f"查询条件: {query}")
            
            # 执行查询并转换为列表
            pending_cases = list(self.mongo.cases.find(query))
            
            # 处理数据，确保JSON可序列化
            for case in pending_cases:
                if '_id' in case:
                    case['_id'] = str(case['_id'])
                
                # 处理必要字段
                case['case_id'] = case.get('case_id', str(case['_id']))
                case['category'] = case.get('category', [])
                
                # 处理 case_score，将 NaN 转换为 None
                case_score = case.get('case_score')
                if case_score is None or (isinstance(case_score, float) and math.isnan(case_score)):
                    case['case_score'] = None
                
                case['case_review'] = case.get('case_review', '待审核')
            
            logging.info(f"找到 {len(pending_cases)} 个待审核案例")
            if pending_cases:
                logging.info(f"第一个待审核案例示例: {pending_cases[0]}")
            else:
                logging.info("没有找到任何待审核案例")
                # 输出一个样本案例，看看数据结构
                sample = self.mongo.cases.find_one()
                if sample:
                    logging.info(f"数据库中的样本案例结构: {sample}")
            
            return pending_cases
            
        except Exception as e:
            logging.error(f"获取待审核案例失败: {str(e)}")
            logging.exception("详细错误信息：")
            return []
    
    def audit_case(self, case_id, audit_result):
        """审核案例分类结果"""
        try:
            update_data = {
                'audit_status': 'completed',
                'audit_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'category': audit_result['category'],
                'case_comment': audit_result.get('comment', ''),
                'auditor': audit_result.get('auditor', 'unknown')
            }
            
            result = self.mongo.cases.update_one(
                {'case_id': case_id},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logging.error(f"审核案例失败: {str(e)}")
            return False 