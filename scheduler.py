'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 15:43:25
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-03 15:56:55
FilePath: \test\scheduler.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from update_knowledge_graph import update_knowledge_graph
from audit_handler import AuditHandler
import logging

class SchedulerManager:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.audit_handler = AuditHandler()
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            filename='scheduler.log',
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """启动定时任务"""
        try:
            # 每天凌晨2点更新知识图谱
            self.scheduler.add_job(
                update_knowledge_graph,
                CronTrigger(hour=2),
                id='update_kg',
                name='Update Knowledge Graph'
            )
            
            # 每4小时检查一次需要审核的案例
            self.scheduler.add_job(
                self.check_pending_audits,
                CronTrigger(hour='*/4'),
                id='check_audits',
                name='Check Pending Audits'
            )
            
            self.scheduler.start()
            #self.logger.info("定时任务已启动")
        except Exception as e:
            self.logger.error(f"启动定时任务失败: {str(e)}")
    
    def check_pending_audits(self):
        """检查需要审核的案例并发送通知"""
        try:
            pending_cases = self.audit_handler.get_pending_audits()
            if pending_cases:
                self.send_audit_notification(pending_cases)
            #self.logger.info(f"检查到 {len(pending_cases)} 个待审核案例")
        except Exception as e:
            self.logger.error(f"检查待审核案例失败: {str(e)}")
    
    def send_audit_notification(self, pending_cases):
        """发送审核通知（可以通过邮件、企业微信等方式）"""
        # 这里实现具体的通知逻辑
        pass
    
    def stop(self):
        """停止定时任务"""
        self.scheduler.shutdown()
        #self.logger.info("定时任务已停止") 