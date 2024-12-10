'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 14:12:58
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-05 21:26:16
FilePath: \test\case_data_handler.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import pandas as pd
import logging

logger = logging.getLogger(__name__)

import chardet

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read()
        result = chardet.detect(raw_data)
        return result['encoding']

class CaseDataHandler:
    def __init__(self):
        self.df = pd.read_csv('cases.csv', encoding=detect_encoding('cases.csv'))
        #logger.info("CaseDataHandler initialized")

    def get_case_info(self, case_id):
        try:
            case = self.df[self.df['案例编号'] == case_id].iloc[0]
            return {
                'status': 'success',
                'customer_name': case['客户名称'],
                'contact_person': case['联系人'],
                'contact_phone': case['联系电话'],
                'project_subject': case['案例标题'],
                'system_version': case['系统版本'],
                'project_owner': case['case_owner'],
                'project_scale': case['案例进度']
            }
        except Exception as e:
            logger.error(f"Error getting case info: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def get_case_emails(self, case_id):
        try:
            case = self.df[self.df['案例编号'] == case_id].iloc[0]
            return case['案例详情']
        except Exception as e:
            logger.error(f"Error getting case emails: {str(e)}")
            return None
    
    def get_case_description(self, case_id):
        """Retrieve the case description from the CSV file."""
        try:
            case = self.df[self.df['案例编号'] == case_id].iloc[0]
            return case['案例定义']
        except Exception as e:
            logger.error(f"Error getting case description: {str(e)}")
            return None