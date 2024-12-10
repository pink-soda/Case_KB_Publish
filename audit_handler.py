from mongo_handler import MongoHandler
from datetime import datetime

class AuditHandler:
    def __init__(self):
        self.mongo = MongoHandler()
        
    def get_pending_audits(self, confidence_threshold=0.8):
        """获取需要人工审核的分类结果"""
        try:
            # 获取置信度低于阈值或标记为需要审核的案例
            pending_cases = self.mongo.cases.find({
                '$or': [
                    {'category.confidence': {'$lt': confidence_threshold}},
                    {'audit_status': 'pending'}
                ]
            })
            return list(pending_cases)
        except Exception as e:
            print(f"获取待审核案例失败: {str(e)}")
            return []
    
    def audit_case(self, case_id, audit_result):
        """审核案例分类结果"""
        try:
            update_data = {
                'audit_status': 'completed',
                'audit_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'category': audit_result['category'],
                'audit_comment': audit_result.get('comment', ''),
                'auditor': audit_result.get('auditor', 'unknown')
            }
            
            self.mongo.cases.update_one(
                {'case_id': case_id},
                {'$set': update_data}
            )
            return True
        except Exception as e:
            print(f"审核案例失败: {str(e)}")
            return False 