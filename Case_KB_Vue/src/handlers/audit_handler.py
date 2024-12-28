'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 15:43:14
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-19 16:08:18
FilePath: \Case_KB\audit_handler.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from mongo_handler import MongoHandler
from datetime import datetime
import logging
import math
import json

logger = logging.getLogger(__name__)

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
    
    def get_completed_audits(self):
        """获取已审核案例"""
        try:
            query = {
                'case_review': 'completed'
            }
            completed_cases = list(self.mongo.cases.find(query))
            
            # 处理数据
            for case in completed_cases:
                if '_id' in case:
                    case['_id'] = str(case['_id'])
                case['case_id'] = case.get('case_id', str(case['_id']))
                case['category'] = case.get('category', [])
                case['audit_comment'] = case.get('case_comment', '')
                
            return completed_cases
        except Exception as e:
            logger.error(f"获取已审核案例失败: {str(e)}")
            return []
    
    def audit_case(self, case_id, audit_result):
        """审核案例分类结果"""
        try:
            # 1. 更新 MongoDB - 添加100%的置信度得分
            update_data = {
                'case_review': 'completed',
                'audit_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'category': audit_result['category'],
                'case_comment': audit_result.get('comment', ''),
                'auditor': audit_result.get('auditor', 'unknown'),
                'case_score': '1.0'  # 修改为字符串格式
            }
            
            result = self.mongo.cases.update_one(
                {'case_id': case_id},
                {'$set': update_data}
            )

            if result.modified_count == 0:
                return False

            # 2. 更新 classified_cases.json - 添加置信度得分
            try:
                with open('classified_cases.json', 'r', encoding='utf-8') as f:
                    cases = json.load(f)
                
                for case in cases:
                    if case.get('file_path', '').endswith(f'{case_id}.pdf'):
                        case['classification'] = {
                            'level1': audit_result['category'][0],
                            'level2': audit_result['category'][1],
                            'level3': audit_result['category'][2]
                        }
                        case['category_score'] = {  # JSON文件中保持对象格式
                            'level1': 1.0,
                            'level2': 1.0,
                            'level3': 1.0
                        }
                        break
                
                with open('classified_cases.json', 'w', encoding='utf-8') as f:
                    json.dump(cases, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"更新 classified_cases.json 失败: {str(e)}")
                return False

            # 3. 更新 category_hierarchy.json
            if audit_result.get('has_new_category'):
                try:
                    with open('category_hierarchy.json', 'r', encoding='utf-8') as f:
                        hierarchy = json.load(f)
                    
                    level1, level2, level3 = audit_result['category']
                    
                    if level1 not in hierarchy:
                        hierarchy[level1] = {}
                    if level2 not in hierarchy[level1]:
                        hierarchy[level1][level2] = []
                    if level3 not in hierarchy[level1][level2]:
                        hierarchy[level1][level2].append(level3)
                    
                    with open('category_hierarchy.json', 'w', encoding='utf-8') as f:
                        json.dump(hierarchy, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.error(f"更新 category_hierarchy.json 失败: {str(e)}")
                    return False

            # 4. 更新 Neo4j 图谱
            from knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            if not kg.ensure_category_hierarchy(audit_result['category']):
                logger.error("更新 Neo4j 图谱失败")
                return False

            return True
            
        except Exception as e:
            logger.error(f"审核案例失败: {str(e)}")
            return False 