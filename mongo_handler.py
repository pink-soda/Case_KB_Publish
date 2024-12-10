'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 14:27:30
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-05 14:51:38
FilePath: \test\mongo_handler.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from pymongo import MongoClient
import logging
import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class MongoHandler:
    def __init__(self):
        # 连接MongoDB
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['cases_db']
        self.cases = self.db['cases']
        #logger.info("MongoHandler initialized")
        
    def get_case_list(self, case_ids):
        """获取案例列表信息"""
        try:
            cases = []
            for case_id in case_ids:
                case = self.cases.find_one({'case_id': case_id})
                if case:
                    cases.append({
                        'case_id': case['case_id'],
                        'summary': case['summary']
                    })
            return cases
        except Exception as e:
            raise Exception(f"获取案例列表失败: {str(e)}")
            
    def get_case_details(self, case_id):
        """获取单个案例的详细信息"""
        try:
            case = self.cases.find_one({'case_id': case_id})
            if not case:
                logger.warning(f"Case not found: {case_id}")
                return None
            return case
        except Exception as e:
            logger.error(f"Error getting case details: {str(e)}")
            return None
    def search_cases_by_tags(self, tags):
        try:
            # 按置信度降序排序标签
            sorted_tags = sorted(tags, key=lambda x: x['confidence'], reverse=True)
            
            # 构建查询条件
            query = {'$or': [{'tags.classification': tag['classification']} 
                           for tag in sorted_tags]}
            
            return list(self.cases.find(query))
        except Exception as e:
            logger.error(f"Error searching cases: {str(e)}")
            return []
    '''
    def insert_case(self, case_data):
        """插入新案例"""
        try:
            case_document = {
                'case_id': case_data['案例编号'],
                'summary': case_data['案例总结'],
                'details': {
                    'title': case_data.get('案例标题', ''),
                    'description': case_data.get('案例描述', ''),
                    #'date': case_data.get('date'),
                    'status': case_data.get('status', '案例进度'),
                    'category': case_data.get('所属类别', '')
                    #'tags': case_data.get('tags', []),
                    #'attachments': case_data.get('attachments', []),
                    #'related_cases': case_data.get('related_cases', [])
                },
                'metadata': {
                    'created_at': datetime.datetime.utcnow(),
                    'updated_at': datetime.datetime.utcnow(),
                    'created_by': case_data.get('case_owner'),
                    'last_modified_by': case_data.get('case_owner')
                }
            }
            result = self.cases.insert_one(case_document)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error inserting case: {str(e)}")
            raise
    '''
    def get_all_cases(self):
        """获取所有案例"""
        try:
            cases = self.db.cases.find({})
            return list(cases)
        except Exception as e:
            logger.error(f"获取案例失败: {str(e)}")
            return []

    def get_cases_count(self):
        """获取案例总数"""
        try:
            return self.db.cases.count_documents({})
        except Exception as e:
            logger.error(f"获取案例数量失败: {str(e)}")
            return 0

    def bulk_insert_cases(self, cases):
        """批量插入案例"""
        try:
            result = self.db.cases.insert_many(cases)
            return len(result.inserted_ids)
        except Exception as e:
            logger.error(f"批量插入案例失败: {str(e)}")
            return 0
